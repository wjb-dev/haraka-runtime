# runtime.py — Main Application Entrypoint for Haraka Runtime
# --------------------------------------------------------
# This file wires up the FastAPI app to the Haraka Runtime Orchestrator.
# It supports service autoloading via service.yaml manifests, structured startup/shutdown,
# and optional API routing via modular routers.

from fastapi import FastAPI
from pathlib import Path
from contextlib import asynccontextmanager

from src.haraka_runtime.orchestrator import Orchestrator
from src.haraka_runtime.loader import load_adapter_from_manifest
from config.settings import settings  # Project-level config via pydantic
from app.routes import include_routers  # Optional route aggregator

# Initialize orchestrator — the core Haraka runtime controller
runtime = Orchestrator()

# Lifecycle wrapper using FastAPI lifespan protocol
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start orchestrator + all services (in dependency/priority order)
    await runtime.run(settings, app)
    yield
    # Clean shutdown of services (reverse order)
    await runtime.shutdown()

# Create FastAPI app with standard Swagger UI config
app = FastAPI(
    title="app_name",
    version="version",
    description="description",
    openapi_url="/openapi.json",
    docs_url="/app_name/docs",
    redoc_url=None,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 1,
        "displayRequestDuration": True,
        "syntaxHighlight": {"theme": "obsidian"},
    },
    lifespan=lifespan,
)

# Optional: Include modular API routers (if HTTP is used)
include_routers(app)

# Load all declared services from service.yaml manifests in ./services/
for manifest_path in Path("services").rglob("service.yaml"):
    load_adapter_from_manifest(manifest_path, runtime)
