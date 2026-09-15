"""Small opt-in LIVE smoke run on the lab fixtures; never runs full evaluation.

Includes explicit confirmation for a local educational ticket.
Inspect the trace: model compliance is not assumed.
Stops at the first provider error. Does not retry failed turns.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import chat


def main():
    chat.load_backend()
    provider = chat.make_provider('gemini')
    model = chat.resolve_model('gemini', provider, None)
    summary = []
    scenarios = {
        'lookup': ['Kiểm tra trạng thái dịch vụ VPN ở production bằng công cụ check_service_status đã khai báo, rồi cho tôi kết quả thực tế.'],
        'clarify_context': [
            'Kiểm tra phần cứng laptop giúp tôi.',
            'Mã máy là LT-204.',
            'Mã máy tôi vừa cung cấp là gì? Chỉ nhắc lại mã đó, không cần kiểm tra lại.',
        ],
        'ticket_confirm': [
            'Tôi muốn tạo ticket cho máy LT-204 với nội dung "Lab UI smoke: VPN AUTH_TIMEOUT", ưu tiên medium. Hãy hỏi xác nhận trước khi tạo.',
            'Tôi đồng ý tạo đúng một ticket cho LT-204, nội dung "Lab UI smoke: VPN AUTH_TIMEOUT", ưu tiên medium.',
        ],
        'ticket_cancel': [
            'Tôi muốn tạo ticket cho LT-318 với nội dung "Lab UI smoke: kiểm tra pin", ưu tiên low. Hãy hỏi xác nhận trước khi tạo.',
            'Hủy yêu cầu tạo ticket đó. Không tạo ticket nào. Chỉ kiểm tra trạng thái email ở production.',
        ],
    }
    for name, prompts in scenarios.items():
        session = chat.new_session(mode='live', provider_name='gemini', model=model, version=chat.current_version())
        session['verification_scenario'] = name
        path = ROOT / 'transcripts' / f"{session['transcript_id']}.transcript.json"
        for prompt in prompts:
            turn = chat.submit_turn(session, prompt, provider=provider, transcript_path=path)
            print(name, turn['turn_index'], turn['status'], [e['tool'] for e in turn['tool_events']], flush=True)
            if turn.get('error'):
                print(turn['error'], flush=True)
            if turn['status'] == 'provider_error':
                summary.append({'scenario': name, 'transcript': str(path.relative_to(ROOT)), 'blocked': True})
                (ROOT / 'analysis' / 'huy_live_smoke_index.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
                return
        summary.append({'scenario': name, 'transcript': str(path.relative_to(ROOT)),
                        'statuses': [t['status'] for t in session['turns']],
                        'tool_calls': [[e['tool'] for e in t['tool_events']] for t in session['turns']]})
        (ROOT / 'analysis' / 'huy_live_smoke_index.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
