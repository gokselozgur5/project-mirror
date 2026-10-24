export type MotionMode = "tracking" | "neutral" | "stopped";

export type EmbodimentState = {
  version: 1;
  sequence: number;
  updated_at_ms: number;
  yaw_deg: number;
  pitch_deg: number;
  mode: MotionMode;
  reason: string | null;
};

export type ControllerStatus = {
  configured: boolean;
  link_state: "simulated" | "awaiting_telemetry" | "online" | "invalid_telemetry" | "stale";
  last_sequence: number | null;
  last_mode: MotionMode | null;
  last_reason: string | null;
  outputs_armed: boolean | null;
  last_received_at_ms: number | null;
  invalid_frames: number;
};

export const initialState: EmbodimentState = {
  version: 1,
  sequence: 0,
  updated_at_ms: 0,
  yaw_deg: 0,
  pitch_deg: 0,
  mode: "neutral",
  reason: "not_connected",
};

export function isEmbodimentState(value: unknown): value is EmbodimentState {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    candidate.version === 1 &&
    Number.isSafeInteger(candidate.sequence) &&
    Number(candidate.sequence) >= 0 &&
    Number(candidate.sequence) <= 4_294_967_295 &&
    typeof candidate.updated_at_ms === "number" &&
    Number.isFinite(candidate.updated_at_ms) &&
    typeof candidate.yaw_deg === "number" &&
    Number.isFinite(candidate.yaw_deg) &&
    candidate.yaw_deg >= -55 &&
    candidate.yaw_deg <= 55 &&
    typeof candidate.pitch_deg === "number" &&
    Number.isFinite(candidate.pitch_deg) &&
    candidate.pitch_deg >= -25 &&
    candidate.pitch_deg <= 25 &&
    (candidate.mode === "tracking" ||
      candidate.mode === "neutral" ||
      candidate.mode === "stopped") &&
    (typeof candidate.reason === "string" || candidate.reason === null)
  );
}

export function controlHeaders(token: string, includeContentType: boolean) {
  const headers: Record<string, string> = {};
  if (includeContentType) headers["content-type"] = "application/json";
  if (token) headers.authorization = `Bearer ${token}`;
  return headers;
}

export function isControllerStatus(value: unknown): value is ControllerStatus {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.configured === "boolean" &&
    (candidate.link_state === "simulated" ||
      candidate.link_state === "awaiting_telemetry" ||
      candidate.link_state === "online" ||
      candidate.link_state === "invalid_telemetry" ||
      candidate.link_state === "stale") &&
    (candidate.last_sequence === null ||
      (Number.isSafeInteger(candidate.last_sequence) &&
        Number(candidate.last_sequence) >= 0 &&
        Number(candidate.last_sequence) <= 4_294_967_295)) &&
    (candidate.last_mode === null ||
      candidate.last_mode === "tracking" ||
      candidate.last_mode === "neutral" ||
      candidate.last_mode === "stopped") &&
    (candidate.last_reason === null || typeof candidate.last_reason === "string") &&
    (candidate.outputs_armed === null || typeof candidate.outputs_armed === "boolean") &&
    (candidate.last_received_at_ms === null ||
      (Number.isSafeInteger(candidate.last_received_at_ms) &&
        Number(candidate.last_received_at_ms) >= 0)) &&
    Number.isSafeInteger(candidate.invalid_frames) &&
    Number(candidate.invalid_frames) >= 0
  );
}
