import os
import re
import json
import uuid

from fastapi import FastAPI, Response, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from graph import run_pipeline
from vector_DB import upsert_file_func
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


SUPPORTED_EXTS = (".pdf", ".txt", ".md", ".docx", ".csv", ".xlsx", ".json")
UPLOAD_ROOT = "./uploads"


def _safe_name(name: str) -> str:
    """Sanitize a username/filename so it's safe to use as a folder name / session id."""
    name = os.path.basename(name)
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", name).strip("_")
    return name or "user"


@app.post("/setup")
async def setup(username: str = Form(...), files: list[UploadFile] = File(default=[])):
    async def stream():
        user = _safe_name(username)
        user_dir = os.path.join(UPLOAD_ROOT, user)
        os.makedirs(user_dir, exist_ok=True)

        saved_paths = []
        for f in files:
            fname = _safe_name(f.filename or "")
            if not fname.lower().endswith(SUPPORTED_EXTS):
                yield json.dumps({"stage": "save", "file": f.filename,
                                  "message": f"skipped unsupported file type"}) + "\n"
                continue
            path = os.path.join(user_dir, fname)
            with open(path, "wb") as out:
                out.write(await f.read())
            saved_paths.append((f.filename, path))

        total = len(saved_paths)
        yield json.dumps({"stage": "index", "current": 0, "total": total,
                          "message": f"{total} file(s) saved, starting indexing..."}) + "\n"

        for i, (orig, path) in enumerate(saved_paths, start=1):
            try:
                count = upsert_file_func(path, user)  # username doubles as session_id
                msg = f"Indexed {orig} ({count} chunks)"
            except Exception as e:
                msg = f"Failed to index {orig}: {e}"
            yield json.dumps({"stage": "index", "current": i, "total": total,
                              "file": orig, "message": msg}) + "\n"

        yield json.dumps({"stage": "done", "session_id": user}) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.get("/health")
@app.head("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)
