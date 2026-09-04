"""
Mock LLM Provider — 基于规则的本地实现，无需外部 API key。
Phase 1/2 的默认 Provider，也作为 fallback 使用。
"""

import time
from typing import Optional

from app.services.llm_providers.base import BaseLLMProvider, HintResult, CodeReviewResult

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
        "动态规划": "DP 框架：\n1. 定义 dp[i] 表示什么（状态定义是关键）\n2. 找出状态转移方程\n3. 确定初始条件和边界\n4. 考虑空间优化（滚动数组）",
        "贪心": "贪心策略：\n1. 确定排序规则\n2. 每次选择局部最优\n3. 证明贪心选择的安全性\n4. 注意反例",
        "二分查找": "二分框架：\n1. 确定搜索区间闭/开\n2. 循环条件\n3. 中点计算防溢出\n4. 根据比较结果缩小范围",
        "二叉树": "递归框架：\n1. 基准情况\n2. 递归处理左右子树\n3. 合并结果\n4. 考虑层序遍历",
        "回溯": "回溯模板：\n1. 定义递归参数\n2. 做选择\n3. 递归下一层\n4. 撤销选择\n5. 剪枝",
        "栈": "单调栈：\n1. 遍历维护单调性\n2. 破坏时弹出计算\n3. 处理剩余元素",
        "堆": "Top-K：\n1. 初始化堆\n2. push/pop\n3. 堆顶为最优\n4. O(n log k)",
        "链表": "链表技巧：\n1. 虚拟头节点\n2. 快慢指针\n3. 反转链表\n4. 合并链表",
        "滑动窗口": "滑动窗口：\n1. 右指针扩展\n2. 左指针收缩\n3. 记录最优结果",
        "并查集": "并查集：\n1. parent数组\n2. 路径压缩find\n3. 按秩合并union",
        "图论": "图遍历：\n- DFS：递归+visited\n- BFS：队列+层数\n- 加权用Dijkstra",
        "排序": "排序后处理：\n1. 自定义排序\n2. 双指针/贪心\n3. O(n log n)",
        "位运算": "位运算技巧：\n1. n&(n-1)消最低位1\n2. 异或性质\n3. 移位乘除2\n4. 掩码操作",
    },
    3: {
        "哈希": "核心代码思路：\n```python\nseen = {}\nfor i, num in enumerate(nums):\n    if target - num in seen:\n        return [seen[target-num], i]\n    seen[num] = i\n```",
        "双指针": "关键逻辑（排序后）：\n```python\nnums.sort()\nl, r = 0, len(nums)-1\nwhile l < r:\n    s = nums[l] + nums[r]\n    if s == target: 记录\n    elif s < target: l += 1\n    else: r -= 1\n```",
        "动态规划": "核心转移方程：\n```python\ndp = [0]*(n+1)\ndp[0] = 1\nfor i in range(1, n+1):\n    dp[i] = dp[i-1] + dp[i-2]\n```",
        "贪心": "贪心实现：\n```python\nintervals.sort(key=lambda x: x[1])\ncount, end = 1, intervals[0][1]\nfor s, e in intervals[1:]:\n    if s >= end:\n        count += 1; end = e\n```",
        "二分查找": "二分模板：\n```python\nl, r = 0, len(nums)-1\nwhile l <= r:\n    m = l + (r-l)//2\n    if nums[m] == t: return m\n    elif nums[m] < t: l = m+1\n    else: r = m-1\n```",
        "二叉树": "递归框架：\n```python\ndef dfs(node):\n    if not node: return 0\n    left = dfs(node.left)\n    right = dfs(node.right)\n    return max(left, right) + 1\n```",
        "回溯": "回溯模板：\n```python\ndef backtrack(path, choices):\n    if 结束: result.append(path[:]); return\n    for c in choices:\n        path.append(c)\n        backtrack(path, 新choices)\n        path.pop()\n```",
        "栈": "单调栈：\n```python\nstack = []\nfor i, h in enumerate(heights):\n    while stack and heights[stack[-1]] > h:\n        height = heights[stack.pop()]\n        width = i if not stack else i-stack[-1]-1\n    stack.append(i)\n```",
        "堆": "Top-K：\n```python\nimport heapq\nheap = []\nfor num in nums:\n    heapq.heappush(heap, num)\n    if len(heap) > k: heapq.heappop(heap)\nreturn heap[0]\n```",
        "链表": "反转链表：\n```python\nprev, curr = None, head\nwhile curr:\n    nxt = curr.next\n    curr.next = prev\n    prev, curr = curr, nxt\nreturn prev\n```",
        "滑动窗口": "滑动窗口：\n```python\nleft = 0\nfor right in range(len(s)):\n    window.add(s[right])\n    while 不满足条件:\n        window.remove(s[left])\n        left += 1\n    更新答案\n```",
        "并查集": "并查集：\n```python\nparent = list(range(n))\ndef find(x):\n    if parent[x] != x:\n        parent[x] = find(parent[x])\n    return parent[x]\ndef union(x, y):\n    px, py = find(x), find(y)\n    if px != py: parent[px] = py\n```",
        "图论": "BFS最短路径：\n```python\nfrom collections import deque\nq = deque([(start, 0)])\nvisited = {start}\nwhile q:\n    node, dist = q.popleft()\n    if node == target: return dist\n    for nbr in graph[node]:\n        if nbr not in visited:\n            visited.add(nbr)\n            q.append((nbr, dist+1))\n```",
        "排序": "排序后双指针：\n```python\nnums.sort()\nl, r = 0, len(nums)-1\nwhile l <= r:\n    # 根据题意选择\n```",
        "位运算": "位运算技巧：\n```python\nif n & 1:  # 奇数\nn = n & (n-1)  # 消最低位1\nlowbit = n & (-n)\n```",
    },
}

