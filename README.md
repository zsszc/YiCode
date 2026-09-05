# 忆码 YiCode

> AI Agent 驱动的智能刷题伴侣 — 站内编码 + 流式 AI 导师 + 间隔重复复习

[![Tests](https://github.com/zsszc/YiCode/actions/workflows/ci.yml/badge.svg)](https://github.com/zsszc/YiCode/actions)

---

## 功能一览

### 💻 站内刷题（不用跳转 LeetCode）
- **在线代码编辑器** — CodeMirror 6，Python 语法高亮，Tab 缩进符合规范
- **双刷题模式** — 核心代码模式（LeetCode 风格，只写关键函数）/ ACM 模式（自己读 stdin、写 stdout，完整程序）
- **内置判题系统** — 核心代码按函数用例判题，ACM 模式按 stdin/stdout 用例判题
- **自由运行** — print 调试，ACM 模式支持自定义标准输入

### 🤖 AI Tutor（真实大模型，流式输出）
- **流式对话** — SSE 打字机效果，带着题目上下文和你当前的代码提问
- **分级提示** — L1 思路方向 → L2 算法框架 → L3 关键代码，流式渲染
- **代码审查** — 复杂度分析 + 边界情况 + 优化建议 + 1-5 星评分
- **苏格拉底式教学** — 引导你想到答案，而不是直接给答案

### ✨ 智能编码辅助
- **静态诊断** — 自研 AST 分析：语法错误红线、未定义变量、可变默认参数等，波浪线 + 悬浮中文解释
- **AI 内联补全** — Copilot 风格幽灵文本，停顿即出建议，Tab 接受 / Esc 拒绝，可一键开关

### 📖 模板速记（面试突击模式）
- **16 个高频模板** — 哈希、双指针、滑动窗口、二分、回溯、DP、单调栈、堆……
- **记忆口诀 + 易错点** — 为背诵优化
- **遮挡默写** — 模糊遮罩，先在脑中默写再核对
- **关联真题** — 背完模板直接跳转对应题目练手
- **AI 变式练习** — 基于模板生成原创变式题（含 ACM 判题用例），防止"背熟了但换个马甲就不会"

### 📋 科学复习
- **每日看板** — 到期复习题 + 新题配额
- **SM-2 复习调度** — 简化遗忘曲线
- **学习画像** — 提示依赖率、首次通过率、连续打卡
- **自适应配额** — 根据画像动态调整每日任务

---

## 快速开始

### 本地开发

**后端**（Python 3.11+）
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload   # http://localhost:8000
```

**前端**（Node 18+）
```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

首次启动自动建表并导入 LeetCode Hot 100 题库（含题面、代码模板、测试用例）。

### 配置 AI（可选）

在 `backend/.env` 中配置（不配则用内置 Mock，功能可用但回答为模板内容）：

```bash
LLM_PROVIDER=kimi
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.kimi.com/coding/v1
LLM_MODEL=kimi-for-coding
```

> ⚠️ `.env` 已在 `.gitignore` 中，**永远不要提交真实密钥**。

### 生产部署（systemd + nginx）

参考 `yicode-backend.service` 与 `yicode-nginx.conf` 模板（其中 IP 与密钥均为占位符，部署时替换为自己的值）。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+, FastAPI, SQLAlchemy 2.0, SQLite |
| 前端 | React 18, TypeScript, Tailwind CSS, CodeMirror 6, TanStack Query |
| AI | Kimi for Coding（OpenAI 兼容协议），SSE 流式 |
| 部署 | systemd + nginx / docker-compose |
| 测试 | pytest（100 tests） |

---

## API 概览

| 模块 | 路径 | 描述 |
|------|------|------|
| Auth | `POST /api/v1/auth/register` `/login` | 注册 / 登录（JWT） |
| Dashboard | `GET /api/v1/dashboard` | 今日看板 |
| Problems | `GET /api/v1/problems` `/{id}` | 题库与题目详情（含题面/测试用例） |
| Review | `POST /api/v1/review/{id}` | 复习打分（SM-2） |
| AI Tutor | `POST /api/v1/tutor/chat` `/chat-stream` | 对话（普通 / SSE 流式） |
| AI Tutor | `POST /api/v1/tutor/hint` · `GET /hint-stream/{id}` | 分级提示 |
| AI Tutor | `POST /api/v1/tutor/review-code` | AI 代码审查 |
| Code | `POST /api/v1/code/run` `/run-tests` | 运行 / 判题 |
| Code | `POST /api/v1/code/lint` | 静态诊断（波浪线数据） |
| Code | `POST /api/v1/code/complete` | AI 内联补全 |
| Templates | `GET /api/v1/templates` `/{slug}` | 面试模板 |
| Profile | `GET /api/v1/profile` `/adaptive` | 学习画像 / 自适应推荐 |

---

## 项目结构

```
YiCode/
├── backend/
│   ├── app/
│   │   ├── core/             # 数据库、安全
│   │   ├── models/           # SQLAlchemy 模型
│   │   ├── routers/          # API 路由
│   │   ├── services/         # 业务逻辑
│   │   │   ├── llm_providers/    # 可插拔 LLM（mock/kimi/openai）
│   │   │   ├── code_lint_service.py      # AST 静态诊断
│   │   │   └── code_complete_service.py  # AI 补全
│   │   └── data/
│   │       └── templates_data.py         # 16 个面试模板
│   ├── scripts/seed_problems.py          # 题库种子（幂等）
│   └── tests/                # pytest (100 tests)
├── frontend/
│   └── src/
│       ├── pages/            # 看板/题库/题目/模板/曲线/设置/登录
│       ├── components/TutorPanel.tsx     # AI Tutor 聊天面板
│       └── editor/aiCompletion.ts        # CM6 内联补全扩展
├── data/                     # 题库 JSON + SQLite
└── docs/                     # 设计文档
```

---

## 测试

```bash
cd backend
python -m pytest tests/ -q    # 100 passed
```

---

## CI/CD

- **CI**（`.github/workflows/ci.yml`）：push / PR 触发，跑后端 pytest + 前端构建 + gitleaks 泄密扫描
- **CD**（`.github/workflows/cd.yml`）：CI 在 main 分支成功后自动部署到生产服务器（自动备份数据库 → 上传 → 重启 → 健康检查）
- CD 需在仓库 Settings → Secrets 配置：`DEPLOY_HOST`、`DEPLOY_USER`、`DEPLOY_KEY`（SSH 私钥）

运维规范见 [docs/SOP.md](docs/SOP.md)，安全事件复盘见 [docs/incident-review-2026-09-05.md](docs/incident-review-2026-09-05.md)。

---

*一天一点，不着急。*
