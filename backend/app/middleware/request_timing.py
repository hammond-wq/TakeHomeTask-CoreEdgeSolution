
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            dur_ms = int((time.perf_counter() - start) * 1000)
            try:
                response.headers["X-Response-Time-ms"] = str(dur_ms)
            except Exception:
                pass
        return response
