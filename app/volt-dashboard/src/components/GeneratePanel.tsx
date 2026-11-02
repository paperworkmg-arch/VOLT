// ── GeneratePanel.tsx — ACE-Step generate panel ─────────────────────────────
// Drop into app/volt-dashboard/src/components/ (adjust the import path to
// wherever the ACE_STEP_APP entry landed). Talks ONLY to the hub on 8500:
//
//   POST /api/acestep/generate         engine surface (the backbone)
//   POST /api/acestep/generate/comfy   ComfyUI surface (picture work)
//   GET  /api/acestep/jobs/{id}        poll — completion files the song
//                                      into the catalog as a DRAFT
//   GET  /api/acestep/jobs/{id}/download
//
// Relative URLs assume the front end is served by / proxied to the hub,
// like the other panels. Defaults mirror the low-memory recipe
// (Turbo, 60s); the hub enforces the Air guardrails.
// ────────────────────────────────────────────────────────────────────────────

import { useEffect, useRef, useState } from "react";

type Job = {
  job_id: string;
  status: "queued" | "running" | "complete" | "error";
  file?: string | null;
  error?: string | null;
};

export default function GeneratePanel() {
  const [prompt, setPrompt] = useState("");
  const [lyrics, setLyrics] = useState("");
  const [duration, setDuration] = useState(60);
  const [bpm, setBpm] = useState("");
  const [keyScale, setKeyScale] = useState("");
  const [surface, setSurface] = useState<"engine" | "comfy">("engine");
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => () => { if (timer.current) window.clearInterval(timer.current); }, []);

  async function poll(jobId: string) {
    const r = await fetch(`/api/acestep/jobs/${jobId}`);
    if (!r.ok) return;
    const j: Job = await r.json();
    setJob(j);
    if (j.status === "complete" || j.status === "error") {
      if (timer.current) window.clearInterval(timer.current);
      setBusy(false);
    }
  }

  async function generate() {
    if (!prompt.trim() || busy) return;
    setBusy(true);
    setJob(null);
    const url = surface === "comfy" ? "/api/acestep/generate/comfy" : "/api/acestep/generate";
    const r = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        lyrics,
        duration,
        bpm: bpm ? Number(bpm) : undefined,
        key_scale: keyScale || undefined,
      }),
    });
    if (!r.ok) {
      setBusy(false);
      setJob({ job_id: "", status: "error", error: `hub returned ${r.status}` });
      return;
    }
    const j: Job = await r.json();
    setJob(j);
    timer.current = window.setInterval(() => poll(j.job_id), 2000);
  }

  return (
    <div className="generate-panel">
      <h3>ACE-Step — Song Generation</h3>

      <label>
        Style / prompt
        <textarea value={prompt} onChange={(e) => setPrompt(e.target.value)}
          placeholder="bedroom-soaked R&B, slow groove, warm keys, female vocal"
          rows={2} />
      </label>

      <label>
        Lyrics (blank = instrumental)
        <textarea value={lyrics} onChange={(e) => setLyrics(e.target.value)} rows={4} />
      </label>

      <div className="row">
        <label>
          Length: {duration}s
          <input type="range" min={30} max={240} step={10} value={duration}
            onChange={(e) => setDuration(Number(e.target.value))} />
        </label>
        <label>
          BPM
          <input type="number" value={bpm} onChange={(e) => setBpm(e.target.value)}
            placeholder="auto" style={{ width: 70 }} />
        </label>
        <label>
          Key
          <input value={keyScale} onChange={(e) => setKeyScale(e.target.value)}
            placeholder="auto" style={{ width: 70 }} />
        </label>
        <label>
          Surface
          <select value={surface} onChange={(e) => setSurface(e.target.value as "engine" | "comfy")}>
            <option value="engine">Engine</option>
            <option value="comfy">ComfyUI</option>
          </select>
        </label>
      </div>

      <button onClick={generate} disabled={busy || !prompt.trim()}>
        {busy ? "Generating…" : "Generate song"}
      </button>

      {job && job.status !== "error" && (
        <p>Status: {job.status}
          {job.status === "complete" && " — filed to the catalog as a draft"}
        </p>
      )}
      {job?.status === "complete" && (
        <audio controls src={`/api/acestep/jobs/${job.job_id}/download`} />
      )}
      {job?.status === "error" && (
        <p className="error">Generation failed: {job.error ?? "unknown error"}</p>
      )}
    </div>
  );
}
