# YiCode v2.0 软件设计文档 (SDD)

> Software Design Document for YiCode — AI-Powered LeetCode Hot 100 Tracker

---

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      客户端层                                │
│  React 18 + TypeScript + Tailwind CSS + shadcn/ui           │
│  - DashboardPage   - ProblemsPage   - SettingsPage          │
│  - TanStack Query (数据获取/缓存)                            │
│  - Zustand (状态管理)                                        │
├─────────────────────────────────────────────────────────────┤
│                      API 网关层                              │
│  FastAPI                                                    │
│  - /api/v1/dashboard    今日看板                            │
│  - /api/v1/problems     题目 CRUD + 搜索筛选                 │
│  - /api/v1/review       复习打分 + SM-2 调度                 │
│  - /api/v1/auth         用户认证 (Phase 1 预留)              │
│  - /api/v1/preview      未来预告                            │
│  - /docs, /redoc        OpenAPI 自动文档                     │
├─────────────────────────────────────────────────────────────┤
│                      服务层                                  │
│  - SM2Service          简化 SM-2 遗忘曲线算法                │
│  - DashboardService    今日看板动态计算                      │
│  - SchedulerService    自适应学习调度 (Phase 2)              │
│  - ProblemService      题目管理                              │
├─────────────────────────────────────────────────────────────┤
│                      数据层                                  │
│  SQLite + SQLAlchemy 2.0 + Alembic 迁移                     │
│  - users, problems, progress, review_logs, configs          │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 数据库设计

### ER 图

```
┌──────────┐       ┌──────────┐       ┌──────────┐
│  users   │       │ problems │       │ progress │
├──────────┤       ├──────────┤       ├──────────┤
│ id (PK)  │       │ id (PK)  │       │ id (PK)  │
│ username │       │ title    │       │ user_id  │──┐
│ email    │       │ slug     │       │ problem_id│─┐│
│ created_at│      │ difficulty│      │ status   │  ││
└──────────┘       │ category │       │ review_stage│ │
                   │ leetcode_url│    │ next_review│ │
                   │ is_custom │      │ last_done │  │
                   └──────────┘       │ note      │  │
                                      │ cheatsheet│  │
                                      └──────────┘  │
                                                    │
                          ┌──────────────┐          │
                          │ review_logs  │          │
                          ├──────────────┤          │
                          │ id (PK)      │          │
                          │ user_id (FK)─┘          │
                          │ problem_id (FK)─────────┘
                          │ score
                          │ from_stage
                          │ to_stage
                          │ created_at
                          └──────────────┘
```

### 表结构详情

#### users
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    hashed_password TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### problems
```sql
CREATE TABLE problems (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    slug TEXT,
    difficulty TEXT NOT NULL CHECK(difficulty IN ('简单','中等','困难')),
    category TEXT NOT NULL,
    leetcode_url TEXT,
    is_custom BOOLEAN DEFAULT FALSE,
    deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### progress
```sql
CREATE TABLE progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id),
    problem_id INTEGER NOT NULL REFERENCES problems(id),
    status TEXT NOT NULL DEFAULT 'todo' CHECK(status IN ('todo','forgot','shaky','solid','archived')),
    review_stage INTEGER NOT NULL DEFAULT -1,
    next_review DATE,
    last_done DATE,
    note TEXT DEFAULT '',
    cheatsheet TEXT DEFAULT '',
    UNIQUE(user_id, problem_id)
);
```

#### review_logs
```sql
CREATE TABLE review_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id),
    problem_id INTEGER NOT NULL REFERENCES problems(id),
    score TEXT NOT NULL CHECK(score IN ('easy','ok','hard')),
    from_stage INTEGER NOT NULL,
    to_stage INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### configs
```sql
CREATE TABLE configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1 REFERENCES users(id),
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, key)
);
```

---

## 3. API 设计

### Dashboard

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/v1/dashboard | 今日看板（到期复习 + 新题配额 + 加练池） |
| GET | /api/v1/dashboard/preview | 明日/未来预览 |
| GET | /api/v1/dashboard/preview-range?days=30 | 未来 N 天预告 |
| POST | /api/v1/dashboard/shift-forward | 逾期整体后移一天 |

