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
