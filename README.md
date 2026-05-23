# CooMate

想清楚，再出发。

CooMate 是一个基于 AI 对话的认知引导工具。它不直接给答案，而是通过 5 步结构化提问，引导你自己理清思路、找到答案。

## 核心理念

CooMate 通过"咨询师-来访者"双角色架构实现深度引导：

- **主流程**：AI 扮演认知咨询师，逐步提出 5 个结构化问题
- **选项生成**：独立 LLM 调用，以用户视角生成具体的回答选项（而非泛泛的"同意/不同意"）
- **复盘报告**：完成 5 步后，基于完整对话记录生成深度认知复盘报告

### 5 步引导流程

1. **反问成立性** — 质疑问题本身是否成立
2. **深挖追问** — 暴露隐藏的假设和情绪
3. **复盘与情绪标记** — 识别防御、逃避和循环模式
4. **多角度思考题** — 从不同维度探索问题
5. **一个微型实验** — 给出下一分钟就能执行的行动

## 功能特性

- 5 步逐步交互式对话（非一次性输出）
- 每步提供 A/B/C 选项 + 自定义输入 + 跳过
- 独立 API 生成具体选项（并行预加载）
- 结构化 Markdown 复盘报告（含对话回顾表格、情绪模式、未被回应的问题）
- SSE 流式输出
- 会话保存与历史查看
- 用户名注册/登录（支持游客模式）
- 响应式设计

## 技术栈

**前端：**
- Vue 3 + TypeScript
- Vite
- Pinia 状态管理
- CSS 自定义属性（Design Tokens）

**后端：**
- Python FastAPI
- SQLAlchemy ORM
- PostgreSQL
- httpx 异步客户端

## 快速开始

### 前置要求

- Python 3.9+（推荐 Conda 管理）
- Node.js 18+
- PostgreSQL

### 安装步骤

1. 克隆项目
```bash
git clone https://github.com/Septemc/CooMate.git
cd CooMate
```

2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，配置你的 LLM API 密钥和数据库连接
```

3. 安装后端依赖
```bash
pip install -r apps/backend/requirements.txt
```

4. 安装前端依赖
```bash
cd apps/frontend
npm install
```

5. 初始化数据库
```bash
cd apps/backend
python -c "from database import init_db; init_db()"
```

6. 启动服务

**方式一：使用启动脚本（Windows）**
```bash
start-dev.bat
```

**方式二：手动启动**
```bash
# 终端 1 - 后端
cd apps/backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8266

# 终端 2 - 前端
cd apps/frontend
npm run dev
```

7. 访问应用
- 前端：http://localhost:5066
- 后端 API：http://localhost:8266

## 项目结构

```
CooMate/
├── .env.example            # 环境变量示例
├── .gitignore              # Git 忽略配置
├── start-dev.bat           # Windows 启动脚本
├── requirements.txt        # Python 依赖
├── docs/
│   ├── DESIGN.md           # 设计文档
│   └── system_prompt.txt   # AI 系统提示词
├── apps/
│   ├── backend/            # 后端服务
│   │   ├── main.py         # FastAPI 入口
│   │   ├── config.py       # 配置管理
│   │   ├── llm_client.py   # LLM 调用 + 选项生成
│   │   ├── database.py     # 数据库管理
│   │   ├── auth.py         # 认证模块（用户名登录）
│   │   ├── routers/
│   │   │   └── chat.py     # 聊天 + 选项生成 API
│   │   └── models/
│   │       └── schemas.py  # Pydantic 模型
│   └── frontend/           # 前端应用
│       └── src/
│           ├── components/  # Vue 组件
│           ├── stores/      # Pinia 状态管理
│           ├── services/    # API 服务
│           ├── types/       # TypeScript 类型
│           └── views/       # 页面视图
└── reference/              # 参考代码
```

## API 端点

### 聊天
- `POST /api/chat` — 发送消息（SSE 流式响应）
- `POST /api/chat/generate-options` — 生成步骤选项
- `GET /api/conversations` — 获取会话列表
- `GET /api/conversations/{id}` — 获取会话详情
- `DELETE /api/conversations/{id}` — 删除会话

### 认证
- `POST /api/auth/register` — 用户注册（用户名）
- `POST /api/auth/login` — 用户登录
- `POST /api/auth/guest` — 游客登录
- `POST /api/auth/logout` — 退出登录

## 配置说明

在 `.env` 文件中配置以下变量：

```env
# LLM Provider
LLM_BASE_URL=https://token-plan-cn.xiaomimimo.com/anthropic
LLM_API_KEY=your-api-key-here
LLM_MODEL=mimo-v2.5-pro
LLM_PROVIDER=anthropic_messages

# Server
HOST=0.0.0.0
PORT=8266
DEBUG=true

# CORS
CORS_ORIGINS=http://localhost:5066,http://localhost:3000,http://127.0.0.1:5066

# Database (PostgreSQL)
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/coomate
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

MIT License
