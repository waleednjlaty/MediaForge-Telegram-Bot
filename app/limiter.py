import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, count: int, window: int):
        self.count = count
        self.window = window
        self.data: dict[int, deque[float]] = defaultdict(deque)

    def allow(self, user_id: int) -> bool:
        now = time.monotonic()
        q = self.data[user_id]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.count:
            return False
        q.append(now)
        return True
