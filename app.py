import uuid

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from graph import run_pipeline
from websocket import manager, reset_active_connection, set_active_connection

app = FastAPI(title="Research Agent Backend")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def index():
    return FileResponse("frontend/index.html")


#websocket to call the agent and get the response
@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    await manager.connect(websocket)
    connection_token = set_active_connection(websocket)

    async def ask_user(question: str) -> str:
        # Send the agent's question to the frontend and wait for the reply
        await manager.send(websocket, {"type": "agent_question", "content": question})
        reply = await websocket.receive_json()
        return reply.get("content", "")

    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") != "message":
                continue

            query = message.get("content", "")
            await manager.send(websocket, {"type": "status", "content": "Researching..."})

            answer = await run_pipeline(query, thread_id, ask_user)

            await manager.send(websocket, {"type": "response", "content": answer})
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