DEFAULT_HINTS = {
    1: "这道题需要仔细分析题目要求，找出数据之间的关系。尝试用不同的数据结构来思考。",
    2: "考虑这道题的核心约束条件，思考是否有经典的算法模式可以应用。画图或举例子通常很有帮助。",
    3: "从暴力解法开始思考，然后分析瓶颈在哪里，尝试用更高效的数据结构或算法来优化。",
}


def _get_hint_text(problem, level: int, profile) -> str:
    """基于题目分类和级别生成提示文本。"""
    templates = HINT_TEMPLATES.get(level, HINT_TEMPLATES[1])
    text = templates.get(problem.category, DEFAULT_HINTS.get(level, DEFAULT_HINTS[1]))

    if profile:
        if profile.hint_dependency_rate > 0.7 and level < 3:
            text += "\n\n💡 提示：你最近比较依赖提示，这次先尝试自己写出伪代码，再点开下一级提示。"
        elif profile.first_try_success_rate > 0.8 and level == 1:
            text += "\n\n🌟 以你的水平，这道题应该不难，试试直接写代码？"

    return text


class MockLLMProvider(BaseLLMProvider):
    """基于规则的 mock LLM，无需外部 API key。"""

    async def generate_hint(
        self,
        problem,
        level: int,
        user_code: Optional[str],
        profile,
    ) -> HintResult:
        start = time.time()
        text = _get_hint_text(problem, level, profile)
        latency = int((time.time() - start) * 1000)
        return HintResult(content=text, tokens_used=len(text) // 2, latency_ms=latency)

    async def review_code(
        self,
        problem,
        code: str,
        language: str,
    ) -> CodeReviewResult:
        start = time.time()
        code_len = len(code)
        has_comments = "#" in code or "//" in code

        if "for" in code and code.count("for") >= 2:
            time_c = "O(n²)"
            space_c = "O(1) 或 O(n)"
        elif "for" in code or "while" in code:
            time_c = "O(n)"
            space_c = "O(1)"
        else:
            time_c = "O(1)"
            space_c = "O(1)"

        rating = 3
        if code_len > 200 and has_comments:
            rating = 4
        if code_len < 50 and not has_comments:
            rating = 2

        edge_cases = ["空输入处理", "边界值测试"]
        if "数组" in problem.category or "链表" in problem.category:
            edge_cases.append("单元素情况")

        style = []
        if not has_comments:
            style.append("建议添加注释说明关键逻辑")
        if code_len > 300:
            style.append("代码较长，考虑拆分为更小的函数")

        optimizations = []
        if time_c == "O(n²)":
            optimizations.append("尝试用哈希表将时间复杂度优化到 O(n)")

        overall = f"整体评价：{'⭐' * rating}\n"
        if rating >= 4:
            overall += "代码质量良好，逻辑清晰。继续保持！"
        elif rating >= 3:
            overall += "代码基本正确，但可以进一步优化代码风格。"
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
