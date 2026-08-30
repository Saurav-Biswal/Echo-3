"""Structured action derivation - the ACT half of the loop (§36)."""

from __future__ import annotations

from app.models.enums import ActionType, Category
from app.services.actions import build_actions


def test_place_actions_include_maps_and_source():
    actions = build_actions(
        category=Category.PLACE,
        title="Cafe XYZ",
        entity=None,
        source_url="https://example.com/cafe",
        suggested=[ActionType.OPEN_MAPS, ActionType.OPEN_SOURCE],
    )
    types = [a.action_type for a in actions]
    assert ActionType.OPEN_MAPS in types
    assert ActionType.OPEN_SOURCE in types
    # First action is primary; sort order is contiguous.
    assert actions[0].is_primary is True
    assert [a.sort_order for a in actions] == list(range(len(actions)))
    maps = next(a for a in actions if a.action_type == ActionType.OPEN_MAPS)
    assert maps.deep_link.startswith("geo:")
    assert maps.web_link.startswith("https://www.google.com/maps/search/")


def test_open_source_appended_when_url_present():
    actions = build_actions(
        category=Category.TOPIC,
        title="An article",
        entity=None,
        source_url="https://example.com/read",
        suggested=[],
    )
    # Falls back to the category default (OPEN_URL) and appends OPEN_SOURCE.
    types = [a.action_type for a in actions]
    assert ActionType.OPEN_SOURCE in types
    assert actions[0].is_primary is True


def test_duplicate_suggestions_are_deduplicated():
    actions = build_actions(
        category=Category.TOOL,
        title="Notion",
        entity=None,
        source_url="https://notion.so",
        suggested=[ActionType.OPEN_TOOL, ActionType.OPEN_TOOL, ActionType.OPEN_SOURCE],
    )
    types = [a.action_type for a in actions]
    assert types.count(ActionType.OPEN_TOOL) == 1


def test_unresolvable_actions_dropped_and_empty_when_no_link():
    # OPEN_URL needs a URL; with none and no source, it is dropped, leaving nothing.
    actions = build_actions(
        category=Category.TOPIC,
        title="A thought",
        entity=None,
        source_url=None,
        suggested=[ActionType.OPEN_URL],
    )
    assert actions == []
