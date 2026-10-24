import asyncio
import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from time import time_ns
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from .gateway import CommandRejected, EmbodimentGateway
from .models import (
    ControllerLinkState,
    ControllerStatus,
    EmbodimentState,
    GatewayMetrics,
    Health,
    MotionMode,
    PoseTarget,
)
from .serial_device import SerialDevice
from .serial_protocol import SerialProtocolError
from .serial_transport import HeadControllerTransport, SerialTransportError


async def read_controller_telemetry(
    application: FastAPI,
    device: SerialDevice,
    transport: HeadControllerTransport,
) -> None:
    while True:
        frame = await asyncio.to_thread(device.read_frame)
        if not frame:
            mark_controller_telemetry_stale(
                application,
                transport,
                now_ms=time_ns() // 1_000_000,
            )
            continue
        accept_controller_telemetry(application, transport, frame)


def accept_controller_telemetry(
    application: FastAPI,
    transport: HeadControllerTransport,
    frame: bytes,
) -> None:
    previous: ControllerStatus = application.state.controller_status
    try:
        telemetry = transport.accept_telemetry(frame)
    except (SerialProtocolError, SerialTransportError):
        application.state.controller_status = previous.model_copy(
            update={
                "link_state": ControllerLinkState.INVALID_TELEMETRY,
                "outputs_armed": None,
                "invalid_frames": previous.invalid_frames + 1,
            }
        )
        stop_for_controller_fault(transport, reason="invalid_controller_telemetry")
        return
    application.state.controller_status = ControllerStatus(
        version=1,
        configured=True,
        link_state=ControllerLinkState.ONLINE,
        last_sequence=telemetry.seq,
        last_mode=MotionMode(telemetry.mode),
        last_reason=telemetry.reason,
        outputs_armed=telemetry.armed,
        last_received_at_ms=time_ns() // 1_000_000,
        invalid_frames=previous.invalid_frames,
    )


def mark_controller_telemetry_stale(
    application: FastAPI,
    transport: HeadControllerTransport,
    *,
    now_ms: int,
) -> None:
    previous: ControllerStatus = application.state.controller_status
    if (
        previous.link_state is ControllerLinkState.ONLINE
        and previous.last_received_at_ms is not None
        and now_ms > previous.last_received_at_ms + 1_000
    ):
        application.state.controller_status = previous.model_copy(
            update={"link_state": ControllerLinkState.STALE, "outputs_armed": None}
        )
        stop_for_controller_fault(transport, reason="stale_controller_telemetry")


def stop_for_controller_fault(transport: HeadControllerTransport, *, reason: str) -> None:
    if gateway.state().mode is not MotionMode.STOPPED:
        gateway.stop(reason=reason)
    try:
        transport.publish_control("stop")
    except SerialTransportError:
        return


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    device: SerialDevice | None = None
    reader_task: asyncio.Task[None] | None = None
    port = os.getenv("MIRROR_SERIAL_PORT")
    if port:
        if not os.getenv("MIRROR_CONTROL_TOKEN"):
            raise RuntimeError(
                "MIRROR_CONTROL_TOKEN is required when a serial controller is enabled"
            )
        device = SerialDevice(port)
        transport = HeadControllerTransport(device)
        try:
            transport.request_status()
            handshake_frame = device.read_frame()
            if not handshake_frame:
                raise RuntimeError("head controller did not answer the status handshake")
            transport.synchronize(handshake_frame)
            stop_sequence = transport.publish_control("stop")
            stop_frame = device.read_frame()
            if not stop_frame:
                raise RuntimeError("head controller did not acknowledge startup stop")
            handshake = transport.accept_telemetry(stop_frame)
            if (
                handshake.seq != stop_sequence
                or handshake.mode != MotionMode.STOPPED
                or handshake.armed
            ):
                raise RuntimeError("head controller did not enter stopped startup state")
        except RuntimeError:
            device.close()
            raise
        except (SerialProtocolError, SerialTransportError) as error:
            device.close()
            raise RuntimeError("head controller returned an invalid status handshake") from error
        application.state.controller = transport
        application.state.controller_status = ControllerStatus(
            version=1,
            configured=True,
            link_state=ControllerLinkState.ONLINE,
            last_sequence=handshake.seq,
            last_mode=MotionMode(handshake.mode),
            last_reason=handshake.reason,
            outputs_armed=handshake.armed,
            last_received_at_ms=time_ns() // 1_000_000,
        )
        gateway.stop(reason="controller_startup")
        reader_task = asyncio.create_task(read_controller_telemetry(application, device, transport))
    try:
        yield
    finally:
        if reader_task is not None:
            reader_task.cancel()
            with suppress(asyncio.CancelledError):
                await reader_task
        application.state.controller = None
        application.state.controller_status = ControllerStatus(
            version=1,
            configured=False,
            link_state=ControllerLinkState.SIMULATED,
        )
        if device is not None:
            device.close()


