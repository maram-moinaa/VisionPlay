import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

import { DwellSelector } from "./dwell.js";
import "./styles.css";

const WS_URL = import.meta.env.VITE_TRACKING_WS_URL || "ws://127.0.0.1:8765/ws/tracking";
const CURSOR_RENDER_RESPONSE = 34;

const companies = [
  {
    id: "northstar",
    name: "Northstar Robotics",
    area: "Robotics · Autonomy",
    description: "Building adaptive robotic systems that make complex industrial work safer.",
    initials: "NR",
    accent: "mint",
  },
  {
    id: "voltara",
    name: "Voltara Energy",
    area: "Climate tech · Energy",
    description: "A smarter grid platform accelerating the shift to resilient clean power.",
    initials: "VE",
    accent: "amber",
  },
  {
    id: "synapse",
    name: "Synapse Health",
    area: "AI · Digital health",
    description: "Turning clinical signals into more personal, proactive patient care.",
    initials: "SH",
    accent: "violet",
  },
  {
    id: "orbit",
    name: "Orbit Systems",
    area: "Aerospace · Data",
    description: "Making satellite intelligence accessible to teams solving real-world problems.",
    initials: "OS",
    accent: "blue",
  },
  {
    id: "form",
    name: "Form & Function",
    area: "Product · Design",
    description: "Human-centred digital products, from early research to thoughtful launch.",
    initials: "FF",
    accent: "rose",
  },
  {
    id: "fieldnote",
    name: "Fieldnote",
    area: "Software · Collaboration",
    description: "A calm workspace helping distributed teams turn good ideas into action.",
    initials: "FN",
    accent: "lime",
  },
];

function elementAtCursor(point) {
  if (!point) return null;
  const target = document.elementFromPoint(
    point.x * window.innerWidth,
    point.y * window.innerHeight,
  );
  if (!(target instanceof HTMLElement)) return null;
  return target.closest("[data-company-id], button") || target;
}

