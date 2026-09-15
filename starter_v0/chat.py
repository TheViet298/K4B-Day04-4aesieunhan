from __future__ import annotations

import argparse
import csv
import os
from uuid import uuid4
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

def load_backend():
    """Load the shared provider adapters, registry and environment; no API request."""
    global make_provider, ToolCall, TOOL_FUNCTIONS
    global load_tool_declarations, to_openai_tools
    global artifact_version_dict, build_artifact_version
    from env_loader import load_lab_env
    from providers import make_provider
    from providers.base import ToolCall
    from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
    from versioning import artifact_version_dict, build_artifact_version
    load_lab_env(ROOT)


ROOT = Path(__file__).resolve().parent
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
        result = {"error": type(exc).__name__, "message": safe_error(exc)}
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
    on_progress: Any = None,
) -> dict[str, Any]:
    load_backend()
    if max_tool_rounds < 1:
        raise ValueError("max_tool_rounds must be at least 1")
    working_messages = list(messages)
    ticket_attempted = False
    rounds: list[dict[str, Any]] = []
    all_tool_events: list[dict[str, Any]] = []

    for round_index in range(1, max_tool_rounds + 1):
        try:
            response = provider.complete(working_messages, tools, model=model, temperature=0.0)
        except Exception as exc:
            return {
                "status": "provider_error", "assistant_text": "",
                "error": safe_error(exc), "rounds": rounds,
                "tool_events": all_tool_events,
            }
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
            if call.name == "create_ticket" and ticket_attempted:
                event = {"tool": call.name, "args": call.args, "result": {
                    "error": "duplicate_write_blocked",
                    "message": "Ticket creation was already attempted in this turn. Inspect its result; do not retry automatically.",
                }}
            else:
                if call.name == "create_ticket":
                    ticket_attempted = True
                event = execute_tool_call(call)
            round_record["tool_results"].append(event)
            all_tool_events.append(event)
            if on_progress:
                on_progress({"rounds": [*rounds, round_record], "tool_events": all_tool_events})

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
    # Replace atomically so a partial write does not corrupt the previous trace.
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(json_text(transcript), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)



def safe_error(exc: Exception) -> str:
    """Keep diagnostic details while removing configured credentials from errors."""
    message = f"{type(exc).__name__}: {exc}"
    for name, value in os.environ.items():
        if value and any(part in name.upper() for part in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
            message = message.replace(value, "[REDACTED]")
    return message


def display_reply(text: str | None) -> str:
    """Presentation only; never interpret text as executable tool calls."""
    raw = text or ""
    candidate = raw.strip()
    if candidate.startswith("```json\n") and candidate.endswith("```"):
        candidate = candidate[8:-3].strip()
    elif candidate.startswith("```\n") and candidate.endswith("```"):
        candidate = candidate[4:-3].strip()
    try:
        value = json.loads(candidate)
    except (ValueError, TypeError):
        return raw
    return value["reply"] if isinstance(value, dict) and isinstance(value.get("reply"), str) else raw


def current_version() -> str:
    """Use a recorded version only when BOTH actual artifact hashes match."""
    load_backend()
    actual = artifact_version_dict(build_artifact_version("current", ARTIFACTS_DIR / "system_prompt.md", ARTIFACTS_DIR / "tools.yaml"))
    path = ARTIFACTS_DIR / "version_log.csv"
    if path.exists():
        for row in reversed(list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))):
            if all(len(row.get(key, "")) >= 12 and actual[key].startswith(row[key]) for key in ("prompt_hash", "tools_hash")):
                return row["version"]
    return "current"


def resolve_model(provider_name: str, provider: Any, model: str | None) -> str:
    return model or (os.getenv("GEMINI_MODEL") if provider_name == "gemini" else None) or provider.default_model


def new_session(*, mode: str, provider_name: str | None = None,
                model: str | None = None, version: str = "current",
                prompt_path: Path = ARTIFACTS_DIR / "system_prompt.md",
                tools_path: Path = ARTIFACTS_DIR / "tools.yaml",
                history_window: int = 5, max_tool_rounds: int = 4) -> dict[str, Any]:
    load_backend()
    artifact = artifact_version_dict(build_artifact_version(version, prompt_path, tools_path)) if mode == "live" else {
        "version": "ui-demo-v1", "artifact_version": "ui-demo-v1",
        "prompt_hash": None, "tools_hash": None,
    }
    return {
        "transcript_id": f"{mode}_{safe_slug(artifact['version'])}_{safe_slug(provider_name or 'fixture')}_{uuid4().hex}",
        "mode": mode, **artifact, "provider": provider_name if mode == "live" else None,
        "model": model if mode == "live" else None,
        "system_prompt": str(prompt_path) if mode == "live" else None,
        "tools": str(tools_path) if mode == "live" else None,
        "history_window": history_window, "max_tool_rounds": max_tool_rounds,
        "created_at": now_iso(), "updated_at": now_iso(), "turns": [],
    }


