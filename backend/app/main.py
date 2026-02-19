"""SEC-Pulse FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import filings, ws
from .services.feed_poller import polling_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise database tables
    await init_db()

    # Start the SEC feed polling loop as a background task
    poll_task = asyncio.create_task(
        polling_loop(broadcast_fn=ws.manager.broadcast)
    )

    yield

    poll_task.cancel()
    try:
        await poll_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="SEC-Pulse",
    description="Real-time SEC market intelligence dashboard",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(filings.router, prefix="/api")
app.include_router(ws.router)