app = FastAPI(title="Project Mirror Embodiment Gateway", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("MIRROR_OPERATOR_ORIGIN", "http://127.0.0.1:5173")],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["authorization", "content-type"],
)
gateway = EmbodimentGateway()
app.state.controller = None
app.state.controller_status = ControllerStatus(
    version=1,
    configured=False,
    link_state=ControllerLinkState.SIMULATED,
)


def controller() -> HeadControllerTransport | None:
    configured: HeadControllerTransport | None = app.state.controller
    return configured


def fail_closed_after_transport_error(
    error: SerialTransportError,
    *,
    reason: str = "controller_write_failure",
) -> None:
    gateway.stop(reason=reason)
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="head controller command failed; gateway stop is latched",
    ) from error


def require_control_token(authorization: Annotated[str | None, Header()] = None) -> None:
    expected = os.getenv("MIRROR_CONTROL_TOKEN")
    if not expected:
        return
    scheme, separator, provided = (authorization or "").partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not secrets.compare_digest(
        provided, expected
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="valid control token required",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_controller_online() -> None:
    if controller() is None:
        return
    current: ControllerStatus = app.state.controller_status
    if current.link_state is not ControllerLinkState.ONLINE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="physical controller telemetry is not online",
        )


@app.get("/health", response_model=Health)
def health() -> Health:
    controller_status: ControllerStatus = app.state.controller_status
    return Health(
        status=(
            "ok"
            if controller_status.link_state
            in (ControllerLinkState.SIMULATED, ControllerLinkState.ONLINE)
            else "degraded"
        ),
        mode=gateway.state().mode,
        controller="serial" if controller() is not None else "simulated",
    )


@app.get("/v1/state", response_model=EmbodimentState)
def get_state() -> EmbodimentState:
    return gateway.state()


@app.get("/v1/metrics", response_model=GatewayMetrics)
def get_metrics() -> GatewayMetrics:
    return gateway.metrics()


@app.get("/v1/controller", response_model=ControllerStatus)
def get_controller_status() -> ControllerStatus:
    current: ControllerStatus = app.state.controller_status
    return current


@app.post(
    "/v1/pose",
    response_model=EmbodimentState,
    dependencies=[Depends(require_control_token), Depends(require_controller_online)],
)
def set_pose(target: PoseTarget) -> EmbodimentState:
    try:
        state = gateway.submit(target)
    except CommandRejected as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    configured = controller()
    if configured is not None:
        try:
            sequence = configured.publish_pose(state)
            acknowledgement = configured.wait_for_telemetry(sequence)
            if (
                acknowledgement.mode != MotionMode.TRACKING
                or acknowledgement.reason != "pose"
                or not acknowledgement.armed
                or acknowledgement.yaw_mdeg != round(state.yaw_deg * 1_000)
                or acknowledgement.pitch_mdeg != round(state.pitch_deg * 1_000)
            ):
                raise SerialTransportError("controller returned an invalid pose acknowledgement")
        except SerialTransportError as error:
            with suppress(SerialTransportError):
                configured.publish_control("stop")
            fail_closed_after_transport_error(error, reason="controller_pose_failed")
    return state


@app.post("/v1/stop", response_model=EmbodimentState)
def stop() -> EmbodimentState:
    state = gateway.stop()
    configured = controller()
    if configured is not None:
        try:
            configured.publish_control("stop")
        except SerialTransportError as error:
            fail_closed_after_transport_error(error)
    return state


@app.post(
    "/v1/arm",
    response_model=EmbodimentState,
    dependencies=[Depends(require_control_token), Depends(require_controller_online)],
)
def arm() -> EmbodimentState:
    configured = controller()
    if configured is not None:
        try:
            sequence = configured.publish_control("arm")
            acknowledgement = configured.wait_for_telemetry(sequence)
            if (
                acknowledgement.mode != MotionMode.NEUTRAL
                or acknowledgement.reason != "operator_arm"
                or acknowledgement.armed
            ):
                raise SerialTransportError("controller returned an invalid arm acknowledgement")
        except SerialTransportError as error:
            with suppress(SerialTransportError):
                configured.publish_control("stop")
            fail_closed_after_transport_error(error, reason="controller_arm_failed")
    return gateway.arm()


@app.websocket("/v1/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(gateway.state().model_dump_json())
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        return
