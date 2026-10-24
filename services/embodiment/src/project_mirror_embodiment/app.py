import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware

from .gateway import CommandRejected, EmbodimentGateway
from .models import EmbodimentState, GatewayMetrics, Health, PoseTarget
from .serial_device import SerialDevice
from .serial_transport import HeadControllerTransport, SerialTransportError


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    device: SerialDevice | None = None
    port = os.getenv("MIRROR_SERIAL_PORT")
    if port:
        device = SerialDevice(port)
        application.state.controller = HeadControllerTransport(device)
    try:
        yield
    finally:
        application.state.controller = None
        if device is not None:
            device.close()


app = FastAPI(title="Project Mirror Embodiment Gateway", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("MIRROR_OPERATOR_ORIGIN", "http://127.0.0.1:5173")],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type"],
)
gateway = EmbodimentGateway()
app.state.controller = None


def controller() -> HeadControllerTransport | None:
    configured: HeadControllerTransport | None = app.state.controller
    return configured


def fail_closed_after_transport_error(error: SerialTransportError) -> None:
    gateway.stop(reason="controller_write_failure")
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="head controller write failed; gateway stop is latched",
    ) from error


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(
        status="ok",
        mode=gateway.state().mode,
        controller="serial" if controller() is not None else "simulated",
    )


@app.get("/v1/state", response_model=EmbodimentState)
def get_state() -> EmbodimentState:
    return gateway.state()


@app.get("/v1/metrics", response_model=GatewayMetrics)
def get_metrics() -> GatewayMetrics:
    return gateway.metrics()


@app.post("/v1/pose", response_model=EmbodimentState)
def set_pose(target: PoseTarget) -> EmbodimentState:
    try:
        state = gateway.submit(target)
    except CommandRejected as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    configured = controller()
    if configured is not None:
        try:
            configured.publish_pose(state)
        except SerialTransportError as error:
            fail_closed_after_transport_error(error)
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


@app.post("/v1/arm", response_model=EmbodimentState)
def arm() -> EmbodimentState:
    configured = controller()
    if configured is not None:
        try:
            configured.publish_control("arm")
        except SerialTransportError as error:
            fail_closed_after_transport_error(error)
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
