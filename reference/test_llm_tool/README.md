# test_llm_tool

这里放的是 5 份独立的工具调用参考脚本，工具 schema 对齐 `apps/backend` 当前实现，并且每份都带完整 tool loop。

对应关系：
- `01_account_quota.py` -> `账号额度` -> `MiniMax-M2.7`
- `02_minimax.py` -> `MiniMax` -> `MiniMax-M2.7`
- `03_deepseek_v4_pro.py` -> `OpenCodeGO` -> `deepseek-v4-pro`
- `04_xiaomi_mimo.py` -> `Xiaomi MiMo` -> `mimo-v2.5`
- `05_gemini_3_1_pro_preview.py` -> `GG公益站` -> `gemini-3.1-pro-preview`

常用命令：
```bash
python sample/test_llm_tool/02_minimax.py models
python sample/test_llm_tool/02_minimax.py run
python sample/test_llm_tool/03_deepseek_v4_pro.py run --mode native
python sample/test_llm_tool/05_gemini_3_1_pro_preview.py run --mode json
```

说明：
- `models`：探测当前 profile 可见模型。
- `run`：执行完整工具链。
- 默认是 `--mode auto`：优先原生工具调用，若提供商不支持，再自动降级到 JSON tool protocol。
- 5 份脚本互相独立，不引用 `apps/backend` 里的 Python 代码。
- 工具定义对齐后端当前 8 个业务工具：`worldbook_lookup`、`read_recent_segments`、`read_character_cards`、`local_semantic_search`、`read_latest_snapshot`、`read_workspace_file`、`read_workspace_map`、`preview_segment_write`。
- `03_deepseek_v4_pro.py` 与 `05_gemini_3_1_pro_preview.py` 现在统一为同一套更干净的 OpenAI-compatible 模板：原生 `tools/tool_calls`、JSON fallback、`429` 限流重试、统一错误收口。
- `01_account_quota.py` 的真实执行依赖额度网关当前余额；若当前账号无额度，会直接返回网关错误。
- `05_gemini_3_1_pro_preview.py` 若 `gemini-3.1-pro-preview` 被限流，会自动尝试 `gemini-3.1-pro-preview-low` 作为回退模型。
