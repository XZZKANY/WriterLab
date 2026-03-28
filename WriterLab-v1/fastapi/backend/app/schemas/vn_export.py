from pydantic import BaseModel, Field


class VNExportRequest(BaseModel):
    draft_text: str
    scene_title: str | None = None
    include_image_prompts: bool = True


class VNDialogueLine(BaseModel):
    kind: str
    character: str | None = None
    expression: str | None = None
    text: str


class VNExportResponse(BaseModel):
    title: str | None = None
    lines: list[VNDialogueLine] = Field(default_factory=list)
    markdown_script: str
    image_prompts: list[str] = Field(default_factory=list)
