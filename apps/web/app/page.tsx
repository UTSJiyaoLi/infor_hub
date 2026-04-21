"use client";

import { useMemo, useState } from "react";

type CollectorResponse = Record<string, any>;

function trimSlash(v: string) {
  return (v || "").trim().replace(/\/+$/, "");
}

export default function HomePage() {
  const [backend, setBackend] = useState(process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8010");
  const [topic, setTopic] = useState("floating offshore wind");
  const [goal, setGoal] = useState("生成工程情报简报，包含案例对比、趋势、风险与跟踪建议");
  const [rawSources, setRawSources] = useState('[{"title":"Demo source","source_type":"report","url":"https://example.com","text":"demo text"}]');
  const [status, setStatus] = useState("Ready");
  const [response, setResponse] = useState<CollectorResponse | null>(null);
  const [streamLog, setStreamLog] = useState<string>("");
  const [busy, setBusy] = useState(false);

  const report = useMemo(() => String(response?.final_report || ""), [response]);

  async function healthCheck() {
    setBusy(true);
    setStatus("Checking health...");
    try {
      const r = await fetch(`${trimSlash(backend)}/health`);
      const text = await r.text();
      setStatus(r.ok ? `Health OK: ${text}` : `Health failed(${r.status}): ${text}`);
    } catch (e: any) {
      setStatus(`Health error: ${String(e?.message || e)}`);
    } finally {
      setBusy(false);
    }
  }

  async function runTask() {
    setBusy(true);
    setStatus("Creating task...");
    setResponse(null);
    try {
      const parsedSources = JSON.parse(rawSources);
      const payload = { topic, user_goal: goal, raw_sources: parsedSources };
      const r = await fetch(`${trimSlash(backend)}/tasks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await r.json();
      if (!r.ok) {
        setStatus(`Create task failed(${r.status}): ${JSON.stringify(data)}`);
        return;
      }
      const taskId = String(data.task_id || "");
      if (!taskId) {
        setStatus("Task id missing in response.");
        return;
      }
      setStatus(`Task created: ${taskId}, polling...`);
      for (let i = 0; i < 120; i += 1) {
        const tr = await fetch(`${trimSlash(backend)}/tasks/${taskId}`);
        const tdata = await tr.json();
        if (!tr.ok) {
          setStatus(`Task poll failed(${tr.status}): ${JSON.stringify(tdata)}`);
          return;
        }
        if (tdata.status === "success" || tdata.status === "failed") {
          setResponse(tdata);
          setStatus(`Task ${tdata.status}: ${taskId}`);
          return;
        }
        await new Promise((resolve) => setTimeout(resolve, 500));
      }
      setStatus("Task polling timeout.");
    } catch (e: any) {
      setStatus(`Run task error: ${String(e?.message || e)}`);
    } finally {
      setBusy(false);
    }
  }

  async function streamReport() {
    setBusy(true);
    setStreamLog("");
    setStatus("Streaming report...");
    try {
      const parsedSources = JSON.parse(rawSources);
      const payload = { topic, user_goal: goal, raw_sources: parsedSources };
      const resp = await fetch(`${trimSlash(backend)}/report/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!resp.ok || !resp.body) {
        setStatus(`Stream failed(${resp.status}).`);
        return;
      }
      const reader = resp.body.getReader();
      const decoder = new TextDecoder("utf-8");
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        if (chunk) setStreamLog((prev) => prev + chunk);
      }
      setStatus("Stream finished.");
    } catch (e: any) {
      setStatus(`Stream error: ${String(e?.message || e)}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main>
      <h1>Infor Hub</h1>
      <p className="muted">Next.js frontend aligned with Wind Agent style, focused on simple workflow execution.</p>

      <section className="card">
        <div className="grid">
          <div>
            <label>Backend URL</label>
            <input value={backend} onChange={(e) => setBackend(e.target.value)} />
          </div>
          <div>
            <label>Status</label>
            <input value={status} readOnly />
          </div>
        </div>
        <div className="actions" style={{ marginTop: 10 }}>
          <button className="primary" disabled={busy} onClick={() => void healthCheck()}>Health</button>
          <button className="primary" disabled={busy} onClick={() => void runTask()}>Run Task</button>
          <button className="primary" disabled={busy} onClick={() => void streamReport()}>Stream Report</button>
          <button disabled={busy} onClick={() => { setResponse(null); setStatus("Cleared"); }}>Clear</button>
        </div>
      </section>

      <section className="card" style={{ marginTop: 12 }}>
        <div className="row">
          <div>
            <label>Topic</label>
            <input value={topic} onChange={(e) => setTopic(e.target.value)} />
          </div>
          <div>
            <label>User Goal</label>
            <input value={goal} onChange={(e) => setGoal(e.target.value)} />
          </div>
        </div>
        <div style={{ marginTop: 10 }}>
          <label>raw_sources JSON</label>
          <textarea value={rawSources} onChange={(e) => setRawSources(e.target.value)} />
        </div>
      </section>

      <section className="card" style={{ marginTop: 12 }}>
        <h3>Final Report (Markdown Text)</h3>
        <pre className="mono">{report || "No report yet."}</pre>
      </section>

      <section className="card" style={{ marginTop: 12 }}>
        <h3>Raw Response</h3>
        <pre className="mono">{response ? JSON.stringify(response, null, 2) : "{}"}</pre>
      </section>
      <section className="card" style={{ marginTop: 12 }}>
        <h3>Stream Events</h3>
        <pre className="mono">{streamLog || "No stream events yet."}</pre>
      </section>
    </main>
  );
}
