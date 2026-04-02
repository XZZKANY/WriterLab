from __future__ import annotations

import re
from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.scene import Scene
from app.models.style_negative_rule import StyleNegativeRule
from app.schemas.workflow import StyleNegativeMatch, StyleNegativeRule as StyleNegativeRuleSchema


def list_active_style_negative_rules(db: Session, *, project_id=None, branch_id=None) -> list[StyleNegativeRule]:
    query = db.query(StyleNegativeRule).filter(StyleNegativeRule.active.is_(True))
    if project_id is not None:
        query = query.filter((StyleNegativeRule.project_id == project_id) | (StyleNegativeRule.project_id.is_(None)))
    if branch_id is not None:
        query = query.filter((StyleNegativeRule.branch_id == branch_id) | (StyleNegativeRule.branch_id.is_(None)))
    now = datetime.utcnow()
    return (
        query.filter((StyleNegativeRule.expires_at.is_(None)) | (StyleNegativeRule.expires_at > now))
        .order_by(StyleNegativeRule.severity.asc(), StyleNegativeRule.updated_at.desc())
        .all()
    )


def serialize_style_negative_rules(rules: Iterable[StyleNegativeRule]) -> list[StyleNegativeRuleSchema]:
    return [
        StyleNegativeRuleSchema(
            id=rule.id,
            project_id=rule.project_id,
            branch_id=rule.branch_id,
            scope_type=rule.scope_type,
            scope_id=rule.scope_id,
            label=rule.label,
            severity=rule.severity,
            match_mode=rule.match_mode,
            pattern=rule.pattern,
            active=rule.active,
            expires_at=rule.expires_at,
        )
        for rule in rules
    ]


def _synthetic_scene_rules(scene: Scene) -> list[StyleNegativeRuleSchema]:
    rules: list[StyleNegativeRuleSchema] = []
    for item in scene.must_avoid or []:
        text = str(item).strip()
        if not text:
            continue
        rules.append(
            StyleNegativeRuleSchema(
                id=None,
                project_id=None,
                branch_id=None,
                scope_type="scene_instruction",
                scope_id=scene.id,
                label=f"scene:{text[:40]}",
                severity="hard",
                match_mode="exact",
                pattern=text,
                active=True,
                expires_at=None,
            )
        )
    return rules


def resolve_style_negative_rules(db: Session, *, scene: Scene, project_id=None, branch_id=None) -> list[StyleNegativeRuleSchema]:
    persistent = serialize_style_negative_rules(list_active_style_negative_rules(db, project_id=project_id, branch_id=branch_id))
    return persistent + _synthetic_scene_rules(scene)


def match_style_negative_rules(text: str, rules: Iterable[StyleNegativeRuleSchema]) -> list[StyleNegativeMatch]:
    matches: list[StyleNegativeMatch] = []
    haystack = text or ""
    lowered = haystack.lower()
    for rule in rules:
        if not rule.active:
            continue
        matched_text = None
        if rule.match_mode == "exact":
            if rule.pattern and rule.pattern.lower() in lowered:
                matched_text = rule.pattern
        elif rule.match_mode == "regex":
            found = re.search(rule.pattern, haystack, re.IGNORECASE)
            if found:
                matched_text = found.group(0)
        elif rule.match_mode == "tag":
            if rule.pattern and rule.pattern.lower() in lowered:
                matched_text = rule.pattern
        elif rule.match_mode == "vector":
            # Schema placeholder only for v1; use simple substring similarity until a vector service exists.
            if rule.pattern and rule.pattern.lower() in lowered:
                matched_text = rule.pattern
        if matched_text is None:
            continue
        matches.append(
            StyleNegativeMatch(
                rule_id=str(rule.id) if rule.id else f"synthetic:{rule.label}",
                label=rule.label,
                severity=rule.severity,
                match_mode=rule.match_mode,
                matched_text=matched_text,
                reason=f"Matched {rule.match_mode} style negative rule",
                source=rule.scope_type,
            )
        )
    return matches
