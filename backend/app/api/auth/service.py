import os
import random
import smtplib
import uuid
from email.message import EmailMessage
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from app.db.models import User, OTPVerification
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
)

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")


# -------------------------
# SIGNUP
# -------------------------
def create_user(db: Session, user_data):
    hashed_password = hash_password(user_data.password)

    user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        phone_number=user_data.phone_number,
        password=hashed_password,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# -------------------------
# LOGIN
# -------------------------
def authenticate_user(db: Session, email: str, password: str):
    user = db.query(User).filter(User.email == email).first()

    if not user:
        return None

    if not verify_password(password, user.password):
        return None

    token = create_access_token({"sub": user.email})

    return {
        "access_token": token,
        "token_type": "bearer",
    }


# -------------------------
# REQUEST OTP
# -------------------------
def send_otp_email(db: Session, payload) -> bool:
    if not EMAIL_USER or not EMAIL_PASS:
        print("❌ EMAIL_USER / EMAIL_PASS missing in .env")
        return False

    otp = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    # ✅ Remove old OTPs for this email
    db.query(OTPVerification).filter(
        OTPVerification.email == payload.email
    ).delete()

    # ✅ Insert into otp_verifications table
    otp_entry = OTPVerification(
        id=str(uuid.uuid4()),
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone_number=payload.phone_number,
        password=payload.password, 
        otp=otp,
        expires_at=expires_at,
    )

    db.add(otp_entry)
    db.commit()

    try:
        msg = EmailMessage()
        msg["Subject"] = "HireHelper OTP Verification"
        msg["From"] = EMAIL_USER
        msg["To"] = payload.email
        msg.set_content(
            f"""
Hello {payload.first_name},

Your OTP is: {otp}

This OTP is valid for 5 minutes.
Do not share it with anyone.

– HireHelper Team
"""
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print("OTP stored in otp_verifications & email sent")
        return True

    except Exception as e:
        print(f"Failed to send OTP email: {e}")
        return False


# -------------------------
# VERIFY OTP
# -------------------------
def verify_otp(db: Session, email: str, otp: str) -> bool:
    # Find the OTP record
    record = db.query(OTPVerification).filter(
        OTPVerification.email == email,
        OTPVerification.otp == otp
    ).first()

    if not record:
        return False

    # Check expiration
    if datetime.utcnow() > record.expires_at:
        return False

    return True


# -------------------------
# PASSWORD RESET FLOW
# -------------------------
def send_password_reset_otp(db: Session, email: str) -> bool:
    if not EMAIL_USER or not EMAIL_PASS:
        print("❌ EMAIL_USER / EMAIL_PASS missing in .env")
        return False

    # Check if user exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False

    otp = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    # Remove old OTPs
    db.query(OTPVerification).filter(
        OTPVerification.email == email
    ).delete()

    # Create OTP record
    otp_entry = OTPVerification(
        id=str(uuid.uuid4()),
        email=email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
        password="RESET_FLOW",
        otp=otp,
        expires_at=expires_at,
    )

    db.add(otp_entry)
    db.commit()

    try:
        msg = EmailMessage()
        msg["Subject"] = "HireHelper Password Reset OTP"
        msg["From"] = EMAIL_USER
        msg["To"] = email
        msg.set_content(
            f"""
Hello {user.first_name},

You requested to reset your password.
Your OTP is: {otp}

This OTP is valid for 5 minutes.
If you did not request this, please ignore this email.

– HireHelper Team
"""
        )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print("Password Reset OTP sent")
        return True

    except Exception as e:
        print(f"Failed to send Password Reset email: {e}")
        return False


def reset_password(db: Session, email: str, otp: str, new_password: str):
    # Verify OTP
    record = db.query(OTPVerification).filter(
        OTPVerification.email == email,
        OTPVerification.otp == otp
    ).first()

    if not record:
        return {"error": "Invalid OTP"}

    if datetime.utcnow() > record.expires_at:
        return {"error": "OTP expired"}

    # Update User Password
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"error": "User not found"}

    user.password = hash_password(new_password)
    db.commit()

    # Delete used OTP
    db.delete(record)
    db.commit()

    return {"message": "Password reset successfully"}
