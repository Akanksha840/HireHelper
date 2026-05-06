from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .database import Base


# -------------------------
# USERS
# -------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone_number = Column(String)
    password = Column(String, nullable=False)
    profile_picture = Column(String)
    bio = Column(String, nullable=True)


# -------------------------
# OTP VERIFICATIONS 
# -------------------------
class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, nullable=False, index=True)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    password = Column(String, nullable=False)

    otp = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)


# -------------------------
# -------------------------
# TASKS
# -------------------------
class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    location = Column(String, nullable=False)

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)

    image_url = Column(String, nullable=True)

    status = Column(String, default="open")

    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")

class TaskRequest(Base):
    __tablename__ = "task_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id"))
    requester_id = Column(String, ForeignKey("users.id"))
    message = Column(String, nullable=True)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task")
    requester = relationship("User", foreign_keys=[requester_id])


# ------------------------- 
# CHAT SYSTEM
# -------------------------
class Chat(Base):
    __tablename__ = "chats"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_request_id = Column(String, ForeignKey("task_requests.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task_request = relationship("TaskRequest")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    sender_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat")
    sender = relationship("User")


class Call(Base):
    __tablename__ = "calls"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    chat_id = Column(String, ForeignKey("chats.id"), nullable=False)
    caller_id = Column(String, ForeignKey("users.id"), nullable=False)
    callee_id = Column(String, ForeignKey("users.id"), nullable=False)

    status = Column(String, default="pending")
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)

    chat = relationship("Chat")

    caller = relationship("User", foreign_keys=[caller_id])
    callee = relationship("User", foreign_keys=[callee_id])