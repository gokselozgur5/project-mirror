import asyncio

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, status

from .gateway import CommandRejected, EmbodimentGateway
from .models import EmbodimentState, Health, PoseTarget

app = FastAPI(title="Project Mirror Embodiment Gateway", version="0.1.0")
gateway = EmbodimentGateway()


@app.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", mode=gateway.state().mode)


@app.get("/v1/state", response_model=EmbodimentState)
def get_state() -> EmbodimentState:
    return gateway.state()


@app.post("/v1/pose", response_model=EmbodimentState)
def set_pose(target: PoseTarget) -> EmbodimentState:
    try:
        return gateway.submit(target)
    except CommandRejected as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@app.post("/v1/stop", response_model=EmbodimentState)
def stop() -> EmbodimentState:
    return gateway.stop()


@app.websocket("/v1/stream")
async def stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(gateway.state().model_dump_json())
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        return
