import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { EvalReview } from "./components/EvalReview";
import { Lab } from "./components/Lab";
import { ModeBanner } from "./components/common";
import { SourceExplorer } from "./components/SourceExplorer";
import { Workspace } from "./components/Workspace";
import type { Health, RunResult } from "./types";

const TABS = [
  { id: "workspace", label: "Workspace" },
  { id: "sources", label: "Source Explorer" },
  { id: "lab", label: "Integrity Lab" },
  { id: "eval", label: "Evaluation & Review" },
] as const;
type Tab = (typeof TABS)[number]["id"];

export default function App() {
  const [tab, setTab] = useState<Tab>("workspace");
  const [health, setHealth] = useState<Health | null>(null);
  const [healthErr, setHealthErr] = useState<string | null>(null);
  const [passageId, setPassageId] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<RunResult | null>(null);

  const [auth, setAuth] = useState<{ auth_required: boolean; authenticated: boolean } | null>(null);
  const [pass, setPass] = useState("");
  const [authErr, setAuthErr] = useState<string | null>(null);
  useEffect(() => {
    const check = () => api.authStatus().then(setAuth).catch(() => setAuth({ auth_required: false, authenticated: true }));
    check();
    window.addEventListener("pramaan-auth-required", check);
    return () => window.removeEventListener("pramaan-auth-required", check);
  }, []);

  const refresh = useCallback(() => {
    api.health().then((h) => { setHealth(h); setHealthErr(null); }).catch((e) => setHealthErr(e.message));
  }, []);
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 15000);
    return () => clearInterval(t);
  }, [refresh]);

  const openPassage = (pid: string) => { setPassageId(pid); setTab("sources"); };

  if (auth && auth.auth_required && !auth.authenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <form className="panel p-6 w-full max-w-sm space-y-3" onSubmit={(e) => {
          e.preventDefault(); setAuthErr(null);
          api.login(pass).then(() => { setPass(""); return api.authStatus().then(setAuth); }).catch((er) => setAuthErr(er.message));
        }}>
          <div className="text-xl font-bold text-forest-700">PRAMAAN demo</div>
          <p className="text-xs text-muted">Access is limited to invited reviewers. Synthetic educational inputs only — do not enter patient data.</p>
          <label className="text-sm block">Passcode<input type="password" className="input mt-1" value={pass} onChange={(e) => setPass(e.target.value)} autoFocus /></label>
          {authErr && <p className="text-sm text-alert-700" role="alert">{authErr}</p>}
          <button className="btn-primary w-full justify-center" disabled={!pass}>Enter</button>
        </form>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <ModeBanner health={health} error={healthErr} />
      <header className="border-b border-line bg-card">
        <div className="max-w-[1400px] mx-auto px-4 py-3 flex flex-wrap items-center gap-4">
          <div>
            <div className="text-xl font-bold text-forest-700 tracking-tight">PRAMAAN <span className="font-deva text-saffron-600 font-semibold">प्रमाण</span></div>
            <div className="text-xs text-muted">Ayurveda Evidence &amp; Safety Workbench · study and clinician-support prototype · not for diagnosis, prescribing or dosing</div>
          </div>
          <nav className="flex gap-1 ml-auto" role="tablist" aria-label="Views">
            {TABS.map((t) => (
              <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium ${tab === t.id ? "bg-forest-700 text-white" : "text-forest-700 hover:bg-forest-50"}`}>{t.label}</button>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-[1400px] w-full mx-auto px-4 py-4">
        <div hidden={tab !== "workspace"}><Workspace health={health} onOpenPassage={openPassage} onRun={setLastRun} /></div>
        {tab === "sources" && <SourceExplorer passageId={passageId} onOpen={setPassageId} health={health} />}
        {tab === "lab" && <Lab lastRunId={lastRun && lastRun.claims.some((c) => c.claim_type === "interpretation") ? lastRun.run_id : null} />}
        {tab === "eval" && <EvalReview health={health} />}
      </main>
      <footer className="border-t border-line text-[11px] text-muted px-4 py-3 text-center">
        Classical texts: SARIT TEI editions (CC BY-SA 3.0). Modern safety reference: NCCIH (public domain). Code: Apache-2.0. Model: bharatgenai/AyurParam.
        No affiliation with or endorsement by any institution is implied. All generated content and rules are pending human review.
      </footer>
    </div>
  );
}
