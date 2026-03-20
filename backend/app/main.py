"""
EDI Dashboard — FastAPI Backend
Routes: /api/upload, /api/fix, /api/chat
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from .sniffer import detect_edi_type
from .parser import parse_edi
from .chat import get_explanation
from .translator import generate_english_summary


app = FastAPI(
    title="EDI Dashboard API",
    description="HIPAA EDI File Parser, Validator & AI Assistant",
    version="1.0.0",
)

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173",
        "http://localhost:5174", 
        "http://127.0.0.1:5174",
        "http://localhost:5175", 
        "http://127.0.0.1:5175",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for the most recently parsed data (for fix/chat endpoints)
_current_data = {"raw": None, "edi_type": None, "result": None}


# ─── Models ────────────────────────────────────────────────────────────────────

class FixRequest(BaseModel):
    path: str
    field: str
    value: str

class ChatRequest(BaseModel):
    question: str
    context: Optional[dict] = None


# ─── Upload Endpoint ──────────────────────────────────────────────────────────

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Accept an EDI file (.txt or .edi), detect its type, parse it,
    validate it, and return structured JSON.
    """
    # Validate file extension
    if file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ("txt", "edi"):
            raise HTTPException(status_code=400, detail="Only .txt and .edi files are accepted")
    
    # Read file content
    try:
        content = await file.read()
        raw = content.decode("utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read file: {str(e)}")
    
    if not raw.strip():
        raise HTTPException(status_code=400, detail="File is empty")
    
    # Log first 100 chars to terminal
    print(f"\n{'='*60}")
    print(f"📄 Received file: {file.filename}")
    print(f"📏 Size: {len(raw)} characters")
    print(f"🔍 First 100 chars: {raw[:100]}")
    print(f"{'='*60}\n")
    
    # Detect EDI type
    edi_type = detect_edi_type(raw)
    if edi_type == "unknown":
        raise HTTPException(
            status_code=400,
            detail="Could not detect EDI type. File must contain an ST segment with code 837, 835, or 834."
        )
    
    print(f"✅ Detected EDI type: {edi_type}")
    
    # Parse and validate
    result = parse_edi(raw, edi_type)
    
    print(f"📊 Parsed {result['stats']['total_segments']} segments, {result['stats']['error_count']} errors")
    
    # Store for fix/chat endpoints
    _current_data["raw"] = raw
    _current_data["edi_type"] = edi_type
    _current_data["result"] = result
    
    return result


# ─── Fix Endpoint ─────────────────────────────────────────────────────────────

@app.put("/api/fix")
async def fix_value(req: FixRequest):
    """
    Accept a fix for a specific field, re-parse the data with the fix applied,
    and return the updated result.
    """
    if not _current_data["result"]:
        raise HTTPException(status_code=400, detail="No file has been parsed yet")
    
    # Apply fix to the parsed data in memory
    result = _current_data["result"]
    parsed = result["parsed"]
    
    # Navigate to the segment using the path and update the value
    try:
        _apply_fix(parsed, req.path, req.field, req.value)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not apply fix: {str(e)}")
    
    # Re-count errors after fix
    error_count = _count_errors(parsed)
    result["stats"]["error_count"] = error_count
    result["stats"]["valid_count"] = result["stats"]["total_segments"] - error_count
    
    return result


def _apply_fix(data: dict, path: str, field: str, value: str):
    """Navigate the data structure and apply a fix."""
    parts = path.split(".")
    current = data
    
    for part in parts:
        if part.startswith("[") and part.endswith("]"):
            idx = int(part[1:-1])
            if isinstance(current, list) and idx < len(current):
                current = current[idx]
            else:
                raise ValueError(f"Invalid index: {part}")
        elif isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                raise ValueError(f"Path not found: {part}")
        else:
            raise ValueError(f"Cannot navigate into: {type(current)}")
    
    if isinstance(current, dict):
        current[field] = value
        # Remove the related error
        if "_errors" in current:
            current["_errors"] = [e for e in current["_errors"] if e.get("field") != field]
            if not current["_errors"]:
                del current["_errors"]


def _count_errors(data, count=0):
    """Recursively count all _errors in the data structure."""
    if isinstance(data, dict):
        if "_errors" in data:
            count += len(data["_errors"])
        for v in data.values():
            count = _count_errors(v, count)
    elif isinstance(data, list):
        for item in data:
            count = _count_errors(item, count)
    return count


# ─── Chat Endpoint ────────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """
    Send a question to the AI assistant with optional EDI context.
    Returns a plain-English explanation.
    """
    context = req.context or _current_data.get("result")
    answer = get_explanation(req.question, context)
    return {"answer": answer}


# ─── Translate Endpoint ───────────────────────────────────────────────────────

@app.get("/api/translate")
async def translate_english():
    """
    Convert the parsed JSON tree into a clean English summary.
    """
    if not _current_data.get("result"):
        raise HTTPException(status_code=400, detail="No file has been uploaded.")
    
    result = _current_data["result"]
    parsed = result["parsed"]
    stats = result["stats"]
    
    english_text = generate_english_summary(parsed, stats)
    return {"text": english_text}


# ─── Health Check ─────────────────────────────────────────────────────────────

@app.get("/")
async def health_check():
    return {
        "status": "ok",
        "service": "EDI Dashboard API",
        "version": "1.0.0",
    }