def session_history(session: dict[str, Any]) -> list[dict[str, str]]:
    history = []
    window = session["history_window"]
    for turn in session["turns"][-window:] if window > 0 else []:
        content = turn.get("assistant_text") or ""
        if turn.get("tool_events"):
            content += "\nExecuted local tool results (already executed; do not repeat writes):\n" + json_text(turn["tool_events"], max_chars=24000)
        if turn.get("error") or turn["status"] in {"started", "interrupted"}:
            content += "\nTurn did not finish. Do not automatically repeat earlier actions."
        history.extend([{"role": "user", "content": turn["user"]}, {"role": "assistant", "content": content}])
    return history


def submit_turn(session: dict[str, Any], user_text: str, *, provider: Any = None,
                scenario: str = "Tra cứu thành công", request_id: str | None = None,
                transcript_path: Path | None = None) -> dict[str, Any]:
    """Called only by a submit event; same request ID is never executed twice."""
    request_id = request_id or uuid4().hex
    for previous in session["turns"]:
        if previous.get("request_id") == request_id:
            return previous
    history = session_history(session)
    turn = {"turn_index": len(session["turns"]) + 1, "request_id": request_id,
            "started_at": now_iso(), "user": user_text, "status": "started",
            "assistant_text": "", "rounds": [], "tool_events": []}
    session["turns"].append(turn)

    def checkpoint(update=None):
        if update:
            turn.update(update)
        if transcript_path:
            try:
                write_transcript(transcript_path, session)
                session.pop("save_error", None)
            except OSError as exc:
                session["save_error"] = safe_error(exc)

    checkpoint()
    try:
        if session["mode"] == "demo":
            turn["demo_scenario"] = scenario
            turn.update(demo_response(user_text, scenario))
        else:
            load_backend()
            provider = provider if provider is not None else make_provider(session["provider"])
            if session["provider"] == "gemini":
                provider.max_attempts = 1  # No automatic quota retry in interactive chat.
            prompt = Path(session["system_prompt"]).read_text(encoding="utf-8")
            tools = to_openai_tools(load_tool_declarations(Path(session["tools"])))
            # A session owns its artifact hashes; refuse silently changed files.
            actual = artifact_version_dict(build_artifact_version(session["version"], Path(session["system_prompt"]), Path(session["tools"])))
            if actual["artifact_version"] != session["artifact_version"]:
                raise ValueError("Artifacts changed. Start a new conversation before continuing.")
            turn.update(run_model_tool_loop(
                provider=provider, messages=[{"role": "system", "content": prompt}, *history, {"role": "user", "content": user_text}],
                tools=tools, model=session["model"], max_tool_rounds=session["max_tool_rounds"], on_progress=checkpoint,
            ))
    except Exception as exc:
        turn.update(status="provider_error", error=safe_error(exc))
    finally:
        if turn["status"] == "started":
            turn.update(status="interrupted", error="Lượt bị gián đoạn; không tự chạy lại. Kiểm tra tool trace trước khi gửi yêu cầu mới.")
        turn["ended_at"] = now_iso()
        checkpoint()
    return turn


