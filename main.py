from uuid import uuid4
from fastapi import Request
from fastapi.responses import JSONResponse

@app.middleware("http")
async def middleware(request: Request, call_next):
    # Get or generate request ID
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id

    # Rate limiting
    client_id = request.headers.get("X-Client-Id")
    if client_id:
        # ... your rate limit logic ...
        if rate_limit_exceeded:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )
            response.headers["X-Request-ID"] = request_id
            return response

    # Call endpoint
    response = await call_next(request)

    # Always add the header
    response.headers["X-Request-ID"] = request_id

    return response
