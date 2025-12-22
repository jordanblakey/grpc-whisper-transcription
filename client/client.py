import os
import logging
from typing import Annotated

import grpc
from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from protos import transcription_pb2, transcription_pb2_grpc

app = FastAPI()
app.mount("/static", StaticFiles(directory="client/static"), name="static")
templates = Jinja2Templates(directory="client/templates")


# Configure gRPC connection
target = os.environ.get("SERVER_ADDRESS", "server:50051")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws/audio")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    async with grpc.aio.insecure_channel(target) as channel:
        stub = transcription_pb2_grpc.WhisperTranscriberStub(channel)
        
        async def request_generator():
            try:
                # First message should be a JSON with sample_rate
                msg = await websocket.receive_text()
                import json
                try:
                    init_data = json.loads(msg)
                    sample_rate = init_data.get("sample_rate", 16000)
                except:
                    sample_rate = 16000
                
                logging.info(f"WebSocket input sample rate: {sample_rate}")
                
                while True:
                    data = await websocket.receive_bytes()
                    yield transcription_pb2.AudioChunk(data=data, sample_rate=int(sample_rate))
            except WebSocketDisconnect:
                pass
            except Exception as e:
                logging.error(f"WebSocket error: {e}")

        try:
            responses = stub.StreamTranscription(request_generator())
            async for response in responses:
                await websocket.send_json({
                    "text": response.text,
                    "is_final": response.is_final,
                    "start_time": response.start_time
                })
        except (WebSocketDisconnect, RuntimeError):
            # Connection already closed or being closed
            pass
        except grpc.RpcError as e:
            logging.error(f"gRPC error: {e}")
        except Exception as e:
            logging.error(f"Bridge error: {e}")
        finally:
            try:
                # Only close if it's still open (though Starlette usually handles this)
                # This is a bit redundant but helps with the 'after sending websocket.close' error
                if websocket.client_state.name == "CONNECTED":
                    await websocket.close()
            except:
                pass

@app.get("/recorder", response_class=HTMLResponse)
async def read_recorder(request: Request):
    return templates.TemplateResponse("recorder.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