def main() -> None:
    parser = argparse.ArgumentParser(description="Interactive IT Helpdesk Agent chat with transcript logging.")
    parser.add_argument("--provider", choices=["openrouter", "openai", "anthropic", "gemini"], required=True)
    parser.add_argument("--model", default=None)
    parser.add_argument("--version", required=True, help="Artifact label; actual prompt/tools hashes are recorded.")
    parser.add_argument("--system-prompt", type=Path, default=ARTIFACTS_DIR / "system_prompt.md")
    parser.add_argument("--tools", type=Path, default=ARTIFACTS_DIR / "tools.yaml")
    parser.add_argument("--transcripts-dir", type=Path, default=ROOT / "transcripts")
    parser.add_argument("--history-window", type=int, default=5)
    parser.add_argument("--max-tool-rounds", type=int, default=4)
    args = parser.parse_args()
    if args.history_window < 0 or args.max_tool_rounds < 1:
        parser.error("history-window must be nonnegative; max-tool-rounds must be positive")
    load_backend()
    provider = make_provider(args.provider)
    session = new_session(mode="live", provider_name=args.provider, model=resolve_model(args.provider, provider, args.model),
                          version=args.version, prompt_path=args.system_prompt, tools_path=args.tools,
                          history_window=args.history_window, max_tool_rounds=args.max_tool_rounds)
    path = args.transcripts_dir / f"{session['transcript_id']}.transcript.json"
    print(f"IT Helpdesk Agent. {session['provider']} / {session['model']} / {session['artifact_version']}")
    print("Type /exit to stop.")
    while True:
        try:
            user_text = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_text in {"/exit", "/quit"}:
            break
        if not user_text:
            continue
        turn = submit_turn(session, user_text, provider=provider, transcript_path=path)
        for event in turn["tool_events"]:
            print(f"[tool] {event['tool']}({json_text(event['args'])})")
            print(f"[result] {json_text(event['result'])}")
        print(f"\nAgent> {turn['assistant_text']}\nStatus: {turn['status']}")
        if turn.get("error"):
            print(f"ERROR> {turn['error']}")
        if session.get("save_error"):
            print(f"SAVE ERROR> {session['save_error']}")
    try:
        write_transcript(path, session)
        print(f"Final transcript: {path}")
    except OSError as exc:
        print(f"SAVE ERROR> {safe_error(exc)}")


def demo_response(text, scenario):
    """Offline fixtures only: never invoke the provider or tool registry."""
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
            "status": "demo_waiting_for_user",
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



