from __future__ import annotations

import json
import re
from typing import AsyncIterator

import httpx

from config import settings

_SYSTEM_PROMPT: str | None = None


def _get_system_prompt() -> str:
    global _SYSTEM_PROMPT
    if _SYSTEM_PROMPT is None:
        prompt_path = settings._prompt_path
        if prompt_path.exists():
            _SYSTEM_PROMPT = prompt_path.read_text(encoding="utf-8")
        else:
            _SYSTEM_PROMPT = "你是 CooMate，用户的专属 AI 认知参谋。通过结构化提问引导用户自己找到答案。"
    return _SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Anthropic Messages API (compatible with MiniMax, Xiaomi MiMo)
# ---------------------------------------------------------------------------

def _anthropic_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01",
        "x-api-key": settings.LLM_API_KEY,
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
    }


def _openai_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
    }


def _build_messages(history: list[dict], user_message: str) -> list[dict]:
    """Build messages array for the LLM API."""
    messages = []
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})
    return messages


def _is_anthropic_format() -> bool:
    return settings.LLM_PROVIDER in ("minimax_anthropic", "anthropic_messages")


def _normalize_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


async def stream_chat(
    messages: list[dict],
    action: str = "chat",
) -> AsyncIterator[str]:
    """Stream LLM response as plain text chunks."""

    system_prompt = _get_system_prompt()
    if action == "regenerate_angles":
        system_prompt += "\n\n用户要求'换个角度'。请只重新生成第四步（多角度思考题），使用完全不同的视角组合。"
    elif action == "export_review":
        system_prompt += "\n\n用户要求'导出复盘'。请将本次对话的复盘内容整理为结构化的 Markdown 报告。"

    if _is_anthropic_format():
        async for chunk in _stream_anthropic(messages, system_prompt):
            yield chunk
    else:
        async for chunk in _stream_openai(messages, system_prompt):
            yield chunk


async def _stream_anthropic(messages: list[dict], system_prompt: str) -> AsyncIterator[str]:
    url = _normalize_url(settings.LLM_BASE_URL, "/v1/messages")
    payload = {
        "model": settings.LLM_MODEL,
        "max_tokens": 8192,
        "stream": True,
        "system": system_prompt,
        "messages": messages,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", url, headers=_anthropic_headers(), json=payload) as resp:
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if data.get("type") == "content_block_delta":
                    delta = data.get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        yield text


async def _stream_openai(messages: list[dict], system_prompt: str) -> AsyncIterator[str]:
    url = _normalize_url(settings.LLM_BASE_URL, "/chat/completions")
    payload = {
        "model": settings.LLM_MODEL,
        "max_tokens": 8192,
        "stream": True,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
    }

    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", url, headers=_openai_headers(), json=payload) as resp:
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                choices = data.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    text = delta.get("content", "")
                    if text:
                        yield text


_OPTIONS_SYSTEM_PROMPT = """你是一个正在寻求帮助的普通人。你刚刚被问了以下问题，你需要从自己的内心出发，给出3种不同的真实回答。

规则：
1. 你不是在解释问题，而是在回答问题——就像你真的是那个困惑的人
2. 3个回答必须代表3种不同的心理状态或应对方式：
   - A：坦诚面对型——愿意直面问题，说出真实感受
   - B：犹豫保留型——还没完全想清楚，或者有些抗拒
   - C：转移/求助型——想换个角度，或者需要更多帮助
3. 每个回答必须是具体的、有内容的，不能是泛泛的"同意/不同意"
4. 回答要像真人在说话，用第一人称，简短但具体
5. 严格按以下JSON格式输出，不要输出任何其他内容：
{"options":[{"key":"A","label":"具体的回答内容"},{"key":"B","label":"具体的回答内容"},{"key":"C","label":"具体的回答内容"}]}"""


async def generate_step_options(step_title: str, step_content: str, user_context: str = "") -> list[dict[str, str]]:
    user_message = f"步骤标题：{step_title}\n\n步骤内容：\n{step_content}"
    if user_context:
        user_message += f"\n\n用户最初的问题：{user_context}"

    messages = [{"role": "user", "content": user_message}]

    if _is_anthropic_format():
        url = _normalize_url(settings.LLM_BASE_URL, "/v1/messages")
        payload = {
            "model": settings.LLM_MODEL,
            "max_tokens": 2048,
            "stream": False,
            "system": _OPTIONS_SYSTEM_PROMPT,
            "messages": messages,
        }
        headers = _anthropic_headers()
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = ""
            thinking = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
                elif block.get("type") == "thinking":
                    thinking += block.get("thinking", "")
            if not text and thinking:
                text = thinking
    else:
        url = _normalize_url(settings.LLM_BASE_URL, "/chat/completions")
        payload = {
            "model": settings.LLM_MODEL,
            "max_tokens": 2048,
            "stream": False,
            "messages": [{"role": "system", "content": _OPTIONS_SYSTEM_PROMPT}] + messages,
        }
        headers = _openai_headers()
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    try:
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            parsed = json.loads(json_match.group())
            options = parsed.get("options", [])
            if isinstance(options, list) and len(options) >= 2:
                return [{"key": o.get("key", chr(65 + i)), "label": o.get("label", "")} for i, o in enumerate(options[:3])]
    except (json.JSONDecodeError, KeyError, TypeError):
        pass

    return [
        {"key": "A", "label": "我愿意直面这个问题"},
        {"key": "B", "label": "我还没完全想清楚"},
        {"key": "C", "label": "我想换个角度看看"},
    ]


def parse_steps(full_text: str) -> list[dict]:
    step_pattern = re.compile(
        r"\*\*第([一二三四五])步[：:]\s*(.+?)\*\*\s*(.*?)(?=\*\*第[一二三四五]步|$)",
        re.DOTALL,
    )
    step_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
    steps = []
    for m in step_pattern.finditer(full_text):
        step_num = step_map.get(m.group(1), 0)
        title = m.group(2).strip()
        raw_content = m.group(3).strip()
        steps.append({"step": step_num, "title": f"第{m.group(1)}步：{title}", "content": raw_content})
    if not steps:
        steps = [{"step": 0, "title": "回复", "content": full_text}]
    return steps
