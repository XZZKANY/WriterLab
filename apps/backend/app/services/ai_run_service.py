import uuid

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.models.ai_run import AIRun


def save_ai_run(
    db: Session,
    *,
    run_id: uuid.UUID,
    scene_id: uuid.UUID | None,
    run_type: str,
    model: str,
    input_payload: dict,
    raw_response: str | None,
    parsed_response: dict | None,
    status: str,
    error_message: str | None,
    latency_ms: int,
    task_type: str | None = None,
    provider: str | None = None,
    prompt_version: str | None = None,
    fallback_used: bool | None = None,
    token_usage: dict | None = None,
    project_id: uuid.UUID | None = None,
) -> None:
    db.add(
        AIRun(
            id=run_id,
            scene_id=scene_id,
            project_id=project_id,
            run_type=run_type,
            task_type=task_type,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
            fallback_used=fallback_used,
            input_payload=jsonable_encoder(input_payload),
            raw_response=raw_response,
            parsed_response=jsonable_encoder(parsed_response) if parsed_response is not None else None,
            token_usage=jsonable_encoder(token_usage) if token_usage is not None else None,
            status=status,
            error_message=error_message,
            latency_ms=latency_ms,
        )
    )
    db.commit()
