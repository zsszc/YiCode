"""
AI Tutor Service — 可插拔 LLM 架构

默认提供基于规则的 mock 实现，接口设计支持切换真实 LLM provider。
"""

import json
import time
from typing import Optional, AsyncIterator
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.problem import Problem
from app.models.learning_profile import LearningProfile
from app.models.ai_tutor_log import AITutorLog
from app.models.user_behavior import UserBehavior


@dataclass
class HintResult:
    content: str
    tokens_used: int = 0
    latency_ms: int = 0


@dataclass
class CodeReviewResult:
    time_complexity: str
    space_complexity: str
    edge_cases: list[str]
    style_suggestions: list[str]
    optimization_hints: list[str]
    rating: int  # 1-5
    overall_comment: str
    tokens_used: int = 0
    latency_ms: int = 0


# ============ Mock LLM Provider (默认) ============

HINT_TEMPLATES = {
    1: {
        "哈希": "这道题可以考虑使用哈希表来优化查找效率。想想如何通过空间换时间？",
        "双指针": "尝试用两个指针从两端或同向移动，看看能否找到满足条件的组合。",
        "动态规划": "这类问题通常有最优子结构，考虑定义一个状态来记录中间结果。",
        "贪心": "每一步都做出局部最优选择，看看能否推导出全局最优解。",
        "二分查找": "数据如果是有序的，考虑能否用二分来加速查找。",
        "二叉树": "树的题目通常考虑递归或层序遍历，从子问题的角度思考。",
        "回溯": "需要枚举所有可能的情况，可以用回溯法系统地搜索解空间。",
        "栈": "考虑用栈来维护某种单调性，或者处理嵌套结构。",
        "堆": "需要快速获取最大/最小元素时，堆是很有用的数据结构。",
        "链表": "链表题常考指针操作，注意边界情况如空链表、单节点等。",
        "滑动窗口": "维护一个动态区间，用双指针控制窗口的扩展和收缩。",
        "并查集": "处理连通性问题，考虑用并查集来维护集合的合并与查询。",
        "图论": "图的问题通常需要遍历（DFS/BFS），注意环和重复访问的处理。",
        "排序": "有时先排序能简化问题，考虑排序后能否用双指针或贪心。",
        "位运算": "利用二进制特性，异或、与、或等操作可能有巧妙用法。",
    },
    2: {
        "哈希": "具体思路：\n1. 遍历数组，将每个元素存入哈希表\n2. 对于每个元素，检查目标值与当前元素的差是否已在表中\n3. 时间复杂度可优化到 O(n)",
        "双指针": "算法框架：\n1. 先对数组排序（如果需要）\n2. 初始化左指针和右指针\n3. 根据两指针所指元素的和与目标值比较，决定移动哪个指针\n4. 注意去重逻辑",
        "动态规划": "DP 框架：\n1. 定义 dp[i] 表示什么（状态定义是关键）\n2. 找出状态转移方程：dp[i] = f(dp[i-1], ..., dp[0])\n3. 确定初始条件和边界\n4. 考虑空间优化（滚动数组）",
        "贪心": "贪心策略：\n1. 确定排序规则（按开始时间/结束时间/某种权重）\n2. 每次选择局部最优\n3. 证明贪心选择的安全性\n4. 注意反例：不是所有问题都适合贪心",
        "二分查找": "二分框架：\n1. 确定搜索区间 [left, right] 是闭区间还是左闭右开\n2. 循环条件：left < right 或 left <= right\n3. 中点计算：mid = left + (right - left) // 2\n4. 根据比较结果缩小搜索范围",
        "二叉树": "递归框架：\n1. 基准情况：空节点返回什么\n2. 递归处理左右子树\n3. 合并子树结果\n4. 考虑层序遍历用队列实现",
        "回溯": "回溯模板：\n1. 定义递归函数参数（路径、选择列表）\n2. 做选择：将选择加入路径\n3. 递归进入下一层决策树\n4. 撤销选择：回溯\n5. 剪枝：提前终止不可能的搜索分支",
        "栈": "栈的应用框架：\n1. 遍历元素，维护栈内单调递增/递减\n2. 遇到破坏单调性的元素时弹出栈顶\n3. 计算以弹出元素为基准的结果\n4. 注意栈中剩余元素的处理",
        "堆": "堆的使用模式：\n1. 初始化堆（优先队列）\n2. 按需 push/pop 元素\n3. 堆顶始终是当前最优解\n4. 时间复杂度通常是 O(n log k)",
        "链表": "链表技巧：\n1. 虚拟头节点简化边界处理\n2. 快慢指针找中点/倒数第 k 个\n3. 反转链表：迭代或递归\n4. 合并链表：类似归并排序的合并过程",
        "滑动窗口": "滑动窗口模板：\n1. 初始化左右指针\n2. 右指针扩展窗口，直到满足条件\n3. 左指针收缩窗口，寻找最优解\n4. 记录过程中的最优结果",
        "并查集": "并查集模板：\n1. parent 数组记录每个元素的根\n2. find：带路径压缩的查找\n3. union：按秩合并\n4. 用集合数量或连通分量个数判断终止条件",
        "图论": "图遍历模板：\n- DFS：递归 + visited 集合\n- BFS：队列 + 层数记录\n- 注意：有向图 vs 无向图，加权图用 Dijkstra",
        "排序": "排序后处理：\n1. 自定义排序规则（lambda/cmp）\n2. 排序后使用双指针或贪心\n3. 时间复杂度至少 O(n log n)",
        "位运算": "位运算技巧：\n1. n & (n-1) 消除最低位的 1\n2. 异或：a ^ a = 0, a ^ 0 = a\n3. 左移右移实现乘除 2\n4. 掩码操作提取特定位",
    },
    3: {
        "哈希": "关键代码思路（Python）：\n```python\nseen = {}\nfor i, num in enumerate(nums):\n    complement = target - num\n    if complement in seen:\n        return [seen[complement], i]\n    seen[num] = i\n```\n核心：用字典实现 O(1) 查找，空间换时间。",
        "双指针": "关键逻辑（排序后）：\n```python\nnums.sort()\nleft, right = 0, len(nums) - 1\nwhile left < right:\n    s = nums[left] + nums[right]\n    if s == target: 记录结果\n    elif s < target: left += 1\n    else: right -= 1\n```\n注意：去重时跳过相同元素。",
        "动态规划": "核心转移方程写法：\n```python\n# 一维 DP\ndp = [0] * (n + 1)\ndp[0] = 1  # 初始条件\nfor i in range(1, n + 1):\n    dp[i] = dp[i-1] + dp[i-2]  # 根据题意修改\n```\n空间优化：只用两个变量滚动更新。",
        "贪心": "贪心实现要点：\n```python\n# 按结束时间排序\nintervals.sort(key=lambda x: x[1])\ncount = 1\nend = intervals[0][1]\nfor i in range(1, len(intervals)):\n    if intervals[i][0] >= end:\n        count += 1\n        end = intervals[i][1]\n```\n关键：排序策略决定贪心是否正确。",
        "二分查找": "二分查找模板：\n```python\nleft, right = 0, len(nums) - 1\nwhile left <= right:\n    mid = left + (right - left) // 2\n    if nums[mid] == target:\n        return mid\n    elif nums[mid] < target:\n        left = mid + 1\n    else:\n        right = mid - 1\nreturn -1\n```\n注意：循环条件和边界更新要一致。",
        "二叉树": "递归处理框架：\n```python\ndef dfs(node):\n    if not node:\n        return 0  # 或 None/[]\n    left = dfs(node.left)\n    right = dfs(node.right)\n    # 根据题意合并左右结果\n    return result\n```\n考虑：是否需要自底向上（后序）或自上而下（前序）。",
        "回溯": "回溯标准模板：\n```python\ndef backtrack(path, choices):\n    if 满足结束条件:\n        result.append(path[:])\n        return\n    for choice in choices:\n        if 不满足约束: continue\n        path.append(choice)\n        backtrack(path, 新choices)\n        path.pop()  # 撤销选择\n```\n剪枝条件写在循环开头。",
        "栈": "单调栈典型用法：\n```python\nstack = []\nfor i, h in enumerate(heights):\n    while stack and heights[stack[-1]] > h:\n        height = heights[stack.pop()]\n        width = i if not stack else i - stack[-1] - 1\n        ans = max(ans, height * width)\n    stack.append(i)\n```\n关键：栈中保持单调性，弹出时计算以该元素为极值的结果。",
        "堆": "Top-K 问题用堆：\n```python\nimport heapq\nheap = []\nfor num in nums:\n    heapq.heappush(heap, num)\n    if len(heap) > k:\n        heapq.heappop(heap)\nreturn heap[0]  # 第 K 大\n```\nPython 默认小根堆，求最大用负号或自定义。",
        "链表": "反转链表（迭代）：\n```python\nprev, curr = None, head\nwhile curr:\n    nxt = curr.next\n    curr.next = prev\n    prev = curr\n    curr = nxt\nreturn prev\n```\n三个指针配合，注意保存 next 再修改。",
        "滑动窗口": "滑动窗口核心逻辑：\n```python\nleft = 0\nfor right in range(len(s)):\n    window.add(s[right])\n    while 窗口不满足条件:\n        window.remove(s[left])\n        left += 1\n    # 此时窗口满足条件，更新答案\n```\n关键：右指针主动扩展，左指针被动收缩。",
        "并查集": "并查集实现：\n```python\nparent = list(range(n))\n\ndef find(x):\n    if parent[x] != x:\n        parent[x] = find(parent[x])\n    return parent[x]\n\ndef union(x, y):\n    px, py = find(x), find(y)\n    if px != py:\n        parent[px] = py\n```\n路径压缩 + 按秩合并优化。",
        "图论": "BFS 最短路径：\n```python\nfrom collections import deque\nqueue = deque([(start, 0)])\nvisited = {start}\nwhile queue:\n    node, dist = queue.popleft()\n    if node == target:\n        return dist\n    for neighbor in graph[node]:\n        if neighbor not in visited:\n            visited.add(neighbor)\n            queue.append((neighbor, dist + 1))\n```\n注意：加权图用 Dijkstra，有环图记 visited。",
        "排序": "自定义排序 + 双指针：\n```python\nnums.sort(key=lambda x: abs(x))  # 或其他规则\nleft, right = 0, len(nums) - 1\nwhile left <= right:\n    # 根据题意选择 left 或 right\n```\n排序后问题通常变得更简单。",
        "位运算": "位运算常用技巧：\n```python\n# 判断奇偶\nif n & 1:  # 奇数\n\n# 消除最低位 1\nn = n & (n - 1)\n\n# 获取最低位的 1\nlowbit = n & (-n)\n\n# 异或交换（不额外空间）\na = a ^ b\nb = a ^ b\na = a ^ b\n```",
    },
}

