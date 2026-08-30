import type { Category, IntentAction } from "@/lib/types";

export const CATEGORIES: readonly Category[] = [
  "PLACE",
  "EVENT",
  "RECIPE",
  "TOOL",
  "TOPIC",
];

export interface CategoryMeta {
  /** The one glyph allowed per category. */
  glyph: string;
  label: string;
  plural: string;
  href: string;
  /** What Echo does with this kind of save, in Echo's voice. */
  blurb: string;
}

export const CATEGORY_META: Record<Category, CategoryMeta> = {
  PLACE: {
    glyph: "📍",
    label: "Place",
    plural: "Places",
    href: "/places",
    blurb: "Comes back when you're nearby.",
  },
  EVENT: {
    glyph: "📅",
    label: "Event",
    plural: "Events",
    href: "/events",
    blurb: "Comes back before the date.",
  },
  RECIPE: {
    glyph: "🍳",
    label: "Recipe",
    plural: "Recipes",
    href: "/recipes",
    blurb: "Comes back when you have time to cook.",
  },
  TOOL: {
    glyph: "🛠",
    label: "Tool",
    plural: "Tools",
    href: "/tools",
    blurb: "Comes back when you sit down to build.",
  },
  TOPIC: {
    glyph: "🧠",
    label: "Topic",
    plural: "Topics",
    href: "/topics",
    blurb: "Comes back when you want to go deeper.",
  },
};

/**
 * The "Not quite" choices from §14. Each answers "what did you want to do?",
 * which is exactly a (category, intent_action) pair. "Other" deliberately
 * sends no category so the backend keeps what it has.
 */
export interface IntentChoice {
  label: string;
  category: Category | null;
  intent_action: IntentAction;
}

export const INTENT_CHOICES: readonly IntentChoice[] = [
  { label: "Visit", category: "PLACE", intent_action: "VISIT" },
  { label: "Attend", category: "EVENT", intent_action: "ATTEND" },
  { label: "Cook", category: "RECIPE", intent_action: "COOK" },
  { label: "Try", category: "TOOL", intent_action: "TRY" },
  { label: "Learn", category: "TOPIC", intent_action: "LEARN" },
  { label: "Other", category: null, intent_action: "OTHER" },
];
