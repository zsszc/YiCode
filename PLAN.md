# YiCode v2.0 开发计划

> 忆码 (YiCode) — LeetCode Hot 100 智能刷题伴侣
> Phase 1 骨架搭建 | TDD + SDD 驱动

---

## 一、目标

搭建可运行的 V2.0 工程骨架，包含：
- FastAPI 分层后端（SQLite + SQLAlchemy + Alembic）
- React + TypeScript + Tailwind 前端骨架
- 核心 SM-2 复习算法（TDD：测试先行）
- 每日看板 API
- Docker + docker-compose 一键启动
- 完整测试覆盖（pytest）

---

## 二、开发规范

### SDD（Software Design Document）
- 每模块编写前，先在 `docs/` 中写明接口契约
- 数据库 Schema 变更通过 Alembic 迁移管理
- API 设计遵循 RESTful + OpenAPI 自动生成

### TDD（Test-Driven Development）
1. 红：先写测试，确认失败
2. 绿：实现最小代码，测试通过
3. 重构：优化实现，保持测试通过

### 代码规范
- 后端：Black + Ruff + mypy
- 前端：ESLint + Prettier
- 提交前必须全量测试通过

---

## 三、Phase 1 任务清单

### Week 1 — 后端骨架
- [x] 项目目录结构
- [ ] 数据库设计（SQLAlchemy models）
- [ ] Alembic 初始化 + 首版迁移
- [ ] Pydantic Settings 配置管理
- [ ] SM-2 算法核心（test → impl → refactor）
- [ ] 每日看板 Service（build_dashboard 迁移）
- [ ] API 路由（Dashboard, Problems, Review）
- [ ] pytest 测试套件（>80% 覆盖目标）

### Week 2 — 前端骨架 + Docker
- [ ] Vite + React + TS 初始化
- [ ] Tailwind + shadcn/ui 配置
- [ ] 页面骨架（Dashboard, Problems, Settings）
- [ ] API 客户端封装（axios + TanStack Query）
- [ ] Docker + docker-compose
- [ ] GitHub Actions CI/CD

### Week 3 — 数据迁移 + 集成测试
- [ ] 原 problems.json → SQLite 迁移脚本
- [ ] 进度数据导入/导出
- [ ] E2E 测试（Playwright）
- [ ] 文档完善

---

## 四、技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic, pytest |
| 前端 | React 18, TypeScript 5, Vite, Tailwind CSS, shadcn/ui, TanStack Query |
| 数据 | SQLite（默认）, PostgreSQL（未来多用户） |
| 部署 | Docker, docker-compose |
| CI/CD | GitHub Actions |

---

*Plan 版本: v1.0 | 2026-09-04*
