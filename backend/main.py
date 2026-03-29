"""
FastAPI application entry point.

This is the file that uvicorn runs. It creates the app, includes
all route handlers, and configures middleware.

Think of this like the front door of a restaurant:
  - It sets up the building (FastAPI app)
  - It posts the menu (API documentation at /docs)
  - It directs customers to the right section (routers)
  - It doesn't cook food — that's the routers' and agents' job

Run locally:
  uvicorn main:app --reload --port 8000

Then visit:
  http://localhost:8000/docs  → Interactive API documentation
  http://localhost:8000/      → Health check
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import reviews
from routers.webhook import router as webhook_router

# ─── Logging Setup ───────────────────────────────────────────
#
# This configures Python's logging so you can see what's happening
# in your terminal. Every logger.info() and logger.error() call
# in your agents and routes will print here.
#
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Lifespan (startup/shutdown events) ──────────────────────
#
# This runs code when the server starts and when it shuts down.
# Right now it just logs a message. In Phase 6, this is where
# you'll initialize Redis connections and Celery workers.
#
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Screvyn API starting up...")
    yield
    # Shutdown
    logger.info("Screvyn API shutting down...")


# ─── Create the App ──────────────────────────────────────────
#
# FastAPI() creates the application. The parameters here control
# what shows up in the auto-generated documentation at /docs.
#
app = FastAPI(
    title="Screvyn",
    description="AI Senior Developer — Multi-Agent Code Review System",
    version="0.2.0",
    lifespan=lifespan,
)


# ─── CORS Middleware ─────────────────────────────────────────
#
# CORS (Cross-Origin Resource Sharing) controls which websites
# can call your API. Without this, your Next.js frontend (running
# on localhost:3000) wouldn't be able to talk to your backend
# (running on localhost:8000) — the browser would block it.
#
# allow_origins=["*"] means "allow everyone" — fine for development.
# In production, you'd restrict this to your actual frontend URL.
#
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Include Routers ─────────────────────────────────────────
#
# Routers organize your endpoints into logical groups.
# This line says: "take all the routes defined in routers/reviews.py
# and add them to this app under the /api prefix."
#
# So if reviews.py defines POST /review,
# the full path becomes POST /api/review.
#
app.include_router(reviews.router, prefix="/api", tags=["Reviews"])
app.include_router(webhook_router, tags=["Webhooks"])


# ─── Health Check ────────────────────────────────────────────
#
# A simple endpoint that returns "ok". This is used by:
# - Railway to check if your server is alive (health checks)
# - Monitoring tools to verify the API is responsive
# - You, to quickly test "is the server running?"
#
@app.get("/")
async def health_check():
    return {
        "status": "ok",
        "service": "screvyn",
        "version": "0.2.0",
    }