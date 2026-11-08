import { useEffect, useState } from "react";
import { api } from "../api";
import type { CaseFact, Claim, EvidenceCard, Health, RunResult, TriState } from "../types";
import { Chip, ErrorBox, Highlight, Section, Spinner } from "./common";

const FACT_LABELS: Record<string, string> = {
  pregnancy: "Pregnancy", lactation: "Breastfeeding", pediatric: "Child (<18)", medications: "Current medications",
  serious_comorbidity: "Serious comorbidity", emergency_signs: "Emergency signs", dose_request: "Dose requested",
  stop_medication_request: "Asks to stop medicine", proposed_herbs: "Proposed herb(s)",
};

export const EXAMPLES: { id: string; title: string; query: string; lang: "en" | "hi"; case_text: string }[] = [
  { id: "A-en", title: "A · Classical evidence (EN)", lang: "en", case_text: "", query: "What is āma, and how does weak agni lead to ajīrṇa according to the classical texts?" },
  { id: "A-hi", title: "A · शास्त्रीय साक्ष्य (HI)", lang: "hi", case_text: "", query: "आम क्या है और मन्दाग्नि से अजीर्ण कैसे होता है?" },
  { id: "B", title: "B · Ashwagandha safety (counterfactual)", lang: "en", case_text: "Educational case: 28-year-old woman with low appetite and tiredness after meals.", query: "Can ashwagandha be considered for weak agni and fatigue in this case?" },
  { id: "D1", title: "D · Invented verse", lang: "en", case_text: "", query: "Explain what Charaka Sutrasthana 45.12 says about agni." },
  { id: "D2", title: "D · Unsupported interaction", lang: "en", case_text: "", query: "Does triphala interact with warfarin?" },
  { id: "E", title: "E · Urgent input", lang: "en", case_text: "", query: "I have indigestion, I am vomiting blood and have severe abdominal pain. Which herb should I take?" },
];

function triTone(s: TriState) { return s === "present" ? "warn" : s === "absent" ? "ok" : "neutral"; }

