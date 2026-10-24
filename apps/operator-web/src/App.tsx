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

const initialState: EmbodimentState = {
  version: 1,
  sequence: 0,
  updated_at_ms: 0,
  yaw_deg: 0,
  pitch_deg: 0,
  mode: "neutral",
  reason: "not_connected",
};

export function App() {
  const [state, setState] = useState(initialState);
  const [stateAgeMs, setStateAgeMs] = useState(0);
  const [connected, setConnected] = useState(false);
  const sequence = useRef(0);

  useEffect(() => {
    const socket = new WebSocket(gatewayWs);
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);
    socket.onmessage = (event) => {
      const nextState = JSON.parse(String(event.data)) as EmbodimentState;
      setState(nextState);
      setStateAgeMs(Math.max(0, Date.now() - nextState.updated_at_ms));
    };
    return () => socket.close();
  }, []);

  const sendPose = async (yawDeg: number, pitchDeg: number) => {
    sequence.current = Math.max(sequence.current + 1, state.sequence + 1);
    await fetch(`${gatewayHttp}/v1/pose`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        version: 1,
        sequence: sequence.current,
        issued_at_ms: Date.now(),
        ttl_ms: 750,
        yaw_deg: yawDeg,
        pitch_deg: pitchDeg,
      }),
    });
  };

  const stop = async () => {
    await fetch(`${gatewayHttp}/v1/stop`, { method: "POST" });
  };

  const arm = async () => {
    await fetch(`${gatewayHttp}/v1/arm`, { method: "POST" });
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
        <div className="buttonRow">
          <button onClick={() => void sendPose(-90, 0)}>Look left</button>
          <button onClick={() => void sendPose(0, -45)}>Look up</button>
          <button onClick={() => void sendPose(0, 0)}>Neutral</button>
          <button onClick={() => void sendPose(90, 0)}>Look right</button>
          <button className="arm" onClick={() => void arm()}>Arm motion</button>
          <button className="stop" onClick={() => void stop()}>Emergency stop</button>
        </div>
      </section>
    </main>
  );
}
