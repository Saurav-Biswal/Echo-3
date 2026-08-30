"""Deterministic offline AI provider.

Not a stub: it implements the same contract as Gemini and produces a plausible,
*stable* :class:`IntentAnalysis` from whatever text the media carries. This is
what makes the hackathon demo run with no network and no key (§45), and what
lets the test-suite assert on intent without mocking a live model.

The heuristics are intentionally simple and transparent - keyword buckets, not a
model - because the point is determinism, not cleverness.
"""

from __future__ import annotations

import re

from app.models.enums import ActionType, Category, IntentAction, TriggerType
from app.schemas.ai_output import (
    ExtractedEntity,
    IntentAnalysis,
    IntentDetails,
    IntentEntities,
    IntentResurfacing,
    SourceProvenance,
)
from app.services.ai.base import AIProvider, AnalysisResult
from app.services.media.normalized import NormalizedMedia
from app.utils.timeparse import parse_date, parse_time

MODEL_NAME = "mock-intent-v1"

# Keyword buckets. Order matters only for ties; scoring picks the best.
_SIGNALS: dict[Category, tuple[str, ...]] = {
    Category.RECIPE: (
        "recipe", "ingredient", "cook", "bake", "roast", "fry", "dish",
        "curry", "pasta", "cake", "dough", "marinade", "tablespoon", "teaspoon",
        "preheat", "simmer", "grams", "serves", "meal", "sauce",
    ),
    Category.EVENT: (
        "event", "concert", "festival", "gig", "show", "tickets", "lineup",
        "conference", "meetup", "summit", "screening", "launch party", "workshop",
        "happening", "rsvp", "doors open", "live on",
    ),
    Category.PLACE: (
        "cafe", "café", "restaurant", "bar", "coffee", "bistro", "eatery",
        "street", "road", "nagar", "mumbai", "bangalore", "bengaluru", "delhi",
        "located", "address", "neighbourhood", "rooftop", "brunch", "visit",
        "trail", "beach", "hotel", "bakery",
    ),
    Category.TOOL: (
        "app", "tool", "gadget", "product", "software", "extension", "plugin",
        "device", "buy", "$", "subscription", "install", "download", "features",
        "startup", "saas", "framework", "library", "api",
    ),
    Category.TOPIC: (
        "article", "guide", "tutorial", "how to", "explained", "thread",
        "learn", "study", "research", "concept", "history", "science",
        "philosophy", "essay", "read", "blog", "paper", "documentary",
    ),
}

_ACTION_BY_CATEGORY: dict[Category, IntentAction] = {
    Category.PLACE: IntentAction.VISIT,
    Category.EVENT: IntentAction.ATTEND,
    Category.RECIPE: IntentAction.COOK,
    Category.TOOL: IntentAction.TRY,
    Category.TOPIC: IntentAction.READ,
}

_WHY_BY_CATEGORY: dict[Category, str] = {
    Category.PLACE: "you want to visit this place when you get the chance",
    Category.EVENT: "you want to attend this and not miss the date",
    Category.RECIPE: "you want to make this yourself later",
    Category.TOOL: "you want to try this out when you have a moment",
    Category.TOPIC: "you want to come back and read into this properly",
}

_RESURFACING_BY_CATEGORY: dict[Category, TriggerType] = {
    Category.PLACE: TriggerType.LOCATION,
    Category.EVENT: TriggerType.DATE,
    Category.RECIPE: TriggerType.TIME,
    Category.TOOL: TriggerType.MANUAL,
    Category.TOPIC: TriggerType.MANUAL,
}

_ACTIONS_BY_CATEGORY: dict[Category, list[ActionType]] = {
    Category.PLACE: [ActionType.OPEN_MAPS, ActionType.OPEN_SOURCE],
    Category.EVENT: [ActionType.ADD_TO_CALENDAR, ActionType.OPEN_EVENT],
    Category.RECIPE: [ActionType.VIEW_RECIPE, ActionType.OPEN_SOURCE],
    Category.TOOL: [ActionType.OPEN_TOOL, ActionType.OPEN_SOURCE],
    Category.TOPIC: [ActionType.OPEN_URL, ActionType.OPEN_SOURCE],
}


