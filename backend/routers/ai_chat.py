import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ChatMessage
from ..schemas import ChatPromptRequest, ChatPromptResponse
from ..ai_service import AIDiscountMachineService

router = APIRouter(prefix="/api/ai", tags=["AI Discount Machine"])


@router.post("/chat", response_model=ChatPromptResponse)
def chat_with_discount_ai(payload: ChatPromptRequest, db: Session = Depends(get_db)):
    """
    Process owner's natural language command to create, inspect, or manage discount rules.
    Powered by Gemini API with seamless deterministic fallback parser.
    """
    result = AIDiscountMachineService.process_prompt(
        prompt=payload.message,
        db=db,
        api_key=payload.api_key
    )
    return result


@router.get("/history")
def get_chat_history(db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).order_by(ChatMessage.id.asc()).limit(50).all()
    history = []
    for m in messages:
        structured = None
        if m.structured_action:
            try:
                structured = json.loads(m.structured_action)
            except Exception:
                pass
        history.append({
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "structured_action": structured,
            "created_at": m.created_at.isoformat() if m.created_at else None
        })
    return history

