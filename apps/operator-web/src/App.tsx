import { useEffect, useRef, useState } from "react";

type MotionMode = "tracking" | "neutral" | "stopped";

type EmbodimentState = {
  version: 1;
  sequence: number;
  updated_at_ms: number;
  yaw_deg: number;
  pitch_deg: number;
  mode: MotionMode;
  reason: string | null;
};

const gatewayHttp = import.meta.env.VITE_GATEWAY_HTTP ?? "http://127.0.0.1:8080";
const gatewayWs = import.meta.env.VITE_GATEWAY_WS ?? "ws://127.0.0.1:8080/v1/stream";

function unixMilliseconds() {
  return Date.now();
}

const initialState: EmbodimentState = {
  version: 1,
  sequence: 0,
  updated_at_ms: 0,
  yaw_deg: 0,
  pitch_deg: 0,
  mode: "neutral",
  reason: "not_connected",
};

function isEmbodimentState(value: unknown): value is EmbodimentState {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    candidate.version === 1 &&
    Number.isSafeInteger(candidate.sequence) &&
    typeof candidate.updated_at_ms === "number" &&
    Number.isFinite(candidate.updated_at_ms) &&
    typeof candidate.yaw_deg === "number" &&
    Number.isFinite(candidate.yaw_deg) &&
    typeof candidate.pitch_deg === "number" &&
    Number.isFinite(candidate.pitch_deg) &&
    (candidate.mode === "tracking" ||
      candidate.mode === "neutral" ||
      candidate.mode === "stopped") &&
    (typeof candidate.reason === "string" || candidate.reason === null)
  );
}

export function App() {
  const [state, setState] = useState(initialState);
  const [stateAgeMs, setStateAgeMs] = useState(0);
  const [connected, setConnected] = useState(false);
  const [commandStatus, setCommandStatus] = useState("No command sent");
  const [controlToken, setControlToken] = useState("");
  const sequence = useRef(0);

  useEffect(() => {
    const socket = new WebSocket(gatewayWs);
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);
    socket.onmessage = (event) => {
      try {
        const payload: unknown = JSON.parse(String(event.data));
        if (!isEmbodimentState(payload)) {
          setCommandStatus("Rejected invalid gateway state");
          return;
        }
        setState(payload);
        setStateAgeMs(Math.max(0, Date.now() - payload.updated_at_ms));
      } catch {
        setCommandStatus("Rejected malformed gateway message");
      }
    };
    return () => socket.close();
  }, []);

  const sendPose = async (yawDeg: number, pitchDeg: number) => {
    sequence.current = Math.max(sequence.current + 1, state.sequence + 1);
    await sendCommand("pose", `${gatewayHttp}/v1/pose`, {
      method: "POST",
      headers: controlHeaders(true),
      body: JSON.stringify({
        version: 1,
        sequence: sequence.current,
        issued_at_ms: unixMilliseconds(),
        ttl_ms: 750,
        yaw_deg: yawDeg,
        pitch_deg: pitchDeg,
      }),
    });
  };

  const stop = async () => {
    await sendCommand("stop", `${gatewayHttp}/v1/stop`, { method: "POST" });
  };

  const arm = async () => {
    await sendCommand("arm", `${gatewayHttp}/v1/arm`, {
      method: "POST",
      headers: controlHeaders(false),
    });
  };

  const controlHeaders = (includeContentType: boolean) => {
    const headers: Record<string, string> = {};
    if (includeContentType) headers["content-type"] = "application/json";
    if (controlToken) headers.authorization = `Bearer ${controlToken}`;
    return headers;
  };

  const sendCommand = async (name: string, url: string, init: RequestInit) => {
    setCommandStatus(`Sending ${name}…`);
    try {
      const response = await fetch(url, init);
      if (!response.ok) {
        const body: unknown = await response.json().catch(() => null);
        const detail =
          typeof body === "object" && body !== null && "detail" in body
            ? String(body.detail)
            : `HTTP ${response.status}`;
        setCommandStatus(`${name} rejected: ${detail}`);
        return;
      }
      setCommandStatus(`${name} accepted`);
    } catch {
      setCommandStatus(`${name} failed: gateway unavailable`);
    }
  };

  const faceTransform = `rotateY(${state.yaw_deg * 0.35}deg) rotateX(${-state.pitch_deg * 0.3}deg)`;
  const pupilTransform = `translate(${state.yaw_deg * 0.08}px, ${state.pitch_deg * 0.08}px)`;
  return (
    <main>
      <header>
        <div>
          <p className="eyebrow">PROJECT MIRROR / OPERATOR</p>
          <h1>One state. Two bodies.</h1>
        </div>
        <div className={`connection ${connected ? "online" : "offline"}`}>
          <span />
          {connected ? "Gateway online" : "Gateway offline"}
        </div>
      </header>

      <section className="stage" aria-label="Simulated character head">
        <div className="grid" />
        <div className="head" style={{ transform: faceTransform }}>
          <div className="eye left"><i style={{ transform: pupilTransform }} /></div>
          <div className="eye right"><i style={{ transform: pupilTransform }} /></div>
          <div className="mouth" />
        </div>
        <div className="crosshair" />
      </section>

      <section className="panel">
        <div className="metric">
          <span>MODE</span>
          <strong>{state.mode}</strong>
        </div>
        <div className="metric">
          <span>YAW</span>
          <strong>{state.yaw_deg.toFixed(1)}°</strong>
        </div>
        <div className="metric">
          <span>PITCH</span>
          <strong>{state.pitch_deg.toFixed(1)}°</strong>
        </div>
        <div className="metric">
          <span>SEQUENCE</span>
          <strong>{state.sequence}</strong>
        </div>
        <div className="metric">
          <span>RECEIPT AGE</span>
          <strong>{stateAgeMs} ms</strong>
        </div>
      </section>

      <section className="controls">
        <h2>Bench controls</h2>
        <p>Commands are intentionally outside the mechanical range to prove gateway clamping.</p>
        <p className="commandStatus" role="status">{commandStatus}</p>
        <label className="tokenField">
          Physical control token
          <input
            type="password"
            autoComplete="off"
            value={controlToken}
            onChange={(event) => setControlToken(event.target.value)}
            placeholder="Optional in simulation"
          />
        </label>
        <div className="buttonRow">
          <button disabled={!connected} onClick={() => void sendPose(-90, 0)}>Look left</button>
          <button disabled={!connected} onClick={() => void sendPose(0, -45)}>Look up</button>
          <button disabled={!connected} onClick={() => void sendPose(0, 0)}>Neutral</button>
          <button disabled={!connected} onClick={() => void sendPose(90, 0)}>Look right</button>
          <button disabled={!connected} className="arm" onClick={() => void arm()}>Arm motion</button>
          <button className="stop" onClick={() => void stop()}>Emergency stop</button>
        </div>
      </section>
    </main>
  );
}
