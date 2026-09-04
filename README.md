# 忆码 YiCode v2.0

> AI-Powered LeetCode Hot 100 Tracker — 你的智能刷题伴侣
> Phase 3: 真实 LLM 接入 + 用户认证 + 数据导出

[![Tests](https://github.com/zsszc/YiCode/actions/workflows/ci.yml/badge.svg)](https://github.com/zsszc/YiCode/actions)

---

## 快速开始

### Docker 一键启动

```bash
docker-compose up --build
```

- 后端 API: http://localhost:8000
- 前端页面: http://localhost:5173
- API 文档: http://localhost:8000/docs

### 本地开发

**后端**
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**前端**
```bash
cd frontend
npm install
npm run dev
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12, FastAPI, SQLAlchemy 2.0, SQLite |
| 前端 | React 18, TypeScript, Tailwind CSS, TanStack Query |
| 部署 | Docker, docker-compose |
| 测试 | pytest (68 tests) |

---

## Phase 1 核心功能

- 📋 **每日看板** — 自动计算到期复习题 + 新题配额
- 🧠 **SM-2 复习调度** — 简化遗忘曲线算法
- 📝 **题目管理** — Hot 100 + 自定义题目
- 🏷️ **进度追踪** — forgot / shaky / solid / archived 四档状态
- 📊 **未来预告** — 前向模拟未来 30 天复习计划

## Phase 2 新增功能

### 🤖 AI Tutor
- **分级解题提示** — 3 级提示（思路 → 算法框架 → 关键代码）
- **代码审查** — 自动分析时间/空间复杂度 + 优化建议
- **可插拔 LLM 架构** — 默认 mock 实现，支持切换真实 LLM provider

### 📈 自适应学习系统
- **学习画像建模** — 追踪解题时间、提示依赖率、首次尝试成功率
- **AI 自适应配额** — 基于画像动态调整每日新题比例和难度分布

### 💬 飞书 Bot
- **对话式刷题** — 在飞书中查看今日看板、复习列表、学习统计
- **飞书卡片消息** — 美观的交互式卡片

## Phase 3 新增功能

### 🔌 真实 LLM 接入
- **Kimi (Moonshot AI) Provider** — 接入 Kimi API，真实 AI 解题提示
- **OpenAI-compatible Provider** — 支持 OpenAI / Azure / 兼容 API
- **自动 Fallback** — 无 API key 时自动使用 Mock Provider
- **环境变量配置** — `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`

### 🔐 用户认证系统
- **JWT Token 认证** — 注册 / 登录 / Token 刷新
- **密码安全** — bcrypt 哈希，不存储明文
- **多用户隔离** — 每个用户独立的进度、画像、行为日志
- **向后兼容** — 未登录时自动使用默认用户

### 📤 数据导出
- **进度导出** — JSON 格式导出全部刷题进度
- **画像导出** — 导出学习画像 + 复习历史

---

## 环境变量配置

创建 `.env` 文件：

```bash
# 数据库
DATABASE_URL=sqlite:///./data/yicode.db

# LLM (可选，不配置则使用 Mock)
LLM_PROVIDER=kimi          # mock | kimi | openai
LLM_API_KEY=your-api-key
LLM_MODEL=moonshot-v1-8k   # 或 gpt-4o-mini

# 飞书 Bot (可选)
FEISHU_WEBHOOK=your-webhook-url
```

---

## API 概览

| 模块 | 路径 | 描述 |
|------|------|------|
| Dashboard | `GET /api/v1/dashboard` | 今日看板 |
| Problems | `GET /api/v1/problems` | 题目列表 |
| Review | `POST /api/v1/review/{id}` | 复习打分 |
| **Auth** | `POST /api/v1/auth/register` | 用户注册 |
| **Auth** | `POST /api/v1/auth/login` | 用户登录 |
| **Auth** | `GET /api/v1/auth/me` | 当前用户 |
| AI Tutor | `POST /api/v1/tutor/hint` | 解题提示 |
| AI Tutor | `POST /api/v1/tutor/review-code` | 代码审查 |
| Profile | `GET /api/v1/profile` | 学习画像 |
| Profile | `GET /api/v1/profile/adaptive` | 自适应推荐 |
| **Export** | `GET /api/v1/export/progress` | 导出进度 |
| Feishu | `POST /api/v1/feishu/webhook` | 飞书 Bot 回调 |

---

## 项目结构

```
YiCode/
├── backend/
│   ├── app/
│   │   ├── core/           # 数据库、安全、异常
│   │   │   └── security.py   # JWT + bcrypt
│   │   ├── models/         # SQLAlchemy 模型
│   │   ├── routers/        # API 路由
│   │   │   ├── auth.py         # 注册/登录
│   │   │   ├── tutor.py        # AI Tutor
│   │   │   ├── profile.py      # 学习画像
│   │   │   ├── feishu.py       # 飞书 Bot
│   │   │   └── export.py       # 数据导出
│   │   └── services/       # 业务逻辑
│   │       ├── ai_tutor_service.py
│   │       ├── llm_providers/  # 可插拔 LLM
│   │       │   ├── base.py
│   │       │   ├── mock_provider.py
│   │       │   ├── kimi_provider.py
│   │       │   └── openai_provider.py
│   │       └── learning_profile_service.py
│   └── tests/              # pytest (68 tests)
├── frontend/
│   └── src/
│       ├── pages/          # 页面组件
│       │   ├── AuthPage.tsx       # 登录/注册
│       │   ├── ProblemDetailPage.tsx
│       │   └── SettingsPage.tsx
│       └── services/       # API 客户端
├── data/                   # SQLite 数据文件
└── docs/                   # 设计文档 (SDD)
```

---

## 测试

```bash
cd backend
python -m pytest tests/ -v
```

**Phase 1**: 31 tests — Dashboard, Problems, Review, SM-2  
**Phase 2**: 28 tests — AI Tutor, Learning Profile, Feishu Bot  
**Phase 3**: 9 tests — Auth, Security, LLM Provider  
**Total**: 68 tests ✅

---

*一天一点，不着急。*