class MockAIProvider(AIProvider):
    name = "mock"

    async def analyze(self, media: NormalizedMedia) -> AnalysisResult:
        text = media.text_context
        haystack = text.lower()

        category, score, hits = _classify(haystack)
        title = _pick_title(media, category)
        confidence = _confidence(media, score, hits)

        # --- content understanding: only facts actually present in the text ---
        detected_date = _detect_date(text) if category == Category.EVENT else None
        detected_time = _detect_time(text) if category == Category.EVENT else None
        detected_location = _detect_location(text) if category == Category.PLACE else None
        detected_address = _detect_address(text) if category == Category.PLACE else None
        detected_price = _detect_price(text)
        detected_duration = _detect_duration(text) if category == Category.RECIPE else None
        urls = _detect_urls(text, media.source_url)
        primary_url = urls[0] if urls else None

        resurfacing_type = _RESURFACING_BY_CATEGORY[category]
        if category == Category.EVENT and detected_date is None:
            # No concrete date: fall back to a manual reminder rather than an
            # invented one.
            resurfacing_type = TriggerType.MANUAL

        entity = _build_entity(
            media,
            category,
            title,
            confidence,
            date=detected_date,
            time=detected_time,
            location=detected_location,
            address=detected_address,
            price=detected_price,
            duration_minutes=detected_duration,
            url=primary_url,
            text=text,
        )
        details = IntentDetails(
            date=detected_date,
            time=detected_time,
            location=detected_location,
            address=detected_address,
            price=detected_price,
            url=primary_url,
            urls=urls,
            # The mock never geocodes: coordinates are only ever real if the AI
            # read literal lat/lng, which the deterministic mock cannot do.
            latitude=None,
            longitude=None,
        )
        provenance = SourceProvenance(
            location_stated=detected_location is not None,
            address_stated=detected_address is not None,
            coordinates_stated=False,
            date_stated=detected_date is not None,
            time_stated=detected_time is not None,
            price_stated=detected_price is not None,
            url_stated=bool(urls),
        )

        analysis = IntentAnalysis(
            category=category,
            title=title,
            summary=_summary(media, title),
            why_saved=f"You probably saved this because {_WHY_BY_CATEGORY[category]}.",
            intent_action=_ACTION_BY_CATEGORY[category],
            confidence=confidence,
            entities=_entities_for(category, entity),
            details=details,
            provenance=provenance,
            resurfacing=IntentResurfacing(
                type=resurfacing_type,
                reason=_resurfacing_reason(category, resurfacing_type),
                fire_at=_fire_at(detected_date, detected_time),
            ),
            suggested_actions=_ACTIONS_BY_CATEGORY[category],
            uncertainty_note=(
                None
                if confidence >= 0.55
                else "The shared content was thin, so Echo is guessing at the intent."
            ),
        )
        return AnalysisResult(analysis=analysis, model=MODEL_NAME)


# --------------------------------------------------------------- heuristics


def _classify(haystack: str) -> tuple[Category, int, int]:
    """Return (category, score, distinct-hit-count). Ties break to TOPIC."""
    best_category = Category.TOPIC
    best_score = 0
    best_hits = 0
    for category, keywords in _SIGNALS.items():
        matched = [word for word in keywords if word in haystack]
        score = sum(haystack.count(word) for word in matched)
        if score > best_score:
            best_category, best_score, best_hits = category, score, len(matched)
    return best_category, best_score, best_hits


def _confidence(media: NormalizedMedia, score: int, hits: int) -> float:
    """Deterministic band: rich+specific -> HIGH, thin -> LOW.

    Kept explicit so a demo can reliably show all three confidence paths just by
    varying the input text.
    """
    if not media.text_context.strip() and not (media.has_video or media.has_image):
        return 0.3
    base = 0.45
    base += min(hits, 4) * 0.09          # up to +0.36 for distinct signals
    base += min(score, 6) * 0.02         # up to +0.12 for repetition
    if media.user_note:
        base += 0.12                     # an explicit note is strong intent
    if media.title:
        base += 0.05
    return round(min(base, 0.97), 2)


def _pick_title(media: NormalizedMedia, category: Category) -> str:
    if media.title and media.title.strip():
        return media.title.strip()[:120]
    text = (media.extracted_text or media.transcript or media.user_note or "").strip()
    if text:
        first_line = text.splitlines()[0].strip()
        if first_line:
            return first_line[:120]
    return f"Saved {category.value.lower()}"


def _summary(media: NormalizedMedia, title: str) -> str:
    for value in (media.description, media.extracted_text, media.transcript):
        if value and value.strip():
            condensed = " ".join(value.split())
            return condensed[:280]
    return f"{title} - saved from {media.platform.value}."


def _detect_date(text: str) -> str | None:
    for token in _candidate_date_tokens(text):
        parsed = parse_date(token)
        if parsed is not None:
            return parsed.isoformat()
    return None


def _candidate_date_tokens(text: str) -> list[str]:
    tokens: list[str] = re.findall(r"\d{4}-\d{1,2}-\d{1,2}", text)
    tokens += re.findall(
        r"(?i)\b(?:\d{1,2}\s+)?[A-Za-z]{3,9}\.?\s+\d{1,2}(?:,?\s+\d{4})?",
        text,
    )
    tokens += re.findall(r"(?i)\b\d{1,2}\s+[A-Za-z]{3,9}(?:,?\s+\d{4})?", text)
    return tokens


