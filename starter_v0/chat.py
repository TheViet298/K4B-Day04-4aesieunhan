from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

def load_backend():
    """Load lab dependencies only for real CLI chat; demo UI needs no API."""
    global make_provider, ToolCall, TOOL_FUNCTIONS
    global load_tool_declarations, to_openai_tools
    global artifact_version_dict, build_artifact_version
    from env_loader import load_lab_env
    from providers import make_provider
    from providers.base import ToolCall
    from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
    from versioning import artifact_version_dict, build_artifact_version
    load_lab_env(ROOT)


ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "run"


def json_text(value: Any, *, max_chars: int | None = None) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars] + "\n...<truncated>"
    return text


def trim_history(history: list[dict[str, str]], window: int) -> list[dict[str, str]]:
    if window <= 0:
        return []
    return history[-window * 2:]


def execute_tool_call(call: ToolCall) -> dict[str, Any]:
    func = TOOL_FUNCTIONS.get(call.name)
    if not func:
        return {
            "tool": call.name,
            "args": call.args,
            "result": {"error": "unknown_tool", "message": f"No local implementation for {call.name}"},
        }
    try:
        result = func(**call.args)
    except Exception as exc:
        result = {"error": type(exc).__name__, "message": str(exc)}
    return {"tool": call.name, "args": call.args, "result": result}


def tool_results_message(events: list[dict[str, Any]]) -> dict[str, str]:
    return {
        "role": "user",
        "content": (
            "TOOL_RESULTS_JSON:\n"
            f"{json_text(events, max_chars=24000)}\n\n"
            "Use only these tool results. If the user asked for an incident report and the findings are ready, "
            "call the reporting tool. Otherwise answer directly, state uncertainty, and give the safest next step."
        ),
    }


def assistant_tool_message(
    response_text: str | None,
    calls: list[ToolCall],
) -> dict[str, str]:
    tool_names = ", ".join(call.name for call in calls)
    return {
        "role": "assistant",
        "content": (
            f"I requested these tools: {tool_names}. "
            "Their execution results follow."
        ),
    }


def run_model_tool_loop(
    *,
    provider: Any,
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]],
    model: str | None,
    max_tool_rounds: int,
) -> dict[str, Any]:
    working_messages = list(messages)
    rounds: list[dict[str, Any]] = []
    all_tool_events: list[dict[str, Any]] = []

    for round_index in range(1, max_tool_rounds + 1):
        response = provider.complete(working_messages, tools, model=model, temperature=0.0)
        calls = response.tool_calls
        round_record: dict[str, Any] = {
            "round": round_index,
            "assistant_text": response.text,
            "tool_calls": [{"name": call.name, "args": call.args} for call in calls],
            "tool_results": [],
        }

        if not calls:
            rounds.append(round_record)
            return {
                "status": "answered",
                "assistant_text": response.text or "",
                "rounds": rounds,
                "tool_events": all_tool_events,
            }

        working_messages.append(assistant_tool_message(response.text, calls))
        non_clarification_events: list[dict[str, Any]] = []

        for call in calls:
            print(f"[tool] {call.name}({json.dumps(call.args, ensure_ascii=False, sort_keys=True)})")
            event = execute_tool_call(call)
            print(f"[result] {json_text(event['result'])}")
            round_record["tool_results"].append(event)
            all_tool_events.append(event)

            # Detect the clarification/pause tool by its output flag (rename-proof),
            # not by a hard-coded tool name.
            result = event.get("result", {})
            if isinstance(result, dict) and result.get("awaiting_user"):
                question = result.get("question") or call.args.get("question") or "Bạn bổ sung thêm thông tin nhé."
                rounds.append(round_record)
                return {
                    "status": "waiting_for_user",
                    "assistant_text": question,
                    "rounds": rounds,
                    "tool_events": all_tool_events,
                }

            non_clarification_events.append(event)

        rounds.append(round_record)
        working_messages.append(tool_results_message(non_clarification_events))

    return {
        "status": "max_tool_rounds",
        "assistant_text": f"Stopped after {max_tool_rounds} tool rounds. Inspect the transcript for details.",
        "rounds": rounds,
        "tool_events": all_tool_events,
    }


