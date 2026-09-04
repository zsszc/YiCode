# YiCode v2.0 Phase 2 SDD — AI Tutor & 自适应学习

> Software Design Document for Phase 2: AI-Powered Adaptive Learning
> 目标: 让 Agent 可自进化、自学习、自适应用户学习习惯

---

## 1. Phase 2 架构概览

```
┌─────────────────────────────────────────────────────────────────────┐
│                         客户端层                                     │
│  React 18 + TanStack Query                                          │
│  - DashboardPage (增强: AI 提示气泡)                                 │
│  - ProblemDetailPage (新增: AI Tutor 侧边栏)                         │
│  - ProblemsPage (增强: 进度可视化)                                   │
│  - SettingsPage (新增: 学习偏好设置)                                 │
├─────────────────────────────────────────────────────────────────────┤
│                         API 网关层                                   │
│  FastAPI                                                            │
│  - /api/v1/tutor/hint          AI 解题提示 (流式 SSE)                 │
│  - /api/v1/tutor/review-code   AI 代码审查                          │
│  - /api/v1/profile             学习画像 (GET/PUT)                    │
│  - /api/v1/profile/adaptive    自适应推荐结果                        │
│  - /api/v1/feishu/webhook      飞书 Bot 消息接收                    │
│  - /api/v1/feishu/card         飞书卡片消息发送                      │
├─────────────────────────────────────────────────────────────────────┤
│                         服务层 (Phase 2 新增)                        │
│  - AITutorService          LLM 调用 + Prompt 工程                    │
│    ├─ generate_hint()      生成解题提示 (分级: 思路/伪代码/关键代码)   │
│    └─ review_code()        代码审查 (时间/空间复杂度 + 优化建议)       │
│  - LearningProfileService  用户行为分析 + 自适应建模                  │
│    ├─ record_behavior()    记录解题行为                              │
│    ├─ analyze_patterns()   分析学习模式                              │
│    └─ adaptive_quota()     自适应调整每日配额                        │
│  - FeishuBotService        飞书消息格式化 + 卡片构建                  │
├─────────────────────────────────────────────────────────────────────┤
│                         数据层 (扩展)                                │
│  SQLite + SQLAlchemy 2.0                                            │
│  - progress (扩展: solve_time_ms, hint_count, attempt_count, patterns)│
│  - user_behaviors (新增)   详细行为日志                               │
│  - learning_profiles (新增) 学习画像聚合                              │
│  - ai_tutor_logs (新增)    AI 交互历史                                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 数据库扩展设计

### user_behaviors (行为日志)
```sql
CREATE TABLE user_behaviors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    problem_id INTEGER NOT NULL,
    action_type TEXT NOT NULL CHECK(action_type IN ('open','hint','attempt','submit','review','skip')),
    action_data TEXT DEFAULT '{}',  -- JSON: {hint_level, solve_time_ms, code_length, ...}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### learning_profiles (学习画像)
```sql
CREATE TABLE learning_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1 UNIQUE,
    -- 能力评估
    avg_solve_time_easy_ms INTEGER DEFAULT 0,
    avg_solve_time_medium_ms INTEGER DEFAULT 0,
    avg_solve_time_hard_ms INTEGER DEFAULT 0,
    hint_dependency_rate REAL DEFAULT 0.0,  -- 依赖提示的比例
    first_try_success_rate REAL DEFAULT 0.0, -- 首次尝试成功率
    -- 习惯模式
    peak_hour_start INTEGER DEFAULT 9,
    peak_hour_end INTEGER DEFAULT 22,
    preferred_difficulty TEXT DEFAULT 'balanced', -- easy/balanced/challenging
    streak_days INTEGER DEFAULT 0,
    max_streak INTEGER DEFAULT 0,
    total_solved INTEGER DEFAULT 0,
    total_reviewed INTEGER DEFAULT 0,
    -- 自适应配置
    adaptive_quota_enabled BOOLEAN DEFAULT TRUE,
    custom_quota_weekday INTEGER,
    custom_quota_weekend INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### ai_tutor_logs (AI 交互历史)
```sql
CREATE TABLE ai_tutor_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL DEFAULT 1,
    problem_id INTEGER,
    request_type TEXT NOT NULL CHECK(request_type IN ('hint','review_code')),
    prompt TEXT,
    response TEXT,
    tokens_used INTEGER,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. AI Tutor 设计

