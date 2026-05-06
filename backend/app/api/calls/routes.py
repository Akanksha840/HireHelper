from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json

from app.db.database import get_db
from app.db.models import Call, Chat, TaskRequest, User
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/calls", tags=["Calls"])

# Schemas
class CallCreate(BaseModel):
    chat_id: str

class CallSignal(BaseModel):
    type: str  # offer, answer, ice-candidate
    data: dict

class CallOut(BaseModel):
    id: str
    chat_id: str
    caller_id: str
    callee_id: str
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]

# WebRTC Signaling Manager
class SignalingManager:
    def __init__(self):
        self.active_calls: dict[str, dict] = {}  # call_id -> {caller_ws, callee_ws}

    async def connect(self, websocket: WebSocket, call_id: str, user_id: str):
        await websocket.accept()
        if call_id not in self.active_calls:
            self.active_calls[call_id] = {}
        self.active_calls[call_id][user_id] = websocket

    def disconnect(self, call_id: str, user_id: str):
        if call_id in self.active_calls and user_id in self.active_calls[call_id]:
            del self.active_calls[call_id][user_id]
            if not self.active_calls[call_id]:
                del self.active_calls[call_id]

    async def send_to_other(self, call_id: str, sender_id: str, message: dict):
        if call_id in self.active_calls:
            for uid, ws in self.active_calls[call_id].items():
                if uid != sender_id:
                    await ws.send_json(message)

signaling_manager = SignalingManager()

# Routes
@router.post("/")
def initiate_call(
    call_data: CallCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if chat exists and user is part of it
    chat = db.query(Chat).filter(Chat.id == call_data.chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    task_request = chat.task_request
    if task_request.requester_id != current_user.id and task_request.task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if task_request.status != "accepted":
        raise HTTPException(status_code=400, detail="Cannot call until request is accepted")

    # Determine callee
    callee_id = task_request.requester_id if current_user.id == task_request.task.user_id else task_request.task.user_id

    # Create call record
    call = Call(
        chat_id=call_data.chat_id,
        caller_id=current_user.id,
        callee_id=callee_id,
        status="pending"
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    return CallOut(
        id=call.id,
        chat_id=call.chat_id,
        caller_id=call.caller_id,
        callee_id=call.callee_id,
        status=call.status,
        started_at=call.started_at,
        ended_at=call.ended_at
    )

@router.put("/{call_id}/status")
def update_call_status(
    call_id: str,
    status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    if call.caller_id != current_user.id and call.callee_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    call.status = status
    if status == "active" and not call.started_at:
        call.started_at = datetime.utcnow()
    elif status == "ended" and not call.ended_at:
        call.ended_at = datetime.utcnow()

    db.commit()
    db.refresh(call)

    return CallOut(
        id=call.id,
        chat_id=call.chat_id,
        caller_id=call.caller_id,
        callee_id=call.callee_id,
        status=call.status,
        started_at=call.started_at,
        ended_at=call.ended_at
    )

@router.websocket("/ws/{call_id}")
async def signaling_websocket(
    websocket: WebSocket,
    call_id: str,
    token: str,
    db: Session = Depends(get_db)
):
    # Verify token and get user
    from app.core.security import verify_token
    payload = verify_token(token)
    if not payload:
        await websocket.close(code=1008)
        return
    
    user_email = payload.get("sub")
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        await websocket.close(code=1008)
        return

    # Check if call exists and user is part of it
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call or (call.caller_id != user.id and call.callee_id != user.id):
        await websocket.close(code=1008)
        return

    await signaling_manager.connect(websocket, call_id, user_id)
    try:
        while True:
            data = await websocket.receive_json()
            # Relay signaling data to the other participant
            await signaling_manager.send_to_other(call_id, user_id, data)
    except WebSocketDisconnect:
        signaling_manager.disconnect(call_id, user_id)