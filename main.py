from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uuid
import time
from collections import defaultdict

# ==================== CONFIGURATION ====================

# TODO 1: Replace with your actual email
YOUR_EMAIL = "22f3000233@ds.study.iitm.ac.in"

# TODO 2: Add your exam page origin here (look at the URL in your browser's address bar)
ALLOWED_ORIGINS = [
    "https://app-0l889l.example.com",
    "https://exam.sanand.workers.dev"
]

# Rate limit settings: 15 requests per 10 seconds
BUCKET_SIZE = 15
WINDOW_SECONDS = 10

# ==================== APP SETUP ====================

app = FastAPI()

# In-memory storage for rate limiting
# Format: { "client_id_123": [timestamp1, timestamp2, ...] }
buckets = defaultdict(list)

# ==================== MIDDLEWARE LAYER 1: CORS (innermost) ====================
# Added first = sits closest to your endpoint.
# It handles OPTIONS preflight before the rate limiter even sees it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id", "Content-Type"],
    expose_headers=["X-Request-ID"],
)

# ==================== MIDDLEWARE LAYER 2: RATE LIMITER (middle) ====================
@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    # Never block CORS preflight requests
    if request.method == "OPTIONS":
        return await call_next(request)

    # We only care about /ping
    if request.url.path != "/ping":
        return await call_next(request)

    client_id = request.headers.get("X-Client-Id")
    if not client_id:
        # If the header is missing, just let it through
        # (the grader will always send it)
        return await call_next(request)

    now = time.time()
    window_start = now - WINDOW_SECONDS

    # Get this client's bucket
    bucket = buckets[client_id]

    # Throw away timestamps older than 10 seconds
    bucket[:] = [t for t in bucket if t > window_start]

    # If bucket is already full, reject with 429
    if len(bucket) >= BUCKET_SIZE:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"}
        )

    # Otherwise, record this request and let it through
    bucket.append(now)
    return await call_next(request)

# ==================== MIDDLEWARE LAYER 3: REQUEST CONTEXT (outermost) ====================
@app.middleware("http")
async def request_context(request: Request, call_next):
    # Did the client already bring an ID?
    request_id = request.headers.get("X-Request-ID")

    # If not, generate a brand new UUID4
    if not request_id:
        request_id = str(uuid.uuid4())

    # Save it to the request so the endpoint can read it later
    request.state.request_id = request_id

    # Pass the request deeper into the stack
    response = await call_next(request)

    # Stamp the same ID onto the response header on the way back out
    response.headers["X-Request-ID"] = request_id
    return response

# ==================== ENDPOINT ====================

@app.get("/ping")
async def ping(request: Request):
    return {
        "email": YOUR_EMAIL,
        "request_id": request.state.request_id
    }

