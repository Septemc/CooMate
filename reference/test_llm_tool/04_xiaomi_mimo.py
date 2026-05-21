from __future__ import annotations

import argparse
import base64
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx


SCRIPT_ID = "04_xiaomi_mimo"
PROFILE_MATCHERS = ["Xiaomi MiMo", "MiMo"]
PROFILE_KIND = "anthropic_messages"
DEFAULT_MODEL = "mimo-v2.5"
PREFER_DEFAULT_MODEL = True
PROFILE_PATH = Path.home() / ".storydex" / "config" / "llm-profiles.json"
USER_TOKEN_PATH = Path.home() / ".storydex" / "auth" / "user-token.json"
DEFAULT_MAX_ROUNDS = 6
DEFAULT_MAX_TOKENS = 700
PROBE_PREVIEW_PATH = "sample/test_llm_tool/_probe_output.txt"
PROBE_MAP_ARGS = {"maxItems": 30}
PROBE_README_ARGS = {"relativePath": "README.md", "limit": 80}

TOOL_SPECS = [
    {
        "name": "worldbook_lookup",
        "description": "Search markdown files under .storydex/worldbook and return scored matches.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 12000},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_recent_segments",
        "description": "Return the most recently modified markdown segments in the workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 8, "default": 6},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "read_character_cards",
        "description": "Read character card JSON files from .storydex/characters.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "local_semantic_search",
        "description": "Run a lightweight keyword search across markdown, text, json, and python files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 12000},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_latest_snapshot",
        "description": "Return the newest JSON snapshot found under .storydex.",
        "input_schema": {
            "type": "object",
            "properties": {
                "force": {"type": "boolean", "default": False},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "read_workspace_file",
        "description": "Read a workspace-relative file with optional line windowing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "relativePath": {"type": "string", "minLength": 1},
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 2000},
            },
            "required": ["relativePath"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_workspace_map",
        "description": "Return a flattened workspace tree capped by maxItems.",
        "input_schema": {
            "type": "object",
            "properties": {
                "maxItems": {"type": "integer", "minimum": 20, "maximum": 400, "default": 120},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "preview_segment_write",
        "description": "Preview a segment write without touching the filesystem.",
        "input_schema": {
            "type": "object",
            "properties": {
                "relativePath": {"type": "string", "minLength": 1},
                "content": {"type": "string", "default": ""},
            },
            "required": ["relativePath"],
            "additionalProperties": False,
        },
    },
]


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


class ToolModeUnsupportedError(RuntimeError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description=f"Standalone tool loop probe: {SCRIPT_ID}")
    parser.add_argument("action", choices=["models", "run"])
    parser.add_argument("--model", default="", help="Override model name")
    parser.add_argument("--prompt", default="", help="Override the default probe prompt")
    parser.add_argument("--mode", choices=["auto", "native", "json"], default="auto")
    parser.add_argument("--max-rounds", type=int, default=DEFAULT_MAX_ROUNDS)
    parser.add_argument(
        "--auth-token",
        default=os.getenv("STORYDEX_AUTH_TOKEN", "").strip(),
        help="Storydex auth token for the quota gateway. Falls back to the desktop login token.",
    )
    args = parser.parse_args()

    profile = load_profile()
    if args.action == "models":
        return probe_models(profile=profile, auth_token=args.auth_token)

    result = run_probe(
        profile=profile,
        model_override=args.model,
        prompt=args.prompt or default_prompt(resolve_model(profile, args.model)),
        mode=args.mode,
        max_rounds=max(1, args.max_rounds),
        auth_token=args.auth_token,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def load_profile() -> Dict[str, Any]:
    payload = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    profiles = payload.get("profiles") if isinstance(payload, dict) else []
    if not isinstance(profiles, list):
        raise SystemExit(f"Invalid profile file: {PROFILE_PATH}")

    lowered_matchers = [item.lower() for item in PROFILE_MATCHERS]
    for item in profiles:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        profile_id = str(item.get("id") or "").strip()
        if name in PROFILE_MATCHERS or profile_id in PROFILE_MATCHERS:
            return item
        lowered_name = name.lower()
        if any(matcher in lowered_name for matcher in lowered_matchers):
            return item
    raise SystemExit(f"Profile not found. Matchers={PROFILE_MATCHERS}")


def resolve_model(profile: Dict[str, Any], model_override: str) -> str:
    if str(model_override or "").strip():
        model = str(model_override).strip()
    elif PREFER_DEFAULT_MODEL and DEFAULT_MODEL:
        model = str(DEFAULT_MODEL).strip()
    else:
        model = str(profile.get("model") or DEFAULT_MODEL).strip()
    if not model:
        raise SystemExit("No model configured. Pass --model <model-name>.")
    return model


def default_prompt(model: str) -> str:
    preview_content = f"tool loop probe by {SCRIPT_ID} using {model}"
    return (
        "Follow this exact tool plan before the final answer: "
        f"1) call read_workspace_map with {json.dumps(PROBE_MAP_ARGS, ensure_ascii=False)}; "
        f"2) call read_workspace_file with {json.dumps(PROBE_README_ARGS, ensure_ascii=False)}; "
        "3) call preview_segment_write with "
        f"{json.dumps({'relativePath': PROBE_PREVIEW_PATH, 'content': preview_content}, ensure_ascii=False)}; "
        "4) then output strict JSON with keys final, reply, used_tools, preview_path. "
        "reply must be one short Chinese sentence. Do not skip tools."
    )


def run_probe(
    *,
    profile: Dict[str, Any],
    model_override: str,
    prompt: str,
    mode: str,
    max_rounds: int,
    auth_token: str,
) -> Dict[str, Any]:
    model = resolve_model(profile, model_override)
    last_error = ""
    if mode in {"auto", "native"}:
        try:
            return run_native_loop(
                profile=profile,
                model=model,
                prompt=prompt,
                max_rounds=max_rounds,
                auth_token=auth_token,
            )
        except ToolModeUnsupportedError as exc:
            last_error = str(exc)
            if mode == "native":
                raise SystemExit(last_error)

    if mode in {"auto", "json"}:
        result = run_json_loop(
            profile=profile,
            model=model,
            prompt=prompt,
            max_rounds=max_rounds,
            auth_token=auth_token,
        )
        if last_error:
            result["fallbackReason"] = last_error
        return result

    raise SystemExit(f"Unsupported mode: {mode}")


def run_native_loop(
    *,
    profile: Dict[str, Any],
    model: str,
    prompt: str,
    max_rounds: int,
    auth_token: str,
) -> Dict[str, Any]:
    if api_style() == "openai":
        return run_native_openai_loop(
            profile=profile,
            model=model,
            prompt=prompt,
            max_rounds=max_rounds,
            auth_token=auth_token,
        )

    messages: List[Dict[str, Any]] = [{"role": "user", "content": prompt}]
    used_tools: List[str] = []

    for round_index in range(1, max_rounds + 1):
        data = call_anthropic_native(
            profile=profile,
            model=model,
            messages=messages,
            auth_token=auth_token,
        )
        blocks = data.get("content") if isinstance(data, dict) else []
        if not isinstance(blocks, list):
            blocks = []

        tool_uses = [block for block in blocks if isinstance(block, dict) and block.get("type") == "tool_use"]
        if tool_uses:
            messages.append({"role": "assistant", "content": blocks})
            tool_results = []
            for tool_use in tool_uses:
                tool_name = str(tool_use.get("name") or "").strip()
                tool_input = tool_use.get("input") if isinstance(tool_use.get("input"), dict) else {}
                used_tools.append(tool_name)
                output = execute_tool(tool_name, tool_input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": str(tool_use.get("id") or ""),
                        "content": json.dumps(output, ensure_ascii=False),
                        "is_error": False,
                    }
                )
            messages.append({"role": "user", "content": tool_results})
            continue

        text = extract_anthropic_text(blocks)
        if not tool_sequence_complete(used_tools):
            messages.append({"role": "assistant", "content": blocks or [{"type": "text", "text": text}]})
            messages.append({"role": "user", "content": [{"type": "text", "text": next_tool_instruction(model, used_tools)}]})
            continue

        return build_result(
            protocol="native_anthropic_tools",
            model=model,
            rounds=round_index,
            used_tools=used_tools,
            final_text=text,
        )

    raise SystemExit("Native tool loop reached max rounds before completion.")


def run_json_loop(
    *,
    profile: Dict[str, Any],
    model: str,
    prompt: str,
    max_rounds: int,
    auth_token: str,
) -> Dict[str, Any]:
    if api_style() == "openai":
        return run_json_openai_loop(
            profile=profile,
            model=model,
            prompt=prompt,
            max_rounds=max_rounds,
            auth_token=auth_token,
        )

    messages: List[Dict[str, Any]] = [
        {"role": "user", "content": build_json_prompt(prompt, model)},
    ]
    used_tools: List[str] = []

    for round_index in range(1, max_rounds + 1):
        data = call_anthropic_json(
            profile=profile,
            model=model,
            messages=messages,
            auth_token=auth_token,
        )
        blocks = data.get("content") if isinstance(data, dict) else []
        if not isinstance(blocks, list):
            blocks = []
        text = extract_anthropic_text(blocks)
        payload = extract_json_payload(text)
        tool_calls = payload.get("tool_calls") if isinstance(payload.get("tool_calls"), list) else []
        final_flag = bool(payload.get("final"))

        if tool_calls:
            messages.append({"role": "assistant", "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}]})
            tool_results = []
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                tool_name = str(tool_call.get("name") or "").strip()
                raw_args = tool_call.get("arguments") if isinstance(tool_call.get("arguments"), dict) else {}
                used_tools.append(tool_name)
                tool_results.append(
                    {
                        "toolCallId": str(tool_call.get("id") or ""),
                        "name": tool_name,
                        "status": "ok",
                        "output": execute_tool(tool_name, raw_args),
                    }
                )
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "TOOL_RESULTS:\n"
                            + json.dumps(tool_results, ensure_ascii=False, indent=2)
                            + "\nContinue. "
                            + next_tool_instruction(model, used_tools),
                        }
                    ],
                }
            )
            continue

        if final_flag and tool_sequence_complete(used_tools):
            return build_result(
                protocol="json_tool_protocol",
                model=model,
                rounds=round_index,
                used_tools=used_tools,
                final_text=json.dumps(payload, ensure_ascii=False),
            )

        messages.append({"role": "assistant", "content": [{"type": "text", "text": text or json.dumps(payload, ensure_ascii=False)}]})
        messages.append({"role": "user", "content": [{"type": "text", "text": next_tool_instruction(model, used_tools)}]})

    raise SystemExit("JSON tool loop reached max rounds before completion.")


def run_native_openai_loop(
    *,
    profile: Dict[str, Any],
    model: str,
    prompt: str,
    max_rounds: int,
    auth_token: str,
) -> Dict[str, Any]:
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": build_native_system_prompt(model)},
        {"role": "user", "content": prompt},
    ]
    used_tools: List[str] = []

    for round_index in range(1, max_rounds + 1):
        data = call_openai_native(
            profile=profile,
            model=model,
            messages=messages,
            auth_token=auth_token,
        )
        message = first_openai_message(data)
        tool_calls = message.get("tool_calls") if isinstance(message.get("tool_calls"), list) else []
        if tool_calls:
            assistant_message: Dict[str, Any] = {
                "role": "assistant",
                "content": str(message.get("content") or ""),
                "tool_calls": tool_calls,
            }
            if message.get("reasoning_content"):
                assistant_message["reasoning_content"] = message["reasoning_content"]
            messages.append(assistant_message)
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                function = tool_call.get("function") if isinstance(tool_call.get("function"), dict) else {}
                tool_name = str(function.get("name") or "").strip()
                raw_arguments = str(function.get("arguments") or "{}")
                try:
                    arguments = json.loads(raw_arguments) if raw_arguments.strip() else {}
                except json.JSONDecodeError:
                    arguments = {}
                used_tools.append(tool_name)
                output = execute_tool(tool_name, arguments if isinstance(arguments, dict) else {})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": str(tool_call.get("id") or ""),
                        "content": json.dumps(output, ensure_ascii=False),
                    }
                )
            continue

        text = extract_openai_text(message)
        if not tool_sequence_complete(used_tools):
            assistant_message = {"role": "assistant", "content": text}
            if message.get("reasoning_content"):
                assistant_message["reasoning_content"] = message["reasoning_content"]
            messages.append(assistant_message)
            messages.append({"role": "user", "content": next_tool_instruction(model, used_tools)})
            continue

        return build_result(
            protocol="native_openai_tools",
            model=model,
            rounds=round_index,
            used_tools=used_tools,
            final_text=text,
        )

    raise SystemExit("Native OpenAI tool loop reached max rounds before completion.")


