from fastapi import FastAPI

from app.errors import ErrorResponse, register_error_handlers
from app.routes import (
    bills,
    health,
    leases,
    me,
    onboarding,
    payments,
    properties,
    settings,
    summary,
    system,
)

app = FastAPI(
    title="Arrendi",
    responses={422: {"model": ErrorResponse}},
)
register_error_handlers(app)

app.include_router(health.router, prefix="/api")
app.include_router(me.router, prefix="/api")
app.include_router(properties.router, prefix="/api")
app.include_router(leases.router, prefix="/api")
app.include_router(onboarding.router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(bills.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
