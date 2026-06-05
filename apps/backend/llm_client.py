from __future__ import annotations

import json
import re
from typing import AsyncIterator

import httpx

from config import settings

def _get_system_prompt() -> str:
    prompt_path = settings._prompt_path
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return "你是 CooMate，用户的专属 AI 认知参谋。通过结构化提问引导用户自己找到答案。"


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


def resolve_chat_action(action: str, has_assistant_history: bool, multi_probe: bool = False) -> str:
    if action != "chat":
        return action
    if not has_assistant_history:
        return "chat"
    return "multi_probe" if multi_probe else "follow_up"


_FOLLOW_UP_SYSTEM_PROMPT = """你是 CooMate——用户的专属 AI 认知参谋。

当前不是首次建模。首次五步流程已经完成或正在当前会话中存在，因此这次不要再输出五步结构。

你的任务：
1. 用1-2句承接用户刚刚说的话，指出其中最需要继续澄清的点
2. 只提出1个最能推进对话的问题
3. 不要给结论性建议，不要替用户做决定
4. 不要输出选项列表，不要使用"第一步/第二步"等五步标题
5. 问题要具体但不压迫，适合用户自然继续回答
"""


_MULTI_PROBE_SYSTEM_PROMPT = """你是 CooMate——用户的专属 AI 认知参谋。

当前开启了轻量多面追问。首次五步流程已经完成或正在当前会话中存在，因此这次不要再输出完整五步结构。

你的任务：
1. 用1句话承接用户刚刚说的话
2. 按当前上下文只提出1到2个问题；只有确有必要时才问第2个
3. 问题应来自不同维度，例如事实、情绪、需求、代价、下一步行动
4. 按和首次对话相同的步骤标题格式输出，便于前端为每个问题生成选项和自定义输入：
   **第一步：简短标题**
   具体问题
   **第二步：简短标题**
   具体问题
5. 不要超过2个问题，不要给结论性建议，不要替用户做决定
6. 不要在正文里手写 A/B/C 选项；每一步的选项会由独立接口生成
7. 不要在最后询问额外补充信息
"""


_SUMMARY_SYSTEM_PROMPT = """你是 CooMate——用户的专属 AI 认知参谋。

当前任务是生成结构化复盘报告。不要使用五步提问结构，不要继续追问，直接根据用户提供的对话记录输出报告。
"""


async def stream_chat(
    messages: list[dict],
    action: str = "chat",
) -> AsyncIterator[str]:
    """Stream LLM response as plain text chunks."""

    if action == "follow_up":
        system_prompt = _FOLLOW_UP_SYSTEM_PROMPT
    elif action == "multi_probe":
        system_prompt = _MULTI_PROBE_SYSTEM_PROMPT
    elif action == "summarize":
        system_prompt = _SUMMARY_SYSTEM_PROMPT
    else:
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
            resp.raise_for_status()
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
            resp.raise_for_status()
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
4. 回答必须停留在宏观层面：表达可普遍选择的内心状态、倾向、顾虑或需要
5. 不要编造用户没有提供的具体事件、时间、地点、人物行为、争吵细节或身体反应
6. 如果用户只说"纠结要不要分手"，不要写成"昨天他和我吵架"这类具体经历
7. 回答要像真人在说话，用第一人称，简短但具体
8. 严格按以下JSON格式输出，不要输出任何其他内容：
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


_STEP_MAP = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
_STEP_NUM_TO_CN = {v: k for k, v in _STEP_MAP.items()}
_INTAKE_TITLES = {
    1: "反问成立性",
    2: "深挖追问",
    3: "复盘与情绪标记",
    4: "多角度思考题",
    5: "一个微型实验",
}
_INTAKE_FALLBACK_QUESTIONS = {
    1: "你现在纠结的前提，是这段关系还有修复空间，还是你只是还没有准备好离开？",
    2: "你第一次认真冒出这个念头，是从哪一个具体时刻开始的？",
    3: "你在这段关系里最反复出现的感受是什么？",
    4: "如果暂时放下害怕，你最想先确认的事实是什么？",
    5: "你愿意现在写下这段关系里最不能接受的一件事是什么吗？",
}