def run_json_openai_loop(
    *,
    profile: Dict[str, Any],
    model: str,
    prompt: str,
    max_rounds: int,
    auth_token: str,
) -> Dict[str, Any]:
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": "Return strict JSON only."},
        {"role": "user", "content": build_json_prompt(prompt, model)},
    ]
    used_tools: List[str] = []

    for round_index in range(1, max_rounds + 1):
        data = call_openai_json(
            profile=profile,
            model=model,
            messages=messages,
            auth_token=auth_token,
        )
        message = first_openai_message(data)
        text = extract_openai_text(message)
        payload = extract_json_payload(text)
        tool_calls = payload.get("tool_calls") if isinstance(payload.get("tool_calls"), list) else []
        final_flag = bool(payload.get("final"))

        if tool_calls:
            messages.append({"role": "assistant", "content": json.dumps(payload, ensure_ascii=False)})
            tool_results = []
            for tool_call in tool_calls:
                if not isinstance(tool_call, dict):
                    continue
                tool_name = str(tool_call.get("name") or "").strip()
                arguments = tool_call.get("arguments") if isinstance(tool_call.get("arguments"), dict) else {}
                used_tools.append(tool_name)
                tool_results.append(
                    {
                        "toolCallId": str(tool_call.get("id") or ""),
                        "name": tool_name,
                        "status": "ok",
                        "output": execute_tool(tool_name, arguments),
                    }
                )
            messages.append(
                {
                    "role": "user",
                    "content": "TOOL_RESULTS:\n"
                    + json.dumps(tool_results, ensure_ascii=False, indent=2)
                    + "\nContinue. "
                    + next_tool_instruction(model, used_tools),
                }
            )
            continue

        if final_flag and tool_sequence_complete(used_tools):
            return build_result(
                protocol="json_tool_protocol",
                model=model,
                rounds=round_index,
                used_tools=used_tools,
                final_text=json.dumps(payload, ensure_ascii=False),
            )

        messages.append({"role": "assistant", "content": text or json.dumps(payload, ensure_ascii=False)})
        messages.append({"role": "user", "content": next_tool_instruction(model, used_tools)})

    raise SystemExit("JSON OpenAI tool loop reached max rounds before completion.")


