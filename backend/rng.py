"""
可注入随机数生成器 — 全部游戏随机数收敛于此。
支持：
  - 种子确定性序列（用于测试/Agent 复现）
  - nextRandom(v) 测试钩子（压入下一个返回值，覆盖种子序列）

RandomNum(upper) → [0, upper) 整数，语义同 C++ rand() % upper。
"""

import random


class RNG:
    def __init__(self, seed: int | None = None):
        self._state = seed if seed is not None else random.randint(0, 2**31 - 1)
        self._test_queue: list[int] = []
        # Pre-seed Python's random for any auxiliary use
        random.seed(self._state)

    def random(self, upper: int) -> int:
        """返回 [0, upper) 整数。等价于 RandomNum(upper)。"""
        if self._test_queue:
            return self._test_queue.pop(0) % upper
        self._state = (self._state * 1103515245 + 12345) & 0x7FFFFFFF
        return self._state % upper

    def push_test(self, *values: int) -> None:
        """测试钩子：压入接下来 N 次 random() 的返回值。"""
        self._test_queue.extend(values)

    @property
    def seed(self) -> int:
        return self._state