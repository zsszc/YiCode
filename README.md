# 忆码 YiCode v2.0

> AI-Powered LeetCode Hot 100 Tracker — 你的智能刷题伴侣

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
| 测试 | pytest |

---

## 核心功能

- 📋 **每日看板** — 自动计算到期复习题 + 新题配额
- 🧠 **SM-2 复习调度** — 简化遗忘曲线算法
- 📝 **题目管理** — Hot 100 + 自定义题目
- 🏷️ **进度追踪** — forgot / shaky / solid / archived 四档状态
- 📊 **未来预告** — 前向模拟未来 30 天复习计划

---

## 项目结构

```
YiCode/
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── core/     # 数据库、异常
│   │   ├── models/   # SQLAlchemy 模型
│   │   ├── schemas/  # Pydantic 数据校验
│   │   ├── routers/  # API 路由
│   │   └── services/ # 业务逻辑
│   └── tests/        # pytest 测试
├── frontend/         # React 前端
│   └── src/
│       ├── pages/    # 页面组件
│       ├── hooks/    # 数据获取 Hooks
│       └── services/ # API 客户端
├── data/             # SQLite 数据文件
└── docs/             # 设计文档
```

---

*一天一点，不着急。*
