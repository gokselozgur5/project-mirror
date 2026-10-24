# Local detector evaluation

This plan evaluates a face-box detector on Jetson AGX Thor without allowing raw
camera media to cross the detector process boundary. It selects an adapter from
measured evidence; it does not preselect a model or authorize camera use.

## Privacy and consent gate

Before opening a camera:

- Show an unambiguous camera-active indicator in the participant's view.
- Obtain explicit consent and provide an immediate stop control.
- Disable frame, crop, embedding, and debug-image persistence.
- Keep inference local and verify that the process has no cloud destination.
- Use synthetic or redistribution-approved fixtures in Git. Keep consented live
  captures ephemeral and outside the repository.
- Do not perform face recognition, identity tracking, demographic inference, or
  biometric enrollment.

Fail the run if a raw frame, crop, or embedding reaches an HTTP request, log,
trace, crash report, or repository artifact.

## Adapter boundary

The detector owns camera capture, decoding, preprocessing, and inference in one
local process. It may publish only `FrameDetections` to the perception service:

```json
{
  "version": 1,
  "sequence": 42,
  "observed_at_ms": 1000,
  "faces": [
    {"left": 0.25, "top": 0.2, "right": 0.55, "bottom": 0.7, "confidence": 0.9}
  ]
}
```

Coordinates are normalized, at most 32 candidates are allowed, and no identity
or media field exists. The perception service remains responsible for target
selection; the detector must not silently invent participant identity policy.

## Candidate record

Create one record per candidate and version:

```text
candidate and exact version:
source and immutable revision/digest:
model format and exact weights digest:
model/data/code licenses:
JetPack, CUDA, TensorRT, and driver versions:
precision and input dimensions:
camera identity, format, resolution, and frame rate:
pre/post-processing implementation:
warm-up duration:
```

Do not compare candidates across different camera modes, power modes, precision,
input dimensions, or thermal states without labeling the difference.

## Measurements

After a warm-up, measure a five-minute run and retain only numeric results:

- Capture, preprocessing, inference, postprocessing, and publish latency at p50,
  p95, p99, and maximum.
- Camera-to-gateway state age at p50, p95, p99, and maximum.
- Input, processed, published, and dropped frame counts.
- CPU utilization, GPU utilization, RAM, VRAM, temperature, clocks, and power.
- Confidence behavior for no face, partial face, profile, backlight, glasses,
  head covering, near/far distance, and rapid entrance or exit.
- Target stability with zero, one, and multiple consenting participants.
- Recovery after camera disconnect, detector crash, runtime loss, and gateway
  stop; no failure may create a search motion or bypass the gateway.

Use monotonic time for stage latency and wall-clock time only for cross-process
timestamps. Record the sampling method and interval with every metric.

## Deterministic behavior checks

1. No eligible face publishes `face: null`; the gateway expires toward neutral.
2. A face below the confidence threshold cannot become a pose.
3. For a fixed candidate set, selection is stable and deterministic.
4. Candidate ordering alone cannot beat a larger eligible face; exact ties use
   confidence and then original order as documented.
5. More than 32 candidates is rejected rather than truncated silently.
6. Stale, future, duplicate, and out-of-order observations cannot move the
   embodiment gateway.
7. Camera or detector loss becomes visible to the operator and does not retain
   the final participant indefinitely.

## Selection gate

Select a candidate only when all of the following evidence exists:

- The complete five-minute metric record is reproducible from a clean setup.
- Its license permits the intended public repository and eventual distribution.
- Raw-media boundary inspection and network observation are clean.
- No-face and multiple-face behavior satisfy the deterministic checks.
- Thermal or memory growth does not invalidate the five-minute result.
- End-to-end behavior remains bounded by the existing gateway safety layer.

If no candidate passes, record the failure and keep issue 3 open. A fast demo is
not evidence that the privacy, stability, or deployment gate passed.
