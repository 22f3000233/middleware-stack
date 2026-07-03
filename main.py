from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
import time
from collections import defaultdict

# ==================== CONFIGURATION ====================

YOUR_EMAIL = "22f3000233@ds.study.iitm.ac.in"

# IMPORTANT: Include BOTH origins
ALLOWED_ORIGINS = [
   "https://app-0l889l.example.com",
    "https://exam.sanand.workers.dev"
]

BUCKET_SIZE = 15
WINDOW_SECONDS = 10

# ==================== APP SETUP ====================

app = FastAPI()
buckets = defaultdict(list)

# ==================== MIDDLEWARE 1: RATE LIMITER (innermost) ====================

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Never block CORS preflight
        if request.method == "OPTIONS":
            return await call_next(request)

        # Only rate-limit /ping
        if request.url.path != "/ping":
            return await call_next(request)

        client_id = request.headers.get("X-Client-Id")
        if not client_id:
            return await call_next(request)

        now = time.time()
        window_start = now - WINDOW_SECONDS
        bucket = buckets[client_id]

        # Evict stale timestamps
        bucket[:] = [t for t in bucket if t > window_start]

        # If bucket is full, return 429
        if len(bucket) >= BUCKET_SIZE:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )

        # Record this request and proceed
        bucket.append(now)
        return await call_next(request)

# Add FIRST → becomes innermost
app.add_middleware(RateLimitMiddleware)

# ==================== MIDDLEWARE 2: CORS (middle layer) ====================

# Add SECOND → wraps around the rate limiter, so it processes ALL responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id", "Content-Type"],
    expose_headers=["X-Request-ID"],
)

# ==================== MIDDLEWARE 3: REQUEST CONTEXT (outermost) ====================

@app.middleware("http")
async def request_context(request: Request, call_next):
    # Reuse existing ID or generate fresh UUID4
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())

    # Attach to request state for the endpoint to read
    request.state.request_id = request_id

    # Proceed down the stack
    response = await call_next(request)

    # Stamp the response header on the way back out
    response.headers["X-Request-ID"] = request_id
    return response

# ==================== ENDPOINT ====================

@app.get("/ping")
async def ping(request: Request):
    return {
        "email": YOUR_EMAIL,
        "request_id": request.state.request_id
    }


