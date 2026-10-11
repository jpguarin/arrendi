from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorResponse(BaseModel):
    detail: str
    code: str


class AppError(Exception):
    """Error with a message for the owner (in Spanish) and a stable code."""

    def __init__(self, status_code: int, detail: str, code: str) -> None:
        self.status_code = status_code
        self.detail = detail
        self.code = code


HTTP_ERRORS = {
    401: ("Tu sesión no es válida. Vuelve a ingresar.", "unauthorized"),
    404: ("No encontramos lo que buscas.", "not_found"),
    405: ("Esta acción no está permitida.", "method_not_allowed"),
}
DEFAULT_HTTP_ERROR = ("No pudimos completar la solicitud.", "http_error")


def unauthorized() -> AppError:
    detail, code = HTTP_ERRORS[401]
    return AppError(401, detail, code)


def auth_unavailable() -> AppError:
    return AppError(
        503,
        "No pudimos verificar tu sesión. Inténtalo de nuevo en un momento.",
        "auth_unavailable",
    )


def _response(status_code: int, detail: str, code: str) -> JSONResponse:
    body = ErrorResponse(detail=detail, code=code)
    return JSONResponse(status_code=status_code, content=body.model_dump())


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return _response(exc.status_code, exc.detail, exc.code)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail, code = HTTP_ERRORS.get(exc.status_code, DEFAULT_HTTP_ERROR)
        return _response(exc.status_code, detail, code)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _response(422, "Revisa los datos e inténtalo de nuevo.", "validation_error")
