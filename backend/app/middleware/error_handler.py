
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger("app.error_handler")

async def http_error_handler(request: Request, exc: Exception):
   
    log.exception("Unhandled error", extra={"path": str(request.url)})
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "error": str(exc)},
    )
