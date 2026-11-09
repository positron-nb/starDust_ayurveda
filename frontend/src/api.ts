import type { CaseFact, Health, RunResult } from "./types";

async function j<T>(r: Response): Promise<T> {
  if (r.status === 401) { window.dispatchEvent(new Event("pramaan-auth-required")); }
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`;
    try { const d = await r.json(); msg = typeof d.detail === "string" ? d.detail : JSON.stringify(d.detail ?? d); } catch { /* ignore */ }
    throw new Error(msg);
  }
  return r.json();
}

export const SESSION_ID = (() => {
  try {
    const k = "pramaan-session";
    let v = sessionStorage.getItem(k);
    if (!v) { v = "s-" + Math.random().toString(36).slice(2, 10); sessionStorage.setItem(k, v); }
    return v;
  } catch { return "s-" + Math.random().toString(36).slice(2, 10); }
})();

const post = (url: string, body: unknown) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  authStatus: () => fetch("/api/auth/status").then(j<{ auth_required: boolean; authenticated: boolean }>),
  login: (passcode: string) => post("/api/login", { passcode }).then(j<any>),
  logout: () => post("/api/logout", {}).then(j<any>),
  health: () => fetch("/api/health").then(j<Health>),
  extractFacts: (query: string, case_text: string) => post("/api/facts/extract", { query, case_text }).then(j<CaseFact[]>),
  query: (body: { query: string; lang: string; case_text: string; facts?: CaseFact[] | null; use_model: boolean; retrieval_mode?: string }) =>
    post("/api/query", { ...body, session_id: SESSION_ID }).then(j<RunResult>),
  run: (id: string) => fetch(`/api/runs/${encodeURIComponent(id)}`).then(j<RunResult>),
  runs: () => fetch(`/api/runs?session_id=${SESSION_ID}`).then(j<any[]>),
  allRuns: () => fetch(`/api/runs?limit=100`).then(j<any[]>),
  passage: (id: string) => fetch(`/api/passages/${encodeURIComponent(id)}?context=2`).then(j<any>),
  chapters: () => fetch("/api/chapters").then(j<any[]>),
  chapter: (key: string) => fetch(`/api/chapters/${encodeURIComponent(key)}`).then(j<any[]>),
  search: (q: string) => fetch(`/api/search?q=${encodeURIComponent(q)}`).then(j<any>),
  sources: () => fetch("/api/sources").then(j<any>),
  rules: () => fetch("/api/rules").then(j<any>),
  review: (b: any) => post("/api/reviews", b).then(j<any>),
  reviews: () => fetch("/api/reviews").then(j<any[]>),
  labExperiments: () => fetch("/api/lab/experiments").then(j<Record<string, string>>),
  labRun: (b: any) => post("/api/lab/run", b).then(j<any>),
  evalResults: () => fetch("/api/eval/results").then(j<any[]>),
  evalSmoke: () => fetch("/api/eval/smoke").then(j<any>),
  evalCases: () => fetch("/api/eval/cases").then(j<any[]>),
  resetSession: () => fetch(`/api/session/reset?session_id=${SESSION_ID}`, { method: "POST" }).then(j<any>),
};
