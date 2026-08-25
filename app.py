import uuid

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agents import ask_agent
from websocket import manager, reset_active_connection, set_active_connection

app = FastAPI(title="Andromeda Backend")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

#websocket to call the agent and get the response
@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await manager.connect(websocket)
    connection_token = set_active_connection(websocket)
    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") != "message":
                continue
            response = await ask_agent(
                thread_id,
                message.get("content", ""),
                message.get("model_name", "deepseek/deepseek-v4-flash"),
                message.get("system_prompt"),
            )
            await manager.send(websocket, {"type": "response", "content": response})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        reset_active_connection(connection_token)

@app.get("/generate_thread_id")
def generate_UUID_thread_id(response: Response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    return {"thread_id": str(uuid.uuid4())}


@app.get("/health")
@app.head("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)
