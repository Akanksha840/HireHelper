from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

from app.db.database import engine, Base
from app.db import models
from app.api.auth.routes import router as auth_router
from app.api.tasks.routes import router as task_router
from app.api.requests.routes import router as requests_router
from app.api.chat.routes import router as chat_router
from app.api.calls.routes import router as calls_router
from app.api.dependencies import get_current_user

app = FastAPI(
    title="HireHelper Backend",
    version="1.0.0"
)

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)

# ✅ Safe column migrations (adds missing columns to existing tables)
# def run_migrations():
#     with engine.connect() as conn:
#         # Add 'bio' column if it doesn't exist
#         try:
#             conn.execute(text("ALTER TABLE users ADD COLUMN bio TEXT"))
#             conn.commit()
#             print("✅ Migration: added 'bio' column to users")
#         except Exception:
#             pass  # Column already exists

#         # Add 'profile_picture' column if it doesn't exist
#         try:
#             conn.execute(text("ALTER TABLE users ADD COLUMN profile_picture TEXT"))
#             conn.commit()
#             print("✅ Migration: added 'profile_picture' column to users")
#         except Exception:
#             pass  # Column already exists

# run_migrations()
def run_migrations():
    with engine.connect() as conn:
        # Define a list of migrations to run: (Table Name, Column Name, Column Type)
        migrations = [
            ("users", "bio", "TEXT"),
            ("users", "profile_picture", "TEXT"),
            ("task_requests", "message", "TEXT"), # <--- Fixes your current error
            ("task_requests", "status", "TEXT"),  # Just in case
        ]

        for table, column, col_type in migrations:
            try:
                # SQLite doesn't have a native 'IF NOT EXISTS' for columns
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                conn.commit()
                print(f"Migration: added '{column}' to '{table}'")
            except Exception:
                # If it fails, the column likely already exists, so we skip silently
                pass

run_migrations()


from fastapi.staticfiles import StaticFiles

# Routers
app.include_router(auth_router)       # /auth/*
app.include_router(task_router, prefix="/api")  # /api/tasks/*
app.include_router(requests_router, prefix="/api")   # /api/requests/*
app.include_router(chat_router, prefix="/api")   # /api/chat/*
app.include_router(calls_router, prefix="/api")   # /api/calls/*

# Mount uploads directory to serve static images
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def root():
    return {"message": "HireHelper backend is running"}

@app.get("/me")
def read_current_user(current_user=Depends(get_current_user)):
    return current_user
