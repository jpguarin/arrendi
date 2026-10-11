from fastapi import FastAPI

from app.errors import ErrorResponse, register_error_handlers
from app.routes import health, me

app = FastAPI(
    title="Arrendi",
    responses={422: {"model": ErrorResponse}},
)
register_error_handlers(app)

app.include_router(health.router, prefix="/api")
app.include_router(me.router, prefix="/api")
