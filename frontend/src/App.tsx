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

  const refresh = useCallback(() => {
    api.health().then((h) => { setHealth(h); setHealthErr(null); }).catch((e) => setHealthErr(e.message));
  }, []);
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 15000);
    return () => clearInterval(t);
  }, [refresh]);

  const openPassage = (pid: string) => { setPassageId(pid); setTab("sources"); };

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