def write_transcript(path: Path, transcript: dict[str, Any]) -> None:
    transcript["updated_at"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive IT Helpdesk Agent chat with transcript logging.")
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "gemini"], required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--version", required=True, help="Student-chosen artifact version label, e.g. v0, v1, v2.")
    parser.add_argument("--system-prompt", type=Path, default=ARTIFACTS_DIR / "system_prompt.md")
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    parser.add_argument("--transcripts-dir", type=Path, default=ROOT / "transcripts")
    parser.add_argument("--history-window", type=int, default=5, help="Keep the last N user/assistant pairs in context.")
    parser.add_argument("--max-tool-rounds", type=int, default=4)
    args = parser.parse_args()
    load_backend()

    system_prompt = args.system_prompt.read_text(encoding="utf-8")
    tool_declarations = load_tool_declarations(args.tools)
    openai_tools = to_openai_tools(tool_declarations)
    provider = make_provider(args.provider)
    selected_model = args.model or getattr(provider, "default_model", None)
    artifact_version = build_artifact_version(args.version, args.system_prompt, args.tools)

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    transcript_id = "_".join([
        safe_slug(args.version),
        safe_slug(args.provider),
        timestamp,
    ])
    transcript_path = args.transcripts_dir / f"{transcript_id}.transcript.json"
    transcript: dict[str, Any] = {
        "transcript_id": transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": args.provider,
        "model": selected_model,
        "system_prompt": str(args.system_prompt),
        "tools": str(args.tools),
        "history_window": args.history_window,
        "max_tool_rounds": args.max_tool_rounds,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "turns": [],
    }

    print(f"IT Helpdesk Agent chat. artifact_version={artifact_version.artifact_version}")
    print("Type /exit to stop.")

    history: list[dict[str, str]] = []
    turn_index = 0
    while True:
        try:
            user_text = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_text:
            continue
        if user_text in {"/exit", "/quit"}:
            break

        turn_index += 1
        messages = [
            {"role": "system", "content": system_prompt},
            *trim_history(history, args.history_window),
            {"role": "user", "content": user_text},
        ]

        turn_record: dict[str, Any] = {
            "turn_index": turn_index,
            "started_at": now_iso(),
            "user": user_text,
            "status": "started",
            "assistant_text": None,
            "rounds": [],
            "tool_events": [],
        }

        try:
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=openai_tools,
                model=args.model,
                max_tool_rounds=args.max_tool_rounds,
            )
            turn_record.update(result)
            assistant_text = result["assistant_text"]
            print(f"\nAgent> {assistant_text}")
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": assistant_text})
        except Exception as exc:
            turn_record.update({
                "status": "provider_error",
                "error": f"{type(exc).__name__}: {str(exc)}",
            })
            print(f"\nERROR> {turn_record['error']}")

        turn_record["ended_at"] = now_iso()
        transcript["turns"].append(turn_record)
        write_transcript(transcript_path, transcript)
        print(f"Transcript saved: {transcript_path}")

    write_transcript(transcript_path, transcript)
    print(f"Final transcript: {transcript_path}")


