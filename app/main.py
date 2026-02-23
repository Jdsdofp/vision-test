"""
PPE Detection API - SmartX Vision
"""

import cv2
import base64
import numpy as np
import os
import sys
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json

# Resolve caminhos absolutos
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

sys.path.insert(0, str(BASE_DIR))
try:
    from app.detector import PPEDetector
except ImportError:
    from detector import PPEDetector

app = FastAPI(title="SmartX PPE Detection API", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

detector = PPEDetector()

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health():
    return {"status": "ok", "model": detector.model_name, "classes": detector.ppe_classes}


@app.post("/detect/image")
async def detect_image(file: UploadFile = File(...)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse(status_code=400, content={"error": "Imagem inválida"})
    result = detector.detect(frame)
    _, buffer = cv2.imencode(".jpg", result["annotated_frame"])
    return {
        "detections": result["detections"],
        "compliance": result["compliance"],
        "missing_ppe": result["missing_ppe"],
        "annotated_image": base64.b64encode(buffer).decode("utf-8")
    }


@app.post("/detect/base64")
async def detect_base64(payload: dict):
    try:
        frame = cv2.imdecode(np.frombuffer(base64.b64decode(payload["image"]), np.uint8), cv2.IMREAD_COLOR)
        result = detector.detect(frame, required_ppe=payload.get("required_ppe"))
        _, buffer = cv2.imencode(".jpg", result["annotated_frame"])
        return {
            "detections": result["detections"],
            "compliance": result["compliance"],
            "missing_ppe": result["missing_ppe"],
            "annotated_image": base64.b64encode(buffer).decode("utf-8")
        }
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})


@app.websocket("/ws/camera")
async def websocket_camera(websocket: WebSocket):
    await websocket.accept()
    print("✅ WebSocket conectado")
    try:
        while True:
            payload = json.loads(await websocket.receive_text())
            frame = cv2.imdecode(np.frombuffer(base64.b64decode(payload["image"]), np.uint8), cv2.IMREAD_COLOR)
            result = detector.detect(frame, required_ppe=payload.get("required_ppe"))
            _, buffer = cv2.imencode(".jpg", result["annotated_frame"], [cv2.IMWRITE_JPEG_QUALITY, 85])
            await websocket.send_text(json.dumps({
                "detections": result["detections"],
                "compliance": result["compliance"],
                "missing_ppe": result["missing_ppe"],
                "annotated_image": base64.b64encode(buffer).decode("utf-8")
            }))
    except WebSocketDisconnect:
        print("❌ WebSocket desconectado")
    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
