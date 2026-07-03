from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from uuid import uuid4
import time

app = FastAPI()

# -------------------------------
# CHANGE THIS
# -------------------------------

EMAIL = "22f3000233@ds.study.iitm.ac.in"

ALLOWED_ORIGIN = "https://app-0l889l.example.com"

# Also allow the exam page origin.
# Replace this with the exam page origin if your assignment provides it.
EXAM_ORIGIN = "https://exam.example.com"

RATE_LIMIT = 15
WINDOW = 10

# -------------------------------
# CORS
# -------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        ALLOWED_ORIGIN,
        EXAM_ORIGIN,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------
# Simple in-memory rate limiter
# -------------------------------

clients = {}

# -------------------------------
# Middleware
# -------------------------------

@app.middleware("http")
async def middleware(request: Request, call_next):

    # ---------------------------
    # Request ID
    # ---------------------------

    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid4())

    request.state.request_id = request_id

    # ---------------------------
    # Rate limiting
    # ---------------------------

    client_id = request.headers.get("X-Client-Id")

    if client_id:

        now = time.time()

        timestamps = clients.get(client_id, [])

        # Keep only requests in last 10 seconds
        timestamps = [
            t
            for t in timestamps
            if now - t < WINDOW
        ]

        if len(timestamps) >= RATE_LIMIT:

            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )

            response.headers["X-Request-ID"] = request_id

            return response

        timestamps.append(now)

        clients[client_id] = timestamps

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response

# -------------------------------
# Endpoint
# -------------------------------

@app.get("/ping")
async def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }