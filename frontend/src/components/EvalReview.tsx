import { useEffect, useState } from "react";
import { api } from "../api";
import type { Health } from "../types";
import { Chip, ErrorBox, Section } from "./common";

function fmt(v: any, digits = 3) {
  if (v === null || v === undefined) return <span className="text-muted italic">not measured</span>;
  if (typeof v === "number") return Number.isInteger(v) ? String(v) : v.toFixed(digits);
  return String(v);
}

function Metric({ name, m }: { name: string; m: any }) {
  if (!m || m.value === null || m.value === undefined) return <tr className="border-t border-line"><td className="p-1">{name}</td><td className="p-1" colSpan={2}><span className="text-muted italic">not measured</span>{m?.reason ? ` — ${m.reason}` : ""}</td></tr>;
  return (
    <tr className="border-t border-line">
      <td className="p-1">{name}</td>
      <td className="p-1 font-semibold">{fmt(m.value)}</td>
      <td className="p-1 text-muted">{m.numerator !== undefined ? `${m.numerator}/${m.denominator}` : m.n !== undefined ? `n=${m.n}` : ""} {m.note ?? ""}</td>
    </tr>
  );
}

export function EvalReview({ health }: { health: Health | null }) {
  const [results, setResults] = useState<any[]>([]);
  const [smoke, setSmoke] = useState<any | null>(null);
  const [cases, setCases] = useState<any[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);
  const [rules, setRules] = useState<any | null>(null);
  const [sources, setSources] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState<{ target_type: string; target_id: string; decision: string; note: string; reviewer_name: string; reviewer_role: string }>({ target_type: "eval_case", target_id: "", decision: "accepted", note: "", reviewer_name: "", reviewer_role: "student_bams" });
  const [msg, setMsg] = useState<string | null>(null);
  const readOnly = health?.deploy_mode === "public_demo";

  const load = () => {
    api.evalResults().then(setResults).catch((e) => setError(e.message));
    api.evalSmoke().then(setSmoke).catch(() => {});
    api.evalCases().then(setCases).catch(() => {});
    api.reviews().then(setReviews).catch(() => {});
    api.rules().then(setRules).catch(() => {});
    api.sources().then(setSources).catch(() => {});
  };
  useEffect(load, []);

  const submit = async () => {
    try { await api.review(form); setMsg("Recorded."); load(); } catch (e: any) { setMsg(e.message); }
  };
  const ruleReviewed = rules ? Object.keys(rules.reviews || {}).length : 0;
  const caseReviewed = cases.filter((c) => c.latest_review).length;
  const splitCounts = cases.reduce((acc: any, c: any) => { const k = `${c.category}/${c.split}`; acc[k] = (acc[k] || 0) + 1; return acc; }, {});

  return (
    <div className="space-y-4">
      <ErrorBox error={error} />
      <Section title="Review coverage (live from the review log)">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
          <div className="panel p-3"><div className="label">Indexed passages reviewed</div><div className="text-xl font-semibold">{sources ? `${sources.passage_reviews.reviewed} / ${sources.passage_reviews.indexed}` : "…"}</div></div>
          <div className="panel p-3"><div className="label">Safety rules reviewed</div><div className="text-xl font-semibold">{rules ? `${ruleReviewed} / ${rules.rules.length}` : "…"}</div></div>
          <div className="panel p-3"><div className="label">Eval cases reviewed</div><div className="text-xl font-semibold">{caseReviewed} / {cases.length}</div></div>
          <div className="panel p-3"><div className="label">Review log entries</div><div className="text-xl font-semibold">{reviews.length}</div></div>
        </div>
        <p className="text-[11px] text-muted mt-2">Everything not listed as reviewed is pending. Reviewer roles are self-declared; nothing here constitutes clinical validation.</p>
      </Section>

      <Section title="AyurParam smoke test (real weights)" right={<Chip>{smoke?.file ?? "not run"}</Chip>}>
        {!smoke ? <p className="text-sm text-muted">Not run. <code>python model_server/smoke_test.py</code></p> : (
          <div className="text-sm space-y-1">
            <div><b>{smoke.result}</b> · {smoke.started}</div>
            <div>revision {smoke.revision?.slice(0, 12)} · {smoke.gpu} · torch {smoke.torch} · transformers {smoke.transformers} · {smoke.dtype}</div>
            <div>load {smoke.load_seconds} s · {smoke.gpu_mem_after_load_mb} MB after load · context limit {smoke.config_max_position_embeddings}</div>
            <div>System message reaches model via chat template: <b>{String(smoke.system_message_reaches_model_via_template)}</b> → instructions are placed in the &lt;context&gt; block. Serialised: <code>{smoke.chat_template_serialized}</code></div>
          </div>
        )}
      </Section>

      <Section title="Measured evaluation runs" right={<Chip>from eval/results/eval_*.json</Chip>}>
        {results.length === 0 && <p className="text-sm text-muted">No evaluation has been run yet — all metrics: <i>not measured</i>. Run <code>python -m pramaan.eval.run</code>.</p>}
        {results.map((r) => (
          <details key={r.eval_id} className="border border-line rounded-md bg-white p-3 mb-3" open={r === results[0]}>
            <summary className="cursor-pointer font-medium">{r.eval_id} · {r.created_at} · {r.config_name} · cases {r.n_cases} · LLM {r.llm_mode} (inference ran in {r.n_live_inference ?? 0} runs) {r.current_corpus ? "" : <Chip tone="warn">superseded corpus</Chip>}</summary>
            <p className="text-xs text-muted mt-1">{r.description} · hardware: {r.hardware} · corpus {r.corpus_version} · split {r.split}</p>
            <table className="w-full text-sm mt-2"><tbody>
              {Object.entries(r.metrics || {}).map(([k, m]) => <Metric key={k} name={k.replace(/_/g, " ")} m={m} />)}
            </tbody></table>
            {r.failures?.length > 0 && <details className="mt-2 text-xs"><summary className="cursor-pointer">Failures ({r.failures.length})</summary><ul className="list-disc pl-5">{r.failures.map((f: any, i: number) => <li key={i}>{f.case_id}: {f.reason}</li>)}</ul></details>}
          </details>
        ))}
      </Section>

      <Section title={`Evaluation cases (${cases.length}) — synthetic, unreviewed unless marked`}>
        <div className="flex flex-wrap gap-1.5 mb-2">{Object.entries(splitCounts).map(([k, v]) => <Chip key={k}>{k}: {String(v)}</Chip>)}</div>
        <div className="max-h-80 overflow-auto">
          <table className="w-full text-xs"><thead className="bg-paper sticky top-0"><tr><th className="p-1 text-left">id</th><th className="p-1 text-left">category</th><th className="p-1 text-left">query</th><th className="p-1">expected</th><th className="p-1">label status</th></tr></thead>
            <tbody>{cases.map((c) => (
              <tr key={c.case_id} className="border-t border-line align-top"><td className="p-1">{c.case_id}</td><td className="p-1">{c.category}/{c.split}</td><td className="p-1">{c.query}</td>
                <td className="p-1">{c.expected?.status ?? ""} {c.expected?.relevant_passages?.length ? `· ${c.expected.relevant_passages.slice(0, 3).join(", ")}` : ""}</td>
                <td className="p-1">{c.latest_review ? <Chip tone="ok">{c.latest_review.decision} by {c.latest_review.reviewer_name}</Chip> : <Chip tone="warn">{c.label_status}</Chip>}</td></tr>
            ))}</tbody></table>
        </div>
      </Section>

      <Section title="Record a review (passage, gloss, rule or evaluation case)">
        {readOnly ? <p className="text-sm text-muted">Disabled on the read-only public demo.</p> : (
          <div className="grid md:grid-cols-3 gap-2 text-sm">
            <select className="input" value={form.target_type} onChange={(e) => setForm({ ...form, target_type: e.target.value })}>
              {["eval_case", "passage", "gloss", "rule", "claim"].map((t) => <option key={t}>{t}</option>)}
            </select>
            <input className="input" placeholder="target id (e.g. AE-001, Ah.1.13.25, R-PREG-ASHWA-001)" value={form.target_id} onChange={(e) => setForm({ ...form, target_id: e.target.value })} />
            <select className="input" value={form.decision} onChange={(e) => setForm({ ...form, decision: e.target.value })}>{["accepted", "needs_revision", "rejected", "comment"].map((d) => <option key={d}>{d}</option>)}</select>
            <input className="input" placeholder="reviewer name" value={form.reviewer_name} onChange={(e) => setForm({ ...form, reviewer_name: e.target.value })} />
            <select className="input" value={form.reviewer_role} onChange={(e) => setForm({ ...form, reviewer_role: e.target.value })}>{["student_bams", "student_md_phd", "practitioner", "engineer", "other"].map((d) => <option key={d}>{d}</option>)}</select>
            <input className="input" placeholder="note / correction" value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} />
            <div className="md:col-span-3 flex items-center gap-2"><button className="btn-primary" disabled={!form.target_id || !form.reviewer_name} onClick={submit}>Record review</button>{msg && <span className="text-forest-700">{msg}</span>}</div>
          </div>
        )}
      </Section>

      <Section title="Review history (append-only)">
        {reviews.length === 0 ? <p className="text-sm text-muted">No reviews recorded yet.</p> : (
          <table className="w-full text-xs"><thead className="bg-paper"><tr><th className="p-1 text-left">when</th><th className="p-1 text-left">target</th><th className="p-1">decision</th><th className="p-1">previous</th><th className="p-1 text-left">reviewer</th><th className="p-1 text-left">note</th></tr></thead>
            <tbody>{reviews.map((r) => <tr key={r.review_id} className="border-t border-line"><td className="p-1">{r.created_at}</td><td className="p-1">{r.target_type} {r.target_id}</td><td className="p-1">{r.decision}</td><td className="p-1">{r.previous_decision ?? "—"}</td><td className="p-1">{r.reviewer_name} ({r.reviewer_role})</td><td className="p-1">{r.note}</td></tr>)}</tbody></table>
        )}
      </Section>
    </div>
  );
}
