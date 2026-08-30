"""Memory assembly and correction - the SAVE that ties the loop together.

``create_from_analysis`` is the single place a full Echo memory is composed:
the memory row, its structured entities, its resurfacing trigger(s) and its
executable actions, all persisted together. ``apply_correction`` implements the
"Not quite" path (§14): changing the category re-derives triggers and actions,
because the point of the correction is to fix what Echo will *do*.
"""

from __future__ import annotations

from typing import Any

from app.models import (
    Category,
    EchoMemory,
    Entity,
    EntityType,
    MediaSource,
    MemoryStatus,
    TriggerType,
)
from app.repositories import MemoryRepository, SourceRepository
from app.schemas.ai_output import ExtractedEntity, IntentAnalysis, IntentResurfacing
from app.schemas.memory import MemoryCorrection
from app.services.actions import build_actions
from app.services.intent import IntentResult
from app.services.media.normalized import NormalizedMedia
from app.services.trigger import build_triggers
from app.utils.timeparse import combine, parse_date, parse_time

# What moment a re-categorised memory should resurface at.
_CORRECTION_RESURFACING: dict[Category, TriggerType] = {
    Category.PLACE: TriggerType.LOCATION,
    Category.EVENT: TriggerType.DATE,
    Category.RECIPE: TriggerType.TIME,
    Category.TOOL: TriggerType.MANUAL,
    Category.TOPIC: TriggerType.MANUAL,
}

def _synthesize_entity(analysis: IntentAnalysis) -> ExtractedEntity:
    """When the AI named no entity, make one from the memory's own fields.

    A PLACE with no place, or an EVENT with no event, would have nothing to
    build a trigger or a maps/calendar action from - so we fall back to the
    title plus whatever details survived extraction.
    """
    details = analysis.details
    return ExtractedEntity(
        name=analysis.title,
        description=analysis.summary,
        location=details.location,
        address=details.address,
        latitude=details.latitude,
        longitude=details.longitude,
        date=details.date,
        time=details.time,
        url=details.url,
        price=details.price,
        confidence=analysis.confidence,
    )


def _to_orm_entity(
    extracted: ExtractedEntity, category: Category, *, is_primary: bool
) -> Entity:
    event_date = parse_date(extracted.date) if extracted.date else None
    starts_at = (
        combine(event_date, parse_time(extracted.time))
        if event_date is not None
        else None
    )
    ends_at = (
        combine(event_date, parse_time(extracted.end_time))
        if event_date is not None and extracted.end_time
        else None
    )

    details: dict[str, Any] = {}
    if extracted.ingredients:
        details["ingredients"] = extracted.ingredients
    if extracted.steps:
        details["steps"] = extracted.steps
    if extracted.key_points:
        details["key_points"] = extracted.key_points
    if extracted.purpose:
        details["purpose"] = extracted.purpose

    return Entity(
        entity_type=EntityType(category.value),
        name=extracted.name,
        description=extracted.description,
        location=extracted.location,
        address=extracted.address,
        latitude=extracted.latitude,
        longitude=extracted.longitude,
        event_date=event_date,
        event_time=extracted.time,
        starts_at=starts_at,
        ends_at=ends_at,
        venue=extracted.venue,
        url=extracted.url,
        price=extracted.price,
        duration_minutes=extracted.duration_minutes,
        details=details,
        confidence=extracted.confidence,
        is_primary=is_primary,
    )


def _entities_from_analysis(analysis: IntentAnalysis) -> list[Entity]:
    extracted = analysis.entities.for_category(analysis.category)
    if not extracted:
        extracted = [_synthesize_entity(analysis)]
    return [
        _to_orm_entity(item, analysis.category, is_primary=(index == 0))
        for index, item in enumerate(extracted[:5])
    ]


