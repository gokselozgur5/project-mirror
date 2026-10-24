import { describe, expect, it } from "vitest";

import { controlHeaders, initialState, isEmbodimentState } from "./gateway";

describe("gateway state validation", () => {
  it("accepts the complete versioned state", () => {
    expect(isEmbodimentState(initialState)).toBe(true);
  });

  it.each([
    { ...initialState, version: 2 },
    { ...initialState, sequence: 0.5 },
    { ...initialState, sequence: 4_294_967_296 },
    { ...initialState, yaw_deg: Number.NaN },
    { ...initialState, yaw_deg: 55.1 },
    { ...initialState, pitch_deg: -25.1 },
    { ...initialState, mode: "moving" },
    { ...initialState, reason: undefined },
  ])("rejects an invalid state", (state) => {
    expect(isEmbodimentState(state)).toBe(false);
  });
});

describe("control authorization", () => {
  it("keeps simulation requests token-free", () => {
    expect(controlHeaders("", true)).toEqual({ "content-type": "application/json" });
  });

  it("adds an in-memory bearer token for physical control", () => {
    expect(controlHeaders("session-token", false)).toEqual({
      authorization: "Bearer session-token",
    });
  });
});