def build_json_prompt(prompt: str, model: str) -> str:
    tool_names = ", ".join(item["name"] for item in TOOL_SPECS)
    return (
        "Return strict JSON only. Available tools: "
        + tool_names
        + ".\n"
        + "When a tool is needed, return "
        + '{"final":false,"tool_calls":[{"id":"call-1","name":"read_workspace_map","arguments":{"maxItems":30}}]}. '
        + "When complete, return "
        + '{"final":true,"reply":"中文一句话总结","used_tools":["..."],"preview_path":"sample/test_llm_tool/_probe_output.txt"}. '
        + "No markdown fences.\n"
        + f"Model target: {model}\n"
        + f"User task: {prompt}"
    )


def next_tool_instruction(model: str, used_tools: List[str]) -> str:
    preview_args = {"relativePath": PROBE_PREVIEW_PATH, "content": f"tool loop probe by {SCRIPT_ID} using {model}"}
    progress = tool_sequence_progress(used_tools)
    if progress <= 0:
        return f"You still must call read_workspace_map with {json.dumps(PROBE_MAP_ARGS, ensure_ascii=False)}."
    if progress == 1:
        return f"You still must call read_workspace_file with {json.dumps(PROBE_README_ARGS, ensure_ascii=False)}."
    if progress == 2:
        return f"You still must call preview_segment_write with {json.dumps(preview_args, ensure_ascii=False)}."
    return "Now return the final strict JSON answer."


