"""Minimal Render entry point for scheduled or webhook-triggered ETL jobs.

This file is intentionally narrow in scope: it exposes a small FastAPI app and a
single endpoint that runs the extraction worker for a given mock transcript text.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from etl_worker import (
    EtlAuthorizationError,
    EtlConfigurationError,
    authorize_etl_request,
    extract_assembly_record,
)

logger = logging.getLogger("gijiraku.render_etl")

app = FastAPI(title="MachiVoice ETL Worker", version="0.1.0")


class ETLRequest(BaseModel):
    raw_text: str = Field(min_length=1, max_length=100_000)
    model: Optional[str] = Field(default=None, max_length=100)


class ETLResponse(BaseModel):
    ok: bool
    record: Dict[str, Any]


@app.get("/health")
def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/etl/extract", response_model=ETLResponse)
def run_extract(
    request: ETLRequest,
    x_etl_api_key: Optional[str] = Header(default=None),
) -> ETLResponse:
    try:
        authorize_etl_request(x_etl_api_key)
        record = extract_assembly_record(request.raw_text, model_name=request.model)
    except EtlConfigurationError as exc:
        raise HTTPException(status_code=503, detail="ETL endpoint is not configured") from exc
    except EtlAuthorizationError as exc:
        raise HTTPException(status_code=401, detail="Invalid ETL API key") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - depends on deployment env
        logger.exception("ETL extraction failed")
        raise HTTPException(status_code=500, detail="ETL extraction failed") from exc

    return ETLResponse(ok=True, record=record)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("render_etl_service:app", host="0.0.0.0", port=port, reload=False)