### 3.1 架构原则
- **可插拔 LLM**: 接口统一，支持切换 provider (Kimi/OpenAI/本地模型)
- **分级提示**: hint_level 1=思路引导, 2=算法框架, 3=关键代码
- **上下文感知**: 根据用户历史表现调整提示深度
- **流式输出**: SSE 流式返回，提升体验

### 3.2 Prompt 模板

**Hint 生成**:
```
你是一位耐心的算法导师。用户正在做 LeetCode 题目。

题目: {title}
难度: {difficulty}
分类: {category}

用户画像:
- 首次尝试: {is_first_try}
- 已请求提示次数: {hint_count}
- 历史同类题正确率: {category_accuracy}

请提供 hint_level={level} 的提示:
- level 1: 只给解题思路方向，不涉及具体算法
- level 2: 说明适用的算法/数据结构框架
- level 3: 提供关键代码片段（伪代码或核心逻辑）

要求:
1. 用中文回答
2. 鼓励性语气
3. 不直接给出完整 AC 代码
4. 如果用户已多次请求提示，适当给出更多细节
```

**代码审查**:
```
你是一位代码审查专家。请审查以下 LeetCode 题解代码。

题目: {title}
用户代码:
```{language}
{code}
```

请分析:
1. 时间复杂度 & 空间复杂度
2. 是否有边界情况未处理
3. 代码风格建议
4. 是否有更优解法的提示
5. 总体评价 (1-5 星)

用中文回答，格式化为 JSON。
```

### 3.3 API 设计

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/v1/tutor/hint | 请求解题提示 |
| POST | /api/v1/tutor/review-code | 代码审查 |
| GET | /api/v1/tutor/logs | AI 交互历史 |

### 3.4 请求/响应 Schema

**POST /tutor/hint**
```json
{
  "problem_id": 1,
  "hint_level": 1,  // 1|2|3
  "user_code": "optional: 用户已写的代码",
  "language": "python"
}
```

响应 (SSE 流):
```
data: {"type":"start"}
data: {"type":"chunk","content":"这道题可以用哈希表来..."}
data: {"type":"chunk","content":"降低时间复杂度..."}
data: {"type":"end","tokens_used":128}
```

---

## 4. 学习画像 & 自适应系统

### 4.1 行为追踪
每个用户行为触发 `record_behavior()`:
- `open`: 打开题目页面
- `hint`: 请求 AI 提示 (记录 hint_level)
- `attempt`: 提交代码尝试 (记录 solve_time_ms, code_length)
- `submit`: 成功 AC
- `review`: 复习打分
- `skip`: 跳过题目

### 4.2 画像计算 (每日聚合)
```python
def analyze_patterns(user_id: int, days: int = 7) -> dict:
    """分析最近 N 天学习模式，返回画像更新数据。"""
    # 1. 平均解题时间 (按难度)
    # 2. 提示依赖率 = hint_count / open_count
    # 3. 首次尝试成功率 = first_try_AC / total_attempts
    # 4. 活跃时段分析 (peak hours)
    # 5. 难度偏好 (用户主动选择的比例)
```

