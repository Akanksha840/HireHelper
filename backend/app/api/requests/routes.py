from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.db.models import TaskRequest, Task, User
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/requests", tags=["Requests"])


# ── Schemas ──────────────────────────────────────────────────────────────────

class RequestCreate(BaseModel):
    task_id: str
    message: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str   # "accepted" | "rejected"


class RequestOut(BaseModel):
    id: str
    task_id: str
    requester_id: str
    message: Optional[str]
    status: str
    created_at: datetime

    # enriched fields
    task_title: Optional[str] = None
    task_location: Optional[str] = None
    sender_name: Optional[str] = None
    owner_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Helper ────────────────────────────────────────────────────────────────────

def _enrich_incoming(req: TaskRequest, db: Session) -> dict:
    task = db.query(Task).filter(Task.id == req.task_id).first()
    sender = db.query(User).filter(User.id == req.requester_id).first()
    return {
        "id": req.id,
        "task_id": req.task_id,
        "requester_id": req.requester_id,
        "message": req.message,
        "status": req.status,
        "created_at": req.created_at,
        "task_title": task.title if task else None,
        "task_location": task.location if task else None,
        "sender_name": f"{sender.first_name} {sender.last_name}" if sender else None,
    }


def _enrich_outgoing(req: TaskRequest, db: Session) -> dict:
    task = db.query(Task).filter(Task.id == req.task_id).first()
    owner = db.query(User).filter(User.id == task.user_id).first() if task else None
    return {
        "id": req.id,
        "task_id": req.task_id,
        "requester_id": req.requester_id,
        "message": req.message,
        "status": req.status,
        "created_at": req.created_at,
        "task_title": task.title if task else None,
        "task_location": task.location if task else None,
        "owner_name": f"{owner.first_name} {owner.last_name}" if owner else None,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
def create_request(
    body: RequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a request to help with a task."""
    task = db.query(Task).filter(Task.id == body.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot request your own task")

    existing = db.query(TaskRequest).filter(
        TaskRequest.task_id == body.task_id,
        TaskRequest.requester_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already requested this task")

    req = TaskRequest(
        task_id=body.task_id,
        requester_id=current_user.id,
        message=body.message,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return {"message": "Request sent successfully", "id": req.id}


@router.get("/incoming")
def get_incoming_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Requests sent to tasks owned by the current user."""
    my_task_ids = [t.id for t in db.query(Task).filter(Task.user_id == current_user.id).all()]
    reqs = db.query(TaskRequest).filter(TaskRequest.task_id.in_(my_task_ids)).all()
    return [_enrich_incoming(r, db) for r in reqs]


@router.get("/my")
def get_my_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Requests sent by the current user."""
    reqs = db.query(TaskRequest).filter(TaskRequest.requester_id == current_user.id).all()
    return [_enrich_outgoing(r, db) for r in reqs]


@router.patch("/{request_id}/status")
def update_request_status(
    request_id: str,
    body: StatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Accept or reject an incoming request (only task owner can do this)."""
    if body.status not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="status must be 'accepted' or 'rejected'")

    req = db.query(TaskRequest).filter(TaskRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    task = db.query(Task).filter(Task.id == req.task_id).first()
    if not task or task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this request")

    req.status = body.status
    db.commit()
    db.refresh(req)
    return {"message": f"Request {body.status}", "id": req.id, "status": req.status}
