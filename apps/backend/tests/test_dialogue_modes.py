from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx


BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

import llm_client
from routers.chat import finalize_assistant_response


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

    def test_multi_probe_prompt_uses_step_questions_with_options(self):
        prompt = llm_client._MULTI_PROBE_SYSTEM_PROMPT
        self.assertIn("第一步", prompt)
        self.assertIn("第二步", prompt)
        self.assertIn("选项", prompt)
        self.assertNotIn("不要输出选项列表", prompt)

    def test_multi_probe_prompt_skips_final_supplement(self):
        self.assertIn("不要在最后询问额外补充信息", llm_client._MULTI_PROBE_SYSTEM_PROMPT)

    def test_options_prompt_rejects_fabricated_specific_events(self):
        self.assertIn("不要编造用户没有提供的具体事件", llm_client._OPTIONS_SYSTEM_PROMPT)
        self.assertIn("宏观层面", llm_client._OPTIONS_SYSTEM_PROMPT)

    def test_initial_system_prompt_requires_one_question_per_step(self):
        prompt = llm_client.settings._prompt_path.read_text(encoding="utf-8")
        self.assertIn("每一步只能提出 1 个问题", prompt)
        self.assertIn("不要在同一步里连续追问", prompt)
        self.assertNotIn("至少连续追问 2-3 层", prompt)
        self.assertNotIn("抛出至少 3 个不同视角的问题", prompt)

    def test_system_prompt_reload_reflects_file_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prompt_path = Path(tmpdir) / "system_prompt.txt"
            prompt_path.write_text("旧提示词", encoding="utf-8")

            with patch.object(llm_client.settings, "_prompt_path", prompt_path):
                llm_client._SYSTEM_PROMPT = None
                self.assertEqual(llm_client._get_system_prompt(), "旧提示词")

                prompt_path.write_text("新提示词", encoding="utf-8")
                self.assertEqual(llm_client._get_system_prompt(), "新提示词")


class StepParsingTests(unittest.TestCase):
    def test_initial_intake_normalizes_verbose_model_output(self):
        verbose_text = """
# 我听到了，先别急

你现在愿意说出来"纠结"，说明这件事已经在你心里压了一阵子了。

---

## 第一步：反问成立性

你说"纠结要不要分手"——

> 你现在的状态，真的还是"在一段关系中"吗？还是其实你已经在心理上半离开了，只是还没有做那个宣布动作？

> 是什么让你还没走？

---

## 第二步：深挖追问

请你现在诚实回答以下几个问题：

第一个追问：
> 你第一次产生"要不要分手"这个念头，是发生了什么事？还记得当时的场景吗？

第二个追问：
> 在这段关系里，你最经常感到的是什么感觉？

第三个追问：
> 明天彻底分开，你第一反应是松一口气，还是心里空一块？

---

## 第三步：复盘与情绪标记

- 你说的是"纠结"，而不是"痛苦"。
- 这说明你可能处于疲惫权衡状态。

---

## 第四步：多角度思考题

恐惧验证视角：
> 你最害怕的是什么？

成本收益视角：
> 如果维持现状再过一年，你会变成什么样？

第三方视角：
> 如果朋友遇到同样情况，你会说什么？

---

## 第五步：一个微型实验

打开手机备忘录，写一句话："在这段关系里，我最不能接受的一件事是______。"
"""
        steps = llm_client.parse_steps(
            verbose_text,
            require_full_intake=True,
            user_context="我纠结要不要分手",
        )

        self.assertEqual([step["step"] for step in steps], [1, 2, 3, 4, 5])
        for step in steps:
            self.assertLessEqual(len(step["content"]), 120)
            self.assertEqual(step["content"].count("？"), 1)
            self.assertNotIn("---", step["content"])
            self.assertNotIn("第一个追问", step["content"])
            self.assertNotIn("第二个追问", step["content"])

    def test_initial_intake_fills_missing_steps(self):
        steps = llm_client.parse_steps(
            "**第一步：反问成立性**\n你现在这个问题成立的关键前提是什么？",
            require_full_intake=True,
            user_context="我纠结要不要分手",
        )

        self.assertEqual([step["step"] for step in steps], [1, 2, 3, 4, 5])
        self.assertTrue(all(step["content"].endswith("？") for step in steps))

    def test_non_intake_keeps_short_multi_probe_shape(self):
        steps = llm_client.parse_steps(
            "**第一步：确认感受**\n你现在最想先确认的是对方的态度，还是你自己的底线？",
            require_full_intake=False,
        )

        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0]["step"], 1)

    def test_error_message_is_not_forced_into_intake_steps(self):
        error_text = "抱歉，上游 AI 服务暂时不可用。请检查 LLM API Key 或稍后重试。"
        steps = llm_client.parse_steps(
            error_text,
            require_full_intake=False,
            user_context="我纠结要不要分手",
        )

        self.assertEqual(steps, [{"step": 0, "title": "回复", "content": error_text}])

    def test_chat_finalize_stores_normalized_intake(self):
        verbose_text = """
开场白不应落库。

## 第一步：反问成立性
> 你现在真正纠结的是分不分手，还是不知道自己为什么还没走？

## 第二步：深挖追问
第一个追问：
> 你第一次产生这个念头，是发生了什么事？
第二个追问：
> 你当时最强烈的感受是什么？

## 第三步：复盘与情绪标记
- 你说的是纠结。

## 第四步：多角度思考题
恐惧验证视角：
> 你最害怕分手后发生什么？

## 第五步：一个微型实验
现在写下：我最不能接受的是______。
"""
        steps, stored_content = finalize_assistant_response(
            verbose_text,
            "chat",
            "我纠结要不要分手",
            upstream_failed=False,
        )

        self.assertEqual([step["step"] for step in steps], [1, 2, 3, 4, 5])
        self.assertEqual(stored_content.count("**第"), 5)
        self.assertNotIn("开场白", stored_content)
        self.assertNotIn("第二个追问", stored_content)

    def test_chat_finalize_keeps_upstream_errors_as_plain_reply(self):
        error_text = "抱歉，上游 AI 服务暂时不可用。请检查 LLM API Key 或稍后重试。"
        steps, stored_content = finalize_assistant_response(
            error_text,
            "chat",
            "我纠结要不要分手",
            upstream_failed=True,
        )

        self.assertEqual(steps, [{"step": 0, "title": "回复", "content": error_text}])
        self.assertEqual(stored_content, error_text)


class LlmStreamErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_anthropic_stream_raises_on_http_error(self):
        class FakeStreamResponse:
            status_code = 401

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                request = httpx.Request("POST", "https://example.test/v1/messages")
                response = httpx.Response(401, request=request, json={"error": {"message": "Invalid API Key"}})
                raise httpx.HTTPStatusError("invalid key", request=request, response=response)

            async def aiter_lines(self):
                yield '{"error":{"message":"Invalid API Key"}}'

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            def stream(self, *args, **kwargs):
                return FakeStreamResponse()

        with patch.object(llm_client.httpx, "AsyncClient", FakeClient):
            with self.assertRaises(httpx.HTTPStatusError):
                async for _ in llm_client._stream_anthropic([], "system"):
                    pass


if __name__ == "__main__":
    unittest.main()