def _match_step_heading(line: str) -> tuple[int, str] | None:
    match = re.match(
        r"^\s*(?:#{1,6}\s*)?(?:\*\*)?第([一二三四五])步[：:]\s*([^*\n#]+?)(?:\*\*)?(?:\s*.*)?$",
        line.strip(),
    )
    if not match:
        return None
    return _STEP_MAP[match.group(1)], match.group(2).strip()


def _strip_markdown_noise(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^\s*(?:[-*+]\s+|\d+[.、]\s*)", "", line)
    line = re.sub(r"^>+\s*", "", line)
    line = re.sub(r"^第[一二三四五六七八九十]+个追问[：:]?\s*", "", line)
    line = re.sub(r"^[\w\u4e00-\u9fff]{2,10}视角[：:]?\s*", "", line)
    line = re.sub(r"[*_`#]", "", line)
    return line.strip(" \t\"'“”")


def _first_question(content: str, step_num: int) -> str:
    content = re.sub(r"\[OPTIONS\][\s\S]*?\[/OPTIONS\]", "", content).strip()
    for raw_line in content.splitlines():
        line = _strip_markdown_noise(raw_line)
        if not line or set(line) <= {"-"}:
            continue
        question_marks = [idx for idx in (line.find("？"), line.find("?")) if idx >= 0]
        if not question_marks:
            continue
        end_idx = min(question_marks)
        question = line[: end_idx + 1].strip()
        if question:
            return _limit_question(question)
    return _INTAKE_FALLBACK_QUESTIONS.get(step_num, "你现在最需要先回答自己的那个问题是什么？")


def _limit_question(question: str, max_len: int = 120) -> str:
    question = re.sub(r"\s+", " ", question).strip()
    if len(question) <= max_len:
        return question
    question = question[: max_len - 1].rstrip("，,；;：:、。！？?")
    return f"{question}？"


def _canonical_step(step_num: int, content: str) -> dict:
    cn_num = _STEP_NUM_TO_CN[step_num]
    return {
        "step": step_num,
        "title": f"第{cn_num}步：{_INTAKE_TITLES[step_num]}",
        "content": _first_question(content, step_num),
    }


def steps_to_markdown(steps: list[dict]) -> str:
    if not steps or steps[0].get("step", 0) <= 0:
        return steps[0].get("content", "") if steps else ""
    return "\n\n".join(f"**{step['title']}**\n{step['content']}" for step in steps)


def parse_steps(
    full_text: str,
    require_full_intake: bool = False,
    user_context: str = "",
) -> list[dict]:
    parsed_steps: list[dict] = []
    current: dict | None = None

    for line in full_text.splitlines():
        heading = _match_step_heading(line)
        if heading:
            if current:
                parsed_steps.append(current)
            step_num, title = heading
            current = {"step": step_num, "title": title, "content_lines": []}
            continue
        if current:
            current["content_lines"].append(line)

    if current:
        parsed_steps.append(current)

    if not parsed_steps:
        if require_full_intake:
            parsed_steps = [
                {"step": step_num, "title": _INTAKE_TITLES[step_num], "content_lines": [user_context]}
                for step_num in range(1, 6)
            ]
        else:
            return [{"step": 0, "title": "回复", "content": full_text}]

    if require_full_intake:
        by_step = {
            step["step"]: "\n".join(step["content_lines"]).strip()
            for step in parsed_steps
            if step["step"] in _INTAKE_TITLES
        }
        return [
            _canonical_step(step_num, by_step.get(step_num) or user_context)
            for step_num in range(1, 6)
        ]

    steps = []
    for step in parsed_steps:
        step_num = step["step"]
        cn_num = _STEP_NUM_TO_CN[step_num]
        raw_content = "\n".join(step["content_lines"]).strip()
        steps.append({
            "step": step_num,
            "title": f"第{cn_num}步：{step['title']}",
            "content": _first_question(raw_content, step_num),
        })
    return steps
