"""
面试高频算法模板数据 — 模板刷题/背诵模式

每个模板包含：适用场景、记忆口诀、可背诵的标准代码、易错点、关联题库题目。
面向短期突击面试的用户：先背模板，再去关联题目里默写验证。
"""

TEMPLATES: list[dict] = [
    {
        "slug": "hash-map",
        "name": "哈希表查找",
        "scenario": "需要 O(1) 查「某个值是否出现过 / 配对的另一半在哪」时",
        "mnemonic": "边遍历边记录，先查后存防自配",
        "code": '''def solve(nums, target):
    seen = {}  # 值 -> 下标（或次数）
    for i, x in enumerate(nums):
        need = target - x
        if need in seen:      # ① 先查：搭档之前见过吗？
            return [seen[need], i]
        seen[x] = i           # ② 后存：把自己记进去
    return []''',
        "key_points": [
            "先查后存：避免同一个元素和自己配对（两数之和的坑）",
            "dict 查、存都是平均 O(1)，整体 O(n)",
            "只需要计数时用 dict 存次数；只需要存在性用 set",
        ],
        "problem_ids": [1, 49, 128],
    },
    {
        "slug": "two-pointers-opposite",
        "name": "双指针 · 对撞",
        "scenario": "有序数组/两头夹逼求最优（盛水、三数之和、接雨水）",
        "mnemonic": "左右夹逼，谁小移谁；有序才能贪",
        "code": '''def solve(arr):
    left, right = 0, len(arr) - 1
    best = 0
    while left < right:
        # 计算当前答案并更新最优
        best = max(best, calc(arr[left], arr[right]))
        if arr[left] < arr[right]:
            left += 1    # 短板决定上限，移走短的
        else:
            right -= 1
    return best''',
        "key_points": [
            "前提通常是数组有序，或问题有「短板效应」可贪心",
            "三数之和 = 排序 + 固定一个数 + 对撞双指针，注意去重",
            "while left < right，不要写成 <=",
        ],
        "problem_ids": [11, 15, 42],
    },
    {
        "slug": "fast-slow-pointers",
        "name": "双指针 · 快慢（链表）",
        "scenario": "链表判环、找环入口、找倒数第 N 个、找中点",
        "mnemonic": "快慢赛跑：有环必相遇；先走 N 步找倒数",
        "code": '''def hasCycle(head):
    slow = fast = head
    while fast and fast.next:
        slow = slow.next          # 慢指针走 1 步
        fast = fast.next.next     # 快指针走 2 步
        if slow is fast:
            return True           # 相遇即有环
    return False

# 找倒数第 N 个：fast 先走 N 步，再同步走，fast 到尾时 slow 即答案''',
        "key_points": [
            "循环条件 fast and fast.next，防 None.next 报错",
            "找环入口：相遇后一个指针回头部，同步走再相遇即入口",
            "用 is 而不是 == 判断节点相等（比较的是引用）",
        ],
        "problem_ids": [141, 142, 19, 160],
    },
    {
        "slug": "sliding-window",
        "name": "滑动窗口",
        "scenario": "子串/子数组的「最长/最短/恰好 K 个」类问题",
        "mnemonic": "右扩左缩：右指针扩张进元素，违规就左指针收缩",
        "code": '''def longest(s):
    window = {}
    left = 0
    best = 0
    for right, ch in enumerate(s):     # 右指针扩张
        window[ch] = window.get(ch, 0) + 1
        while 不满足条件(window):       # 违规就收缩
            window[s[left]] -= 1
            if window[s[left]] == 0:
                del window[s[left]]
            left += 1
        best = max(best, right - left + 1)  # 更新答案
    return best''',
        "key_points": [
            "窗口内元素用 dict 计数，收缩到 0 记得删除 key",
            "「最长」在收缩后更新答案；「最短」在收缩前更新",
            "左右指针都只前进不回退，整体 O(n)",
        ],
        "problem_ids": [3, 438, 76, 239],
    },
    {
        "slug": "binary-search",
        "name": "二分查找",
        "scenario": "有序（或局部有序）数组中查找目标/边界",
        "mnemonic": "左闭右闭区间：while l <= r，收缩时 ±1",
        "code": '''def search(nums, target):
    left, right = 0, len(nums) - 1   # 闭区间 [left, right]
    while left <= right:             # 区间非空就继续
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid + 1           # 闭区间，排除 mid
        else:
            right = mid - 1
    return -1

# 找左边界变种：相等时不返回，right = mid - 1 继续压左''',
        "key_points": [
            "背死一种写法：推荐左闭右闭 [l, r]，while l <= r",
            "旋转数组：二分后必有一半有序，判断 target 是否落在有序半边",
            "防溢出写法 mid = l + (r - l) // 2（Python 无所谓，面试说出来加分）",
        ],
        "problem_ids": [35, 34, 33, 153, 74],
    },
    {
        "slug": "linked-list-reverse",
        "name": "链表反转",
        "scenario": "反转链表、K 个一组反转、回文链表的后半段处理",
        "mnemonic": "三指针 prev/cur/next，cur.next = prev 逐个掉头",
        "code": '''def reverseList(head):
    prev = None
    cur = head
    while cur:
        nxt = cur.next    # ① 先存后继，防止断链丢失
        cur.next = prev   # ② 掉头
        prev = cur        # ③ prev 前进
        cur = nxt         # ④ cur 前进
    return prev           # prev 是新头节点''',
        "key_points": [
            "返回 prev 不是 cur（结束时 cur 是 None）",
            "K 个一组 = 每段先验证长度够 K，再套上面的反转",
            "画一次指针移动图比背十遍都有用",
        ],
        "problem_ids": [206, 24, 25, 234],
    },
    {
        "slug": "binary-tree-dfs",
        "name": "二叉树 DFS（递归）",
        "scenario": "树的遍历、深度、路径、对称、祖先问题",
        "mnemonic": "递归三问：返回值是什么？当前节点干什么？什么时候到底？",
        "code": '''def dfs(root):
    if not root:              # ① 到底：空节点的返回
        return 0
    left = dfs(root.left)     # ② 拿左右子树的结果
    right = dfs(root.right)
    # ③ 当前节点：用左右结果算自己的结果
    return max(left, right) + 1

# 前序：先处理自己再递归左右；后序：先递归再处理；中序：左-自己-右''',
        "key_points": [
            "90% 的树题是「后序」：先拿子树结果再合并",
            "需要自顶向下传信息时，给递归加参数（路径、层号）",
            "最近公共祖先：左右都找到则当前是祖先，否则返回非空那边",
        ],
        "problem_ids": [94, 104, 226, 101, 236, 543],
    },
    {
        "slug": "bfs",
        "name": "BFS 层序遍历",
        "scenario": "最短路径、层序遍历、腐烂扩散、岛屿淹没问题",
        "mnemonic": "队列 + 层级快照：每轮先记 size，一次弹一整层",
        "code": '''from collections import deque

def bfs(root):
    if not root:
        return []
    queue = deque([root])
    result = []
    while queue:
        size = len(queue)          # 关键：锁定本层节点数
        level = []
        for _ in range(size):      # 一次处理一整层
            node = queue.popleft()
            level.append(node.val)
            if node.left:  queue.append(node.left)
            if node.right: queue.append(node.right)
        result.append(level)
    return result''',
        "key_points": [
            "用 deque.popleft()，list.pop(0) 是 O(n) 会超时",
            "记层数/最短步数：每处理完一层 step += 1",
            "图 BFS 要配合 visited 集合防重复入队",
        ],
        "problem_ids": [102, 200, 994, 199],
    },
    {
        "slug": "backtracking",
        "name": "回溯（排列/组合/子集）",
        "scenario": "枚举所有方案：排列、组合、子集、括号生成、棋盘",
        "mnemonic": "做选择 → 递归 → 撤销选择（append / 递归 / pop）",
        "code": '''def backtrack(path, choices):
    if 满足结束条件:
        result.append(path[:])     # ① 必须拷贝！
        return
    for choice in choices:
        if 不合法 or 已用过:
            continue               # 剪枝
        path.append(choice)        # ② 做选择
        backtrack(path, 新choices)  # ③ 递归
        path.pop()                 # ④ 撤销选择

# 子集：每层从 start 开始选，start 参数去重
# 排列：用 used 数组标记，每层都能从头选''',
        "key_points": [
            "result.append(path[:])：path 是引用，不拷贝后面会被改掉",
            "子集/组合用 start 下标去重；排列用 used 数组去重",
            "同一层有重复元素时先排序 + 跳过相同值（if i > start and nums[i]==nums[i-1]）",
        ],
        "problem_ids": [46, 78, 39, 17, 22, 79],
    },
    {
        "slug": "dp-linear",
        "name": "动态规划 · 线性",
        "scenario": "爬楼梯、打家劫舍、最长子序列、单词拆分",
        "mnemonic": "定义状态 → 写转移方程 → 初始化 → 确定遍历顺序",
        "code": '''def solve(nums):
    n = len(nums)
    # ① 状态：dp[i] = 考虑前 i 个元素时的最优解
    dp = [0] * (n + 1)
    # ② 初始化：base case
    dp[0] = 0
    dp[1] = nums[0]
    # ③ 转移：选或不选第 i 个
    for i in range(2, n + 1):
        dp[i] = max(dp[i - 1], dp[i - 2] + nums[i - 1])
    return dp[n]

# 空间优化：状态只依赖前两项时，用两个变量滚动''',
        "key_points": [
            "面试先说清 dp[i] 的含义，一句话说不清就是状态没定义对",
            "子序列问题（LIS）是双层循环 O(n²)：dp[i] = max(dp[j]) + 1, j < i",
            "爬楼梯/打家劫舍都可滚动变量把空间降到 O(1)",
        ],
        "problem_ids": [70, 198, 300, 139, 152],
    },
    {
        "slug": "dp-knapsack",
        "name": "动态规划 · 背包",
        "scenario": "装满容量/凑出目标和：分割等和子集、零钱兑换",
        "mnemonic": "0-1 背包倒序遍历容量，完全背包正序遍历容量",
        "code": '''def canPartition(nums):
    total = sum(nums)
    if total % 2:
        return False
    target = total // 2
    # dp[j] = 能否凑出和 j
    dp = [False] * (target + 1)
    dp[0] = True
    for num in nums:                          # 外层：物品
        for j in range(target, num - 1, -1):  # 内层：容量倒序
            dp[j] = dp[j] or dp[j - num]
    return dp[target]

# 完全背包（零钱兑换）：内层 for j in range(coin, target+1) 正序''',
        "key_points": [
            "0-1 背包倒序（每件只能用一次）；完全背包正序（可重复用）",
            "凑数问题初始化 dp[0] = True/0，其余按题意",
            "「能否」用布尔数组，「最少几个」用 int 数组初始化为 inf",
        ],
        "problem_ids": [416, 322, 279],
    },
    {
        "slug": "monotonic-stack",
        "name": "单调栈",
        "scenario": "下一个更大/更小元素、柱状图矩形、每日温度",
        "mnemonic": "栈存下标维护单调性，新元素破坏单调时就结算栈顶",
        "code": '''def dailyTemperatures(temps):
    n = len(temps)
    ans = [0] * n
    stack = []                      # 存下标，对应温度单调递减
    for i, t in enumerate(temps):
        while stack and temps[stack[-1]] < t:
            prev = stack.pop()      # 找到 prev 的「下一个更高温」
            ans[prev] = i - prev
        stack.append(i)
    return ans''',
        "key_points": [
            "栈里存下标不存值（答案往往要距离/位置）",
            "求「下一个更大」→ 栈内单调递减；「下一个更小」→ 单调递增",
            "接雨水、柱状图最大矩形都是单调栈的经典变体",
        ],
        "problem_ids": [739, 84, 42],
    },
    {
        "slug": "heap-topk",
        "name": "堆 · TopK",
        "scenario": "第 K 大/小、前 K 个高频、数据流中位数",
        "mnemonic": "求第 K 大用大小为 K 的小顶堆，堆顶就是第 K 大",
        "code": '''import heapq

def findKthLargest(nums, k):
    heap = []
    for x in nums:
        heapq.heappush(heap, x)      # 小顶堆
        if len(heap) > k:
            heapq.heappop(heap)      # 弹掉最小的，留 K 个最大的
    return heap[0]                   # 堆顶 = 第 K 大

# Python heapq 只有小顶堆；大顶堆就存相反数
# 前 K 高频：先 Counter 计数，再堆存 (频次, 元素)''',
        "key_points": [
            "heapq 是小顶堆；要大顶堆就 push(-x)",
            "保持堆大小为 K：时间 O(n log k)，优于全排序 O(n log n)",
            "中位数 = 大顶堆放小半 + 小顶堆放大半，两堆平衡",
        ],
        "problem_ids": [215, 347, 295, 23],
    },
    {
        "slug": "prefix-sum",
        "name": "前缀和",
        "scenario": "子数组和类问题：和为 K 的子数组、区间求和",
        "mnemonic": "pre[j] - pre[i] = 区间 (i, j] 的和；配哈希表查 pre[i] - k",
        "code": '''def subarraySum(nums, k):
    count = 0
    pre = 0
    seen = {0: 1}              # 前缀和 0 出现 1 次（空前缀）
    for x in nums:
        pre += x
        count += seen.get(pre - k, 0)   # 有多少个旧前缀 = pre - k
        seen[pre] = seen.get(pre, 0) + 1
    return count''',
        "key_points": [
            "seen 必须先放 {0: 1}，漏了就统计不到从头开始的子数组",
            "先查后存（同两数之和），顺序反了会算错",
            "只问「是否存在」时 seen 用 set 存前缀和即可",
        ],
        "problem_ids": [560, 238],
    },
    {
        "slug": "union-find",
        "name": "并查集",
        "scenario": "连通性问题：岛屿数量、省份数量、冗余连接",
        "mnemonic": "find 带路径压缩，union 按秩合并",
        "code": '''class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.count = n               # 连通分量个数

    def find(self, x):
        # 路径压缩：顺手把沿途节点都挂到根上
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False             # 已连通
        self.parent[ra] = rb
        self.count -= 1
        return True''',
        "key_points": [
            "路径压缩 + 按秩合并后，单次操作近似 O(1)",
            "岛屿数量也能用 DFS/BFS 淹没法做，并查集是通用解",
            "网格转编号：id = i * cols + j",
        ],
        "problem_ids": [200, 128],
    },
    {
        "slug": "interval-merge",
        "name": "区间合并",
        "scenario": "合并区间、插入区间、区间交集",
        "mnemonic": "先按起点排序，再看当前区间与上一个是否重叠",
        "code": '''def merge(intervals):
    intervals.sort(key=lambda x: x[0])   # ① 按起点排序
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        last_end = merged[-1][1]
        if start <= last_end:            # ② 重叠：合并
            merged[-1][1] = max(last_end, end)
        else:                            # ③ 不重叠：新开一个
            merged.append([start, end])
    return merged''',
        "key_points": [
            "忘记排序是最常见错误",
            "重叠条件 start <= last_end（端点相接也算重叠，按题意）",
            "合并时 end 要取 max，不能直接覆盖（可能包含关系）",
        ],
        "problem_ids": [56],
    },
]


def get_template_list() -> list[dict]:
    """列表页摘要（不含代码正文）。"""
    return [
        {
            "slug": t["slug"],
            "name": t["name"],
            "scenario": t["scenario"],
            "mnemonic": t["mnemonic"],
            "problem_ids": t["problem_ids"],
        }
        for t in TEMPLATES
    ]


def get_template(slug: str) -> dict | None:
    for t in TEMPLATES:
        if t["slug"] == slug:
            return t
    return None
