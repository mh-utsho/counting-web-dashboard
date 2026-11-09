import { useCallback, useEffect, useMemo, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import {
  Activity, AlertTriangle, Bell, Camera, CheckCircle2, CircleDot,
  Clock3, Gauge, LayoutDashboard, Play, Radio, RefreshCw, ShieldCheck,
  Square, Users
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "";
const WS = import.meta.env.VITE_WS_URL || `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/live`;

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Request failed");
  return body;
}

function useLiveData() {
  const [metrics, setMetrics] = useState({
    running: false, count: 0, threshold: 3, status: "STOPPED", fps: 0, unique_total: 0
  });
  const [frame, setFrame] = useState("");
  const [alerts, setAlerts] = useState([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let socket;
    let retry;
    let disposed = false;
    const connect = () => {
      socket = new WebSocket(WS);
      socket.onopen = () => { setConnected(true); setError(""); };
      socket.onclose = () => {
        setConnected(false);
        if (!disposed) retry = window.setTimeout(connect, 1800);
      };
      socket.onerror = () => setConnected(false);
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "snapshot") {
          setMetrics(data.metrics);
          setAlerts(data.alerts || []);
        }
        if (data.type === "frame") {
          setFrame(data.image);
          setMetrics((old) => ({
            ...old, running: true, count: data.count, threshold: data.threshold,
            status: data.status, fps: data.fps, unique_total: data.unique_total
          }));
          if (data.alert) setAlerts((old) => [data.alert, ...old.filter((a) => a.id !== data.alert.id)].slice(0, 250));
        }
        if (data.type === "status") setMetrics((old) => ({ ...old, running: data.running, status: data.status }));
        if (data.type === "error" || data.type === "system") setError(data.message);
        if (data.type === "settings") setMetrics((old) => ({ ...old, threshold: data.threshold }));
      };
    };
    connect();
    return () => {
      disposed = true;
      window.clearTimeout(retry);
      socket?.close();
    };
  }, []);

  return { metrics, frame, alerts, connected, error, setMetrics, setAlerts, setError };
}

