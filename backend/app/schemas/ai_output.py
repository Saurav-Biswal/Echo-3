"""The AI contract.

This module is the *only* place that describes what the model is allowed to
return. It is handed to Gemini as a response schema (so the constraint is
enforced at generation time) and re-validated on receipt, because business logic
never reads free-form model text (§10).

Deliberate constraints, all so the schema survives Gemini's JSON-schema subset:
  * no ``dict``/``Any`` fields - open maps are not expressible;
  * enums are real Python enums, which become ``enum`` constraints;
  * dates/times are strings, parsed defensively server-side, because models are
    far more reliable emitting "2026-09-15" than a typed timestamp.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ActionType, Category, IntentAction, TriggerType


class ExtractedEntity(BaseModel):
    """One concrete thing the user might act on.

    A single shape serves all five buckets: a place fills coordinates, an event
    fills date/venue, a recipe fills ingredients. Unused fields must be null
    rather than invented (§9).
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="The specific name of this entity as stated in the content.")
    description: str | None = Field(
        default=None, description="One short line about this entity. Null if unknown."
    )

    # --- place ---
    location: str | None = Field(
        default=None, description="City or locality, e.g. 'Mumbai'. Null if not stated."
    )
    address: str | None = Field(default=None, description="Street address if stated, else null.")
    latitude: float | None = Field(
        default=None, description="Only if explicitly present in the content. Never estimated."
    )
    longitude: float | None = Field(
        default=None, description="Only if explicitly present in the content. Never estimated."
    )

    # --- event ---
    date: str | None = Field(
        default=None, description="Event date as YYYY-MM-DD. Null if not stated."
    )
    time: str | None = Field(
        default=None, description="Start time as 24h HH:MM. Null if not stated."
    )
    end_time: str | None = Field(default=None, description="End time as 24h HH:MM, else null.")
    venue: str | None = Field(default=None, description="Venue name if stated, else null.")

    # --- recipe ---
    ingredients: list[str] = Field(
        default_factory=list, description="Ingredients named in the content. Empty if none."
    )
    steps: list[str] = Field(
        default_factory=list, description="Key steps, only if clearly stated. Empty if none."
    )
    duration_minutes: int | None = Field(
        default=None, description="Cooking or reading time in minutes, else null."
    )

    # --- tool / topic ---
    purpose: str | None = Field(
        default=None, description="What this tool or topic is for, else null."
    )
    key_points: list[str] = Field(
        default_factory=list, description="Notable features or key ideas. Empty if none."
    )

    # --- shared ---
    url: str | None = Field(default=None, description="Direct URL if stated, else null.")
    price: str | None = Field(default=None, description="Price or cost if stated, else null.")
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="How sure you are this entity is correct."
    )

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("entity name must not be blank")
        return cleaned[:300]

    @model_validator(mode="after")
    def _sanitize_coordinates(self) -> "ExtractedEntity":
        """Anti-hallucination guard (§9): coordinates must be a valid, complete
        pair or they are dropped. A lone latitude, or a value outside Earth's
        range, is a fabricated/garbled coordinate and would send a reminder to
        the wrong place - so we null both rather than trust it."""
        lat, lng = self.latitude, self.longitude
        valid = (
            lat is not None
            and lng is not None
            and -90.0 <= lat <= 90.0
            and -180.0 <= lng <= 180.0
            and not (lat == 0.0 and lng == 0.0)  # null island == "unknown"
        )
        if not valid:
            self.latitude = None
            self.longitude = None
        return self


class IntentEntities(BaseModel):
    """Entities grouped by the five Echo categories."""

    model_config = ConfigDict(extra="ignore")

    places: list[ExtractedEntity] = Field(default_factory=list)
    events: list[ExtractedEntity] = Field(default_factory=list)
    recipes: list[ExtractedEntity] = Field(default_factory=list)
    tools: list[ExtractedEntity] = Field(default_factory=list)
    topics: list[ExtractedEntity] = Field(default_factory=list)

    def for_category(self, category: Category) -> list[ExtractedEntity]:
        return {
            Category.PLACE: self.places,
            Category.EVENT: self.events,
            Category.RECIPE: self.recipes,
            Category.TOOL: self.tools,
            Category.TOPIC: self.topics,
        }[category]

    def all_entities(self) -> list[ExtractedEntity]:
        return [*self.places, *self.events, *self.recipes, *self.tools, *self.topics]


class IntentDetails(BaseModel):
    """Memory-level facts, as opposed to per-entity facts.

    Every field here is CONTENT UNDERSTANDING: a fact that must be *directly
    present* in the source. When it is not stated, it is ``null`` - never
    inferred, never guessed. Which of these were actually stated is declared
    separately in :class:`SourceProvenance`.
    """

    model_config = ConfigDict(extra="ignore")

    date: str | None = Field(default=None, description="Primary date as YYYY-MM-DD, else null.")
    time: str | None = Field(default=None, description="Primary time as 24h HH:MM, else null.")
    location: str | None = Field(default=None, description="Primary city/locality, else null.")
    address: str | None = Field(default=None, description="Primary address, else null.")
    latitude: float | None = Field(
        default=None, description="Only if explicitly present in the content. Never estimated."
    )
    longitude: float | None = Field(
        default=None, description="Only if explicitly present in the content. Never estimated."
    )
    price: str | None = Field(default=None, description="Price if relevant, else null.")
    url: str | None = Field(default=None, description="Most useful single URL, else null.")
    urls: list[str] = Field(
        default_factory=list,
        description="All useful URLs found in the content, best-first. Empty if none.",
    )

    @field_validator("urls")
    @classmethod
    def _clean_urls(cls, value: list[str]) -> list[str]:
        seen: list[str] = []
        for raw in value:
            url = (raw or "").strip()
            if url.startswith(("http://", "https://")) and url not in seen:
                seen.append(url)
        return seen[:5]

    @model_validator(mode="after")
    def _sanitize_coordinates(self) -> "IntentDetails":
        lat, lng = self.latitude, self.longitude
        valid = (
            lat is not None
            and lng is not None
            and -90.0 <= lat <= 90.0
            and -180.0 <= lng <= 180.0
            and not (lat == 0.0 and lng == 0.0)
        )
        if not valid:
            self.latitude = None
            self.longitude = None
        return self


