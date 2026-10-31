from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
import json

app = FastAPI()
templates = Jinja2Templates(directory="templates")

class ChannelManager:
    def __init__(self):
        self.channels: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        if channel not in self.channels:
            self.channels[channel] = []
        self.channels[channel].append(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self.channels:
            if websocket in self.channels[channel]:
                self.channels[channel].remove(websocket)
            if not self.channels[channel]:
                del self.channels[channel]

    async def broadcast(self, channel: str, message: str, sender: WebSocket = None):
        if channel in self.channels:
            for connection in self.channels[channel]:
                if connection != sender:
                    try:
                        await connection.send_text(message)
                    except Exception:
                        pass

manager = ChannelManager()

@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/{channel}/{username}")
async def websocket_endpoint(websocket: WebSocket, channel: str, username: str):
    await manager.connect(websocket, channel)
    await manager.broadcast(channel, json.dumps({"type": "status", "username": username, "status": "online"}), websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            if message_data.get("type") == "location" or message_data.get("type") == "audio":
                await manager.broadcast(channel, data, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, channel)
        disconnect_msg = json.dumps({"type": "status", "username": username, "status": "offline"})
        await manager.broadcast(channel, disconnect_msg, websocket)