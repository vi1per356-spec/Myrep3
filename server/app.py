"""FastAPI server (run this on Termux).

Endpoints:
  POST /login                 {username,password} -> {token}
  GET  /targets               (Bearer) -> current snapshot
  GET  /route/{id}            (Bearer) -> target + full history
  POST /training/route        (Bearer) multipart image -> stored route
  POST /training/situation    (Bearer) multipart image -> spawned situation
  WS   /ws?token=...          live snapshots
  GET  /icons/{name}.svg|png  red target icons
  GET  /config                map bounds/center for the client
"""

from __future__ import annotations

import asyncio
import os

from fastapi import (Depends, FastAPI, File, Header, HTTPException, UploadFile,
                     WebSocket, WebSocketDisconnect)
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import config
from auth import login as do_login
from auth import verify
from gemini_parser import parse_situation_image
from state import store
from telegram_reader import run_telegram
from training import add_route

app = FastAPI(title="Ukraine Threat Tracker")

ICON_DIR = os.path.join(os.path.dirname(__file__), "icons")


def require_token(authorization: str | None = Header(None)):
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:]
    if not verify(token):
        raise HTTPException(status_code=401, detail="unauthorized")
    return True


@app.post("/login")
async def login(body: dict):
    tok = do_login(body.get("username", ""), body.get("password", ""))
    if not tok:
        raise HTTPException(status_code=401, detail="bad credentials")
    return {"token": tok}


@app.get("/config")
async def get_config():
    return {"bounds": config.UA_BOUNDS, "center": config.UA_CENTER}


@app.get("/targets")
async def targets(_=Depends(require_token)):
    return {"targets": store.snapshot()}


@app.get("/route/{target_id}")
async def route(target_id: str, _=Depends(require_token)):
    r = store.route(target_id)
    if not r:
        raise HTTPException(status_code=404, detail="not found")
    return r


@app.post("/training/route")
async def training_route(file: UploadFile = File(...), _=Depends(require_token)):
    rec = await asyncio.to_thread(add_route, await file.read())
    return JSONResponse(rec)


@app.post("/training/situation")
async def training_situation(file: UploadFile = File(...),
                             _=Depends(require_token)):
    data = await file.read()
    events = await asyncio.to_thread(parse_situation_image, data)
    await store.apply_events(events)
    return {"spawned": len(events), "events": events}


@app.get("/icons/{name}")
async def icon(name: str):
    safe = os.path.basename(name)
    path = os.path.join(ICON_DIR, safe)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="no icon")
    return FileResponse(path)


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not verify(token):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    q = store.subscribe()
    try:
        await websocket.send_json({"type": "snapshot",
                                   "targets": store.snapshot()})
        while True:
            msg = await q.get()
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        pass
    finally:
        store.unsubscribe(q)


@app.on_event("startup")
async def _startup():
    asyncio.create_task(store.run(config.SIM_TICK))
    asyncio.create_task(run_telegram())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.HOST, port=config.PORT)
