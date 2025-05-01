import time
from fastapi import Request, HTTPException

class RateLimiter:
    def __init__(self, calls: int, period: int):
        self.calls = calls
        self.period = period
        self.timestamps = {}

    async def __call__(self, request: Request):
        ip = request.client.host
        now = time.time()
        request_times = self.timestamps.get(ip, []):
        request_times = [t for t in request_times if now - t < self.period]
        if len(request_times) >= self.calls:
            raise HTTPException(status_code=429, detail="Too many requests")
        request_times.append(now)
        self.timestamps[ip] = request_times

# To use, add RateLimiter as a dependency in your FastAPI endpoints