### 4.3 自适应配额算法
```python
def adaptive_quota(profile: LearningProfile, history: list) -> dict:
    """基于画像动态调整每日配额。"""
    base = profile.custom_quota_weekday or settings.daily_quota_weekday
    
    # 正向激励: 连续打卡增加配额
    streak_bonus = min(profile.streak_days // 7, 2)  # 最多+2
    
    # 负向保护: 提示依赖率高则减少新题，增加复习
    if profile.hint_dependency_rate > 0.7:
        new_ratio = 0.5  # 新题比例降低
    elif profile.hint_dependency_rate > 0.4:
        new_ratio = 0.7
    else:
        new_ratio = 0.8
    
    # 能力匹配: 高难度成功率高则增加困难题比例
    hard_ratio = 0.1  # 默认
    if profile.first_try_success_rate > 0.8:
        hard_ratio = 0.2
    elif profile.first_try_success_rate < 0.3:
        hard_ratio = 0.05
    
    return {
        "quota": base + streak_bonus,
        "new_ratio": new_ratio,
        "hard_ratio": hard_ratio,
        "reasoning": "连续 5 天打卡，配额+1；提示依赖率 30%，新题比例正常"
    }
```

### 4.4 API 设计

| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/v1/profile | 获取学习画像 |
| PUT | /api/v1/profile | 更新偏好设置 |
| GET | /api/v1/profile/adaptive | 获取自适应推荐 |
| POST | /api/v1/behaviors | 记录行为 (前端自动上报) |

---

## 5. 飞书 Bot 设计

### 5.1 交互流程
```
用户@Bot → 飞书服务器 → POST /api/v1/feishu/webhook
                                  ↓
                    解析消息 → 识别意图 → 调用对应 Service
                                  ↓
                    构建卡片消息 → POST 飞书回调
```

### 5.2 支持命令
| 命令 | 功能 |
|------|------|
| `今日看板` / `dashboard` | 返回今日待复习 + 新题卡片 |
| `复习` / `review` | 列出到期复习题，支持直接打分 |
| `题目 {id}` | 查看某题详情 + LeetCode 链接 |
| `统计` / `stats` | 学习数据统计 |
| `帮助` / `help` | 命令列表 |

### 5.3 飞书卡片格式
使用飞书 OpenAPI 的 interactive card，包含:
- 标题 + 日期
- 题目列表 (带难度标签)
- 操作按钮 (秒A/磕绊/卡住)
- 进度统计图表 (简化文本版)

---

## 6. 前端增强

### 6.1 新增页面
- **ProblemDetailPage**: 题目详情 + AI Tutor 侧边栏
  - 左侧: 题目信息 + LeetCode 链接 + 笔记编辑器
  - 右侧: AI Tutor 面板 (提示分级选择 + 流式输出)
- **SettingsPage**: 学习偏好设置
  - 每日配额调节
  - 难度偏好选择
  - AI Tutor 级别设置

### 6.2 组件增强
- DashboardPage:
  - 增加 "AI 建议" 卡片 (根据画像推荐今日策略)
  - 增加连续打卡天数显示
- ProblemsPage:
  - 增加进度可视化 (环形进度条)
  - 增加搜索高亮

---

## 7. 测试策略

### 7.1 TDD 流程
1. 红: 编写测试用例 (mock LLM response)
2. 绿: 实现最小代码
3. 重构: 优化 prompt 模板、异常处理

### 7.2 测试覆盖目标
| 模块 | 目标覆盖率 |
|------|-----------|
| AI Tutor Service | > 90% |
| Learning Profile | > 85% |
| 飞书 Bot | > 80% |
| API Router | > 85% |

### 7.3 Mock 策略
- LLM 调用: 使用 `unittest.mock.patch`  mock `httpx.post`
- 飞书 API: mock 回调请求验证
- 数据库: 继续使用内存 SQLite

---

## 8. 性能 & 安全

### 8.1 性能
- LLM 调用: 异步 + 流式，避免阻塞
- 行为记录: 批量写入 (每 10 条 flush)
- 画像计算: 后台定时任务 (每日凌晨)

### 8.2 安全
- LLM API key: 环境变量注入，不存入代码
- 飞书 webhook: 验证 challenge + signature
- 用户输入: 长度限制 + 过滤

---

*SDD Phase 2 版本: v1.0 | 2026-09-04*
