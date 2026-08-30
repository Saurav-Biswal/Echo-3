import type { ActionRead } from "@/lib/types";
import { btnChip, btnPrimary, btnSecondary, cn } from "@/lib/ui";

/** `web_link` is for a browser; `deep_link` is an Android intent. Either may be null. */
function hrefFor(action: ActionRead): string | null {
  if (action.web_link) return action.web_link;
  if (action.deep_link && /^https?:/i.test(action.deep_link)) return action.deep_link;
  return null;
}

function ActionLink({
  action,
  className,
}: {
  action: ActionRead;
  className: string;
}) {
  const href = hrefFor(action);

  if (!href) {
    return (
      <span
        className={cn(className, "cursor-not-allowed opacity-45")}
        title={`${action.label} is only available on your phone`}
      >
        {action.label}
      </span>
    );
  }

  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className={className}
      data-action-type={action.action_type}
    >
      {action.label}
      <span aria-hidden="true" className="text-[11px] opacity-60">
        ↗
      </span>
    </a>
  );
}

/**
 * ACTION — the last of the four questions a card must answer. `actions[]`
 * arrives ordered; `is_primary` is the one to emphasise.
 */
export function ActionButtons({
  actions,
  variant = "card",
  className,
}: {
  actions: ActionRead[];
  variant?: "card" | "full";
  className?: string;
}) {
  if (actions.length === 0) return null;

  const ordered = [...actions].sort((a, b) => a.sort_order - b.sort_order);
  const primary = ordered.find((action) => action.is_primary) ?? ordered[0];
  const rest = ordered.filter((action) => action.id !== primary.id);
  const shown = variant === "full" ? rest : rest.slice(0, 1);

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      <ActionLink
        action={primary}
        className={variant === "full" ? btnPrimary : cn(btnSecondary, "h-9")}
      />
      {shown.map((action) => (
        <ActionLink key={action.id} action={action} className={btnChip} />
      ))}
      {variant === "card" && rest.length > shown.length ? (
        <span className="font-mono text-[11px] text-fog-500">
          +{rest.length - shown.length}
        </span>
      ) : null}
    </div>
  );
}
