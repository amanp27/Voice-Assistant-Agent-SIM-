"""
FastAPI application with WebSocket for real-time voice communication
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import os
import base64
import asyncio
from backend import VoiceAssistantBackend
import uvicorn

app = FastAPI(title="Voice Assistant API")

# Store active sessions
sessions = {}

# Load HTML content
with open("templates/index.html", "r") as f:
    html_content = f.read()


@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the main page"""
    return html_content


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await websocket.accept()
    
    # Create session
    session_id = id(websocket)
    backend = VoiceAssistantBackend()
    sessions[session_id] = backend
    print(f"Client connected: {session_id}")
    
    # Send connection confirmation
    await websocket.send_json({
        "type": "connected",
        "session_id": str(session_id)
    })

    # --- SEND GREETING IMMEDIATELY ---
    try:
        welcome_audio = backend.get_welcome_audio()
        audio_base64 = base64.b64encode(welcome_audio).decode('utf-8')
        
        await websocket.send_json({
            "type": "assistant_response",
            "text": "Hello! How may I help you today?",
            "audio": audio_base64,
            "is_welcome": True
        })
    except Exception as e:
        print(f"Error sending welcome message: {e}")

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "user_audio":
                try:
                    # Decode audio from base64
                    audio_data = base64.b64decode(data['audio'])
                    
                    # Process through pipeline: STT -> LLM -> TTS
                    text_response, audio_response = backend.process_user_audio(audio_data)
                    
                    if text_response and audio_response:
                        # Send assistant response
                        audio_base64 = base64.b64encode(audio_response).decode('utf-8')
                        await websocket.send_json({
                            "type": "assistant_response",
                            "text": text_response,
                            "audio": audio_base64
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Failed to process audio"
                        })
                
                except Exception as e:
                    print(f"Error processing audio: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
            
            elif message_type == "end_conversation":
                # Save conversation
                filename = backend.save_conversation()
                await websocket.send_json({
                    "type": "conversation_saved",
                    "filename": filename
                })
                print(f"Conversation ended and saved: {filename}")
    
    except WebSocketDisconnect:
        # Clean up on disconnect
        if session_id in sessions:
            filename = sessions[session_id].save_conversation()
            print(f"Client disconnected: {session_id}, conversation saved to {filename}")
            del sessions[session_id]
    
    except Exception as e:
        print(f"WebSocket error: {e}")
        if session_id in sessions:
            del sessions[session_id]


if __name__ == '__main__':
    # Run the app with uvicorn
    uvicorn.run(
        app, 
        host='127.0.0.1',  # Use 127.0.0.1 for mic access in browsers
        port=8000,
        log_level='info'
    )
