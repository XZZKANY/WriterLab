from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.ai_run import AIRun
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.character import Character
from app.models.consistency_issue import ConsistencyIssue
from app.models.knowledge_chunk import KnowledgeChunk
from app.models.knowledge_document import KnowledgeDocument
from app.models.location import Location
from app.models.lore_entry import LoreEntry
from app.models.project import Project
from app.models.scene import Scene
from app.models.scene_analysis import SceneAnalysis
from app.models.scene_analysis_item import SceneAnalysisItem
from app.models.scene_version import SceneVersion
from app.models.story_branch import StoryBranch
from app.models.style_memory import StyleMemory
from app.models.style_negative_rule import StyleNegativeRule
from app.models.timeline_event import TimelineEvent
from app.models.workflow_request_dedup import WorkflowRequestDedup
from app.models.workflow_run import WorkflowRun
from app.models.workflow_step import WorkflowStep
from app.repositories.scene_repository import list_scenes_by_chapter


def _collect_ids(db: Session, column, *filters) -> list[UUID]:
    query = db.query(column)
    if filters:
        query = query.filter(*filters)
    return [item[0] for item in query.all()]


def _delete_matching(db: Session, model, filters: Sequence[object], *, use_or: bool = False) -> None:
    active_filters = [item for item in filters if item is not None]
    if not active_filters:
        return
    query = db.query(model)
    query = query.filter(or_(*active_filters)) if use_or else query.filter(*active_filters)
    query.delete(synchronize_session=False)


def _delete_by_ids(db: Session, model, column, ids: Sequence[UUID]) -> None:
    if not ids:
        return
    db.query(model).filter(column.in_(ids)).delete(synchronize_session=False)


def _clear_scene_version_workflow_steps(db: Session, scene_ids: Sequence[UUID]) -> None:
    if not scene_ids:
        return
    (
        db.query(SceneVersion)
        .filter(SceneVersion.scene_id.in_(scene_ids), SceneVersion.workflow_step_id.is_not(None))
        .update({SceneVersion.workflow_step_id: None}, synchronize_session=False)
    )


def list_projects(db: Session) -> list[Project]:
    return db.query(Project).order_by(Project.created_at.desc()).all()


def list_books_by_project(db: Session, project_id):
    return db.query(Book).filter(Book.project_id == project_id).order_by(Book.created_at.asc()).all()


def list_chapters_by_book(db: Session, book_id):
    return db.query(Chapter).filter(Chapter.book_id == book_id).order_by(Chapter.chapter_no.asc()).all()


def get_project_overview(db: Session, project_id: UUID) -> dict | None:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return None

    books = list_books_by_project(db, project_id)
    chapters_by_book = {
        str(book.id): list_chapters_by_book(db, book.id)
        for book in books
    }
    scenes_by_chapter = {
        str(chapter.id): list_scenes_by_chapter(db, chapter.id)
        for chapters in chapters_by_book.values()
        for chapter in chapters
    }

    return {
        "project": project,
        "books": books,
        "chapters_by_book": chapters_by_book,
        "scenes_by_chapter": scenes_by_chapter,
        "counts": {
            "books": len(books),
            "chapters": sum(len(items) for items in chapters_by_book.values()),
            "scenes": sum(len(items) for items in scenes_by_chapter.values()),
        },
    }


def delete_project(db: Session, project_id: UUID) -> bool:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return False

    book_ids = _collect_ids(db, Book.id, Book.project_id == project_id)
    chapter_ids = _collect_ids(db, Chapter.id, Chapter.book_id.in_(book_ids)) if book_ids else []
    scene_ids = _collect_ids(db, Scene.id, Scene.chapter_id.in_(chapter_ids)) if chapter_ids else []
    document_ids = _collect_ids(db, KnowledgeDocument.id, KnowledgeDocument.project_id == project_id)
    branch_ids = _collect_ids(db, StoryBranch.id, StoryBranch.project_id == project_id)
    analysis_ids = _collect_ids(
        db,
        SceneAnalysis.id,
        or_(
            SceneAnalysis.project_id == project_id,
            SceneAnalysis.scene_id.in_(scene_ids) if scene_ids else False,
        ),
    )

    workflow_run_filters = [WorkflowRun.project_id == project_id]
    if scene_ids:
        workflow_run_filters.append(WorkflowRun.scene_id.in_(scene_ids))
    if branch_ids:
        workflow_run_filters.append(WorkflowRun.branch_id.in_(branch_ids))
    workflow_run_ids = _collect_ids(db, WorkflowRun.id, or_(*workflow_run_filters))

    cleanup_steps: tuple[tuple[object, tuple[object, ...], bool], ...] = (
        (WorkflowRequestDedup, (WorkflowRequestDedup.workflow_run_id.in_(workflow_run_ids),), False),
        (WorkflowStep, (WorkflowStep.workflow_run_id.in_(workflow_run_ids),), False),
        (
            ConsistencyIssue,
            (
                ConsistencyIssue.project_id == project_id,
                ConsistencyIssue.scene_id.in_(scene_ids) if scene_ids else None,
                ConsistencyIssue.workflow_run_id.in_(workflow_run_ids) if workflow_run_ids else None,
            ),
            True,
        ),
        (
            StyleNegativeRule,
            (
                StyleNegativeRule.project_id == project_id,
                StyleNegativeRule.branch_id.in_(branch_ids) if branch_ids else None,
            ),
            True,
        ),
        (WorkflowRun, (WorkflowRun.id.in_(workflow_run_ids),), False),
        (SceneAnalysisItem, (SceneAnalysisItem.analysis_id.in_(analysis_ids),), False),
        (
            SceneAnalysis,
            (
                SceneAnalysis.project_id == project_id,
                SceneAnalysis.scene_id.in_(scene_ids) if scene_ids else None,
            ),
            True,
        ),
        (
            AIRun,
            (
                AIRun.project_id == project_id,
                AIRun.scene_id.in_(scene_ids) if scene_ids else None,
            ),
            True,
        ),
        (StyleMemory, (StyleMemory.project_id == project_id,), False),
        (TimelineEvent, (TimelineEvent.project_id == project_id,), False),
        (
            KnowledgeChunk,
            (
                KnowledgeChunk.document_id.in_(document_ids) if document_ids else None,
                KnowledgeChunk.project_id == project_id,
            ),
            True,
        ),
        (KnowledgeDocument, (KnowledgeDocument.project_id == project_id,), False),
        (Character, (Character.project_id == project_id,), False),
        (Location, (Location.project_id == project_id,), False),
        (LoreEntry, (LoreEntry.project_id == project_id,), False),
    )
    for model, filters, use_or in cleanup_steps:
        if model is WorkflowStep:
            _clear_scene_version_workflow_steps(db, scene_ids)
        _delete_matching(db, model, filters, use_or=use_or)

    _delete_by_ids(db, StoryBranch, StoryBranch.id, branch_ids)
    _delete_by_ids(db, SceneVersion, SceneVersion.scene_id, scene_ids)
    _delete_by_ids(db, Scene, Scene.id, scene_ids)
    _delete_by_ids(db, Chapter, Chapter.id, chapter_ids)
    _delete_by_ids(db, Book, Book.id, book_ids)

    db.delete(project)
    db.commit()
    return True
