import structlog
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app import __version__
from app.config import settings
from app.middleware.request_id import RequestIDMiddleware
from app.routers import auth as auth
from app.routers import assistant as assistant
from app.routers import entitlement as entitlement
from app.routers import exports as exports
from app.routers import finance as finance
from app.routers import governance as governance
from app.routers import health as health
from app.routers import jobs as jobs
from app.routers import parcels as parcels
from app.routers import plans as plans
from app.routers import policy as policy
from app.routers import projects as projects
from app.routers import scenarios as scenarios
from app.routers import simulation as simulation
from app.routers import ingestion as ingestion
from app.routers import uploads as uploads
from app.routers import design_versions as design_versions

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)


def create_app() -> FastAPI:
    application = FastAPI(
        title="Arterial",
        description="Land-development due diligence platform",
        version=__version__,
    )

    application.add_middleware(RequestIDMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.API_V1_PREFIX

    application.include_router(auth.router, prefix=prefix, tags=["auth"])
    application.include_router(health.router, prefix=prefix, tags=["health"])
    application.include_router(assistant.router, prefix=prefix, tags=["assistant"])
    application.include_router(projects.router, prefix=prefix, tags=["projects"])
    application.include_router(parcels.router, prefix=prefix, tags=["parcels"])
    application.include_router(scenarios.router, prefix=prefix, tags=["scenarios"])
    application.include_router(simulation.router, prefix=prefix, tags=["simulation"])
    application.include_router(finance.router, prefix=prefix, tags=["finance"])
    application.include_router(governance.router, prefix=prefix, tags=["governance"])
    application.include_router(entitlement.router, prefix=prefix, tags=["entitlement"])
    application.include_router(policy.router, prefix=prefix, tags=["policy"])
    application.include_router(exports.router, prefix=prefix, tags=["exports"])
    application.include_router(plans.router, prefix=prefix, tags=["plans"])
    application.include_router(jobs.router, prefix=prefix, tags=["jobs"])
    application.include_router(uploads.router, prefix=prefix, tags=["uploads"])
    application.include_router(ingestion.router, prefix=prefix, tags=["ingestion"])
    application.include_router(design_versions.router, prefix=prefix, tags=["designs"])

    # Serve built React frontend (production only — when frontend-dist exists)
    frontend_dist = Path(__file__).parent.parent / "frontend-dist"
    if frontend_dist.exists():
        application.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")

        @application.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            return FileResponse(frontend_dist / "index.html")

    return application


app = create_app()
