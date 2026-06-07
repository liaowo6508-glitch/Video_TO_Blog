from __future__ import annotations

import json

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import pipelines  # noqa: F401
from api.routes.tasks import router as tasks_router
from engine.registry import PipelineRegistry

app = FastAPI(title="AI Pipeline Platform", version="0.1.0")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    body_json = None
    try:
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8", errors="replace")
        body_json = json.loads(body_str) if body_str.strip() else None
    except Exception:
        pass

    print(f"[422 DEBUG] path={request.url.path} method={request.method}")
    print(f"[422 DEBUG] request_body={body_json}")
    print(f"[422 DEBUG] validation_errors={exc.errors()}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )
app.include_router(tasks_router)


@app.get("/pipelines", response_model=list[str])
def list_pipelines() -> list[str]:
    return PipelineRegistry.list_names()


@app.get("/healthz")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
