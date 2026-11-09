import asyncio, os, time, uuid
from collections import deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .engine import CounterEngine

engine = None
task = None
clients = set()
alerts = deque(maxlen=250)
metrics = {"running":False,"count":0,"threshold":3,"status":"STOPPED","fps":0,"unique_total":0}

class StartBody(BaseModel):
    source: str = "0"
    threshold: int | None = Field(default=None, ge=0, le=10000)
class ThresholdBody(BaseModel):
    threshold: int = Field(ge=0, le=10000)

async def broadcast(data):
    stale = []
    for ws in list(clients):
        try: await ws.send_json(data)
        except Exception: stale.append(ws)
    for ws in stale: clients.discard(ws)

async def processing_loop():
    global engine
    try:
        while engine:
            current = engine
            payload = await asyncio.to_thread(current.next)
            if payload is None:
                await broadcast({"type":"system","message":"Video ended or no frame received."})
                break
            metrics.update(running=True,count=payload["count"],threshold=payload["threshold"],
                status=payload["status"],fps=payload["fps"],unique_total=payload["unique_total"])
            if payload["new_alert"]:
                alert = {"id":str(uuid.uuid4()),"created_at":time.time(),"severity":"critical",
                    "title":"Crowd threshold exceeded",
                    "message":f'{payload["count"]} people detected (limit: {payload["threshold"]}).',
                    "count":payload["count"],"threshold":payload["threshold"]}
                alerts.appendleft(alert)
                payload["alert"] = alert
            else: payload["alert"] = None
            await broadcast(payload)
            await asyncio.sleep(0)
    except asyncio.CancelledError: raise
    except Exception as exc: await broadcast({"type":"error","message":str(exc)})
    finally:
        if engine: await asyncio.to_thread(engine.close)
        engine = None
        metrics.update(running=False,status="STOPPED")
        await broadcast({"type":"status","running":False,"status":"STOPPED"})

@asynccontextmanager
async def lifespan(app):
    yield
    if task and not task.done():
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass

app = FastAPI(title="Crowd Counter API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS","http://localhost:5173").split(","),
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/api/health")
async def health(): return {"ok":True}
@app.get("/api/status")
async def status(): return metrics
@app.get("/api/alerts")
async def get_alerts(limit:int=100): return list(alerts)[:max(1,min(limit,250))]
@app.post("/api/camera/start")
async def start(body:StartBody):
    global engine, task
    if engine: return {"ok":True,"message":"Already running"}
    try: engine = await asyncio.to_thread(CounterEngine, body.source, body.threshold)
    except Exception as exc: raise HTTPException(400,str(exc))
    metrics.update(running=True,count=0,threshold=engine.alert.threshold,status="NORMAL",fps=0,unique_total=0)
    task = asyncio.create_task(processing_loop())
    return {"ok":True}
@app.post("/api/camera/stop")
async def stop():
    if task and not task.done():
        task.cancel()
        try: await task
        except asyncio.CancelledError: pass
    return {"ok":True}
@app.put("/api/settings/threshold")
async def threshold(body:ThresholdBody):
    if engine: engine.set_threshold(body.threshold)
    metrics["threshold"] = body.threshold
    await broadcast({"type":"settings","threshold":body.threshold})
    return {"ok":True,"threshold":body.threshold}
@app.websocket("/ws/live")
async def websocket_live(ws:WebSocket):
    await ws.accept(); clients.add(ws)
    await ws.send_json({"type":"snapshot","metrics":metrics,"alerts":list(alerts)})
    try:
        while True: await ws.receive_text()
    except WebSocketDisconnect: clients.discard(ws)
