"use client";

import {
  forwardRef, useEffect, useId, useRef, type ButtonHTMLAttributes, type InputHTMLAttributes,
  type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes,
} from "react";

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(" ");
}

// --- Button ---------------------------------------------------------------------------
type Variant = "primary" | "secondary" | "quiet" | "danger" | "stamp";

const variants: Record<Variant, string> = {
  primary: "bg-ink text-paper hover:bg-[#2c3140] disabled:bg-ink-3",
  stamp: "bg-stamp text-white hover:bg-stamp-ink disabled:bg-ink-3",
  secondary: "border border-rule-strong bg-sheet text-ink hover:border-ink disabled:text-ink-3 disabled:hover:border-rule-strong",
  quiet: "text-ink underline decoration-rule-strong underline-offset-4 hover:decoration-ink disabled:text-ink-3",
  danger: "bg-fail text-white hover:bg-[#8a2219] disabled:bg-ink-3",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md";
  busy?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", busy, className, children, disabled, ...rest }, ref,
) {
  return (
    <button
      ref={ref}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={cx(
        "inline-flex items-center justify-center gap-2 font-medium transition-colors disabled:cursor-not-allowed",
        variant === "quiet" ? "px-0" : size === "sm" ? "h-8 rounded-sm px-3 text-xs" : "h-10 rounded-sm px-4 text-sm",
        variants[variant],
        className,
      )}
      {...rest}
    >
      {busy && <Spinner className="size-3.5" />}
      {children}
    </button>
  );
});

export function Spinner({ className }: { className?: string }) {
  return (
    <svg className={cx("animate-spin", className)} viewBox="0 0 16 16" aria-hidden="true">
      <circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" strokeOpacity="0.25" strokeWidth="2" />
      <path d="M14.5 8A6.5 6.5 0 0 0 8 1.5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

// --- Form fields ----------------------------------------------------------------------
interface FieldShellProps {
  label: string;
  hint?: ReactNode;
  error?: string;
  children: (ids: { id: string; describedBy?: string }) => ReactNode;
  optional?: boolean;
  className?: string;
}

export function FieldShell({ label, hint, error, children, optional, className }: FieldShellProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errId = error ? `${id}-err` : undefined;
  const describedBy = [hintId, errId].filter(Boolean).join(" ") || undefined;
  return (
    <div className={cx("flex flex-col gap-1.5", className)}>
      <label htmlFor={id} className="text-sm font-medium text-ink">
        {label}
        {optional && <span className="ml-1.5 font-normal text-ink-3">optional</span>}
      </label>
      {children({ id, describedBy })}
      {hint && !error && <p id={hintId} className="text-xs text-ink-2">{hint}</p>}
      {error && <p id={errId} className="text-xs font-medium text-fail">{error}</p>}
    </div>
  );
}

const inputBase =
  "w-full rounded-sm border bg-sheet px-3 text-sm text-ink placeholder:text-ink-3 transition-colors focus:border-ink focus:outline-none";

export function TextField({ label, hint, error, optional, className, ...rest }:
  InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: ReactNode; error?: string; optional?: boolean }) {
  return (
    <FieldShell label={label} hint={hint} error={error} optional={optional} className={className}>
      {({ id, describedBy }) => (
        <input id={id} aria-describedby={describedBy} aria-invalid={!!error || undefined}
          className={cx(inputBase, "h-10", error ? "border-fail" : "border-rule-strong")} {...rest} />
      )}
    </FieldShell>
  );
}

export function TextArea({ label, hint, error, optional, className, ...rest }:
  TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; hint?: ReactNode; error?: string; optional?: boolean }) {
  return (
    <FieldShell label={label} hint={hint} error={error} optional={optional} className={className}>
      {({ id, describedBy }) => (
        <textarea id={id} aria-describedby={describedBy} aria-invalid={!!error || undefined}
          className={cx(inputBase, "min-h-24 py-2 leading-relaxed", error ? "border-fail" : "border-rule-strong")} {...rest} />
      )}
    </FieldShell>
  );
}

export function SelectField({ label, hint, error, optional, className, children, ...rest }:
  SelectHTMLAttributes<HTMLSelectElement> & { label: string; hint?: ReactNode; error?: string; optional?: boolean }) {
  return (
    <FieldShell label={label} hint={hint} error={error} optional={optional} className={className}>
      {({ id, describedBy }) => (
        <select id={id} aria-describedby={describedBy} aria-invalid={!!error || undefined}
          className={cx(inputBase, "h-10 pr-8", error ? "border-fail" : "border-rule-strong")} {...rest}>
          {children}
        </select>
      )}
    </FieldShell>
  );
}

// --- Notices --------------------------------------------------------------------------
export function Notice({ tone = "info", title, children, action }:
  { tone?: "info" | "error" | "warn"; title?: string; children: ReactNode; action?: ReactNode }) {
  const tones = {
    info: "border-rule-strong bg-sheet text-ink",
    error: "border-fail/40 bg-fail-wash text-ink",
    warn: "border-wait/40 bg-wait-wash text-ink",
  };
  return (
    <div role={tone === "error" ? "alert" : "status"} className={cx("rounded-sm border px-4 py-3 text-sm", tones[tone])}>
      {title && <p className="font-semibold">{title}</p>}
      <div className={cx(title && "mt-0.5", "text-ink-2")}>{children}</div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

/** Labels a feature that exists in the interface but isn't connected yet. */
export function NotYet({ children }: { children: ReactNode }) {
  return <p className="text-xs text-ink-2">{children}</p>;
}

// --- Confirm dialog -------------------------------------------------------------------
export function ConfirmDialog({ open, title, body, confirmLabel, onConfirm, onCancel, busy }:
  { open: boolean; title: string; body: ReactNode; confirmLabel: string; onConfirm: () => void; onCancel: () => void; busy?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog ref={ref} onCancel={(e) => { e.preventDefault(); onCancel(); }}
      className="m-auto w-[min(26rem,calc(100vw-2rem))] rounded-md border border-rule bg-sheet p-0 text-ink shadow-[var(--shadow-pop)]">
      <div className="p-6">
        <h2 className="font-display text-xl">{title}</h2>
        <div className="mt-2 text-sm text-ink-2">{body}</div>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel} autoFocus>Keep it</Button>
          <Button variant="danger" onClick={onConfirm} busy={busy}>{confirmLabel}</Button>
        </div>
      </div>
    </dialog>
  );
}

// --- Wordmark -------------------------------------------------------------------------
export function Wordmark({ className }: { className?: string }) {
  return (
    <span className={cx("font-display text-lg font-semibold tracking-tight", className)}>
      Launchcraft
    </span>
  );
}