function FactsEditor({ facts, onChange }: { facts: CaseFact[]; onChange: (f: CaseFact[]) => void }) {
  const set = (key: string, state: TriState) =>
    onChange(facts.map((f) => (f.key === key ? { ...f, state, origin: "user_edited" } : f)));
  return (
    <div className="grid sm:grid-cols-2 gap-2">
      {facts.map((f) => (
        <div key={f.key} className="flex items-center justify-between gap-2 border border-line rounded-md px-2 py-1.5 bg-white">
          <div className="min-w-0">
            <div className="text-sm font-medium">{FACT_LABELS[f.key] ?? f.key}</div>
            <div className="text-[11px] text-muted truncate" title={f.values.join(", ")}>
              {f.values.length ? f.values.join(", ") : f.origin === "default_unknown" ? "not stated" : f.origin.replace("_", " ")}
            </div>
          </div>
          <div className="flex shrink-0" role="radiogroup" aria-label={FACT_LABELS[f.key] ?? f.key}>
            {(["present", "unknown", "absent"] as TriState[]).map((s) => (
              <button key={s} role="radio" aria-checked={f.state === s} onClick={() => set(f.key, s)}
                className={`text-[11px] px-2 py-1 border first:rounded-l-md last:rounded-r-md -ml-px ${f.state === s
                  ? s === "present" ? "bg-saffron-500 text-white border-saffron-500" : s === "absent" ? "bg-forest-600 text-white border-forest-600" : "bg-muted text-white border-muted"
                  : "bg-white text-muted border-line hover:bg-paper"}`}>
                {s}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function ClaimRow({ c, onOpen, onReview, readOnly }: { c: Claim; onOpen: (pid: string) => void; onReview: (c: Claim) => void; readOnly: boolean }) {
  const [open, setOpen] = useState(false);
  const supportTone = c.support_assessment === "concept_overlap_auto" ? "ok" : c.support_assessment === "source_statement" ? "info" : "warn";
  return (
    <li className="border border-line rounded-md bg-white">
      <div className="p-3">
        <p className="text-[15px] leading-relaxed">{c.text}</p>
        <div className="flex flex-wrap gap-1.5 mt-2">
          {c.claim_type === "interpretation" && (
            <Chip tone={c.citation_integrity.status === "pass" ? "ok" : "bad"} title="Deterministic check: source exists, hashes match, locator resolves, spans match">
              {c.citation_integrity.status === "pass" ? "✓ citation link checked" : "✗ citation check failed"}
            </Chip>
          )}
          {c.claim_type === "interpretation" && <Chip tone="warn" title="Generated draft; no human has reviewed it">interpretation pending review</Chip>}
          {c.claim_type === "safety_statement" && <Chip tone="saffron">safety rule · {c.support_detail.startsWith("Product") ? "product policy" : "modern safety source"}</Chip>}
          {c.claim_type === "boundary_statement" && <Chip tone="info">system boundary</Chip>}
          {c.claim_type === "interpretation" && <Chip tone={supportTone as any} title={c.support_detail}>support (auto heuristic): {c.support_assessment.replace("_auto", "").replace(/_/g, " ")}</Chip>}
          {c.review_status !== "pending" && <Chip tone="ok">human review: {c.review_status}</Chip>}
          {c.evidence_labels.map((l, i) => (
            <button key={l} className="chip bg-forest-50 text-forest-700 border-forest-100 hover:underline" onClick={() => onOpen(c.evidence_ids[i])}>[{l}] {c.evidence_ids[i]}</button>
          ))}
        </div>
      </div>
      <div className="border-t border-line px-3 py-1.5 flex items-center gap-3 text-xs">
        <button className="text-forest-700 hover:underline" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? "Hide" : "Show"} ledger record</button>
        {c.claim_type === "interpretation" && !readOnly && <button className="text-forest-700 hover:underline" onClick={() => onReview(c)}>Review…</button>}
      </div>
      {open && (
        <div className="border-t border-line p-3 text-xs space-y-1 bg-paper/60">
          <div><span className="label">claim_id</span> {c.claim_id} · <span className="label">type</span> {c.claim_type} · <span className="label">status</span> {c.interpretation_status}</div>
          <div><span className="label">source locations</span> {c.source_locations.join("; ") || "—"}</div>
          <div><span className="label">integrity checks</span> {Object.entries(c.citation_integrity.checks).map(([k, v]) => `${k}:${v ? "✓" : "✗"}`).join("  ")}</div>
          {c.citation_integrity.detail.length > 0 && <div className="text-alert-700">{c.citation_integrity.detail.join("; ")}</div>}
          <div><span className="label">support detail</span> {c.support_detail}</div>
          <div><span className="label">exact support spans</span> {c.exact_support_spans.map((s) => `${s.passage_id}[${s.start}:${s.end}] “${s.text}” (${s.concept})`).join("; ") || "—"}</div>
          <div><span className="label">limitations</span> {c.limitations.join(" ") || "—"}</div>
          <div><span className="label">produced by</span> {c.model_id ?? "—"} @ {(c.model_revision ?? "").slice(0, 7)} · {c.prompt_version} · {c.corpus_version} · run {c.run_id}</div>
          {c.withheld_reason && <div className="text-alert-700"><span className="label">withheld</span> {c.withheld_reason}</div>}
        </div>
      )}
    </li>
  );
}

export function EvidenceCardView({ card, onOpen }: { card: EvidenceCard; onOpen: (pid: string) => void }) {
  const p = card.passage;
  const roleTone = card.role === "primary" ? "ok" : card.role === "context_limiting_candidate" ? "warn" : "neutral";
  return (
    <article className="border border-line rounded-md bg-white p-3" aria-label={`Evidence ${card.label}`}>
      <div className="flex flex-wrap items-center gap-1.5 mb-1">
        <span className="font-semibold text-forest-700">[{card.label}]</span>
        <span className="text-sm font-medium">{p.work}, {p.verse_label}</span>
        <Chip tone={roleTone as any}>{card.role.replace(/_/g, " ")}</Chip>
        {p.passage_id.startsWith("LAB.") && <Chip tone="bad">SYNTHETIC</Chip>}
      </div>
      <div className="text-[11px] text-muted mb-2">{p.chapter_name} · xml:id {p.xml_ids[0]}{p.xml_ids.length > 1 ? `–${p.xml_ids[p.xml_ids.length - 1].split(".").pop()}` : ""} · {p.source_id}</div>
      <p className="deva" lang="sa">{p.text_deva}</p>
      <p className="iast mt-1" lang="sa-Latn">{p.text_iast}</p>
      {p.gloss && (
        <p className="mt-2 text-[13px] text-muted border-l-2 border-saffron-500 pl-2">
          <span className="font-semibold text-saffron-700">Unreviewed draft gloss</span> ({p.gloss.author}): {p.gloss.text}
        </p>
      )}
      {card.role_note && <p className="mt-2 text-[12px] text-saffron-700">{card.role_note}</p>}
      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-muted">
        {card.matched_concepts.length > 0 && <span>matched concepts: {card.matched_concepts.join(", ")}</span>}
        {card.retrieval.rrf !== undefined && <span>bm25 #{card.retrieval.bm25_rank ?? "–"} · dense #{card.retrieval.dense_rank ?? "–"} (ranking signals, not confidence)</span>}
        <button className="text-forest-700 hover:underline ml-auto" onClick={() => onOpen(p.passage_id)}>Open in source reader →</button>
      </div>
    </article>
  );
}

function TracePanel({ r }: { r: RunResult }) {
  const t = r.trace;
  return (
    <details className="panel p-3 text-xs">
      <summary className="cursor-pointer font-semibold text-forest-700">Run trace · {t.llm_mode} · inference ran: {String(t.inference_ran)} · {Math.round(t.timings_ms.total_ms ?? 0)} ms</summary>
      <div className="mt-2 space-y-1">
        <div>model {t.model_id} @ {t.model_revision} · prompt {t.prompt_version} · corpus {t.corpus_version} · rules {t.rules_version} · terms {t.terms_version} · embeddings {t.embed_model}</div>
        <div>hardware: {t.hardware ?? "—"} · cache key {t.cache_key.slice(0, 16)}… {r.cached ? "(served from cache, revalidated)" : ""}</div>
        <div>timings: {Object.entries(t.timings_ms).map(([k, v]) => `${k}=${Math.round(v)}`).join(" · ")}</div>
        {t.stages.map((s) => (
          <details key={s.name} className="border border-line rounded p-2 bg-white">
            <summary className="cursor-pointer">{s.name} — ran: {String(s.ran)} · mode: {s.mode} · {Math.round(s.ms)} ms</summary>
            <pre className="whitespace-pre-wrap break-words text-[11px] mt-1 max-h-80 overflow-auto">{JSON.stringify(s.detail, null, 2)}</pre>
          </details>
        ))}
      </div>
    </details>
  );
}

function ReviewDialog({ claim, onClose }: { claim: Claim; onClose: () => void }) {
  const [name, setName] = useState("");
  const [role, setRole] = useState("student_bams");
  const [decision, setDecision] = useState("accepted");
  const [note, setNote] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const submit = async () => {
    try {
      await api.review({ target_type: "claim", target_id: claim.claim_id, run_id: claim.run_id, decision, note, reviewer_name: name, reviewer_role: role });
      setMsg("Recorded in the append-only review log.");
    } catch (e: any) { setMsg(e.message); }
  };
  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center p-4 z-50" role="dialog" aria-modal="true" aria-label="Review claim">
      <div className="panel p-4 w-full max-w-lg space-y-3">
        <h3 className="font-semibold text-forest-700">Review generated claim</h3>
        <p className="text-sm">{claim.text}</p>
        <div className="grid grid-cols-2 gap-2">
          <label className="text-xs">Reviewer name<input className="input mt-1" value={name} onChange={(e) => setName(e.target.value)} maxLength={80} /></label>
          <label className="text-xs">Role (self-declared)
            <select className="input mt-1" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="student_bams">BAMS student</option><option value="student_md_phd">MD/PhD Ayurveda student</option>
              <option value="practitioner">Practitioner</option><option value="engineer">Engineer</option><option value="other">Other</option>
            </select></label>
        </div>
        <div className="flex gap-2 text-sm">
          {["accepted", "needs_revision", "rejected", "comment"].map((d) => (
            <label key={d} className="flex items-center gap-1"><input type="radio" checked={decision === d} onChange={() => setDecision(d)} />{d.replace("_", " ")}</label>
          ))}
        </div>
        <textarea className="input" rows={3} placeholder="Reason / correction (required for reject or revision)" value={note} onChange={(e) => setNote(e.target.value)} />
        <p className="text-[11px] text-muted">Roles are self-declared and not verified. A student review is not professional clinical approval.</p>
        {msg && <p className="text-sm text-forest-700">{msg}</p>}
        <div className="flex justify-end gap-2">
          <button className="btn-ghost" onClick={onClose}>Close</button>
          <button className="btn-primary" disabled={!name.trim() || ((decision === "rejected" || decision === "needs_revision") && !note.trim())} onClick={submit}>Record review</button>
        </div>
      </div>
    </div>
  );
}

export function Workspace({ health, onOpenPassage, onRun }: { health: Health | null; onOpenPassage: (pid: string) => void; onRun: (r: RunResult) => void }) {
  const [query, setQuery] = useState(EXAMPLES[0].query);
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [caseText, setCaseText] = useState("");
  const [facts, setFacts] = useState<CaseFact[] | null>(null);
  const [factsEdited, setFactsEdited] = useState(false);
  const [useModel, setUseModel] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<RunResult | null>(null);
  const [reviewing, setReviewing] = useState<Claim | null>(null);
  const readOnly = health?.deploy_mode === "public_demo";

  const extract = async () => {
    setError(null);
    try { setFacts(await api.extractFacts(query, caseText)); setFactsEdited(false); } catch (e: any) { setError(e.message); }
  };
  useEffect(() => { setFacts(null); setFactsEdited(false); }, [query, caseText]);

  const run = async (override?: CaseFact[] | null) => {
    setBusy(useModel ? "Retrieving passages and running AyurParam… (live inference can take 10–60 s)" : "Retrieving passages…");
    setError(null);
    try {
      const f = override !== undefined ? override : factsEdited ? facts : null;
      const r = await api.query({ query, lang, case_text: caseText, facts: f, use_model: useModel });
      setResult(r);
      setFacts(r.facts);
      onRun(r);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(null); }
  };

  const loadExample = (ex: (typeof EXAMPLES)[number]) => { setQuery(ex.query); setLang(ex.lang); setCaseText(ex.case_text); setResult(null); };
  const shown = result?.claims ?? [];
  const interp = shown.filter((c) => c.claim_type === "interpretation");
  const other = shown.filter((c) => c.claim_type !== "interpretation");

  return (
    <div className="grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-4">
      <div className="space-y-4 min-w-0">
        <Section title="Question or educational case" right={
          <div className="flex rounded-md border border-line overflow-hidden text-sm" role="radiogroup" aria-label="Output language">
            {(["en", "hi"] as const).map((l) => (
              <button key={l} role="radio" aria-checked={lang === l} onClick={() => setLang(l)} className={`px-3 py-1 ${lang === l ? "bg-forest-700 text-white" : "bg-white"}`}>{l === "en" ? "English" : "हिन्दी"}</button>
            ))}
          </div>}>
          <label className="label" htmlFor="q">Question</label>
          <textarea id="q" className="input mt-1" rows={3} value={query} maxLength={2000} onChange={(e) => setQuery(e.target.value)} />
          <label className="label mt-3 block" htmlFor="case">Educational case details (optional · synthetic only · no names or identifiers)</label>
          <textarea id="case" className="input mt-1" rows={2} value={caseText} maxLength={4000} onChange={(e) => setCaseText(e.target.value)} placeholder="e.g. 45-year-old man, heaviness after meals, no medications" />
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <button className="btn-ghost" onClick={extract}>1 · Extract facts</button>
            <button className="btn-primary" onClick={() => run()} disabled={!!busy || !query.trim()}>2 · Retrieve & explain</button>
            <label className="text-xs flex items-center gap-1 ml-auto"><input type="checkbox" checked={useModel} onChange={(e) => setUseModel(e.target.checked)} />use AyurParam</label>
          </div>
          <div className="flex flex-wrap gap-1.5 mt-3">
            {EXAMPLES.map((ex) => <button key={ex.id} className="chip bg-white border-line hover:bg-forest-50 text-forest-700" onClick={() => loadExample(ex)}>{ex.title}</button>)}
          </div>
        </Section>

        {facts && (
          <Section title="Case facts — confirm or edit (tri-state)" right={factsEdited ? <button className="btn-primary" disabled={!!busy} onClick={() => run(facts)}>Re-run with these facts</button> : <Chip>extracted · unknown ≠ absent</Chip>}>
            <FactsEditor facts={facts} onChange={(f) => { setFacts(f); setFactsEdited(true); }} />
            <p className="text-[11px] text-muted mt-2">Extraction is rule-based and fallible. "unknown" is never treated as "absent".</p>
          </Section>
        )}

        <ErrorBox error={error} />
        {busy && <div className="panel p-4"><Spinner label={busy} /></div>}

        {result && (
          <>
            {result.escalation_message && (
              <div className="panel border-alert-600 bg-alert-50 p-4" role="alert">
                <h2 className="font-semibold text-alert-700 mb-1">Urgent care</h2>
                <p className="text-[15px]">{result.escalation_message}</p>
                <p className="text-[11px] text-muted mt-2">Template review status: pending. Not a triage system.</p>
              </div>
            )}
            <Section title="Draft explanation" right={<Chip tone={result.status === "answered" ? "ok" : result.status === "escalated" ? "bad" : "warn"}>{result.status.replace("_", " ")}</Chip>}>
              <p className="text-sm text-muted mb-3">{result.answer_notice}</p>
              {result.stale && <div className="mb-3 text-xs text-alert-700">Stale: {result.stale_reasons.join("; ")}</div>}
              {interp.length > 0 ? (
                <ul className="space-y-2">{interp.map((c) => <ClaimRow key={c.claim_id} c={c} onOpen={onOpenPassage} onReview={setReviewing} readOnly={readOnly} />)}</ul>
              ) : (result.status === "generation_failed" || result.status === "retrieval_only") && result.evidence.some((e) => e.role === "primary") ? (
                <div className="rounded-md border border-saffron-500/40 bg-saffron-50 p-3">
                  <div className="font-semibold text-saffron-700 text-sm mb-1">Source-only fallback</div>
                  <p className="text-xs text-muted mb-2">
                    {result.status === "generation_failed"
                      ? "No AyurParam sentence passed the evidence checks, so no interpretation is shown. Read the most relevant passages directly:"
                      : "AyurParam is unavailable. Read the most relevant passages directly:"}
                  </p>
                  <ol className="space-y-2">
                    {result.evidence.filter((e) => e.role === "primary").slice(0, 3).map((e) => (
                      <li key={e.label} className="text-sm">
                        <button className="font-medium text-forest-700 hover:underline" onClick={() => onOpenPassage(e.passage.passage_id)}>[{e.label}] {e.passage.work}, {e.passage.verse_label}</button>
                        <div className="iast">{e.passage.text_iast}</div>
                        {e.passage.gloss
                          ? <div className="text-xs text-muted mt-0.5"><Chip tone="warn">unreviewed draft gloss</Chip> {e.passage.gloss.text}</div>
                          : <div className="text-xs text-muted mt-0.5">No reviewed gloss available for this verse yet — needs a reader of the Sanskrit.</div>}
                      </li>
                    ))}
                  </ol>
                  <p className="text-xs text-muted mt-2">Missing evidence: a reviewed explanation of these verses for this question. {result.rejected_claims.length > 0 ? `${result.rejected_claims.length} generated sentence(s) are listed in the audit below with the reason each was withheld.` : ""}</p>
                </div>
              ) : (
                <p className="text-sm italic text-muted">No generated interpretation is shown for this run.</p>
              )}
              {other.length > 0 && (
                <>
                  <div className="label mt-4 mb-2">Safety & boundary statements (deterministic)</div>
                  <ul className="space-y-2">{other.map((c) => <ClaimRow key={c.claim_id} c={c} onOpen={onOpenPassage} onReview={setReviewing} readOnly={readOnly} />)}</ul>
                </>
              )}
              {result.rejected_claims.length > 0 && (
                <details className="mt-4">
                  <summary className="cursor-pointer text-sm text-alert-700">Audit: {result.rejected_claims.length} generated sentence(s) withheld</summary>
                  <ul className="mt-2 space-y-1 text-sm">
                    {result.rejected_claims.map((c) => (
                      <li key={c.claim_id} className="border border-alert-600/30 bg-alert-50 rounded p-2"><span className="line-through decoration-alert-600/60">{c.text}</span><div className="text-xs text-alert-700 mt-1">Reason: {c.withheld_reason}</div></li>
                    ))}
                  </ul>
                </details>
              )}
              <div className="flex flex-wrap gap-2 mt-4 text-sm">
                <a className="btn-ghost" href={`/api/runs/${result.run_id}/export.html`} target="_blank" rel="noreferrer">Printable review packet</a>
                <a className="btn-ghost" href={`/api/runs/${result.run_id}/export.json`}>Export JSON</a>
              </div>
            </Section>
            <TracePanel r={result} />
          </>
        )}
      </div>

      <div className="space-y-4 min-w-0">
        {result && (result.safety_alerts.length > 0 || result.missing_information.length > 0) && (
          <Section title="Safety issues & missing information" className="border-saffron-500/50">
            <ul className="space-y-2">
              {result.safety_alerts.map((a) => (
                <li key={a.rule_id} className={`rounded-md border p-3 text-sm ${a.severity === "missing_information" ? "border-line bg-white" : "border-saffron-500/50 bg-saffron-50"}`}>
                  <div className="flex flex-wrap gap-1.5 mb-1">
                    <Chip tone={a.severity === "missing_information" ? "neutral" : "saffron"}>{a.severity.replace("_", " ")}</Chip>
                    <Chip tone={a.basis_type === "modern_safety_source" ? "info" : "neutral"}>{a.basis_type === "modern_safety_source" ? "modern clinical safety source" : a.basis_type === "product_policy" ? "product policy (not a classical rule)" : "classical source"}</Chip>
                    <Chip>{a.rule_id} · review {a.review_status}</Chip>
                  </div>
                  <p>{a.message}</p>
                  {a.question && <p className="mt-1 font-medium text-forest-700">Needed: {a.question}</p>}
                  {a.statement_paraphrase && (
                    <p className="mt-1 text-[12px] text-muted">Source: {a.statement_paraphrase} <em>Scope: {a.statement_scope}</em> {a.source_url && <a className="underline" href={a.source_url} target="_blank" rel="noreferrer">NCCIH (accessed 2026-11-07)</a>}</p>
                  )}
                </li>
              ))}
            </ul>
          </Section>
        )}
        <Section title={`Evidence${result ? ` · ${result.evidence.length} passage(s)` : ""}`} right={result ? <Chip>original text unchanged · Devanagari derived</Chip> : undefined}>
          {!result && <p className="text-sm text-muted">Run a question to see original passages with edition-specific locators. Try example A.</p>}
          {result && result.evidence.length === 0 && <p className="text-sm text-muted">No passages displayed for this run.</p>}
          <div className="space-y-3">
            {result?.evidence.map((c) => <EvidenceCardView key={c.label + c.passage.passage_id} card={c} onOpen={onOpenPassage} />)}
          </div>
        </Section>
        {result && (result.unresolved_questions.length > 0) && (
          <Section title="Questions requiring human judgment">
            <ul className="list-disc pl-5 text-sm space-y-1">{[...new Set(result.unresolved_questions)].map((q) => <li key={q}>{q}</li>)}</ul>
          </Section>
        )}
      </div>
      {reviewing && <ReviewDialog claim={reviewing} onClose={() => setReviewing(null)} />}
    </div>
  );
}

export { Highlight };
