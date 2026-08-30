"""Deriving structured, executable actions - the "ACT" half of the loop (§36).

Actions are typed rows with resolved links, never free text: the Android app and
the dashboard render and execute them without parsing anything. ``deep_link`` is
an Android-native intent URI; ``web_link`` is the browser-openable equivalent.
Either may be null when it does not apply.

This module is pure: it takes plain data and returns unattached
:class:`MemoryAction` rows. The memory service attaches them to a memory.
"""

from __future__ import annotations

from urllib.parse import quote, urlencode

from app.models import ActionType, Category, Entity, MemoryAction

_LABELS: dict[ActionType, str] = {
    ActionType.OPEN_MAPS: "Open in Maps",
    ActionType.ADD_TO_CALENDAR: "Add to Calendar",
    ActionType.OPEN_EVENT: "View Event",
    ActionType.VIEW_RECIPE: "View Recipe",
    ActionType.OPEN_TOOL: "Open Tool",
    ActionType.OPEN_SOURCE: "Open Original",
    ActionType.OPEN_URL: "Open Link",
    ActionType.SET_REMINDER: "Remind Me",
}

# What Echo offers when the model suggested nothing usable, per category.
_DEFAULT_ACTIONS: dict[Category, list[ActionType]] = {
    Category.PLACE: [ActionType.OPEN_MAPS],
    Category.EVENT: [ActionType.ADD_TO_CALENDAR],
    Category.RECIPE: [ActionType.VIEW_RECIPE],
    Category.TOOL: [ActionType.OPEN_TOOL],
    Category.TOPIC: [ActionType.OPEN_URL],
}


def build_actions(
    *,
    category: Category,
    title: str,
    entity: Entity | None,
    source_url: str | None,
    suggested: list[ActionType],
) -> list[MemoryAction]:
    """Return ordered, deduplicated actions with resolved links.

    An action whose links cannot be resolved (e.g. OPEN_MAPS with no place) is
    dropped rather than shipped broken. OPEN_SOURCE is always appended when a
    source URL exists, so every memory keeps a way back to what was saved.
    """
    ordered = list(suggested) or list(_DEFAULT_ACTIONS.get(category, []))
    if source_url and ActionType.OPEN_SOURCE not in ordered:
        ordered.append(ActionType.OPEN_SOURCE)

    actions: list[MemoryAction] = []
    seen: set[ActionType] = set()
    for action_type in ordered:
        if action_type in seen:
            continue
        built = _build_one(action_type, title, entity, source_url)
        if built is None:
            continue
        seen.add(action_type)
        built.sort_order = len(actions)
        built.is_primary = not actions
        actions.append(built)

    # Guarantee at least one way to act, even for a bare TOPIC.
    if not actions and source_url:
        fallback = _link_action(ActionType.OPEN_URL, source_url)
        fallback.is_primary = True
        actions.append(fallback)
    return actions


def _build_one(
    action_type: ActionType,
    title: str,
    entity: Entity | None,
    source_url: str | None,
) -> MemoryAction | None:
    if action_type == ActionType.OPEN_MAPS:
        return _maps_action(title, entity)
    if action_type == ActionType.ADD_TO_CALENDAR:
        return _calendar_action(title, entity)
    if action_type in (
        ActionType.OPEN_EVENT,
        ActionType.VIEW_RECIPE,
        ActionType.OPEN_TOOL,
        ActionType.OPEN_URL,
    ):
        url = (entity.url if entity else None) or source_url
        return _link_action(action_type, url) if url else None
    if action_type == ActionType.OPEN_SOURCE:
        return _link_action(action_type, source_url) if source_url else None
    if action_type == ActionType.SET_REMINDER:
        return MemoryAction(action_type=action_type, label=_LABELS[action_type])
    return None


def _maps_action(title: str, entity: Entity | None) -> MemoryAction | None:
    query = title
    lat = lng = None
    if entity is not None:
        if entity.has_coordinates:
            lat, lng = entity.latitude, entity.longitude
        query = entity.address or entity.name or entity.location or title
    if not query and lat is None:
        return None

    if lat is not None and lng is not None:
        deep_link = f"geo:{lat},{lng}?q={quote(query)}"
    else:
        deep_link = f"geo:0,0?q={quote(query)}"
    web_link = "https://www.google.com/maps/search/?" + urlencode(
        {"api": 1, "query": query}
    )
    return MemoryAction(
        action_type=ActionType.OPEN_MAPS,
        label=_LABELS[ActionType.OPEN_MAPS],
        deep_link=deep_link,
        web_link=web_link,
        action_metadata=(
            {"latitude": lat, "longitude": lng} if lat is not None else {}
        ),
    )


def _calendar_action(title: str, entity: Entity | None) -> MemoryAction:
    params: dict[str, str] = {"action": "TEMPLATE", "text": title}
    if entity is not None:
        dates = _calendar_dates(entity)
        if dates:
            params["dates"] = dates
        location = entity.venue or entity.address or entity.location
        if location:
            params["location"] = location
    web_link = "https://calendar.google.com/calendar/render?" + urlencode(params)
    return MemoryAction(
        action_type=ActionType.ADD_TO_CALENDAR,
        label=_LABELS[ActionType.ADD_TO_CALENDAR],
        web_link=web_link,
        action_metadata={"title": title},
    )


def _calendar_dates(entity: Entity) -> str | None:
    start = entity.starts_at
    if start is None and entity.event_date is not None:
        from datetime import datetime, time

        start = datetime.combine(entity.event_date, time(9, 0))
    if start is None:
        return None
    end = entity.ends_at
    fmt = "%Y%m%dT%H%M%S"
    start_str = start.strftime(fmt)
    end_str = end.strftime(fmt) if end is not None else start_str
    return f"{start_str}/{end_str}"


def _link_action(action_type: ActionType, url: str) -> MemoryAction:
    return MemoryAction(
        action_type=action_type,
        label=_LABELS[action_type],
        deep_link=url,
        web_link=url,
    )
