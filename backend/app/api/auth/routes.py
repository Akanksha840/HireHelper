from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.db.database import get_db
from app.db.models import User
from .schemas import (
    UserCreate, UserLogin, RequestOTP, VerifyOTP,
    ForgotPasswordRequest, ResetPassword,
    UpdateProfileRequest, ChangePasswordRequest
)
from .service import create_user, authenticate_user, send_otp_email, verify_otp, send_password_reset_otp, reset_password
from app.api.dependencies import get_current_user
from app.core.security import verify_password, hash_password
from app.core.file_upload import save_image
from pydantic import BaseModel
import cloudinary
import cloudinary.uploader
import os

# Configure Cloudinary from environment variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/token")
def login_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    result = authenticate_user(db, form_data.username, form_data.password)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return result

# -------------------------
# REQUEST OTP
# -------------------------
@router.post("/request-otp")
def request_otp(payload: RequestOTP, db: Session = Depends(get_db)):
    success = send_otp_email(db, payload)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to send OTP")

    return {"message": "OTP sent successfully"}


# -------------------------
# VERIFY OTP
# -------------------------
@router.post("/verify-otp")
def verify_otp_endpoint(payload: VerifyOTP, db: Session = Depends(get_db)):
    is_valid = verify_otp(db, payload.email, payload.otp)

    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid OTP or expired")

    return {"message": "OTP verified successfully"}


# -------------------------
# SIGNUP
# -------------------------
@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user)


# -------------------------
# LOGIN
# -------------------------
@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    result = authenticate_user(db, user.email, user.password)

    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return result


# -------------------------
# PASSWORD RESET
# -------------------------
@router.post("/request-password-reset")
def request_password_reset(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    success = send_password_reset_otp(db, payload.email)

    if not success:
        # We generally don't want to expose if email exists or not, but for this specific app requirement:
        raise HTTPException(status_code=400, detail="Email not found or failed to send OTP")

    return {"message": "Password reset OTP sent"}


@router.post("/reset-password")
def reset_password_endpoint(payload: ResetPassword, db: Session = Depends(get_db)):
    result = reset_password(db, payload.email, payload.otp, payload.new_password)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


# -------------------------
# GET CURRENT USER PROFILE
# -------------------------
@router.get("/me")
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "phone_number": current_user.phone_number,
        "bio": getattr(current_user, "bio", None),
        "profile_picture": current_user.profile_picture,
    }


# -------------------------
# UPLOAD PROFILE PICTURE TO CLOUDINARY
# -------------------------
@router.post("/upload-profile-picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        api_key = os.getenv("CLOUDINARY_API_KEY")
        api_secret = os.getenv("CLOUDINARY_API_SECRET")

        if not (cloud_name and api_key and api_secret):
            # Fallback to local uploads when Cloudinary is not configured
            saved_path = save_image(file)
            host = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
            url = f"{host}/{saved_path.replace('\\', '/')}"
        else:
            contents = await file.read()
            result = cloudinary.uploader.upload(
                contents,
                folder="hire_helper/profile_pictures",
                public_id=f"user_{current_user.id}",
                overwrite=True,
                resource_type="image",
            )
            url = result.get("secure_url")
            if not url:
                raise HTTPException(status_code=500, detail="Upload failed: Cloudinary returned no secure_url")

        current_user.profile_picture = url
        db.commit()
        return {"profile_picture": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# -------------------------
# UPDATE PROFILE INFO
# -------------------------
@router.patch("/update-profile")
def update_profile(
    payload: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.first_name is not None:
        current_user.first_name = payload.first_name
    if payload.last_name is not None:
        current_user.last_name = payload.last_name
    if payload.phone_number is not None:
        current_user.phone_number = payload.phone_number
    if payload.bio is not None:
        current_user.bio = payload.bio
    if payload.profile_picture is not None:
        current_user.profile_picture = payload.profile_picture
    db.commit()
    db.refresh(current_user)
    return {
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "email": current_user.email,
        "phone_number": current_user.phone_number,
        "bio": getattr(current_user, "bio", None),
        "profile_picture": current_user.profile_picture,
    }


# -------------------------
# CHANGE PASSWORD
# -------------------------
@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password = hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully"}