DEFAULT_HINTS = {
    1: "这道题需要仔细分析题目要求，找出数据之间的关系。尝试用不同的数据结构来思考。",
    2: "考虑这道题的核心约束条件，思考是否有经典的算法模式可以应用。画图或举例子通常很有帮助。",
    3: "从暴力解法开始思考，然后分析瓶颈在哪里，尝试用更高效的数据结构或算法来优化。",
}


def _get_hint_text(problem: Problem, level: int, profile: Optional[LearningProfile]) -> str:
    """基于题目分类和级别生成提示文本。"""
    templates = HINT_TEMPLATES.get(level, HINT_TEMPLATES[1])
    text = templates.get(problem.category, DEFAULT_HINTS.get(level, DEFAULT_HINTS[1]))

    # 根据用户画像调整
    if profile:
        if profile.hint_dependency_rate > 0.7 and level < 3:
            text += "\n\n💡 提示：你最近比较依赖提示，这次先尝试自己写出伪代码，再点开下一级提示。"
        elif profile.first_try_success_rate > 0.8 and level == 1:
            text += "\n\n🌟 以你的水平，这道题应该不难，试试直接写代码？"

    return text


class MockLLMProvider:
    """基于规则的 mock LLM，无需外部 API key。"""

    async def generate_hint(
        self,
        problem: Problem,
        level: int,
        user_code: Optional[str],
        profile: Optional[LearningProfile],
    ) -> HintResult:
        start = time.time()
        text = _get_hint_text(problem, level, profile)
        latency = int((time.time() - start) * 1000)
        return HintResult(content=text, tokens_used=len(text) // 2, latency_ms=latency)

    async def review_code(
        self,
        problem: Problem,
        code: str,
        language: str,
    ) -> CodeReviewResult:
        start = time.time()

        # 基于代码长度和语言做简单启发式分析
        lines = code.strip().split("\n")
        code_len = len(code)
        has_comments = "#" in code or "//" in code

        # 复杂度估算（非常粗略）
        if "for" in code and "for" in code[code.find("for") + 1:]:
            time_c = "O(n²)"
            space_c = "O(1) 或 O(n)"
        elif "for" in code or "while" in code:
            time_c = "O(n)"
            space_c = "O(1)"
        else:
            time_c = "O(1)"
            space_c = "O(1)"

        # 评级
        rating = 3
        if code_len > 200 and has_comments:
            rating = 4
        if code_len < 50 and not has_comments:
            rating = 2
        if "优化" in code or "OPTIMIZED" in code.upper():
            rating = 5

        edge_cases = ["空输入处理", "边界值测试"]
        if "数组" in problem.category or "链表" in problem.category:
            edge_cases.append("单元素情况")
        if problem.difficulty == "困难":
            edge_cases.append("大数溢出")

        style = []
        if not has_comments:
            style.append("建议添加注释说明关键逻辑")
        if code_len > 300:
            style.append("代码较长，考虑拆分为更小的函数")

        optimizations = []
        if time_c == "O(n²)":
            optimizations.append("尝试用哈希表将时间复杂度优化到 O(n)")
        if space_c.startswith("O(n)"):
            optimizations.append("看看能否用原地算法减少空间使用")

        overall = f"整体评价：{'⭐' * rating}\n"
        if rating >= 4:
            overall += "代码质量良好，逻辑清晰。继续保持！"
        elif rating >= 3:
            overall += "代码基本正确，但可以进一步优化和优化代码风格。"
        else:
            overall += "建议多思考边界情况，并参考题解学习更优解法。"

        latency = int((time.time() - start) * 1000)

        return CodeReviewResult(
            time_complexity=time_c,
            space_complexity=space_c,
            edge_cases=edge_cases,
            style_suggestions=style,
            optimization_hints=optimizations,
            rating=rating,
            overall_comment=overall,
            tokens_used=code_len // 2,
            latency_ms=latency,
        )


# ============ Service Layer ============

class AITutorService:
    """AI Tutor 服务，可切换 LLM provider。"""

    def __init__(self, db: Session, provider: Optional[MockLLMProvider] = None):
        self.db = db
        self.provider = provider or MockLLMProvider()

    async def generate_hint(
        self,
        problem_id: int,
        level: int = 1,
        user_code: Optional[str] = None,
        user_id: int = 1,
    ) -> HintResult:
        """生成解题提示。"""
        if level not in (1, 2, 3):
            raise ValueError("hint_level must be 1, 2, or 3")

        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")

        profile = (
            self.db.query(LearningProfile)
            .filter(LearningProfile.user_id == user_id)
            .first()
        )

        result = await self.provider.generate_hint(problem, level, user_code, profile)

        # 记录日志
        log = AITutorLog(
            user_id=user_id,
            problem_id=problem_id,
            request_type="hint",
            prompt=f"level={level}, code_present={bool(user_code)}",
            response=result.content[:2000],
            tokens_used=result.tokens_used,
            latency_ms=result.latency_ms,
        )
        self.db.add(log)

        # 记录行为
        behavior = UserBehavior(
            user_id=user_id,
            problem_id=problem_id,
            action_type="hint",
            action_data=json.dumps({"hint_level": level}),
        )
        self.db.add(behavior)

        # 更新 progress hint_count
        from app.models.progress import Progress
        progress = (
            self.db.query(Progress)
            .filter(Progress.user_id == user_id, Progress.problem_id == problem_id)
            .first()
        )
        if progress:
            progress.hint_count = (progress.hint_count or 0) + 1

        self.db.commit()
        return result

    async def review_code(
        self,
        problem_id: int,
        code: str,
        language: str = "python",
        user_id: int = 1,
    ) -> CodeReviewResult:
        """审查用户代码。"""
        problem = self.db.query(Problem).filter(Problem.id == problem_id).first()
        if not problem:
            raise ValueError(f"Problem {problem_id} not found")

        result = await self.provider.review_code(problem, code, language)

        log = AITutorLog(
            user_id=user_id,
            problem_id=problem_id,
            request_type="review_code",
            prompt=f"language={language}, code_length={len(code)}",
            response=json.dumps(result.__dict__, ensure_ascii=False)[:2000],
            tokens_used=result.tokens_used,
            latency_ms=result.latency_ms,
        )
        self.db.add(log)
        self.db.commit()
        return result

    def get_logs(self, user_id: int = 1, limit: int = 20) -> list[dict]:
        """获取 AI Tutor 交互历史。"""
        logs = (
            self.db.query(AITutorLog)
            .filter(AITutorLog.user_id == user_id)
            .order_by(AITutorLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": log.id,
                "problem_id": log.problem_id,
                "request_type": log.request_type,
                "tokens_used": log.tokens_used,
                "latency_ms": log.latency_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
