"use client";

import { useState } from "react";

import { correctMemory } from "@/lib/api";
import { toApiError } from "@/lib/api";
import { CATEGORIES, CATEGORY_META, INTENT_CHOICES } from "@/lib/categories";
import type { Category, MemoryCorrection, MemoryRead } from "@/lib/types";
import { btnChip, btnGhost, btnSecondary, cn, eyebrow, surface } from "@/lib/ui";

interface CorrectionProps {
  memory: MemoryRead;
  onUpdated: (memory: MemoryRead) => void;
}

function useCorrection(onUpdated: (memory: MemoryRead) => void) {
  const [pending, setPending] = useState<string | null>(null);
  const [problem, setProblem] = useState<string | null>(null);

  const send = async (id: string, key: string, correction: MemoryCorrection) => {
    setPending(key);
    setProblem(null);
    try {
      onUpdated(await correctMemory(id, correction));
    } catch (cause: unknown) {
      setProblem(toApiError(cause).message);
    } finally {
      setPending(null);
    }
  };

  return { pending, problem, send };
}

/**
 * §14 — "Is this why you saved it?". Yes records a confirmation; Not quite
 * reveals the six intents, which map to a (category, intent_action) pair.
 */
export function WhyCorrection({ memory, onUpdated }: CorrectionProps) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const { pending, problem, send } = useCorrection(onUpdated);

  return (
    <section className={cn(surface, "space-y-4 p-5")} aria-label="Correct this memory">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className={eyebrow}>Check Echo&apos;s reading</p>
          <p className="mt-1 text-[15px] font-medium text-fog-50">
            Is this why you saved it?
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            className={btnSecondary}
            disabled={pending !== null}
            onClick={() => void send(memory.id, "yes", { confirmed: true })}
          >
            {memory.user_confirmed ? "Confirmed" : "Yes"}
          </button>
          <button
            type="button"
            className={btnGhost}
            aria-expanded={open}
            onClick={() => setOpen((value) => !value)}
          >
            Not quite
          </button>
        </div>
      </div>

      {open ? (
        <div className="echo-rise space-y-3 border-t border-line-soft pt-4">
          <p className="text-sm text-fog-400">
            What did you actually want to do with it?
          </p>
          <div className="flex flex-wrap gap-2">
            {INTENT_CHOICES.map((choice) => (
              <button
                key={choice.label}
                type="button"
                className={btnChip}
                disabled={pending !== null}
                onClick={() =>
                  void send(memory.id, choice.label, {
                    ...(choice.category ? { category: choice.category } : {}),
                    intent_action: choice.intent_action,
                    note: note.trim() || choice.label,
                  })
                }
              >
                {choice.category ? (
                  <span aria-hidden="true">{CATEGORY_META[choice.category].glyph}</span>
                ) : null}
                {pending === choice.label ? "Saving…" : choice.label}
              </button>
            ))}
          </div>
          <label className="block">
            <span className={eyebrow}>Anything else Echo should know?</span>
            <input
              value={note}
              onChange={(event) => setNote(event.target.value)}
              maxLength={500}
              placeholder="it's a meetup"
              className="mt-1.5 w-full rounded-lg border border-line bg-ink-850 px-3 py-2 text-sm text-fog-100 placeholder:text-fog-600"
            />
          </label>
        </div>
      ) : null}

      {problem ? (
        <p role="alert" className="text-sm text-[#ff9aa5]">
          {problem}
        </p>
      ) : null}
      {memory.user_corrected ? (
        <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-fog-500">
          You corrected this — Echo re-derived its trigger and actions.
        </p>
      ) : null}
    </section>
  );
}

/** The Needs-review resolver: pick the right category and Echo rebuilds the plan. */
export function CategoryResolver({ memory, onUpdated }: CorrectionProps) {
  const { pending, problem, send } = useCorrection(onUpdated);

  return (
    <div className="space-y-2 border-t border-line-soft pt-3">
      <p className={eyebrow}>What is this, really?</p>
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((category: Category) => (
          <button
            key={category}
            type="button"
            data-category={category}
            className={cn(btnChip, "hover:border-[color:var(--cat)]")}
            disabled={pending !== null}
            onClick={() => void send(memory.id, category, { category })}
          >
            <span aria-hidden="true">{CATEGORY_META[category].glyph}</span>
            {pending === category ? "Saving…" : CATEGORY_META[category].label}
          </button>
        ))}
      </div>
      {problem ? (
        <p role="alert" className="text-sm text-[#ff9aa5]">
          {problem}
        </p>
      ) : null}
    </div>
  );
}
