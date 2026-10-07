"""Global API exception handlers for uniform error envelopes."""

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

def register_exception_handlers(app: FastAPI) -> None:
    """Registers standard, backwards-compatible error envelopes across all HTTP exceptions."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request, exc: HTTPException):
        code_map = {
            400: "BAD_REQUEST",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "UNPROCESSABLE_ENTITY",
            500: "SERVER_ERROR",
        }
        code = code_map.get(exc.status_code, f"HTTP_{exc.status_code}")
        msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {"code": code, "message": msg},
                "detail": msg,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid request parameters or payload",
                    "details": exc.errors(),
                },
                "detail": exc.errors(),
            },
        )