def ui_main():
    import streamlit as st
    load_backend()
    st.set_page_config(page_title="Northstar • IT Helpdesk", page_icon="💬", layout="wide")
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

    /* Explicit foreground AND background: works even with Streamlit's light theme. */
    [data-testid="stWidgetLabel"], [data-testid="stExpander"] summary,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: #e7ecf5 !important;
    }
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input,
    [data-baseweb="select"] > div, [data-baseweb="select"] input {
        background: #202b43 !important;
        color: #f5f7ff !important;
        -webkit-text-fill-color: #f5f7ff !important;
    }
    [data-baseweb="select"] svg { fill: #d8d1ff !important; }
    [role="listbox"], [role="option"] {
        background: #202b43 !important; color: #f5f7ff !important;
    }
    [role="option"][aria-selected="true"], [role="option"]:hover {
        background: #433878 !important;
    }
    [data-testid="stAlert"] {
        background: #202b43 !important; color: #f5f7ff !important;
        border: 1px solid #66789e;
    }
    [data-testid="stAlert"] p, [data-testid="stAlert"] svg {
        color: #f5f7ff !important;
    }
    [data-testid="stNumberInput"] button {
        background: #202b43 !important; color: #f5f7ff !important;
    }
    [data-testid="stChatInputSubmitButton"] {
        background: #5746ae !important; color: #ffffff !important;
    }
    [data-testid="stTextInput"] input::placeholder {
        color: #bac6de !important; -webkit-text-fill-color: #bac6de !important;
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
        color: #f5f7ff !important;
        -webkit-text-fill-color: #f5f7ff !important;
        background: #151e33 !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #bac6de !important;
        -webkit-text-fill-color: #bac6de !important;
        opacity: 1;
    }

    .stButton > button,
    .stDownloadButton > button {
        background: #5746ae;
        color: white !important;
        border: 1px solid #9385ff;
        border-radius: 12px;
        min-height: 44px;
        font-weight: 600;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: #6553bd;
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


    with st.sidebar:
        st.title("💬 Northstar")
        st.caption("IT HELPDESK · 4aesieunhan")
        mode_label = st.selectbox("Chế độ", ["Demo", "Live"], key="mode")
        mode = mode_label.lower()
        scenario = "Tra cứu thành công"
        provider_name, model = None, None
        version = "ui-demo-v1"
        if mode == "demo":
            scenario = st.selectbox("Kịch bản Demo", ["Tra cứu thành công", "Hỏi lại", "Lỗi công cụ"])
        else:
            with st.expander("Cấu hình Live", expanded=False):
                provider_name = st.selectbox("Provider", ["gemini", "openrouter", "openai", "anthropic"], key="provider")
                requested_model = st.text_input("Model (trống = mặc định)", key=f"model_{provider_name}").strip() or None
            provider = make_provider(provider_name)
            model = resolve_model(provider_name, provider, requested_model)
            version = current_version()
        reset = st.button("＋ Cuộc trò chuyện mới", use_container_width=True)

    try:
        candidate = new_session(mode=mode, provider_name=provider_name, model=model, version=version)
    except Exception as exc:
        st.error(safe_error(exc))
        st.stop()
    config = (mode, provider_name, model, candidate["artifact_version"])
    sessions = st.session_state.setdefault("chat_sessions", {})
    if reset or config not in sessions:
        sessions[config] = candidate
    session = sessions[config]
    st.session_state.active_chat = session
    # Separate demo files from reviewed Live evidence.
    directory = ROOT / ("demo_transcripts" if mode == "demo" else "transcripts")
    path = directory / f"{session['transcript_id']}.transcript.json"
    st.markdown("""
    <div class="hero">
        <div class="hero-label">NORTHSTAR / IT SERVICE DESK</div>
        <h1>Công việc tiếp tục.<br>Vấn đề IT để đây.</h1>
        <p>Không đăng nhập được, mất kết nối hay thiết bị gặp sự cố?
        Bắt đầu cuộc trò chuyện để được hỗ trợ.</p>
    </div>
    """, unsafe_allow_html=True)


    if mode == "demo":
        st.info("DEMO — Phản hồi và tool trace mô phỏng. Không gọi API hoặc thực thi công cụ. Không dùng làm evidence Live.")
    else:
        st.info("LIVE — AI kết nối provider; công cụ dùng dữ liệu giả lập của bài lab.")
    st.caption(f"Provider: {session['provider'] or 'không dùng (Demo)'} · Model: {session['model'] or 'fixture'}")
    st.caption(f"Artifact: {session['artifact_version']}")
    if mode == "live" and version == "current":
        st.caption("Artifact hiện tại chưa khớp cặp hash trong version_log.csv; không gắn nhãn v3.")

    def render_turn(turn):
        with st.chat_message("user"):
            st.write(turn["user"])
        with st.chat_message("assistant"):
            st.write(display_reply(turn.get("assistant_text")))
            st.caption(f"{mode.upper()} · Lượt {turn['turn_index']} · {turn['status']}")
            if turn.get("error"):
                st.error(turn["error"])
                st.caption("Không tự gửi lại yêu cầu. Kiểm tra các công cụ đã chạy trước khi tiếp tục.")
            if turn["status"] == "max_tool_rounds":
                st.warning("Đã đạt giới hạn vòng công cụ; tác vụ có thể chưa hoàn tất.")
            if not turn["tool_events"]:
                if mode == "live":
                    st.warning("Lượt này chỉ có phản hồi văn bản, không có công cụ nào được thực thi. Lời AI nói đã tra cứu hoặc tạo ticket chưa phải kết quả được xác minh.")
                else:
                    st.caption("Không có công cụ nào được thực thi trong lượt này.")
            for event in turn["tool_events"]:
                with st.expander(f"🔧 {event['tool']}" + (" · mô phỏng" if mode == "demo" else "")):
                    st.markdown("**Arguments**")
                    st.json(event["args"])
                    st.markdown("**Kết quả / lỗi**")
                    result = event["result"]
                    if isinstance(result, dict) and result.get("error"):
                        st.error(result.get("message") or str(result["error"]))
                    st.json(result)
            if turn.get("assistant_text") and display_reply(turn["assistant_text"]) != turn["assistant_text"]:
                with st.expander("Phản hồi gốc của AI"):
                    st.code(turn["assistant_text"], language="json")

    if not session["turns"]:
        st.subheader("Chào bạn 👋")
        st.write("Bạn cần hỗ trợ vấn đề gì hôm nay?")
    for turn in session["turns"]:
        render_turn(turn)
    prompt = st.chat_input("Nhập nội dung cần hỗ trợ…")
    if prompt and prompt.strip():
        with st.spinner("Đang xử lý…"):
            submit_turn(session, prompt.strip(), scenario=scenario, transcript_path=path)
        st.rerun()
    if session.get("save_error"):
        st.error(f"Chưa lưu được transcript: {session['save_error']}. Hãy tải bản trong phiên ở thanh bên.")
    with st.sidebar:
        st.caption(f"Phiên: {session['transcript_id'][-8:]}")
        st.download_button(
            f"↓ Tải transcript {mode_label}", data=json_text(session), file_name=path.name,
            mime="application/json", disabled=not session["turns"], use_container_width=True,
        )


if __name__ == "__main__":
    import sys
    if "--ui" in sys.argv:
        ui_main()
    else:
        main()
