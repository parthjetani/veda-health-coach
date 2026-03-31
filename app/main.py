import logging
from contextlib import asynccontextmanager

import httpx
from google import genai
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase import create_client

from app.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    # Initialize Supabase client
    app.state.supabase = create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )

    # Initialize shared HTTP client for WhatsApp API calls
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    )

    # Initialize Gemini client
    app.state.gemini_client = genai.Client(
        api_key=settings.gemini_api_key,
    )

    # Load system prompt
    with open("prompts/health_coach.txt", "r", encoding="utf-8") as f:
        app.state.system_prompt = f.read()

    logger.info("Application started — all clients initialized")
    yield

    # Cleanup
    await app.state.http_client.aclose()
    logger.info("Application shutdown — clients closed")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Veda - AI Health Coach",
        description="WhatsApp AI health coaching chatbot powered by Gemini",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # CORS — allow admin dashboard access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler — never return HTML error pages
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )

    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    # Register routers
    from app.api.webhooks.whatsapp import router as whatsapp_router
    from app.api.admin.users import router as admin_users_router
    from app.api.admin.health_items import router as admin_health_items_router

    app.include_router(whatsapp_router, prefix="/webhook/whatsapp", tags=["WhatsApp"])
    app.include_router(admin_users_router, prefix="/admin", tags=["Admin"])
    app.include_router(admin_health_items_router, prefix="/admin", tags=["Admin"])

    return app


app = create_app()