def _source_from_media(media: NormalizedMedia, *, user_id: Any) -> MediaSource:
    """Persist provenance only - never the raw video/image bytes (§43)."""
    return MediaSource(
        user_id=user_id,
        source_type=media.source_type,
        platform=media.platform,
        media_type=media.media_type,
        source_url=media.source_url,
        canonical_url=media.canonical_url,
        title=media.title,
        description=media.description,
        thumbnail_url=media.thumbnail_url,
        media_uri=media.media_uri,
        transcript=media.transcript,
        extracted_text=media.extracted_text,
        author=media.author,
        duration_seconds=media.duration_seconds,
        source_metadata=media.metadata or {},
    )


class MemoryService:
    """Composes and corrects full memories inside one session/transaction."""

    def __init__(self, session: Any) -> None:
        self.session = session
        self.memories = MemoryRepository(session)
        self.sources = SourceRepository(session)

    async def create_source(
        self, media: NormalizedMedia, *, user_id: Any
    ) -> MediaSource:
        return await self.sources.create(_source_from_media(media, user_id=user_id))

    async def create_from_analysis(
        self,
        *,
        user_id: Any,
        media: NormalizedMedia,
        source: MediaSource,
        intent_result: IntentResult,
    ) -> EchoMemory:
        analysis: IntentAnalysis = intent_result.analysis  # type: ignore[assignment]

        entities = _entities_from_analysis(analysis)
        primary = entities[0] if entities else None
        source_url = source.source_url if source is not None else media.source_url

        triggers = build_triggers(
            analysis=analysis, entity=primary, user_id=user_id
        )
        actions = build_actions(
            category=analysis.category,
            title=analysis.title,
            entity=primary,
            source_url=source_url,
            suggested=analysis.suggested_actions,
        )

        memory = EchoMemory(
            user_id=user_id,
            source_id=source.id if source is not None else None,
            category=analysis.category,
            title=analysis.title,
            summary=analysis.summary,
            why_saved=analysis.why_saved,
            intent_action=analysis.intent_action,
            intent_confidence=analysis.confidence,
            confidence_band=intent_result.band,
            status=intent_result.status,
            needs_review_reason=intent_result.review_reason,
            ai_model=intent_result.model,
            ai_payload=analysis.model_dump(mode="json"),
        )
        memory.entities = entities
        memory.triggers = triggers
        memory.actions = actions
        return await self.memories.create(memory)

    async def apply_correction(
        self, memory: EchoMemory, correction: MemoryCorrection
    ) -> EchoMemory:
        touched = False

        if correction.confirmed:
            memory.user_confirmed = True
            touched = True
        if correction.intent_action is not None:
            memory.intent_action = correction.intent_action
            memory.user_corrected = True
            touched = True
        if correction.category is not None and correction.category != memory.category:
            self._recategorise(memory, correction.category)
            memory.user_corrected = True
            touched = True

        # A correction resolves a review: the user just told us what it is.
        if touched and memory.status == MemoryStatus.NEEDS_REVIEW:
            memory.status = MemoryStatus.ACTIVE
            memory.needs_review_reason = None

        await self.session.flush()
        return memory

    def _recategorise(self, memory: EchoMemory, new_category: Category) -> None:
        """Change the category and re-derive what the memory will *do* (§14)."""
        memory.category = new_category

        primary = memory.primary_entity
        if primary is not None:
            primary.entity_type = EntityType(new_category.value)

        analysis = IntentAnalysis.model_validate(memory.ai_payload)
        analysis.category = new_category
        analysis.resurfacing = IntentResurfacing(
            type=_CORRECTION_RESURFACING[new_category],
            reason=analysis.resurfacing.reason,
            fire_at=analysis.resurfacing.fire_at,
        )

        source_url = memory.source.source_url if memory.source is not None else None
        memory.triggers = build_triggers(
            analysis=analysis, entity=primary, user_id=memory.user_id
        )
        memory.actions = build_actions(
            category=new_category,
            title=memory.title,
            entity=primary,
            source_url=source_url,
            suggested=analysis.suggested_actions,
        )


__all__ = ["MemoryService"]
