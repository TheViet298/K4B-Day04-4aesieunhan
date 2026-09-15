"""Offline / MOCK regression tests, not evidence of live model behavior."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import chat
from providers.base import ModelResponse, ToolCall


class FakeProvider:
    default_model = 'mock-model'
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.messages = []
    def complete(self, messages, *args, **kwargs):
        self.messages.append(messages)
        item = next(self.responses)
        if isinstance(item, BaseException):
            raise item
        return item


class ChatTests(unittest.TestCase):
    def setUp(self):
        chat.load_backend()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'mock.transcript.json'
        self.session = chat.new_session(mode='live', provider_name='gemini', model='mock-model')

    def submit(self, provider, text='Kiểm tra VPN', **kwargs):
        return chat.submit_turn(self.session, text, provider=provider, transcript_path=self.path, **kwargs)

    def test_actual_read_tool_and_raw_reply(self):
        raw = '{"reply":"VPN degraded","intent":"status","action":"answer","evidence_ids":[]}'
        p = FakeProvider(ModelResponse(tool_calls=[ToolCall('check_service_status', {'service':'vpn','environment':'production'})]), ModelResponse(text=raw))
        t = self.submit(p)
        self.assertEqual(t['status'], 'answered')
        self.assertEqual(t['assistant_text'], raw)
        self.assertEqual(chat.display_reply(raw), 'VPN degraded')
        self.assertEqual(chat.display_reply('```json\n' + raw + '\n```'), 'VPN degraded')
        self.assertEqual(json.loads(self.path.read_text())['turns'][0]['assistant_text'], raw)
        self.assertTrue(t['tool_events'])

    def test_clarification_context_and_cancel(self):
        p = FakeProvider(ModelResponse(tool_calls=[ToolCall('clarify', {'question':'Mã máy?', 'response_type':'text'})]))
        self.assertEqual(self.submit(p)['status'], 'waiting_for_user')
        p = FakeProvider(ModelResponse(text='Đã hủy'))
        self.submit(p, 'Hủy yêu cầu cũ')
        self.assertIn('Mã máy?', json.dumps(p.messages[0], ensure_ascii=False))
        self.assertEqual(self.session['turns'][1]['tool_events'], [])

    def test_error_preserves_executed_trace_and_context(self):
        p = FakeProvider(ModelResponse(tool_calls=[ToolCall('check_service_status', {'service':'vpn'})]), RuntimeError('quota 429'))
        t = self.submit(p)
        self.assertEqual(t['status'], 'provider_error')
        self.assertEqual(len(t['tool_events']), 1)
        saved = json.loads(self.path.read_text())
        self.assertEqual(len(saved['turns'][0]['tool_events']), 1)
        self.assertIn('already executed', chat.session_history(self.session)[1]['content'])

    def test_textual_tool_calls_are_never_executed(self):
        with patch.dict(chat.TOOL_FUNCTIONS, {'create_ticket': lambda **kw: self.fail('executed text')}):
            text = 'TOOL_CALLS_JSON: [{"name":"create_ticket","args":{"confirmed":true}}]'
            t = self.submit(FakeProvider(ModelResponse(text=text)))
            self.assertEqual(t['tool_events'], [])
            self.assertEqual(t['assistant_text'], text)

    def test_duplicate_submission_and_repeated_write(self):
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            return {'status':'created','ticket_id':'MOCK-ONLY'}
        action = ModelResponse(tool_calls=[ToolCall('create_ticket', {'summary':'Mock', 'confirmed': True})])
        with patch.dict(chat.TOOL_FUNCTIONS, {'create_ticket':create}):
            p = FakeProvider(action, action, ModelResponse(text='Done'))
            t = self.submit(p, 'Đồng ý', request_id='one')
            again = self.submit(p, 'Đồng ý', request_id='one')
        self.assertIs(t, again)
        self.assertEqual(len(calls), 1)
        self.assertEqual(t['tool_events'][1]['result']['error'], 'duplicate_write_blocked')

    def test_tool_failure_and_limit(self):
        def fail(): raise RuntimeError('mock tool failure')
        with patch.dict(chat.TOOL_FUNCTIONS, {'fail':fail}):
            self.session['max_tool_rounds'] = 1
            t = self.submit(FakeProvider(ModelResponse(tool_calls=[ToolCall('fail', {})])))
        self.assertEqual(t['status'], 'max_tool_rounds')
        self.assertEqual(t['tool_events'][0]['result']['error'], 'RuntimeError')

    def test_mock_confirmation_uses_real_local_ticket_tool(self):
        import importlib
        ticket_module = importlib.import_module('tools.create_ticket.tool')
        ticket_dir = Path(self.temp.name) / 'tickets'
        question = FakeProvider(ModelResponse(tool_calls=[ToolCall('clarify', {'question':'Tạo ticket LT-204 medium?', 'response_type':'yes_no'})]))
        with patch.object(ticket_module, 'TICKET_DIR', ticket_dir):
            self.submit(question, 'Tạo ticket cho LT-204, medium')
            self.assertFalse(ticket_dir.exists())
            action = FakeProvider(ModelResponse(tool_calls=[ToolCall('create_ticket', {'summary':'MOCK model test', 'priority':'medium', 'asset_id':'LT-204', 'confirmed':True})]), RuntimeError('mock post-write failure'))
            t = self.submit(action, 'Đồng ý tạo ticket LT-204 medium', request_id='confirmed')
            self.assertEqual(t['tool_events'][0]['result']['status'], 'created')
            self.assertEqual(t['status'], 'provider_error')
            self.submit(action, 'Đồng ý tạo ticket LT-204 medium', request_id='confirmed')
            self.assertEqual(len(list(ticket_dir.glob('*.json'))), 1)

    def test_unknown_tool(self):
        event = chat.execute_tool_call(ToolCall('not_registered', {}))
        self.assertEqual(event['result']['error'], 'unknown_tool')

    def test_interruption_is_persisted_without_replay(self):
        with self.assertRaises(KeyboardInterrupt):
            self.submit(FakeProvider(KeyboardInterrupt()), request_id='interrupted')
        self.assertEqual(json.loads(self.path.read_text())['turns'][0]['status'], 'interrupted')
        self.submit(FakeProvider(), request_id='interrupted')
        self.assertEqual(len(self.session['turns']), 1)

    def test_error_redaction(self):
        with patch.dict(os.environ, {'LAB_TEST_API_KEY':'fake-secret-for-test'}):
            self.assertNotIn('fake-secret-for-test', chat.safe_error(RuntimeError('key=fake-secret-for-test')))

    def test_demo_is_separate_no_provider(self):
        s = chat.new_session(mode='demo')
        for scenario, expected in [('Tra cứu thành công','demo_answered'),('Hỏi lại','demo_waiting_for_user'),('Lỗi công cụ','demo_error')]:
            t = chat.submit_turn(s, 'Demo', provider=FakeProvider(), scenario=scenario)
            self.assertEqual(t['status'], expected)
        self.assertIsNone(s['provider'])
        self.assertIsNone(s['prompt_hash'])
        self.assertTrue(s['transcript_id'].startswith('demo_'))

    def test_save_error_keeps_downloadable_session(self):
        with patch.object(chat, 'write_transcript', side_effect=OSError('disk full')):
            self.submit(FakeProvider(ModelResponse(text='Done')))
        self.assertEqual(self.session['turns'][0]['status'], 'answered')
        self.assertIn('disk full', self.session['save_error'])

    def test_artifact_change_stops_before_provider(self):
        self.session['artifact_version'] = 'old-hash'
        t = self.submit(FakeProvider())
        self.assertEqual(t['status'], 'provider_error')
        self.assertIn('Artifacts changed', t['error'])

    def test_gemini_env_model_matches_transcript(self):
        with patch.dict(os.environ, {'GEMINI_MODEL':'configured-model'}):
            self.assertEqual(chat.resolve_model('gemini', FakeProvider(), None), 'configured-model')
            self.assertEqual(chat.resolve_model('gemini', FakeProvider(), 'explicit'), 'explicit')


class UITests(unittest.TestCase):
    def test_ui_scenarios_session_isolation_and_no_rerun_call(self):
        from streamlit.testing.v1 import AppTest
        # Temporary transcript destination; the test never creates Live evidence.
        with tempfile.TemporaryDirectory() as tmp, patch('sys.argv', ['chat.py','--ui']):
            entry = Path(tmp) / 'entry.py'
            entry.write_text(f'import sys\nsys.path.insert(0, {str(ROOT)!r})\nimport chat\nchat.ROOT = __import__("pathlib").Path({tmp!r})\nchat.ui_main()\n')
            original = chat.ROOT
            self.addCleanup(setattr, chat, 'ROOT', original)
            at = AppTest.from_file(str(entry)).run()
            self.assertFalse(at.exception)
            for scenario in ['Tra cứu thành công','Hỏi lại','Lỗi công cụ']:
                at.selectbox[1].select(scenario).run()
                at.chat_input[0].set_value('Demo').run()
                self.assertFalse(at.exception)
            self.assertEqual(len(at.session_state.active_chat['turns']), 3)
            import streamlit as st
            with patch('streamlit.download_button', wraps=st.download_button) as download:
                at.run()
                payload = json.loads(download.call_args.kwargs['data'])
                self.assertEqual(payload['mode'], 'demo')
                self.assertEqual(len(payload['turns']), 3)
                self.assertEqual(payload['turns'][-1]['status'], 'demo_error')
            demo_id = at.session_state.active_chat['transcript_id']
            at.selectbox[0].select('Live').run()
            p = FakeProvider(ModelResponse(tool_calls=[ToolCall('lookup_user', {'employee_id':'EMP-1001'})]), ModelResponse(text='Live mock'))
            with patch('providers.make_provider', return_value=p):
                at.chat_input[0].set_value('Mock live').run()
                at.run()  # Same rerun as widgets/download; no resubmission.
            self.assertEqual(len(p.messages), 2)
            self.assertFalse(at.exception)
            self.assertEqual(len(at.session_state.active_chat['turns']), 1)
            with patch('providers.make_provider', return_value=p), patch('streamlit.download_button', wraps=st.download_button) as download:
                at.run()
                payload = json.loads(download.call_args.kwargs['data'])
                self.assertEqual(payload['mode'], 'live')
                self.assertEqual(len(payload['turns'][0]['tool_events']), 1)
                self.assertEqual(len(p.messages), 2)
            with patch('providers.make_provider', return_value=p):
                live_id = at.session_state.active_chat['transcript_id']
                at.text_input[0].set_value('another-mock-model').run()
                self.assertEqual(at.session_state.active_chat['turns'], [])
                at.text_input[0].set_value('').run()
                self.assertEqual(at.session_state.active_chat['transcript_id'], live_id)
                failing = FakeProvider(ModelResponse(tool_calls=[ToolCall('lookup_user', {'employee_id':'EMP-1001'})]), RuntimeError('MOCK quota 429'))
                with patch('providers.make_provider', return_value=failing):
                    at.chat_input[0].set_value('Mock failure').run()
                self.assertTrue(any('MOCK quota 429' in error.value for error in at.error))
                self.assertEqual(len(at.session_state.active_chat['turns'][-1]['tool_events']), 1)
            at.selectbox[0].select('Demo').run()
            self.assertEqual(at.session_state.active_chat['transcript_id'], demo_id)
            self.assertEqual(len(at.session_state.active_chat['turns']), 3)
            at.button[0].click().run()
            self.assertEqual(at.session_state.active_chat['turns'], [])
            self.assertNotEqual(at.session_state.active_chat['transcript_id'], demo_id)


if __name__ == '__main__':
    unittest.main(verbosity=2)
