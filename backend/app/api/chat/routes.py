from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

from app.db.database import get_db
from app.db.models import Chat, Message, TaskRequest, User
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/chat", tags=["Chat"])

# Schemas
class MessageCreate(BaseModel):
    content: str

class MessageOut(BaseModel):
    id: str
    sender_id: str
    content: str
    timestamp: datetime
    sender_name: str

class ChatOut(BaseModel):
    id: str
    task_request_id: str
    messages: List[MessageOut]

# WebSocket manager for real-time chat
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, chat_id: str, user_id: str):
        await websocket.accept()
        key = f"{chat_id}:{user_id}"
        self.active_connections[key] = websocket

    def disconnect(self, chat_id: str, user_id: str):
        key = f"{chat_id}:{user_id}"
        if key in self.active_connections:
            del self.active_connections[key]

    async def send_personal_message(self, message: str, chat_id: str, user_id: str):
        key = f"{chat_id}:{user_id}"
        if key in self.active_connections:
            await self.active_connections[key].send_text(message)

    async def broadcast(self, message: str, chat_id: str, exclude_user: str = None):
        for key, connection in self.active_connections.items():
            if key.startswith(f"{chat_id}:") and (exclude_user is None or not key.endswith(exclude_user)):
                await connection.send_text(message)

manager = ConnectionManager()

# Routes
@router.get("/{task_request_id}")
def get_chat(
    task_request_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if user is part of the task request
    task_request = db.query(TaskRequest).filter(TaskRequest.id == task_request_id).first()
    if not task_request:
        raise HTTPException(status_code=404, detail="Task request not found")
    
    if task_request.requester_id != current_user.id and task_request.task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if task_request.status != "accepted":
        raise HTTPException(status_code=400, detail="Chat not available until request is accepted")

    # Get or create chat
    chat = db.query(Chat).filter(Chat.task_request_id == task_request_id).first()
    if not chat:
        chat = Chat(task_request_id=task_request_id)
        db.add(chat)
        db.commit()
        db.refresh(chat)

    # Get messages
    messages = db.query(Message).filter(Message.chat_id == chat.id).order_by(Message.timestamp).all()
    message_outs = []
    for msg in messages:
        message_outs.append(MessageOut(
            id=msg.id,
            sender_id=msg.sender_id,
            content=msg.content,
            timestamp=msg.timestamp,
            sender_name=f"{msg.sender.first_name} {msg.sender.last_name}"
        ))

    return ChatOut(id=chat.id, task_request_id=task_request_id, messages=message_outs)

@router.post("/{task_request_id}/messages")
def send_message(
    task_request_id: str,
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Check if user is part of the task request
    task_request = db.query(TaskRequest).filter(TaskRequest.id == task_request_id).first()
    if not task_request:
        raise HTTPException(status_code=404, detail="Task request not found")
    
    if task_request.requester_id != current_user.id and task_request.task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if task_request.status != "accepted":
        raise HTTPException(status_code=400, detail="Cannot send messages until request is accepted")

    # Get or create chat
    chat = db.query(Chat).filter(Chat.task_request_id == task_request_id).first()
    if not chat:
        chat = Chat(task_request_id=task_request_id)
        db.add(chat)
        db.commit()
        db.refresh(chat)

    # Create message
    new_message = Message(
        chat_id=chat.id,
        sender_id=current_user.id,
        content=message.content
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    # Broadcast to other user
    other_user_id = task_request.requester_id if current_user.id == task_request.task.user_id else task_request.task.user_id
    message_data = {
        "id": new_message.id,
        "sender_id": new_message.sender_id,
        "content": new_message.content,
        "timestamp": new_message.timestamp.isoformat(),
        "sender_name": f"{current_user.first_name} {current_user.last_name}"
    }
    # Note: Broadcasting would be handled via WebSocket, but for now, we can return the message

    return MessageOut(
        id=new_message.id,
        sender_id=new_message.sender_id,
        content=new_message.content,
        timestamp=new_message.timestamp,
        sender_name=f"{current_user.first_name} {current_user.last_name}"
    )

@router.websocket("/ws/{task_request_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    task_request_id: str,
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

    # Check if user is part of the task request
    task_request = db.query(TaskRequest).filter(TaskRequest.id == task_request_id).first()
    if not task_request or task_request.status != "accepted":
        await websocket.close(code=1008)
        return

    if task_request.requester_id != user.id and task_request.task.user_id != user.id:
        await websocket.close(code=1008)
        return

    # Get or create chat
    chat = db.query(Chat).filter(Chat.task_request_id == task_request_id).first()
    if not chat:
        chat = Chat(task_request_id=task_request_id)
        db.add(chat)
        db.commit()
        db.refresh(chat)

    await manager.connect(websocket, chat.id, user.id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            content = message_data.get("content")

            # Save message to DB
            new_message = Message(
                chat_id=chat.id,
                sender_id=user.id,
                content=content
            )
            db.add(new_message)
            db.commit()
            db.refresh(new_message)

            # Broadcast to other user
            other_user_id = task_request.requester_id if user.id == task_request.task.user_id else task_request.task.user_id
            broadcast_data = {
                "id": new_message.id,
                "sender_id": new_message.sender_id,
                "content": new_message.content,
                "timestamp": new_message.timestamp.isoformat(),
                "sender_name": f"{user.first_name} {user.last_name}"
            }
            await manager.broadcast(json.dumps(broadcast_data), chat.id, exclude_user=user.id)
    except WebSocketDisconnect:
        manager.disconnect(chat.id, user.id)