# Time: "19:30", "7:30 pm", "7pm", "doors at 8 pm". Never matches the day part
# of an ISO date (no bare "2026-09-14" false positive) because a colon or an
# am/pm marker is required.
_TIME_TOKEN = re.compile(r"(?i)\b(\d{1,2}[:.]\d{2}\s*(?:am|pm)?|\d{1,2}\s*(?:am|pm))\b")


def _detect_time(text: str) -> str | None:
    for match in _TIME_TOKEN.finditer(text):
        parsed = parse_time(match.group(1).strip())
        if parsed is not None:
            return parsed.strftime("%H:%M")
    return None


# Known localities the deterministic mock can recognise. Kept in step with the
# PLACE keyword bucket - the mock only ever "knows" a location it can see stated.
_KNOWN_CITIES: dict[str, str] = {
    "mumbai": "Mumbai",
    "bangalore": "Bangalore",
    "bengaluru": "Bengaluru",
    "delhi": "Delhi",
}


def _detect_location(text: str) -> str | None:
    lowered = text.lower()
    for needle, proper in _KNOWN_CITIES.items():
        if needle in lowered:
            return proper
    return None


# Address: a token ending in a street-type word, with 1-4 leading name words,
# e.g. "MG Road", "12 Brigade Road", "Linking Street". Deterministic and only
# ever returns text literally present in the source.
_ADDRESS = re.compile(
    r"\b((?:[A-Z0-9][\w.'-]*\s+){0,3}[A-Z0-9][\w.'-]*\s+"
    r"(?:Road|Rd|Street|St|Nagar|Avenue|Ave|Lane|Marg|Cross|Layout|Boulevard|Blvd))\b"
)


def _detect_address(text: str) -> str | None:
    match = _ADDRESS.search(text)
    return match.group(1).strip() if match else None


# Price: currency symbol/code + amount, or amount + currency word. Only what is
# literally written - the mock never invents a figure.
_PRICE = re.compile(
    r"(?i)("
    r"(?:₹|\$|€|£|rs\.?|inr|usd|eur|gbp)\s?\d[\d,]*(?:\.\d{1,2})?"
    r"|\d[\d,]*(?:\.\d{1,2})?\s?(?:rupees|dollars|euros|pounds)"
    r")"
)


def _detect_price(text: str) -> str | None:
    match = _PRICE.search(text)
    return match.group(1).strip() if match else None


# Duration for recipes: "30 minutes", "45 mins", "1 hour", "1.5 hours".
_DURATION = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*(hours?|hrs?|minutes?|mins?)\b")


def _detect_duration(text: str) -> int | None:
    match = _DURATION.search(text)
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2).lower()
    minutes = amount * 60 if unit.startswith(("hour", "hr")) else amount
    minutes = int(round(minutes))
    return minutes if minutes > 0 else None


_URL = re.compile(r"https?://[^\s)>\]]+", re.IGNORECASE)


def _detect_urls(text: str, source_url: str | None) -> list[str]:
    seen: list[str] = []
    candidates = _URL.findall(text)
    if source_url:
        candidates.append(source_url)
    for raw in candidates:
        url = raw.strip().rstrip(".,;")
        if url.startswith(("http://", "https://")) and url not in seen:
            seen.append(url)
    return seen[:5]


def _fire_at(date: str | None, time: str | None) -> str | None:
    """Absolute ISO datetime for a DATE/TIME trigger, else null. Defaults a
    dateless event to the morning rather than inventing a precise moment."""
    if not date:
        return None
    return f"{date}T{time or '09:00'}:00"


def _build_entity(
    media: NormalizedMedia,
    category: Category,
    title: str,
    confidence: float,
    *,
    date: str | None,
    time: str | None,
    location: str | None,
    address: str | None,
    price: str | None,
    duration_minutes: int | None,
    url: str | None,
    text: str,
) -> ExtractedEntity:
    # Prefer a place name read from the text; fall back to the source's own
    # site name only for a PLACE. Everything else stays null unless stated.
    entity_location = location
    if entity_location is None and category == Category.PLACE:
        entity_location = media.metadata.get("site_name")

    return ExtractedEntity(
        name=title,
        description=(media.description or None),
        location=entity_location,
        address=address,
        date=date,
        time=time,
        duration_minutes=duration_minutes,
        url=url or media.source_url,
        price=price,
        # The mock never geocodes - coordinates are only ever real if literal
        # lat/lng were read, which the deterministic mock cannot do.
        latitude=None,
        longitude=None,
        confidence=confidence,
    )


def _entities_for(category: Category, entity: ExtractedEntity) -> IntentEntities:
    entities = IntentEntities()
    entities.for_category(category).append(entity)
    return entities


def _resurfacing_reason(category: Category, trigger_type: TriggerType) -> str:
    if trigger_type == TriggerType.LOCATION:
        return "You may want this when you are nearby."
    if trigger_type in (TriggerType.DATE, TriggerType.TIME):
        return "This is tied to a specific time, so Echo will remind you before it."
    return "No natural moment to resurface, so Echo keeps it ready for when you look."