function timeLabel(timestamp) {
  return new Date(timestamp * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function Header({ connected, activeAlerts }) {
  return <header className="topbar">
    <div className="brand"><div className="brand-mark"><Activity size={20} /></div>
      <div><strong>CrowdWatch</strong><span>LIVE MONITORING SYSTEM</span></div>
    </div>
    <div className="topbar-right">
      <div className={`connection ${connected ? "online" : ""}`}><span />{connected ? "LIVE LINK" : "CONNECTING"}</div>
      <div className="top-alert"><Bell size={16} /><b>{activeAlerts}</b></div>
      <div className="avatar">U</div>
    </div>
  </header>;
}

function Sidebar() {
  return <aside className="sidebar">
    <div className="side-label">WORKSPACE</div>
    <NavLink to="/" end className={({ isActive }) => isActive ? "nav-item selected" : "nav-item"}><LayoutDashboard size={18} /> Overview</NavLink>
    <NavLink to="/alerts" className={({ isActive }) => isActive ? "nav-item selected" : "nav-item"}><Bell size={18} /> Alert Center <span className="nav-dot" /></NavLink>
    <div className="side-label second">MONITORING</div>
    <div className="camera-nav"><Camera size={17} /><span>Camera 01</span><i /></div>
    <div className="sidebar-bottom"><ShieldCheck size={18} /><span>Privacy-first counting<br /><small>No identity recognition</small></span></div>
  </aside>;
}

function StatCard({ icon: Icon, label, value, detail, tone = "" }) {
  return <div className="stat-card"><div className={`stat-icon ${tone}`}><Icon size={19} /></div>
    <div className="stat-copy"><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>
  </div>;
}

function AlertItem({ alert }) {
  return <div className="alert-item">
    <div className="alert-symbol"><AlertTriangle size={17} /></div>
    <div className="alert-text"><strong>{alert.title}</strong><p>{alert.message}</p><small><Clock3 size={12} /> {timeLabel(alert.created_at)}</small></div>
    <span className="severity">CRITICAL</span>
  </div>;
}

function Overview({ data }) {
  const { metrics, frame, alerts, connected, error, setMetrics, setError } = data;
  const [thresholdInput, setThresholdInput] = useState(metrics.threshold ?? 3);
  const [source, setSource] = useState("0");
  const [busy, setBusy] = useState(false);
  useEffect(() => setThresholdInput(metrics.threshold), [metrics.threshold]);

  const start = async () => {
    setBusy(true); setError("");
    try {
      await api("/api/camera/start", { method: "POST", body: JSON.stringify({ source, threshold: Number(thresholdInput) }) });
      setMetrics((m) => ({ ...m, running: true, status: "STARTING" }));
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const stop = async () => {
    setBusy(true);
    try { await api("/api/camera/stop", { method: "POST" }); setMetrics((m) => ({ ...m, running: false, status: "STOPPED" })); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };
  const saveThreshold = async () => {
    try { await api("/api/settings/threshold", { method: "PUT", body: JSON.stringify({ threshold: Number(thresholdInput) }) }); }
    catch (e) { setError(e.message); }
  };
  const active = metrics.status === "ALERT";
  const statusClass = active ? "danger" : metrics.status === "WARNING" ? "warning" : "normal";

  return <main className="main-content">
    <div className="page-heading"><div><div className="eyebrow">CONTROL ROOM / OVERVIEW</div><h1>Monitoring overview</h1><p>Real-time people counting and crowd threshold monitoring.</p></div>
      <div className="live-clock"><span className="pulse" /> REAL-TIME DATA</div></div>
    {error && <div className="error-banner"><AlertTriangle size={16} />{error}<button onClick={() => setError("")}>Dismiss</button></div>}
    <section className="stats-grid">
      <StatCard icon={Users} label="PEOPLE IN REGION" value={metrics.count} detail="Current detected count" tone="blue" />
      <StatCard icon={Gauge} label="THRESHOLD LIMIT" value={metrics.threshold} detail="Alert when count is greater" tone="purple" />
      <StatCard icon={Activity} label="PROCESSING SPEED" value={`${metrics.fps || 0} FPS`} detail="Live inference performance" tone="green" />
      <StatCard icon={CircleDot} label="UNIQUE TRACKS" value={metrics.unique_total || 0} detail="IDs seen during this run" tone="orange" />
    </section>

    <section className="monitor-grid">
      <div className="panel camera-panel">
        <div className="panel-heading"><div><h2><Camera size={18} /> Camera 01 · Live feed</h2><p>YOLO11n detection · ByteTrack · Region of interest</p></div>
          <span className={`status-pill ${statusClass}`}><i />{metrics.status}</span></div>
        <div className="video-stage">
          {frame ? <img src={`data:image/jpeg;base64,${frame}`} alt="Live camera feed with person detections" /> :
            <div className="video-placeholder"><div className="placeholder-icon"><Camera size={30} /></div><strong>Camera feed is not running</strong><span>Start the camera to view the live detection stream.</span></div>}
          {metrics.running && <div className="feed-tag"><span /> LIVE</div>}
        </div>
        <div className="camera-footer"><div><span className="legend-dot detected" /> Person detection <span className="legend-dot roi" /> Region of interest</div><span>{connected ? "WebSocket connected" : "Waiting for live connection"}</span></div>
      </div>

      <div className="panel alert-panel">
        <div className="panel-heading"><div><h2><Bell size={18} /> Instant alerts</h2><p>New events appear here automatically</p></div><span className="count-badge">{alerts.length}</span></div>
        <div className="alert-list compact">
          {alerts.length ? alerts.slice(0, 5).map((alert) => <AlertItem key={alert.id} alert={alert} />) :
            <div className="empty-state"><CheckCircle2 size={25} /><strong>All clear</strong><span>No crowd alerts have been triggered.</span></div>}
        </div>
        <a className="text-link" href="/alerts">Open full alert center <span>→</span></a>
      </div>
    </section>

    <section className="panel controls-panel">
      <div className="controls-title"><div><h2>Camera controls</h2><p>Configure the source and crowd alert threshold.</p></div><span className={`run-state ${metrics.running ? "is-running" : ""}`}><span />{metrics.running ? "PROCESSING" : "STOPPED"}</span></div>
      <div className="control-row">
        <label className="field"><span>VIDEO SOURCE</span><input value={source} onChange={(e) => setSource(e.target.value)} placeholder="0 or /path/to/video.mp4" disabled={metrics.running} /><small>Use 0 for the default webcam, or provide a video file path.</small></label>
        <label className="field threshold-field"><span>ALERT THRESHOLD</span><input type="number" min="0" max="10000" value={thresholdInput} onChange={(e) => setThresholdInput(e.target.value)} /><small>Alert triggers when people count is above this value.</small></label>
        <div className="control-actions">
          <button className="btn btn-primary" onClick={start} disabled={busy || metrics.running}><Play size={16} /> Start camera</button>
          <button className="btn btn-secondary" onClick={stop} disabled={busy || !metrics.running}><Square size={15} /> Stop</button>
          <button className="btn btn-quiet" onClick={saveThreshold} disabled={busy}><RefreshCw size={15} /> Apply limit</button>
        </div>
      </div>
    </section>
    <footer className="page-footer">CrowdWatch · People counting without face recognition <span>Built with FastAPI, WebSockets & React</span></footer>
  </main>;
}

function AlertsPage({ data }) {
  const { alerts, setAlerts, connected, metrics } = data;
  const [filter, setFilter] = useState("all");
  useEffect(() => { api("/api/alerts").then(setAlerts).catch(() => {}); }, [setAlerts]);
  const filtered = useMemo(() => filter === "all" ? alerts : alerts.filter((a) => a.severity === filter), [alerts, filter]);
  return <main className="main-content">
    <div className="page-heading"><div><div className="eyebrow">CONTROL ROOM / EVENTS</div><h1>Alert center</h1><p>A dedicated alert feed, ready to be embedded in another dashboard.</p></div>
      <div className="live-clock"><span className={connected ? "pulse" : "pulse muted"} /> {connected ? "LIVE UPDATES ON" : "RECONNECTING"}</div></div>
    <section className="alert-summary-grid">
      <div className="summary-card"><span>Total alerts</span><strong>{alerts.length}</strong><small>Recorded in this session</small></div>
      <div className="summary-card"><span>Current people count</span><strong>{metrics.count}</strong><small>Live camera measurement</small></div>
      <div className="summary-card"><span>Monitoring state</span><strong className={metrics.status === "ALERT" ? "red-text" : ""}>{metrics.status}</strong><small>{metrics.running ? "Camera processing active" : "Camera is stopped"}</small></div>
    </section>
    <section className="panel full-alert-panel">
      <div className="panel-heading alert-page-heading"><div><h2><Bell size={18} /> Alert history</h2><p>Events are pushed over WebSocket as soon as the threshold rule is met.</p></div>
        <select value={filter} onChange={(e) => setFilter(e.target.value)}><option value="all">All events</option><option value="critical">Critical</option></select></div>
      <div className="alert-list">
        {filtered.length ? filtered.map((alert) => <AlertItem key={alert.id} alert={alert} />) :
          <div className="empty-state large"><CheckCircle2 size={30} /><strong>No alerts to display</strong><span>When a crowd alert is triggered, it will appear here instantly.</span></div>}
      </div>
    </section>
    <footer className="page-footer">Alert Center API: <code>GET /api/alerts</code> · WebSocket: <code>/ws/live</code></footer>
  </main>;
}

export default function App() {
  const data = useLiveData();
  return <div className="app-shell">
    <Header connected={data.connected} activeAlerts={data.alerts.length} />
    <div className="body-layout"><Sidebar />
      <Routes>
        <Route path="/" element={<Overview data={data} />} />
        <Route path="/alerts" element={<AlertsPage data={data} />} />
      </Routes>
    </div>
  </div>;
}
