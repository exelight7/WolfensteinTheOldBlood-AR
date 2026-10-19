import type { ReactNode } from "react";
import { CheckCircle2, AlertTriangle, XCircle, Loader2 } from "lucide-react";
import type { GameState } from "../lib/types";

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`card p-5 ${className}`}>{children}</div>;
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4 animate-rise">
      <div>
        <h1 className="text-2xl font-bold text-white">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-400">{subtitle}</p>}
      </div>
      {actions}
    </div>
  );
}

const STATE_LABEL: Record<GameState, string> = {
  GAME_NOT_FOUND: "لم يتم العثور على اللعبة",
  SUPPORTED_ORIGINAL: "جاهزة للتعريب",
  NOT_INSTALLED: "جاهزة للتعريب",
  ARABIC_INSTALLED: "التعريب مثبت",
  ARABIC_UPDATE_AVAILABLE: "يتوفر تحديث",
  UNKNOWN_MODIFIED_GAME: "ملفات غير معروفة",
  BROKEN_INSTALL: "تثبيت تالف",
};

const STATE_TONE: Record<GameState, string> = {
  GAME_NOT_FOUND: "border-slate-500/30 bg-slate-500/10 text-slate-300",
  SUPPORTED_ORIGINAL: "border-ember-400/30 bg-ember-400/10 text-ember-400",
  NOT_INSTALLED: "border-ember-400/30 bg-ember-400/10 text-ember-400",
  ARABIC_INSTALLED: "border-emerald-400/30 bg-emerald-400/10 text-emerald-300",
  ARABIC_UPDATE_AVAILABLE: "border-sky-400/30 bg-sky-400/10 text-sky-300",
  UNKNOWN_MODIFIED_GAME: "border-red-400/30 bg-red-400/10 text-red-300",
  BROKEN_INSTALL: "border-red-400/30 bg-red-400/10 text-red-300",
};

export function StatusPill({ state, pulse = false }: { state: GameState; pulse?: boolean }) {
  const dot =
    state === "ARABIC_INSTALLED" ? "bg-emerald-400"
    : state === "ARABIC_UPDATE_AVAILABLE" ? "bg-sky-400"
    : state === "GAME_NOT_FOUND" || state === "UNKNOWN_MODIFIED_GAME" || state === "BROKEN_INSTALL" ? "bg-red-400"
    : "bg-ember-400";
  return (
    <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold ${STATE_TONE[state]}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${dot} ${pulse ? "animate-pulseSoft" : ""}`} />
      {STATE_LABEL[state]}
    </span>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return <Loader2 className={`h-4 w-4 animate-spin ${className}`} />;
}

export function InfoRow({ label, value, mono = false }: { label: string; value: ReactNode; mono?: boolean }) {
  return (
    <div className="min-w-0">
      <div className="label">{label}</div>
      <div className={`value ${mono ? "font-mono text-xs" : ""}`} title={typeof value === "string" ? value : undefined}>{value}</div>
    </div>
  );
}

export type ToastKind = "success" | "error" | "info";

export function Toast({ kind, message, onClose }: { kind: ToastKind; message: string; onClose: () => void }) {
  const Icon = kind === "success" ? CheckCircle2 : kind === "error" ? XCircle : AlertTriangle;
  const tone =
    kind === "success" ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200"
    : kind === "error" ? "border-red-400/30 bg-red-500/10 text-red-200"
    : "border-sky-400/30 bg-sky-500/10 text-sky-200";
  return (
    <div className={`fixed bottom-6 left-6 z-50 flex max-w-md items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-2xl backdrop-blur animate-rise ${tone}`}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <span className="leading-6">{message}</span>
      <button onClick={onClose} className="ms-2 text-xs opacity-60 transition hover:opacity-100" aria-label="إغلاق">✕</button>
    </div>
  );
}
