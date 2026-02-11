"""
NMIA Windows Collector - FastAPI Application

A lightweight service that runs on Windows machines to collect ADCS
certificate inventory via certutil and push data to the main NMIA server.
"""

import logging
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from nmia_collector.settings import settings
from nmia_collector.routes import router


def _configure_logging() -> None:
    """Set up logging based on configuration."""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown logic."""
    _configure_logging()
    logger = logging.getLogger("nmia.collector")
    logger.info("NMIA Windows Collector starting up")
    logger.info("NMIA Server URL: %s", settings.NMIA_SERVER_URL)
    logger.info(
        "Connector Instance ID: %s",
        settings.CONNECTOR_INSTANCE_ID or "(not configured)",
    )

    # Ensure data directory exists
    os.makedirs(settings.DATA_DIR, exist_ok=True)

    yield

    logger.info("NMIA Windows Collector shutting down")


app = FastAPI(
    title="NMIA Windows Collector",
    description=(
        "Collects ADCS certificate inventory from Windows Certificate "
        "Authority servers and pushes data to the NMIA platform."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "nmia-windows-collector",
        "version": "0.1.0",
        "connector_instance_id": settings.CONNECTOR_INSTANCE_ID or None,
    }


def run() -> None:
    """Entry point for the ``nmia-collector`` console script."""
    uvicorn.run(
        "nmia_collector.main:app",
        host="0.0.0.0",
        port=9000,
        log_level=settings.LOG_LEVEL.lower(),
    )