def tool_sequence_progress(used_tools: List[str]) -> int:
    required = ["read_workspace_map", "read_workspace_file", "preview_segment_write"]
    progress = 0
    for name in used_tools:
        if progress < len(required) and name == required[progress]:
            progress += 1
    return progress


def tool_sequence_complete(used_tools: List[str]) -> bool:
    return tool_sequence_progress(used_tools) == 3


def build_result(*, protocol: str, model: str, rounds: int, used_tools: List[str], final_text: str) -> Dict[str, Any]:
    payload = extract_json_payload(final_text)
    if "final" in payload and not isinstance(payload.get("final"), bool):
        payload["final"] = bool(payload.get("final"))
    return {
        "script": SCRIPT_ID,
        "profileKind": PROFILE_KIND,
        "protocol": protocol,
        "model": model,
        "rounds": rounds,
        "usedTools": used_tools,
        "finalText": final_text,
        "finalJson": payload,
    }


def probe_models(*, profile: Dict[str, Any], auth_token: str) -> int:
    base_url = str(profile.get("baseUrl") or "")
    if PROFILE_KIND == "quota_gateway":
        url = providers_url(base_url)
    else:
        url = models_url(base_url)
    response = httpx.get(url, headers=build_headers(profile, auth_token=auth_token), timeout=30, follow_redirects=True)
    if response.status_code == 404:
        print(f"profile={profile.get('name')} provider={profile.get('provider')}")
        print(f"url={url}")
        print("status=404")
        print("models endpoint is not exposed by this provider; use the configured target model: mimo-v2.5")
        return 0
    models = extract_models(response)
    print(f"profile={profile.get('name')} provider={profile.get('provider')}")
    print(f"url={url}")
    print(f"status={response.status_code}")
    print(f"models={models[:20]}" if models else response.text[:500])
    return 0


