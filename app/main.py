import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.middleware.request_id import RequestIDMiddleware
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

    application.include_router(health.router, prefix=prefix, tags=["health"])
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

    return application


app = create_app()