### Problems

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/v1/problems | 题目列表（支持搜索+筛选） |
| GET | /api/v1/problems/{id} | 题目详情 |
| POST | /api/v1/problems | 添加自定义题 |
| PUT | /api/v1/problems/{id} | 更新题目 |
| DELETE | /api/v1/problems/{id} | 软删除自定义题 |
| GET | /api/v1/problems/categories | 分类列表 |

### Review

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/v1/review/first-solve/{problem_id} | 首次刷完（forgot/shaky/solid） |
| POST | /api/v1/review/{problem_id} | 复习打分（easy/ok/hard） |
| PUT | /api/v1/review/{problem_id}/note | 更新笔记 |
| PUT | /api/v1/review/{problem_id}/cheatsheet | 更新 cheatsheet |

---

## 4. SM-2 简化算法

### 间隔定义
```python
INTERVALS = [1, 3, 7, 15, 30]  # 天
```

### 状态流转

```
                    ┌──────────────────────────────────────┐
                    │                                      │
  [新题] ──首次刷完──┼──→ forgot ──复习──┬── easy ──→ solid ──┤
  (todo)            │   (stage=0)        │   (stage+1)        │
                    │                    ├── ok ─────→ shaky  │
                    ├──→ shaky ──复习────┤   (保持 stage)     │
                    │   (stage=0)        ├── hard ──→ forgot  │
                    │                    │   (stage=0)        │
                    ├──→ solid ──复习────┤                    │
                        (stage=1)        │                    │
                                         └─ stage>=5 ─→ archived
```

### 关键函数

```python
def apply_first_solve(stage: int, status: str) -> tuple[int, str]:
    """首次刷完，进入复习队列。"""
    if status == "solid":
        return 1, _next_review(1)   # +3 天
    return 0, _next_review(0)       # +1 天

def apply_review(stage: int, score: str) -> tuple[int, str, str]:
    """复习打分，返回 (new_stage, next_review, new_status)。"""
    if score == "easy":
        new_stage = stage + 1
        new_status = "solid"
    elif score == "ok":
        new_stage = stage
        new_status = "shaky"
    else:  # hard
        new_stage = 0
        new_status = "forgot"
    
    if new_stage >= len(INTERVALS):
        return new_stage, "", "archived"
    return new_stage, _next_review(new_stage), new_status
```

---

## 5. 每日看板算法

### 输入
- 当前日期（考虑 day_boundary_hour）
- 用户配置（每日配额 weekday/weekend）
- 全部题目 + 进度数据

### 输出
- `due_review`: 到期复习题列表（按 next_review ≤ 今天）
- `today_new`: 今日新题配额（按难度均衡抽取）
- `extras_pool`: 加练池（10 道额外推荐）
- `counts`: 各状态统计
- `finish`: 完成预估（逐日模拟）
- `skipped_yesterday`: 昨日空档检测

### 难度均衡策略
```python
def balanced_pick(todo_pool: list, n: int) -> list:
    """按简:中:困 ≈ 2:6:2 比例抽取，保持原分类顺序。"""
```

---

## 6. 模块依赖

```
main.py
  ├─ dependencies.py (DB session, config)
  ├─ routers/
  │   ├─ dashboard.py ──→ DashboardService
  │   ├─ problems.py  ──→ ProblemService
  │   └─ review.py    ──→ SM2Service
  └─ services/
      ├─ dashboard_service.py ──→ SM2Service, ProblemService
      ├─ sm2_service.py
      └─ problem_service.py ────→ models
```

---

## 7. 安全设计

- 密码：bcrypt 哈希（Phase 2 启用）
- API 限流：每 IP 每分钟 60 次（Phase 2 启用 Redis）
- CORS：开发环境允许 localhost:5173
- 数据隐私：SQLite 本地存储，不上传云端

---

## 8. 性能目标

| 指标 | 目标 |
|------|------|
| 看板 API 响应 | < 200ms (P50) |
| 页面首屏加载 | < 2s |
| 测试覆盖率 | > 80% |
| 数据库查询 | 单表索引覆盖 |

---

*SDD 版本: v1.0 | 2026-09-04*
