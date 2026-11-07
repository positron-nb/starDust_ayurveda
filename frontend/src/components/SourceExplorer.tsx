import { useEffect, useState } from "react";
import { api } from "../api";
import type { Health } from "../types";
import { Chip, ErrorBox, Highlight, Section, Spinner } from "./common";

export function SourceExplorer({ passageId, onOpen, health }: { passageId: string | null; onOpen: (pid: string) => void; health: Health | null }) {
  const [chapters, setChapters] = useState<any[]>([]);
  const [chapterKey, setChapterKey] = useState<string | null>(null);
  const [chapterRows, setChapterRows] = useState<any[]>([]);
  const [data, setData] = useState<any | null>(null);
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [sources, setSources] = useState<any | null>(null);

  useEffect(() => { api.chapters().then(setChapters).catch((e) => setError(e.message)); api.sources().then(setSources).catch(() => {}); }, []);
  useEffect(() => {
    if (!passageId) return;
    setLoading(true); setError(null);
    api.passage(passageId).then((d) => { setData(d); setChapterKey(passageId.split(".").slice(0, 3).join(".")); }).catch((e) => { setData(null); setError(e.message); }).finally(() => setLoading(false));
  }, [passageId]);
  useEffect(() => { if (chapterKey) api.chapter(chapterKey).then(setChapterRows).catch(() => setChapterRows([])); }, [chapterKey]);

  const p = data?.passage;
  const spans = data ? Object.entries(data.tags as Record<string, [number, number, string][]>).flatMap(([c, xs]) => xs.map(([s, e]) => ({ start: s, end: e, concept: c }))) : [];
  const src = data?.source;

  return (
    <div className="grid lg:grid-cols-[280px_minmax(0,1fr)] gap-4">
      <aside className="space-y-4 min-w-0">
        <Section title="Search the indexed module">
          <form onSubmit={(e) => { e.preventDefault(); if (q.trim()) api.search(q).then(setHits).catch((er) => setError(er.message)); }} className="flex gap-2">
            <input className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="ajīrṇa, अग्नि, heaviness…" aria-label="Search passages" />
            <button className="btn-ghost">Go</button>
          </form>
          {hits && (
            <ul className="mt-2 space-y-1 text-sm max-h-72 overflow-auto">
              <li className="text-[11px] text-muted">concepts: {hits.concepts.join(", ") || "none"} · {hits.info.mode}</li>
              {hits.hits.map((h: any) => <li key={h.passage_id}><button className="text-left hover:underline text-forest-700" onClick={() => onOpen(h.passage_id)}>{h.label}</button></li>)}
            </ul>
          )}
        </Section>
        <Section title="Indexed chapters">
          <ul className="space-y-1 text-sm">
            {chapters.map((c) => (
              <li key={c.key}>
                <button className={`text-left w-full rounded px-2 py-1 hover:bg-forest-50 ${chapterKey === c.key ? "bg-forest-50 font-medium" : ""}`} onClick={() => { setChapterKey(c.key); onOpen(c.first); }}>
                  {c.name || c.key} <span className="text-muted text-xs">({c.count})</span>
                </button>
              </li>
            ))}
          </ul>
        </Section>
      </aside>
      <div className="space-y-4 min-w-0">
        <ErrorBox error={error} />
        {loading && <Spinner label="Loading passage…" />}
        {!p && !loading && <div className="panel p-6 text-sm text-muted">Select a chapter or open a passage from an evidence card.</div>}
        {p && (
          <Section title={`${p.work}, ${p.verse_label}`} right={<Chip>{p.segment_type}</Chip>}>
            <div className="text-xs text-muted mb-3">{p.chapter_name} · passage {p.passage_id} · xml:id {p.xml_ids.join(", ")} · sha256 {p.text_hash.slice(0, 16)}…</div>
            <div className="grid md:grid-cols-2 gap-4">
              <div><div className="label mb-1">Devanagari (derived transliteration)</div><p className="deva" lang="sa">{p.text_deva}</p></div>
              <div><div className="label mb-1">Original (IAST, as in source) — concept tags highlighted</div><p className="iast" lang="sa-Latn"><Highlight text={p.text_iast} spans={spans} /></p></div>
            </div>
            {p.variants.length > 0 && (
              <div className="mt-3"><div className="label mb-1">Variant readings / editorial notes (kept separate from base text)</div>
                <ul className="text-sm list-disc pl-5">{p.variants.map((v: any, i: number) => <li key={i}>{v.text}</li>)}</ul></div>
            )}
            <div className="mt-3">
              <div className="label mb-1">Translation / gloss</div>
              {p.gloss ? (
                <p className="text-sm border-l-2 border-saffron-500 pl-2"><Chip tone="warn">unreviewed draft · not a published translation</Chip> <span className="text-muted text-xs">{p.gloss.author} · {p.gloss.method}</span><br />{p.gloss.text}</p>
              ) : <p className="text-sm text-muted">No gloss. PRAMAAN does not show machine translations as authoritative.</p>}
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">{p.concepts.map((c: string) => <Chip key={c}>{c}</Chip>)}{p.modules.map((m: string) => <Chip key={m} tone="info">{m}</Chip>)}</div>
            <div className="mt-4">
              <div className="label mb-1">Adjacent context</div>
              <ul className="space-y-1 text-sm">
                {data.neighbours.map((n: any) => (
                  <li key={n.passage_id} className={`rounded px-2 py-1 ${n.passage_id === p.passage_id ? "bg-saffron-50 border border-saffron-100" : ""}`}>
                    <button className="text-forest-700 hover:underline mr-2" onClick={() => onOpen(n.passage_id)}>{n.verse_label}</button><span className="iast">{n.text_iast}</span>
                  </li>
                ))}
              </ul>
            </div>
            {src && (
              <div className="mt-4 text-xs border-t border-line pt-3 space-y-1">
                <div className="label">Source lineage</div>
                <div><b>{src.title}</b> — {src.edition}</div>
                <div>Pinned file: <a className="underline" href={src.url} target="_blank" rel="noreferrer">{src.url}</a></div>
                <div>sha256 {src.sha256} · acquired {src.acquisition_date} · {src.extraction_method}</div>
                <div>Licence: {src.license}</div>
                <div>Reviewer status: {src.reviewer_status}</div>
                <ul className="list-disc pl-5">{(src.known_limitations || []).map((l: string) => <li key={l}>{l}</li>)}</ul>
              </div>
            )}
            <div className="mt-3 text-xs"><span className="label">Review history</span> {data.reviews.length ? data.reviews.map((r: any) => `${r.created_at} ${r.reviewer_name} (${r.reviewer_role}): ${r.decision}`).join(" | ") : "none — passage review pending"}</div>
          </Section>
        )}
        {chapterRows.length > 0 && (
          <Section title={`Chapter reader · ${chapterKey}`}>
            <ol className="space-y-1 text-sm max-h-[480px] overflow-auto">
              {chapterRows.map((r) => (
                <li key={r.passage_id} className={`rounded px-2 py-1 ${p && r.passage_id === p.passage_id ? "bg-saffron-50" : ""}`}>
                  <button className="text-forest-700 hover:underline mr-2" onClick={() => onOpen(r.passage_id)}>{r.verse_label}</button>
                  <span className="iast">{r.text_iast}</span>
                </li>
              ))}
            </ol>
          </Section>
        )}
        {sources && (
          <Section title="Source manifest">
            <ul className="text-xs space-y-1">{sources.manifest.sources.map((s: any) => <li key={s.source_id}><b>{s.source_id}</b> · {s.title} · {s.license} · indexed {sources.counts[s.source_id]?.indexed ?? 0} · review {s.reviewer_status}</li>)}</ul>
            <p className="text-[11px] text-muted mt-2">Passage reviews recorded: {sources.passage_reviews.reviewed} / {sources.passage_reviews.indexed}. Corpus {sources.corpus_version}.</p>
          </Section>
        )}
      </div>
    </div>
  );
}
