# 忆码 YiCode v2.0

> AI-Powered LeetCode Hot 100 Tracker — 你的智能刷题伴侣
> Phase 2: AI Tutor + 自适应学习 + 飞书 Bot

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
| 测试 | pytest (59 tests) |

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
- **提示深度自适应** — 根据用户历史表现调整提示深度

### 📈 自适应学习系统
- **学习画像建模** — 追踪解题时间、提示依赖率、首次尝试成功率
- **连续打卡统计** — 自动计算 streak，正向激励
- **AI 自适应配额** — 基于画像动态调整每日新题比例和难度分布
- **行为日志** — 完整记录 open / hint / attempt / submit / review / skip

### 💬 飞书 Bot
- **对话式刷题** — 在飞书中查看今日看板、复习列表、学习统计
- **飞书卡片消息** — 美观的交互式卡片，支持一键操作
- **命令支持** — `今日看板` / `复习` / `统计` / `帮助`
- **Webhook 接入** — 标准飞书 Bot 回调接口

---

## API 概览

| 模块 | 路径 | 描述 |
|------|------|------|
| Dashboard | `GET /api/v1/dashboard` | 今日看板 |
| Problems | `GET /api/v1/problems` | 题目列表 |
| Review | `POST /api/v1/review/{id}` | 复习打分 |
| **AI Tutor** | `POST /api/v1/tutor/hint` | 解题提示 |
| **AI Tutor** | `POST /api/v1/tutor/review-code` | 代码审查 |
| **Profile** | `GET /api/v1/profile` | 学习画像 |
| **Profile** | `GET /api/v1/profile/adaptive` | 自适应推荐 |
| **Feishu** | `POST /api/v1/feishu/webhook` | 飞书 Bot 回调 |

---

## 项目结构

```
YiCode/
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── core/         # 数据库、异常
│   │   ├── models/       # SQLAlchemy 模型
│   │   ├── schemas/      # Pydantic 数据校验
│   │   ├── routers/      # API 路由
│   │   │   ├── tutor.py      # AI Tutor API
│   │   │   ├── profile.py    # 学习画像 API
│   │   │   └── feishu.py     # 飞书 Bot API
│   │   └── services/     # 业务逻辑
│   │       ├── ai_tutor_service.py       # LLM 提示生成
│   │       ├── learning_profile_service.py # 画像分析
│   │       └── sm2.py                      # 复习算法
│   └── tests/            # pytest 测试 (59 tests)
├── frontend/             # React 前端
│   └── src/
│       ├── pages/        # 页面组件
│       │   ├── ProblemDetailPage.tsx  # AI Tutor 交互页
│       │   └── SettingsPage.tsx       # 偏好设置页
│       ├── hooks/        # 数据获取 Hooks
│       └── services/     # API 客户端
├── data/                 # SQLite 数据文件
└── docs/                 # 设计文档 (SDD)
```

---

## 测试

```bash
cd backend
python -m pytest tests/ -v
```

**Phase 1**: 31 tests — Dashboard, Problems, Review, SM-2  
**Phase 2**: 28 tests — AI Tutor, Learning Profile, Feishu Bot  
**Total**: 59 tests ✅

---

*一天一点，不着急。*
