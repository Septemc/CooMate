from __future__ import annotations

import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

import llm_client


class DialogueModeTests(unittest.TestCase):
    def test_initial_chat_keeps_full_intake(self):
        self.assertTrue(hasattr(llm_client, "resolve_chat_action"))
        self.assertEqual(
            llm_client.resolve_chat_action("chat", has_assistant_history=False, multi_probe=False),
            "chat",
        )

    def test_initial_chat_ignores_multi_probe_toggle(self):
        self.assertEqual(
            llm_client.resolve_chat_action("chat", has_assistant_history=False, multi_probe=True),
            "chat",
        )

    def test_followup_chat_defaults_to_light_followup(self):
        self.assertTrue(hasattr(llm_client, "resolve_chat_action"))
        self.assertEqual(
            llm_client.resolve_chat_action("chat", has_assistant_history=True, multi_probe=False),
            "follow_up",
        )

    def test_followup_chat_uses_multi_probe_when_enabled(self):
        self.assertTrue(hasattr(llm_client, "resolve_chat_action"))
        self.assertEqual(
            llm_client.resolve_chat_action("chat", has_assistant_history=True, multi_probe=True),
            "multi_probe",
        )

    def test_options_prompt_rejects_fabricated_specific_events(self):
        self.assertIn("不要编造用户没有提供的具体事件", llm_client._OPTIONS_SYSTEM_PROMPT)
        self.assertIn("宏观层面", llm_client._OPTIONS_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