def providers_url(base_url: str) -> str:
    normalized = str(base_url or "").strip().rstrip("/")
    if normalized.lower().endswith("/api/providers"):
        return normalized
    return f"{normalized}/api/providers"


def messages_url(base_url: str) -> str:
    normalized = str(base_url or "").strip().rstrip("/")
    lowered = normalized.lower()
    if lowered.endswith("/v1/messages") or lowered.endswith("/messages"):
        return normalized
    if lowered.endswith("/v1"):
        return f"{normalized}/messages"
    return f"{normalized}/v1/messages"


def models_url(base_url: str) -> str:
    normalized = str(base_url or "").strip().rstrip("/")
    if normalized.lower().endswith("/models"):
        return normalized
    if normalized.lower().endswith("/v1"):
        return f"{normalized}/models"
    return f"{normalized}/v1/models"


def chat_url(base_url: str) -> str:
    normalized = str(base_url or "").strip().rstrip("/")
    if normalized.lower().endswith("/chat/completions"):
        return normalized
    return f"{normalized}/chat/completions"


def build_headers(profile: Dict[str, Any], *, auth_token: str, json_content: bool = False) -> Dict[str, str]:
    if PROFILE_KIND == "quota_gateway":
        token = ensure_auth_token(auth_token)
        headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
        if json_content:
            headers["Content-Type"] = "application/json"
            headers["x-storydex-client"] = "storydex"
        return headers

    api_key = str(profile.get("apiKey") or "").strip()
    headers: Dict[str, str]
    if PROFILE_KIND == "minimax_anthropic":
        headers = {
            "Accept": "application/json",
            "anthropic-version": "2023-06-01",
            "x-api-key": api_key,
            "Authorization": f"Bearer {api_key}",
        }
    elif PROFILE_KIND == "anthropic_messages":
        headers = {
            "Accept": "application/json",
            "anthropic-version": "2023-06-01",
            "api-key": api_key,
            "x-api-key": api_key,
        }
    else:
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
    if json_content:
        headers["Content-Type"] = "application/json"
    return headers


def call_anthropic_native(
    *,
    profile: Dict[str, Any],
    model: str,
    messages: List[Dict[str, Any]],
    auth_token: str,
) -> Dict[str, Any]:
    body = {
        "model": model,
        "max_tokens": DEFAULT_MAX_TOKENS,
        "temperature": 0,
        "system": build_native_system_prompt(model),
        "messages": messages,
        "tools": anthropic_tools(),
    }
    response = httpx.post(
        messages_url(str(profile.get("baseUrl") or "")),
        headers=build_headers(profile, auth_token=auth_token, json_content=True),
        json=body,
        timeout=120,
    )
    return parse_response_json(response, native=True)


def call_anthropic_json(
    *,
    profile: Dict[str, Any],
    model: str,
    messages: List[Dict[str, Any]],
    auth_token: str,
) -> Dict[str, Any]:
    body = {
        "model": model,
        "max_tokens": DEFAULT_MAX_TOKENS,
        "temperature": 0,
        "system": "Return strict JSON only.",
        "messages": messages,
    }
    response = httpx.post(
        messages_url(str(profile.get("baseUrl") or "")),
        headers=build_headers(profile, auth_token=auth_token, json_content=True),
        json=body,
        timeout=120,
    )
    return parse_response_json(response, native=False)


def call_openai_native(
    *,
    profile: Dict[str, Any],
    model: str,
    messages: List[Dict[str, Any]],
    auth_token: str,
) -> Dict[str, Any]:
    response = httpx.post(
        chat_url(str(profile.get("baseUrl") or "")),
        headers=build_headers(profile, auth_token=auth_token, json_content=True),
        json={
            "model": model,
            "messages": messages,
            "tools": openai_tools(),
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": 0,
        },
        timeout=120,
    )
    return parse_response_json(response, native=True)


def call_openai_json(
    *,
    profile: Dict[str, Any],
    model: str,
    messages: List[Dict[str, Any]],
    auth_token: str,
) -> Dict[str, Any]:
    response = httpx.post(
        chat_url(str(profile.get("baseUrl") or "")),
        headers=build_headers(profile, auth_token=auth_token, json_content=True),
        json={
            "model": model,
            "messages": messages,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "temperature": 0,
        },
        timeout=120,
    )
    return parse_response_json(response, native=False)


