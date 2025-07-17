from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from typing import List, Dict, Any
from mavlink_parser import MAVLinkParser
from chat_service import ChatService

app = FastAPI(title="UAV Log Analyzer", version="1.0.0")

# Enable CORS for Vue.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
parser = MAVLinkParser()
chat_service = ChatService()

class ChatMessage(BaseModel):
    message: str
    flight_id: str = None

class ChatResponse(BaseModel):
    response: str
    flight_data: Dict[str, Any] = {}

@app.post("/api/upload")
async def upload_flight_data(file: UploadFile = File(...)):
    """Upload and parse .bin flight data file"""
    try:
        # Save uploaded file
        file_path = f"uploads/{file.filename}"
        os.makedirs("uploads", exist_ok=True)

        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Parse flight data
        flight_data = parser.parse_bin_file(file_path)
        
        # Debug logging
        print(f"Parsed flight data keys: {list(flight_data.keys())}")
        print(f"Telemetry keys: {list(flight_data['telemetry'].keys())}")
        print(f"GPS data length: {len(flight_data['telemetry']['gps'])}")
        print(f"Sample GPS data: {flight_data['telemetry']['gps'][:3] if flight_data['telemetry']['gps'] else 'No GPS data'}")

        # Cache flight data in chat service
        chat_service.cache_flight_data(flight_data["flight_id"], flight_data)

        return {
            "flight_id": flight_data["flight_id"],
            "summary": flight_data["summary"],
            "telemetry": flight_data["telemetry"],
            "message": "Flight data uploaded and parsed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_flight_data(chat_message: ChatMessage):
    """Chat about flight data using LLM"""
    try:
        response = await chat_service.process_message(
            chat_message.message,
            chat_message.flight_id
        )
        return ChatResponse(
            response=response["answer"],
            flight_data=response.get("flight_data")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/flights")
async def get_flights():
    """Get list of uploaded flights"""
    return parser.get_flight_list()

@app.get("/api/flights/{flight_id}")
async def get_flight_details(flight_id: str):
    """Get detailed flight information"""
    try:
        return parser.get_flight_details(flight_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail="Flight not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)