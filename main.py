from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from uuid import uuid4
import time

app = FastAPI()

# ==========================
# CHANGE THESE
# ==========================

EMAIL = "22f3000233@ds.study.iitm.ac.in"

ALLOWED_ORIGIN = "https://app-0l889l.example.com"

# Also allow the exam page origin.
# Replace this with the exam page origin if your assignment provides it.
EXAM_ORIGIN = "https://exam.sanand.workers.dev"

RATE_LIMIT = 15
WINDOW_SECONDS = 10

# ==========================
# CORS
# ==========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        ALLOWED_ORIGIN,
        EXAM_ORIGIN,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# ==========================
# In-memory rate limiter
# client_id -> timestamps
# ==========================

client_requests = {}


@app.middleware("http")
async def request_context_and_rate_limit(request: Request, call_next):
    # -----------------------
    # Request ID
    # -----------------------
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid4())

    request.state.request_id = request_id

    # -----------------------
    # Rate limiting
    # -----------------------
    client_id = request.headers.get("X-Client-Id")

    if client_id:
        now = time.time()

        timestamps = client_requests.get(client_id, [])

        # Keep only timestamps inside the window
        timestamps = [
            ts
            for ts in timestamps
            if now - ts < WINDOW_SECONDS
        ]

        if len(timestamps) >= RATE_LIMIT:
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "request_id": request_id,
                    "X-Request-ID": request_id,
                },
            )

            # IMPORTANT
            response.headers["X-Request-ID"] = request_id

            return response

        timestamps.append(now)
        client_requests[client_id] = timestamps

    # -----------------------
    # Continue request
    # -----------------------
    response = await call_next(request)

    # IMPORTANT
    response.headers["X-Request-ID"] = request_id

    return response


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
        "X-Request-ID": request.state.request_id,
    }
