# 该模块是 ORM 模型的汇聚入口：把每个 model 类都 import 一次，
# 让 Alembic 的 autogenerate 与 Base.metadata 能看到全部表。
# 因此这里所有 import 都是有意保留的，pyflakes 报"unused"是误判。
# ruff: noqa: F401
from app.db.session import Base
from app.models.project import Project
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.scene import Scene
from app.models.character import Character
from app.models.location import Location
from app.models.lore_entry import LoreEntry
from app.models.ai_run import AIRun
from app.models.consistency_issue import ConsistencyIssue
from app.models.knowledge_document import KnowledgeDocument
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.model_profile import ModelProfile
from app.models.scene_analysis import SceneAnalysis
from app.models.scene_analysis_item import SceneAnalysisItem
from app.models.scene_version import SceneVersion
from app.models.story_branch import StoryBranch
from app.models.style_memory import StyleMemory
from app.models.style_negative_rule import StyleNegativeRule
from app.models.timeline_event import TimelineEvent
from app.models.workflow_run import WorkflowRun
from app.models.workflow_request_dedup import WorkflowRequestDedup
from app.models.workflow_step import WorkflowStep
from app.models.vram_lock import VRAMLock