def ui_main():
    """Existing styled demo UI; backend integration remains a separate task."""
    import json
    from datetime import datetime
    from uuid import uuid4

    import streamlit as st


    st.set_page_config(
        page_title="Northstar • IT Helpdesk",
        page_icon="💬",
        layout="wide",
    )

    st.markdown("""
    <style>
    .stApp {
        background: #0b1020;
        color: #e7ecf5;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stSidebar"] {
        background: #11182b;
        border-right: 1px solid #25304a;
    }

    [data-testid="stSidebar"] * {
        color: #e7ecf5;
    }

    .block-container {
        max-width: 1200px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: #f5f7ff !important;
        letter-spacing: -0.035em;
    }

    [data-testid="stCaptionContainer"] {
        color: #a5b1ca !important;
    }

    [data-testid="stChatMessage"] {
        background: #151e33;
        border: 1px solid #293550;
        border-radius: 18px;
        padding: 20px;
        margin-bottom: 16px;
    }

    [data-testid="stChatMessage"] p {
        color: #e7ecf5;
        line-height: 1.7;
    }

    [data-testid="stBottom"] > div {
        background: #0b1020;
    }

    [data-testid="stChatInput"] {
        border: 1px solid #5963b8;
        border-radius: 16px;
        background: #151e33;
    }

    [data-testid="stChatInput"] textarea {
        color: #f5f7ff;
        background: #151e33;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #9aa8c3;
    }

    .stButton > button,
    .stDownloadButton > button {
        background: #7565ed;
        color: white !important;
        border: 1px solid #9385ff;
        border-radius: 12px;
        min-height: 44px;
        font-weight: 600;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: #8878ff;
        border-color: #b4aaff;
    }

    .stButton > button:disabled,
    .stDownloadButton > button:disabled {
        background: #26304a;
        border-color: #36415d;
        color: #a5b1ca !important;
    }

    [data-testid="stExpander"] {
        background: #11182b;
        border: 1px solid #2b3854;
        border-radius: 12px;
    }

    .hero {
        padding: 30px;
        margin-bottom: 24px;
        border: 1px solid #394368;
        border-radius: 24px;
        background: linear-gradient(120deg, #202b4d, #262044);
    }

    .hero-label {
        color: #b4aaff;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 2px;
        margin-bottom: 12px;
    }

    .hero h1 {
        margin: 0;
        font-size: clamp(28px, 4vw, 42px);
    }

    .hero p {
        color: #b9c5dd;
        margin: 12px 0 0;
        line-height: 1.6;
    }

    .service-card {
        background: #141d31;
        border: 1px solid #2b3752;
        border-radius: 16px;
        padding: 18px;
        min-height: 120px;
        margin-bottom: 20px;
    }

    .service-card strong {
        display: block;
        color: #eff2ff;
        margin-bottom: 8px;
        font-size: 16px;
    }

    .service-card span {
        color: #a9b6cf;
        font-size: 14px;
    }

    @media (max-width: 640px) {
        .block-container {
            padding-top: 1rem;
        }
        .hero {
            padding: 22px;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    def new_session():
        return {
            "session_id": uuid4().hex,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "mode": "demo",
            "version": "ui-demo-v1",
            "provider": None,
            "model": None,
            "turns": [],
        }


    def demo_response(text, scenario):
        """Điểm nối backend sau này. Hiện chỉ trả dữ liệu mô phỏng."""
        if scenario == "Lỗi công cụ":
            return {
                "assistant_text": (
                    "Không thể kiểm tra dịch vụ trong kịch bản demo này. "
                    "Bạn có thể xem lỗi ở phần chi tiết bên dưới."
                ),
                "status": "demo_error",
                "tool_events": [{
                    "tool": "check_service_status",
                    "args": {"service": "sso"},
                    "result": {
                        "error": "DEMO_TIMEOUT",
                        "message": "Lỗi timeout mô phỏng, không gọi dịch vụ thật.",
                    },
                }],
            }

        if scenario == "Hỏi lại":
            return {
                "assistant_text": (
                    "Bạn vui lòng cung cấp mã nhân viên để tiếp tục "
                    "kịch bản minh họa nhé."
                ),
                "status": "waiting_for_user",
                "tool_events": [{
                    "tool": "clarify",
                    "args": {
                        "question": "Mã nhân viên của bạn là gì?",
                        "response_type": "text",
                    },
                    "result": {
                        "awaiting_user": True,
                        "question": "Mã nhân viên của bạn là gì?",
                    },
                }],
            }

        return {
            "assistant_text": (
                "Đây là phản hồi mẫu: dịch vụ SSO đang hoạt động bình thường. "
                "Kết quả này chỉ dùng để kiểm tra giao diện."
            ),
            "status": "demo_answered",
            "tool_events": [{
                "tool": "check_service_status",
                "args": {"service": "sso"},
                "result": {
                    "service": "sso",
                    "status": "operational",
                    "source": "UI demo fixture",
                },
            }],
        }


    if "demo_session" not in st.session_state:
        st.session_state.demo_session = new_session()

    with st.sidebar:
        st.title("💬 Northstar")
        st.caption("IT HELPDESK · 4aesieunhan")
        st.divider()
        st.markdown("**Chế độ:** Demo")
        st.markdown("**Phiên bản UI:** `ui-demo-v1`")
        st.caption("Provider / Model: chưa kết nối")

        scenario = st.selectbox(
            "Kịch bản phản hồi mẫu",
            ["Tra cứu thành công", "Hỏi lại", "Lỗi công cụ"],
        )
        st.caption("Phản hồi phụ thuộc kịch bản đã chọn, không phân tích bằng AI.")

        if st.button("＋ Cuộc trò chuyện mới", use_container_width=True):
            st.session_state.demo_session = new_session()
            st.rerun()

    session = st.session_state.demo_session

    st.markdown("""
    <div class="hero">
        <div class="hero-label">NORTHSTAR / IT SERVICE DESK</div>
        <h1>Công việc tiếp tục.<br>Vấn đề IT để đây.</h1>
        <p>Không đăng nhập được, mất kết nối hay thiết bị gặp sự cố?
        Bắt đầu cuộc trò chuyện để được hỗ trợ.</p>
    </div>
    """, unsafe_allow_html=True)

    if not session["turns"]:
        cards = st.columns(3)
        services = [
            ("🔐 Tài khoản", "Đăng nhập, tài khoản bị khóa và MFA"),
            ("🌐 Kết nối", "VPN, Wi-Fi và dịch vụ nội bộ"),
            ("💻 Thiết bị", "Máy tính, phần mềm và thiết bị văn phòng"),
        ]
        for column, (title, description) in zip(cards, services):
            with column:
                st.markdown(
                    f'<div class="service-card">'
                    f'<strong>{title}</strong>'
                    f'<span>{description}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    st.info(
        "DEMO — Dữ liệu mô phỏng. Không gọi API, không thực thi tool "
        "và không tạo ticket thật."
    )

    chat_column, guide_column = st.columns([3, 1])

    with guide_column:
        st.subheader("Thông tin phiên")
        st.caption(f"Mã phiên: {session['session_id'][:8]}")
        st.caption(f"Bắt đầu: {session['created_at']}")
        st.markdown(
            "**Thử giao diện**\n\n"
            "1. Chọn kịch bản ở thanh bên.\n"
            "2. Gửi một tin nhắn.\n"
            "3. Mở chi tiết tool bên dưới phản hồi.\n"
            "4. Tải transcript demo."
        )

    with chat_column:
        if not session["turns"]:
            st.markdown("### Chào bạn 👋")
            st.write("Bạn cần hỗ trợ vấn đề gì hôm nay?")
            st.caption("Ví dụ: Tôi không đăng nhập được tài khoản công ty.")

        for turn in session["turns"]:
            with st.chat_message("user"):
                st.write(turn["user"])

            with st.chat_message("assistant"):
                st.write(turn["assistant_text"])
                st.caption(f"Trạng thái: {turn['status']} · DEMO")
                for event in turn["tool_events"]:
                    with st.expander(f"🔧 {event['tool']} · mô phỏng"):
                        st.markdown("**Arguments**")
                        st.json(event["args"])
                        st.markdown("**Kết quả / lỗi**")
                        if event["result"].get("error"):
                            st.error(event["result"]["message"])
                        st.json(event["result"])

    prompt = st.chat_input("Nhập nội dung cần hỗ trợ…")

    if prompt:
        result = demo_response(prompt, scenario)
        session["turns"].append({
            "turn_index": len(session["turns"]) + 1,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user": prompt,
            "demo_scenario": scenario,
            **result,
        })
        st.rerun()

    with st.sidebar:
        st.divider()
        st.download_button(
            "↓ Tải transcript demo",
            data=json.dumps(session, ensure_ascii=False, indent=2),
            file_name=f"demo_{session['session_id'][:8]}.json",
            mime="application/json",
            disabled=not session["turns"],
            use_container_width=True,
        )

if __name__ == "__main__":
    import sys
    if "--ui" in sys.argv:
        ui_main()
    else:
        main()
