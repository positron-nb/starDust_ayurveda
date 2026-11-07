import React from "react";
import type { Health } from "../types";

export function Chip({ tone = "neutral", children, title }: { tone?: "ok" | "warn" | "bad" | "neutral" | "info" | "saffron"; children: React.ReactNode; title?: string }) {
  const cls = {
    ok: "bg-forest-50 text-forest-700 border-forest-100",
    warn: "bg-saffron-50 text-saffron-700 border-saffron-100",
    bad: "bg-alert-50 text-alert-700 border-alert-600/30",
    neutral: "bg-white text-muted border-line",
    info: "bg-sky-50 text-sky-800 border-sky-200",
    saffron: "bg-saffron-100 text-saffron-700 border-saffron-500/40",
  }[tone];
  return <span className={`chip ${cls}`} title={title}>{children}</span>;
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-muted" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-forest-600 border-t-transparent" />
      {label}
    </span>
  );
}

export function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return <div className="panel border-alert-600/40 bg-alert-50 p-3 text-sm text-alert-700" role="alert">{error}</div>;
}

export function ModeBanner({ health, error }: { health: Health | null; error: string | null }) {
  if (error) return <div className="bg-alert-600 text-white text-sm px-4 py-2" role="alert">API unreachable: {error}</div>;
  if (!health) return <div className="bg-line text-sm px-4 py-2">Checking services…</div>;
  const llm = health.llm || {};
  let tone = "bg-alert-600 text-white";
  let text = "RETRIEVAL-ONLY MODE — AyurParam unavailable. Showing source passages only; no generated explanations.";
  if (llm.mode === "live" && llm.available) {
    tone = "bg-forest-700 text-white";
    text = `LIVE AyurParam · ${health.model.id} @ ${health.model.revision.slice(0, 7)} · ${llm.device ?? ""} ${llm.dtype ?? ""} · context ${health.model.context_limit}`;
  } else if (llm.mode === "live" && llm.loading) {
    tone = "bg-saffron-600 text-white";
    text = "AyurParam model server is loading weights… retrieval works meanwhile.";
  } else if (llm.mode === "fixture_replay") {
    tone = "bg-saffron-600 text-white";
    text = `FIXTURE REPLAY — recorded AyurParam outputs for demo prompts only (${llm.records ?? 0} records). This is NOT live inference.`;
  } else if (llm.mode === "live") {
    text += llm.error ? ` (${llm.error})` : "";
  }
  return (
    <div className={`${tone} text-sm px-4 py-2 flex flex-wrap gap-x-4 gap-y-1 items-center`} role="status" aria-live="polite">
      <strong>{text}</strong>
      <span className="opacity-90">corpus {health.corpus_version} · rules {health.rules_version} · {health.indexed_passages} indexed passages · dense {health.dense.enabled ? "on" : "off"}{health.deploy_mode === "public_demo" ? " · read-only public demo" : ""}</span>
    </div>
  );
}

export function Section({ title, right, children, className = "" }: { title: React.ReactNode; right?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={`panel p-4 ${className}`}>
      <div className="flex items-center justify-between gap-2 mb-3">
        <h2 className="text-[15px] font-semibold text-forest-700">{title}</h2>
        {right}
      </div>
      {children}
    </section>
  );
}

export function Highlight({ text, spans }: { text: string; spans: { start: number; end: number; concept?: string }[] }) {
  if (!spans.length) return <>{text}</>;
  const s = [...spans].sort((a, b) => a.start - b.start);
  const out: React.ReactNode[] = [];
  let i = 0;
  s.forEach((sp, k) => {
    if (sp.start < i) return;
    out.push(text.slice(i, sp.start));
    out.push(<mark key={k} className="bg-saffron-100 text-ink rounded px-0.5" title={sp.concept}>{text.slice(sp.start, sp.end)}</mark>);
    i = sp.end;
  });
  out.push(text.slice(i));
  return <>{out}</>;
}