class IntentResurfacing(BaseModel):
    """When Echo should bring this back, and why."""

    model_config = ConfigDict(extra="ignore")

    type: TriggerType = Field(description="The single best trigger type for this memory.")
    reason: str = Field(
        description="One short sentence explaining why that moment is the right moment."
    )
    # Only meaningful for DATE/TIME; ignored otherwise.
    fire_at: str | None = Field(
        default=None,
        description="Absolute ISO-8601 datetime to resurface at, if a specific moment is implied. Else null.",
    )


class SourceProvenance(BaseModel):
    """The explicit source-vs-inference boundary (§9).

    Each flag answers a single question: was this fact DIRECTLY STATED in the
    content the user saved? ``True`` means Echo read it in the video/image/text;
    ``False`` means it was absent (and the matching ``details`` field must be
    null). This is what lets the UI honestly show "from the source" and keeps the
    model from smuggling an inferred coordinate or date in as if it were a fact.

    Nothing about the user's *intention* is recorded here - intention is always
    inferred, by definition, and lives in the block-B fields of IntentAnalysis.
    """

    model_config = ConfigDict(extra="ignore")

    location_stated: bool = Field(default=False, description="A place/locality was named in the source.")
    address_stated: bool = Field(default=False, description="A street address was stated.")
    coordinates_stated: bool = Field(
        default=False, description="Literal latitude/longitude appeared in the source."
    )
    date_stated: bool = Field(default=False, description="A concrete date appeared in the source.")
    time_stated: bool = Field(default=False, description="A concrete time appeared in the source.")
    price_stated: bool = Field(default=False, description="A price/cost was stated.")
    url_stated: bool = Field(default=False, description="A usable URL appeared in the source.")


class IntentAnalysis(BaseModel):
    """The complete, validated result of one AI analysis.

    The object carries the two understandings Echo is built on, kept explicit:

      A. CONTENT UNDERSTANDING - what the source *actually says*: ``summary``,
         ``entities``, ``details``. Every fact here must be directly present in
         the content; anything unstated is null. ``provenance`` records which of
         these facts were literally stated versus absent.

      B. USER INTENTION UNDERSTANDING - what Echo *infers* the user meant to do:
         ``why_saved``, ``intent_action``, ``confidence``, ``resurfacing``,
         ``suggested_actions``. These are inferences, never presented as source
         facts, and ``confidence`` scores the intent, not the summary (§3).

    ``category`` and ``title`` name the thing; the rest splits along A/B above.
    """

    model_config = ConfigDict(extra="ignore")

    category: Category = Field(description="Exactly one primary Echo category.")
    title: str = Field(description="The specific thing saved, e.g. 'Cafe XYZ'. Not a sentence.")

    # --- A. content understanding (facts from the source) ---
    summary: str = Field(description="Two sentences at most describing the content.")
    entities: IntentEntities = Field(default_factory=IntentEntities)
    details: IntentDetails = Field(default_factory=IntentDetails)
    provenance: SourceProvenance = Field(
        default_factory=SourceProvenance,
        description="Which content facts were DIRECTLY STATED in the source.",
    )

    # --- B. user intention understanding (Echo's inference) ---
    why_saved: str = Field(
        description=(
            "One sentence, addressed to the user, stating the likely reason they saved this. "
            "Start with 'You probably saved this because'."
        )
    )
    intent_action: IntentAction = Field(description="The single action the user most likely intends.")
    confidence: float = Field(
        ge=0.0, le=1.0, description="How confident you are in the intent, not in the summary."
    )
    resurfacing: IntentResurfacing
    suggested_actions: list[ActionType] = Field(
        default_factory=list, description="Ordered best-first. One or two is usually right."
    )

    # Free-text note for the fallback path: why the model was unsure.
    uncertainty_note: str | None = Field(
        default=None, description="If anything important was missing, say so here. Else null."
    )

    def content_understanding(self) -> dict:
        """The source-grounded facts (block A), with their provenance."""
        return {
            "title": self.title,
            "summary": self.summary,
            "entities": self.entities.model_dump(mode="json"),
            "details": self.details.model_dump(mode="json"),
            "provenance": self.provenance.model_dump(mode="json"),
        }

    def intent_understanding(self) -> dict:
        """Echo's inference about the user (block B)."""
        return {
            "why_saved": self.why_saved,
            "intent_action": self.intent_action.value,
            "confidence": self.confidence,
            "resurfacing": self.resurfacing.model_dump(mode="json"),
            "suggested_actions": [a.value for a in self.suggested_actions],
        }

    @field_validator("title", "summary", "why_saved")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("field must not be blank")
        return cleaned

    @field_validator("suggested_actions")
    @classmethod
    def _dedupe_actions(cls, value: list[ActionType]) -> list[ActionType]:
        seen: list[ActionType] = []
        for action in value:
            if action not in seen:
                seen.append(action)
        return seen[:3]
