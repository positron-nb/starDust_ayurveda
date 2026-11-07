import { useEffect, useState } from "react";
import { api } from "../api";
import { Chip, ErrorBox, Section, Spinner } from "./common";

function StatusTable({ rows, title }: { rows: any[]; title: string }) {
  return (
    <div className="min-w-0">
      <div className="label mb-1">{title}</div>
      <table className="w-full text-xs border border-line bg-white">
        <thead className="bg-paper"><tr><th className="p-1 text-left">Claim</th><th className="p-1">Evidence</th><th className="p-1">Citation</th><th className="p-1">Shown</th></tr></thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.claim_id} className="border-t border-line align-top">
              <td className="p-1">{c.text}{c.withheld_reason && <div className="text-alert-700">{c.withheld_reason}</div>}</td>
              <td className="p-1">{c.evidence_ids.join(", ") || "—"}</td>
              <td className="p-1 text-center"><Chip tone={c.citation_integrity === "pass" ? "ok" : "bad"}>{c.citation_integrity}</Chip></td>
              <td className="p-1 text-center">{c.shown ? "yes" : <span className="text-alert-700 font-semibold">no</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Lab({ lastRunId }: { lastRunId: string | null }) {
  const [exps, setExps] = useState<Record<string, string>>({});
  const [runs, setRuns] = useState<any[]>([]);
  const [runId, setRunId] = useState<string>("");
  const [exp, setExp] = useState("retract_passage");
  const [res, setRes] = useState<any | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.labExperiments().then(setExps).catch((e) => setError(e.message));
    api.runs().then((r) => { const a = r.filter((x) => x.status === "answered" && x.n_interpretation_claims > 0); setRuns(a); if (lastRunId && a.some((x) => x.run_id === lastRunId)) setRunId(lastRunId); else if (a[0]) setRunId(a[0].run_id); }).catch(() => {});
  }, [lastRunId]);

  const go = async () => {
    setBusy(true); setError(null); setRes(null);
    try { setRes(await api.labRun({ experiment: exp, run_id: exp === "inject_instruction" ? null : runId || null })); }
    catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };
  const needsRun = exp !== "inject_instruction";

  return (
    <div className="space-y-4">
      <Section title="Evidence Integrity Lab" right={<Chip tone="info">disposable snapshot · main corpus never modified</Chip>}>
        <p className="text-sm text-muted mb-3">Each experiment copies the corpus to a throw-away snapshot, injects one fault, and then calls the same validator / pipeline used for ordinary results. The synthetic injected passage is clearly labelled and never enters the real corpus.</p>
        <div className="grid md:grid-cols-2 gap-3">
          <label className="text-sm">Experiment
            <select className="input mt-1" value={exp} onChange={(e) => setExp(e.target.value)}>
              {Object.entries(exps).map(([k, v]) => <option key={k} value={k}>{k.replace(/_/g, " ")} — {v.slice(0, 70)}</option>)}
            </select>
          </label>
          <label className="text-sm">Base run (from this session, with generated claims)
            <select className="input mt-1" value={runId} onChange={(e) => setRunId(e.target.value)} disabled={!needsRun}>
              {runs.length === 0 && <option value="">— run a query with shown AyurParam claims (e.g. example A) first —</option>}
              {runs.map((r) => <option key={r.run_id} value={r.run_id}>{r.run_id} · {r.query.slice(0, 60)} · {r.llm_mode}</option>)}
            </select>
          </label>
        </div>
        <p className="text-xs text-muted mt-2">{exps[exp]}</p>
        <div className="mt-3 flex gap-2">
          <button className="btn-primary" onClick={go} disabled={busy || (needsRun && !runId)}>Run experiment</button>
          {res && <button className="btn-ghost" onClick={() => setRes(null)}>Reset view</button>}
        </div>
      </Section>
      <ErrorBox error={error} />
      {busy && <div className="panel p-4"><Spinner label="Running on disposable snapshot…" /></div>}
      {res && (
        <Section title={`Result · ${res.experiment}`} right={<Chip tone={res.main_corpus_modified ? "bad" : "ok"}>main corpus modified: {String(res.main_corpus_modified)}</Chip>}>
          <div className="text-sm space-y-1 mb-3">
            <div><b>Change:</b> {res.change}</div>
            {res.target_passage && <div><b>Target passage:</b> {res.target_passage}</div>}
            {res.snapshot_corpus_version && <div><b>Snapshot corpus version:</b> {res.snapshot_corpus_version} (base {res.base_corpus_version}) · snapshot deleted: {String(res.snapshot_deleted)}</div>}
            {res.cache && <div><b>Cache:</b> cached result still valid = <b>{String(res.cache.cached_result_valid)}</b>. {res.cache.explanation}</div>}
            {res.stale_reasons?.length > 0 && <div className="text-alert-700"><b>Stale reasons:</b> {res.stale_reasons.join("; ")}</div>}
            {res.accepted_forged && <div><b>Forged citations accepted:</b> {res.accepted_forged.length === 0 ? <Chip tone="ok">none (0)</Chip> : <Chip tone="bad">{res.accepted_forged.length}</Chip>}</div>}
            {res.checks && <div className="flex flex-wrap gap-1.5">{Object.entries(res.checks).map(([k, v]) => <Chip key={k} tone={v ? "ok" : "bad"}>{k.replace(/_/g, " ")}: {String(v)}</Chip>)}</div>}
          </div>
          <div className="grid xl:grid-cols-2 gap-3">
            {res.before && <StatusTable rows={res.before} title="Before (saved run)" />}
            {res.after && <StatusTable rows={res.after} title="After (same validator, faulted snapshot)" />}
          </div>
          {res.synthetic_passage && <div className="mt-3 text-xs"><Chip tone="bad">SYNTHETIC LAB FIXTURE</Chip> <code className="break-words">{res.synthetic_passage}</code></div>}
          {[res.rerun, res.rerun_ordinary_query].filter(Boolean).map((rr: any, i: number) => (
            <div key={i} className="mt-4">
              <div className="label mb-1">Pipeline re-run on snapshot {i === 1 ? "(ordinary query)" : ""} · status {rr.status} · llm {rr.llm_mode} · inference ran {String(rr.inference_ran)}</div>
              <p className="text-xs text-muted mb-1">{rr.note} Alerts: {rr.safety_alerts.join(", ") || "none"}. Evidence: {rr.evidence.map((e: any) => `${e.label}=${e.passage_id}`).join(", ")}</p>
              <StatusTable rows={[...rr.claims, ...rr.rejected]} title="Claims after re-run (shown + withheld)" />
            </div>
          ))}
        </Section>
      )}
    </div>
  );
}
