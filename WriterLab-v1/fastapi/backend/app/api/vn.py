from fastapi import APIRouter

from app.schemas.vn_export import VNExportRequest, VNExportResponse
from app.services.vn_export_service import export_vn_script

router = APIRouter(prefix="/api/vn", tags=["vn"])


@router.post("/export", response_model=VNExportResponse)
def export_vn(payload: VNExportRequest):
    return export_vn_script(
        payload.draft_text,
        scene_title=payload.scene_title,
        include_image_prompts=payload.include_image_prompts,
    )