def parse_response_json(response: httpx.Response, *, native: bool) -> Dict[str, Any]:
    text = response.text[:4000]
    if response.status_code >= 400:
        lowered = text.lower()
        if native and ("tool" in lowered or "function" in lowered):
            raise ToolModeUnsupportedError(f"Native tool calling rejected by provider: {text}")
        raise SystemExit(f"Request failed with status={response.status_code}: {text}")
    payload = response.json()
    if not isinstance(payload, dict):
        raise SystemExit(f"Unexpected response payload: {text}")
    return payload


def anthropic_tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": item["name"],
            "description": item["description"],
            "input_schema": item["input_schema"],
        }
        for item in TOOL_SPECS
    ]


def openai_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": item["name"],
                "description": item["description"],
                "parameters": item["input_schema"],
            },
        }
        for item in TOOL_SPECS
    ]


def extract_anthropic_text(blocks: List[Dict[str, Any]]) -> str:
    parts: List[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            text = str(block.get("text") or "")
            if text.strip():
                parts.append(text)
    return "\n".join(parts).strip()


def first_openai_message(payload: Dict[str, Any]) -> Dict[str, Any]:
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list) or not choices:
        return {}
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message") if isinstance(first.get("message"), dict) else {}
    return message


def extract_openai_text(message: Dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return json.dumps(content, ensure_ascii=False)
    return ""


def extract_models(response: httpx.Response) -> List[str]:
    try:
        payload = response.json()
    except Exception:
        return []
    result: List[str] = []
    data = payload.get("data", payload) if isinstance(payload, dict) else payload
    providers = data.get("providers") if isinstance(data, dict) else None
    if isinstance(providers, list):
        for provider in providers:
            if not isinstance(provider, dict):
                continue
            for item in provider.get("models") or []:
                if isinstance(item, dict):
                    model_id = str(item.get("id") or item.get("name") or "").strip()
                else:
                    model_id = str(item or "").strip()
                if model_id and model_id not in result:
                    result.append(model_id)
        return result
    raw_items = payload.get("data") if isinstance(payload, dict) else payload
    if isinstance(raw_items, list):
        for item in raw_items:
            if isinstance(item, dict):
                model_id = str(item.get("id") or item.get("name") or "").strip()
            else:
                model_id = str(item or "").strip()
            if model_id and model_id not in result:
                result.append(model_id)
    return result


def execute_tool(name: str, payload: Dict[str, Any]) -> Any:
    if name == "read_workspace_map":
        return read_workspace_map(max_items=int(payload.get("maxItems") or 120))
    if name == "read_workspace_file":
        return read_workspace_file(
            relative_path=str(payload.get("relativePath") or ""),
            offset=payload.get("offset"),
            limit=payload.get("limit"),
        )
    if name == "preview_segment_write":
        return preview_segment_write(
            relative_path=str(payload.get("relativePath") or ""),
            content=str(payload.get("content") or ""),
        )
    if name == "worldbook_lookup":
        return worldbook_lookup(query=str(payload.get("query") or ""), limit=int(payload.get("limit") or 5))
    if name == "read_recent_segments":
        return read_recent_segments(limit=int(payload.get("limit") or 6))
    if name == "read_character_cards":
        return read_character_cards(limit=int(payload.get("limit") or 5))
    if name == "local_semantic_search":
        return local_semantic_search(query=str(payload.get("query") or ""), limit=int(payload.get("limit") or 5))
    if name == "read_latest_snapshot":
        return read_latest_snapshot()
    raise SystemExit(f"Unknown tool requested by model: {name}")


def workspace_root() -> Path:
    return Path.cwd()


def safe_resolve(relative_path: str) -> Path:
    normalized = str(relative_path or "").replace("\\", "/").strip().lstrip("/")
    if not normalized:
        raise SystemExit("Tool path is empty.")
    root = workspace_root().resolve()
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SystemExit(f"Path escapes workspace: {relative_path}") from exc
    return candidate


def read_workspace_file(relative_path: str, offset: Any = None, limit: Any = None) -> Dict[str, Any]:
    path = safe_resolve(relative_path)
    if not path.exists() or not path.is_file():
        raise SystemExit(f"File not found: {relative_path}")
    content = path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    offset_value = int(offset) if offset not in (None, "") else 0
    limit_value = int(limit) if limit not in (None, "") else None
    selected = lines[offset_value:]
    if limit_value is not None:
        selected = selected[:limit_value]
    partial = offset_value > 0 or (limit_value is not None and offset_value + len(selected) < len(lines))
    selected_text = "\n".join(selected)
    if not partial:
        selected_text = content
    return {
        "relativePath": relative_path.replace("\\", "/"),
        "content": selected_text,
        "lineCount": len(lines),
        "offset": offset_value if partial else None,
        "limit": limit_value if partial else None,
        "isPartialView": partial,
        "kind": "file",
        "extension": path.suffix.lower(),
        "size": len(content.encode("utf-8")),
    }


def read_workspace_map(max_items: int = 120) -> Dict[str, Any]:
    root = workspace_root().resolve()
    max_items = max(20, min(int(max_items), 400))
    items: List[Dict[str, Any]] = []
    skipped = {".git", "node_modules", ".python39", ".pytest_cache", "__pycache__", "artifacts", "release"}

    def walk(current: Path) -> None:
        if len(items) >= max_items:
            return
        try:
            children = sorted(current.iterdir(), key=lambda item: (item.is_file(), item.name.lower()))
        except OSError:
            return
        for child in children:
            if len(items) >= max_items:
                return
            rel = child.relative_to(root).as_posix()
            if child.name in skipped:
                continue
            if child.is_dir():
                try:
                    child_count = len(list(child.iterdir()))
                except OSError:
                    child_count = 0
                items.append({"relativePath": rel, "kind": "directory", "childCount": child_count})
                walk(child)
            else:
                items.append({"relativePath": rel, "kind": "file", "extension": child.suffix.lower()})

    walk(root)
    return {
        "workspaceRoot": root.as_posix(),
        "storydexRoot": (root / ".storydex").as_posix(),
        "projectName": root.name,
        "defaultFile": "README.md" if (root / "README.md").exists() else "",
        "requiresInitialization": not (root / ".storydex").exists(),
        "items": items,
    }


def preview_segment_write(relative_path: str, content: str) -> Dict[str, Any]:
    path = safe_resolve(relative_path)
    exists = path.exists()
    compact = " ".join(content.split())
    preview = compact[:317] + "..." if len(compact) > 320 else compact
    return {
        "relativePath": relative_path.replace("\\", "/"),
        "exists": exists,
        "changeType": "overwrite" if exists else "create",
        "lineCount": len(content.splitlines()) if content else 0,
        "contentPreview": preview,
    }


def worldbook_lookup(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    worldbook_dir = workspace_root() / ".storydex" / "worldbook"
    if not worldbook_dir.exists():
        return []
    keywords = [item.lower() for item in query.split() if item.strip()]
    results: List[Dict[str, Any]] = []
    for file_path in worldbook_dir.rglob("*.md"):
        if not file_path.is_file():
            continue
        content = file_path.read_text(encoding="utf-8", errors="replace")
        lowered = content.lower()
        score = sum(lowered.count(keyword) for keyword in keywords)
        if score <= 0:
            continue
        snippet = " ".join(content.split())
        if len(snippet) > 220:
            snippet = snippet[:217] + "..."
        results.append(
            {
                "relativePath": file_path.relative_to(workspace_root()).as_posix(),
                "score": score,
                "snippet": snippet,
            }
        )
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[: max(1, min(limit, 10))]


def read_recent_segments(limit: int = 6) -> List[Dict[str, Any]]:
    candidates: List[Path] = []
    for pattern in ("chapters/**/*.md", "docs/**/*.md", "sample/**/*.md", "*.md"):
        candidates.extend(workspace_root().glob(pattern))
    files = [path for path in candidates if path.is_file()]
    unique_files: Dict[str, Path] = {path.resolve().as_posix(): path for path in files}
    ordered = sorted(unique_files.values(), key=lambda path: path.stat().st_mtime, reverse=True)
    result: List[Dict[str, Any]] = []
    for path in ordered[: max(1, min(limit, 8))]:
        result.append(
            {
                "relativePath": path.relative_to(workspace_root()).as_posix(),
                "updatedAt": path.stat().st_mtime,
                "size": path.stat().st_size,
            }
        )
    return result


def read_character_cards(limit: int = 5) -> List[Dict[str, Any]]:
    cards_dir = workspace_root() / ".storydex" / "characters"
    if not cards_dir.exists():
        return []
    result: List[Dict[str, Any]] = []
    files = sorted(cards_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in files[: max(1, min(limit, 10))]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        result.append(
            {
                "relativePath": path.relative_to(workspace_root()).as_posix(),
                "name": payload.get("name") or path.stem,
                "state": payload.get("state", {}),
            }
        )
    return result


def local_semantic_search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    keywords = [item.lower() for item in query.split() if item.strip()]
    if not keywords:
        return []
    files: List[Path] = []
    for pattern in ("README.md", "docs/**/*.md", "sample/**/*.py", "apps/backend/**/*.py"):
        files.extend(workspace_root().glob(pattern))
    results: List[Dict[str, Any]] = []
    for path in files[:300]:
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        lowered = content.lower()
        score = sum(lowered.count(keyword) for keyword in keywords)
        if score <= 0:
            continue
        snippet = " ".join(content.split())
        if len(snippet) > 220:
            snippet = snippet[:217] + "..."
        results.append(
            {
                "relativePath": path.relative_to(workspace_root()).as_posix(),
                "score": score,
                "snippet": snippet,
            }
        )
    results.sort(key=lambda item: item["score"], reverse=True)
    return results[: max(1, min(limit, 20))]


def read_latest_snapshot() -> Dict[str, Any]:
    storydex_root = workspace_root() / ".storydex"
    if not storydex_root.exists():
        return {}
    snapshots = [path for path in storydex_root.rglob("*.json") if path.is_file()]
    if not snapshots:
        return {}
    latest = max(snapshots, key=lambda path: path.stat().st_mtime)
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except Exception:
        payload = {"raw": latest.read_text(encoding="utf-8", errors="replace")}
    return {
        "relativePath": latest.relative_to(workspace_root()).as_posix(),
        "updatedAt": latest.stat().st_mtime,
        "payload": payload,
    }


def build_native_system_prompt(model: str) -> str:
    return (
        f"You are running a tool-loop probe for {model}. "
        "You must use the provided tools before the final answer. "
        "Keep tool arguments minimal and valid. "
        "When done, output strict JSON with keys final, reply, used_tools, preview_path."
    )


def api_style() -> str:
    return "openai" if PROFILE_KIND == "openai_compatible" else "anthropic"


def extract_json_payload(text: str) -> Dict[str, Any]:
    candidate = first_json_candidate(text)
    if not candidate:
        return {}
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def first_json_candidate(text: str) -> str:
    content = str(text or "").strip()
    if not content:
        return ""
    if content.startswith("{") and content.endswith("}"):
        return content
    fenced = extract_fenced_block(content)
    if fenced:
        return fenced
    start = content.find("{")
    if start < 0:
        return ""
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(content)):
        char = content[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1]
    return ""


def extract_fenced_block(text: str) -> str:
    marker = "```"
    start = text.find(marker)
    if start < 0:
        return ""
    language_end = text.find("\n", start + len(marker))
    if language_end < 0:
        return ""
    end = text.find(marker, language_end + 1)
    if end < 0:
        return ""
    return text[language_end + 1 : end].strip()


def _dpapi_unprotect(encrypted: bytes, entropy: bytes) -> bytes:
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_buffer = ctypes.create_string_buffer(encrypted)
    in_blob = _DATA_BLOB(len(encrypted), ctypes.cast(in_buffer, ctypes.POINTER(ctypes.c_char)))
    entropy_buffer = ctypes.create_string_buffer(entropy) if entropy else None
    entropy_blob = _DATA_BLOB(len(entropy), ctypes.cast(entropy_buffer, ctypes.POINTER(ctypes.c_char))) if entropy else None
    out_blob = _DATA_BLOB()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        ctypes.byref(entropy_blob) if entropy_blob is not None else None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    ):
        raise RuntimeError("DPAPI CryptUnprotectData failed")
    try:
        pointer = ctypes.cast(out_blob.pbData, ctypes.POINTER(ctypes.c_ubyte))
        return bytes(pointer[i] for i in range(int(out_blob.cbData)))
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(out_blob.pbData)


def load_decrypted_token() -> str:
    if not USER_TOKEN_PATH.exists():
        raise SystemExit(f"Token file not found: {USER_TOKEN_PATH}")
    payload = json.loads(USER_TOKEN_PATH.read_text(encoding="utf-8"))
    scheme = str(payload.get("scheme") or "").strip().lower()
    user_id = str(payload.get("userId") or "").strip()
    ciphertext_b64 = str(payload.get("ciphertext") or "").strip()
    if not ciphertext_b64:
        raise SystemExit("Token file has no ciphertext.")
    encrypted = base64.b64decode(ciphertext_b64)
    if scheme != "dpapi-v1":
        raise SystemExit(f"Unsupported token scheme: {scheme}")
    raw = _dpapi_unprotect(encrypted, entropy=user_id.encode("utf-8"))
    decoded = json.loads(raw.decode("utf-8"))
    access_token = str(decoded.get("accessToken") or "").strip()
    if not access_token:
        raise SystemExit("Decrypted token has no accessToken.")
    return access_token


def ensure_auth_token(auth_token: str) -> str:
    token = str(auth_token or "").strip()
    return token or load_decrypted_token()


if __name__ == "__main__":
    raise SystemExit(main())
