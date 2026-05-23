# CooMate 项目设计文档

## 1. 项目概述

CooMate 是一个基于对话的 AI 认知参谋。核心理念：**不直接给答案，而是通过结构化提问引导用户自己找到答案**。

适用场景：情感困惑、创意发散、学习路线规划、决策分析。

## 2. 架构总览

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (Vue 3)                  │
│  Vite + Vue 3 + TypeScript + TailwindCSS + Pinia     │
│  单页对话界面，5 步结构化显示                          │
└────────────────────┬────────────────────────────────┘
                     │ HTTP / SSE
                     ▼
┌─────────────────────────────────────────────────────┐
│                   Backend (FastAPI)                   │
│  Python 3.11+ + FastAPI + httpx + SSE                │
│  REST API + Streaming SSE                            │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              LLM Provider (可切换)                    │
│  OpenCodeGO / MiniMax / Xiaomi MiMo / GG公益站       │
│  统一 Anthropic Messages API 兼容协议                 │
└─────────────────────────────────────────────────────┘
```

## 3. 目录结构

```
CooMate/
├── .env                        # 环境变量（API 密钥、模型配置）
├── .gitignore
├── docs/
│   ├── prompt.txt              # 通用认知参谋提示词（参考）
│   ├── system_prompt.txt       # CooMate 完整系统提示词
│   └── DESIGN.md               # 本设计文档
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置加载（从 .env）
│   ├── llm_client.py           # LLM 统一调用客户端
│   ├── routers/
│   │   └── chat.py             # 聊天相关 API 路由
│   ├── models/
│   │   └── schemas.py          # Pydantic 数据模型
│   └── requirements.txt        # Python 依赖
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── tailwind.config.js
    ├── tsconfig.json
    ├── src/
    │   ├── main.ts             # Vue 入口
    │   ├── App.vue             # 根组件
    │   ├── env.d.ts            # 类型声明
    │   ├── stores/
    │   │   └── chat.ts         # Pinia store - 对话状态管理
    │   ├── services/
    │   │   └── api.ts          # API 调用封装（SSE 流式）
    │   ├── components/
    │   │   ├── ChatInput.vue   # 输入框组件
    │   │   ├── ChatMessage.vue # 单条消息组件（含 5 步结构化渲染）
    │   │   ├── ChatPanel.vue   # 对话面板
    │   │   └── StepSection.vue # 单步内容渲染
    │   └── types/
    │       └── index.ts        # TypeScript 类型定义
    └── public/
```

## 4. API 设计

### 4.1 POST /api/chat

发送用户消息，返回 AI 流式回复（SSE）。

**Request:**
```json
{
  "message": "我纠结要不要分手",
  "conversation_id": "uuid-xxx",  // 可选，续接对话
  "action": "chat"                // chat | regenerate_angles | export_review
}
```

**Response (SSE stream):**
```
data: {"type": "step", "step": 1, "content": "第一步：反问成立性\n..."}
data: {"type": "step", "step": 2, "content": "第二步：深挖追问\n..."}
data: {"type": "step", "step": 3, "content": "第三步：复盘与情绪标记\n..."}
data: {"type": "step", "step": 4, "content": "第四步：多角度思考题\n..."}
data: {"type": "step", "step": 5, "content": "第五步：一个微型实验\n..."}
data: {"type": "done", "conversation_id": "uuid-xxx"}
```

### 4.2 GET /api/conversations

获取历史对话列表。

### 4.3 GET /api/conversations/{id}

获取指定对话详情。

### 4.4 DELETE /api/conversations/{id}

删除指定对话。

## 5. 前端组件设计

### 5.1 App.vue
- 左侧：对话列表侧边栏
- 右侧：ChatPanel 对话面板

### 5.2 ChatPanel.vue
- 消息列表区域（滚动）
- ChatInput 输入框（底部固定）
- 顶栏操作按钮：换个角度、导出复盘

### 5.3 ChatMessage.vue
- 用户消息：简单气泡
- AI 消息：5 步结构化卡片，每步用不同颜色标识
  - 第一步（反问）：蓝色标识
  - 第二步（追问）：绿色标识
  - 第三步（复盘）：黄色标识
  - 第四步（多角度）：紫色标识
  - 第五步（实验）：橙色标识

### 5.4 StepSection.vue
- 渲染 Markdown 格式的单步内容
- 支持流式逐字显示
- 追问步骤中的问题高亮显示

## 6. 数据模型

### 6.1 前端 TypeScript 类型

```typescript
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  steps?: StepContent[];  // AI 回复的 5 步结构
  timestamp: number;
}

interface StepContent {
  step: number;       // 1-5
  title: string;      // 步骤标题
  content: string;    // 步骤内容
}

interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}
```

### 6.2 后端 Pydantic 模型

```python
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    action: str = "chat"  # chat | regenerate_angles | export_review

class StepChunk(BaseModel):
    type: str  # "step" | "done"
    step: Optional[int] = None
    content: Optional[str] = None
    conversation_id: Optional[str] = None
```

## 7. LLM 调用策略

### 7.1 消息格式
采用 Anthropic Messages API 兼容格式：
```json
{
  "model": "deepseek-v4-flash",
  "max_tokens": 2048,
  "stream": true,
  "system": "<system_prompt>",
  "messages": [
    {"role": "user", "content": "用户消息"},
    {"role": "assistant", "content": "历史回复"},
    ...
  ]
}
```

### 7.2 Provider 适配
通过 `.env` 中的 `LLM_PROVIDER` 字段适配不同 provider：
- `openai_compatible`: 标准 OpenAI 兼容接口（OpenCodeGO、GG公益站）
- `minimax_anthropic`: MiniMax 的 Anthropic 兼容接口
- `anthropic_messages`: 标准 Anthropic Messages 接口（Xiaomi MiMo）

### 7.3 流式输出解析
SSE 流式解析 Anthropic 格式：
```json
{"type": "content_block_delta", "delta": {"type": "text_delta", "text": "片段"}}
```

## 8. 功能优先级

### P0 - MVP 核心
- [x] 对话界面 + 5 步结构化显示
- [x] 流式输出
- [x] 历史对话存储（localStorage）

### P1 - 增强体验
- [ ] "换个角度"按钮（重新生成第四步）
- [ ] "导出复盘"功能（Markdown 报告）
- [ ] 对话列表管理

### P2 - 后续迭代
- [ ] 多轮上下文优化
- [ ] 情绪分析可视化
- [ ] 自定义认知模型训练

## 9. 启动方式

### 后端
```bash
cd backend
pip install -r requirements.txt
python main.py
# 或 uvicorn main:app --reload --port 8000
```

### 前端
```bash
cd frontend
npm install
npm run dev
# 访问 http://localhost:5173
```