function App() {
  const [connection, setConnection] = useState({ camera: "connecting", tracking: false });
  const [cursorVisible, setCursorVisible] = useState(false);
  const [hoveredId, setHoveredId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [selected, setSelected] = useState(null);
  const [notice, setNotice] = useState("");
  const selectedRef = useRef(selected);
  const cursorTargetRef = useRef(null);
  const cursorDisplayRef = useRef(null);
  const cursorElementRef = useRef(null);
  const selectedIds = useRef(new Set());
  const viewRef = useRef("browse");
  const selector = useRef(null);
  const openHandActive = useRef(false);
  const heldElement = useRef(null);
  selectedRef.current = selected;

  const updateCursorTarget = useCallback((point) => {
    cursorTargetRef.current = point;
    if (cursorDisplayRef.current === null) cursorDisplayRef.current = point;
    setCursorVisible(true);
  }, []);

  useEffect(() => {
    viewRef.current = selected ? "confirm" : "browse";
    if (selected) {
      selector.current?.reset();
      setHoveredId(null);
      setProgress(0);
    }
  }, [selected]);

  const selectCompany = useCallback((id) => {
    if (selectedIds.current.has(id)) return;
    const company = companies.find((item) => item.id === id);
    if (!company) return;
    selectedIds.current.add(id);
    setSelected(company);
  }, []);

  const goBack = useCallback(() => {
    if (selectedRef.current) selectedIds.current.delete(selectedRef.current.id);
    setSelected(null);
    selector.current?.reset();
    setHoveredId(null);
    setProgress(0);
  }, []);

  const restart = useCallback(() => {
    selectedIds.current.clear();
    setSelected(null);
    cursorTargetRef.current = null;
    cursorDisplayRef.current = null;
    setCursorVisible(false);
    selector.current?.reset();
    setHoveredId(null);
    setProgress(0);
    setNotice("");
  }, []);

  useEffect(() => {
    let socket;
    let reconnectTimer;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      socket = new WebSocket(WS_URL);
      socket.onopen = () => setConnection((current) => ({ ...current, connected: true, message: "" }));
      socket.onmessage = (event) => {
        let message;
        try {
          message = JSON.parse(event.data);
        } catch {
          setNotice("The tracking service sent an unreadable message.");
          return;
        }
        if (message.type === "cursor" && Number.isFinite(message.x) && Number.isFinite(message.y)) {
          updateCursorTarget({
            x: Math.min(1, Math.max(0, message.x)),
            y: Math.min(1, Math.max(0, message.y)),
          });
        } else if (message.type === "status") {
          if (Number.isFinite(message.dwell_seconds) && message.dwell_seconds > 0) {
            selector.current = new DwellSelector(message.dwell_seconds * 1000);
          }
          setConnection({
            camera: message.camera,
            tracking: Boolean(message.tracking),
            connected: true,
            message: message.message || "",
          });
        } else if (message.type === "gesture") {
          if (message.name === "open_hand_start" || message.name === "open_hand_end") {
            openHandActive.current = message.name === "open_hand_start";
            selector.current?.reset();
            return;
          }
          if (message.name === "hold_start") {
            const target = elementAtCursor(cursorDisplayRef.current);
            heldElement.current = target;
            if (target) {
              const point = cursorDisplayRef.current;
              target.dispatchEvent(new PointerEvent("pointerdown", {
                bubbles: true,
                cancelable: true,
                clientX: point.x * window.innerWidth,
                clientY: point.y * window.innerHeight,
                button: 0,
                pointerId: 1,
                pointerType: "mouse",
                isPrimary: true,
              }));
            }
            return;
          }
          if (message.name === "hold_end") {
            const target = heldElement.current;
            heldElement.current = null;
            const point = cursorDisplayRef.current;
            if (target?.isConnected && point) {
              target.dispatchEvent(new PointerEvent("pointerup", {
                bubbles: true,
                cancelable: true,
                clientX: point.x * window.innerWidth,
                clientY: point.y * window.innerHeight,
                button: 0,
                pointerId: 1,
                pointerType: "mouse",
                isPrimary: true,
              }));
              if (elementAtCursor(point) === target) {
                target.dispatchEvent(new MouseEvent("click", {
                  bubbles: true,
                  cancelable: true,
                  clientX: point.x * window.innerWidth,
                  clientY: point.y * window.innerHeight,
                  detail: 1,
                }));
              }
            }
            return;
          }
          if (message.name === "right_click") {
            if (viewRef.current === "confirm") {
              goBack();
              return;
            }
            const point = cursorDisplayRef.current;
            const target = elementAtCursor(point);
            if (target) {
              target.dispatchEvent(new MouseEvent("contextmenu", {
                bubbles: true,
                cancelable: true,
                clientX: point.x * window.innerWidth,
                clientY: point.y * window.innerHeight,
                button: 2,
              }));
            }
            return;
          }
          if (message.name === "left_click" || message.name === "double_click") {
            const point = cursorDisplayRef.current;
            if (!point) return;
            const target = elementAtCursor(point);
            if (target) {
              target.dispatchEvent(new MouseEvent("click", {
                bubbles: true,
                cancelable: true,
                clientX: point.x * window.innerWidth,
                clientY: point.y * window.innerHeight,
                detail: message.name === "double_click" ? 2 : 1,
              }));
            }
          }
        }
      };
      socket.onerror = () => setConnection((current) => ({
        ...current,
        connected: false,
        message: "Cannot reach the local tracking service. Start the Python backend.",
      }));
      socket.onclose = () => {
        setConnection((current) => ({ ...current, connected: false }));
        if (!disposed) reconnectTimer = window.setTimeout(connect, 1800);
      };
    };

    connect();
    return () => {
      disposed = true;
      window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [goBack, updateCursorTarget]);

  useEffect(() => {
    const onPointerMove = (event) => {
      if (connection.tracking) return;
      updateCursorTarget({ x: event.clientX / window.innerWidth, y: event.clientY / window.innerHeight });
    };
    window.addEventListener("pointermove", onPointerMove);

    let animationFrame;
    let lastFrameTime = 0;
    const tick = (now) => {
      const target = cursorTargetRef.current;
      let point = cursorDisplayRef.current;
      if (target) {
        if (!point) {
          point = target;
        } else {
          const elapsedSeconds = lastFrameTime
            ? Math.min((now - lastFrameTime) / 1000, 0.1)
            : 1 / 60;
          const blend = 1 - Math.exp(-CURSOR_RENDER_RESPONSE * elapsedSeconds);
          point = {
            x: point.x + (target.x - point.x) * blend,
            y: point.y + (target.y - point.y) * blend,
          };
        }
        cursorDisplayRef.current = point;
        if (cursorElementRef.current) {
          cursorElementRef.current.style.transform =
            `translate3d(${point.x * window.innerWidth}px, ${point.y * window.innerHeight}px, 0) translate(-50%, -50%)`;
        }
      }
      lastFrameTime = now;
      let targetId = null;
      if (point && viewRef.current === "browse") {
        const x = point.x * window.innerWidth;
        const y = point.y * window.innerHeight;
        for (const element of document.querySelectorAll("[data-company-id]")) {
          const rect = element.getBoundingClientRect();
          if (x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom) {
            targetId = element.dataset.companyId;
            break;
          }
        }
      }
      const dwell = selector.current
        ? selector.current.update(openHandActive.current ? targetId : null, now)
        : { targetId, progress: 0, selected: false };
      setHoveredId((current) => current === targetId ? current : targetId);
      setProgress((current) => Math.abs(current - dwell.progress) < 0.01 ? current : dwell.progress);
      if (dwell.selected && dwell.targetId) selectCompany(dwell.targetId);
      animationFrame = window.requestAnimationFrame(tick);
    };
    animationFrame = window.requestAnimationFrame(tick);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.cancelAnimationFrame(animationFrame);
    };
  }, [connection.tracking, selectCompany, updateCursorTarget]);

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "Escape" && selected) goBack();
      if (event.key.toLowerCase() === "r" && !selected) restart();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [goBack, restart, selected]);

  const cameraReady = connection.camera === "ready";
  const connectionLabel = connection.connected === false && connection.camera !== "connecting"
    ? "API disconnected"
    : connection.camera === "error"
      ? "Camera unavailable"
      : cameraReady
        ? connection.tracking ? "Hand tracking" : "Camera ready"
        : "Connecting";

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#" onClick={(event) => event.preventDefault()} aria-label="G3 home">
          <span className="brand-mark">G3</span>
          <span className="brand-divider" />
          <span className="brand-title">Company discovery</span>
        </a>
        <div className={`connection-pill ${cameraReady ? "is-ready" : ""}`}>
          <span className="status-dot" />
          <span>{connectionLabel}</span>
        </div>
      </header>

      {connection.message && (
        <div className="service-notice" role="status">{connection.message}</div>
      )}
      {notice && <div className="service-notice" role="alert">{notice}</div>}

      {selected ? (
        <section className="confirmation" aria-labelledby="confirm-title">
          <div className="confirmation-kicker"><span className="check-icon">✓</span> Selection captured</div>
          <p className="eyebrow">YOUR NEXT CHAPTER</p>
          <h1 id="confirm-title">A great choice.</h1>
          <p className="confirmation-copy">You selected <strong>{selected.name}</strong>. Take a moment to confirm, or go back and explore.</p>
          <article className={`selected-card accent-${selected.accent}`}>
            <div className="company-monogram">{selected.initials}</div>
            <div><span className="company-area">{selected.area}</span><h2>{selected.name}</h2><p>{selected.description}</p></div>
          </article>
          <div className="confirmation-actions">
            <button className="button button-secondary" onClick={goBack}>← Go back</button>
            <button className="button button-primary" onClick={() => setNotice(`${selected.name} confirmed. Thanks for exploring G3.`)}>Confirm selection <span>→</span></button>
          </div>
          <p className="keyboard-hint">Gesture: pinch to activate · right-click or Esc to go back</p>
        </section>
      ) : (
        <section className="content">
          <div className="intro-row">
            <div>
              <p className="eyebrow">MEET YOUR NEXT POSSIBILITY</p>
              <h1>Find your <span>fit.</span></h1>
              <p className="intro-copy">Explore a few teams shaping what comes next. Point to browse, then open your hand and pause to choose.</p>
            </div>
            <div className="gesture-guide" aria-label="Guide des gestes">
              <table>
                <thead><tr><th>Geste</th><th>Utilisation</th></tr></thead>
                <tbody>
                  <tr><td>POINT</td><td>Pointer / sélectionner</td></tr>
                  <tr><td>PINCH</td><td>Attraper / sélectionner</td></tr>
                  <tr><td>OPEN HAND</td><td>Pause / action</td></tr>
                  <tr><td>FIST</td><td>Maintenir</td></tr>
                  <tr><td>TWO FINGERS</td><td>Sélection secondaire</td></tr>
                </tbody>
              </table>
            </div>
          </div>

          <div className="section-heading"><span>Featured companies</span><span className="result-count">01 — 06</span></div>
          <div className="company-grid">
            {companies.map((company, index) => (
              <button
                key={company.id}
                className={`company-card accent-${company.accent} ${hoveredId === company.id ? "is-hovered" : ""}`}
                data-company-id={company.id}
                style={{ "--card-index": index, "--dwell-progress": hoveredId === company.id ? progress : 0 }}
                onClick={() => selectCompany(company.id)}
                onContextMenu={(event) => {
                  event.preventDefault();
                  selectCompany(company.id);
                }}
                aria-label={`Select ${company.name}`}
              >
                <div className="card-topline">
                  <span className="company-monogram">{company.initials}</span>
                  <span className="dwell-ring" aria-hidden="true"><span /></span>
                  <span className="card-arrow" aria-hidden="true">↗</span>
                </div>
                <span className="company-area">{company.area}</span>
                <h2>{company.name}</h2>
                <p>{company.description}</p>
                <span className="card-bottom">{hoveredId === company.id ? "Hold to discover" : "Explore team"} <span>→</span></span>
              </button>
            ))}
          </div>

          <footer className="page-footer">
            <span><i className="footer-spark">✳</i> G3 · Build a future that feels like yours.</span>
            <button onClick={restart} className="restart-button">Restart experience <span>↺</span></button>
          </footer>
        </section>
      )}

      {cursorVisible && <div ref={cursorElementRef} className={`virtual-cursor ${connection.tracking ? "is-tracking" : "is-fallback"}`} aria-hidden="true"><span /></div>}
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
