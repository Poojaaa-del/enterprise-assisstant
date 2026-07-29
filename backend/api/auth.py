# import os
# import smtplib
# from datetime import datetime, timedelta, timezone
# from email.message import EmailMessage
# from typing import Optional
# import bcrypt
# import jwt
# from fastapi import APIRouter, HTTPException, Depends, status
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
# from pydantic import BaseModel, EmailStr
# from sqlalchemy.orm import Session
# from dotenv import load_dotenv

# # Imports from your project

# # Imports from your project
# from database import get_db
# from models.user import User
# import sqlite3
# from google.oauth2 import id_token
# from google.auth.transport import requests as google_requests

# from pathlib import Path

# load_dotenv()

# BASE_DIR = Path(__file__).resolve().parent.parent
# DATABASE_PATH = str(BASE_DIR / "triage.db")

# router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
# security = HTTPBearer()

# # Configuration
# SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "guardcore-super-secret-key-change-me")
# GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
# FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")
# SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
# SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
# SMTP_USERNAME = os.environ.get("SMTP_USERNAME") or os.environ.get("SMTP_USER", "")
# SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
# SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL") or SMTP_USERNAME or "no-reply@localhost"
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 Hour Session
# EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24

# # --- Pydantic Request/Response Schemas ---
# class UserSignup(BaseModel):
#     email: EmailStr
#     username: str
#     password: str
#     full_name: Optional[str] = None

# class UserLogin(BaseModel):
#     username: Optional[str] = None
#     email: Optional[str] = None
#     username_or_email: Optional[str] = None
#     password: str

# class GoogleLoginRequest(BaseModel):
#     token: str

# class UserResponse(BaseModel):
#     id: int
#     email: str
#     username: str
#     full_name: Optional[str] = None
#     role: str
#     department: Optional[str] = "General"
#     avatar_color: Optional[str] = "from-cyan-500 to-blue-600"
#     is_active: bool

#     class Config:
#         from_attributes = True

# class Token(BaseModel):
#     access_token: str
#     token_type: str = "bearer"
#     user: UserResponse


# class VerificationResponse(BaseModel):
#     message: str


# # --- Security Helper Functions ---
# def verify_password(plain_password: str, hashed_password: str) -> bool:
#     try:
#         return bcrypt.checkpw(
#             plain_password.encode("utf-8")[:72],
#             hashed_password.encode("utf-8"),
#         )
#     except (TypeError, ValueError):
#         return False

# def get_password_hash(password: str) -> str:
#     return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")

# def create_access_token(data: dict) -> str:
#     to_encode = data.copy()
#     expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     to_encode.update({"exp": expire})
#     return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# def create_email_verification_token(user: User) -> str:
#     expire = datetime.now(timezone.utc) + timedelta(hours=EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
#     payload = {
#         "sub": str(user.id),
#         "email": user.email,
#         "purpose": "email_verification",
#         "exp": expire,
#     }
#     return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# def send_verification_email(email: str, verification_link: str) -> None:
#     """Send a verification email when SMTP is configured, otherwise log the link for local dev."""
#     # Fallback to terminal ONLY if SMTP password or host is completely missing
#     if not SMTP_HOST or not SMTP_PASSWORD:
#         print(
#             f"\n======== [EMAIL VERIFICATION LINK (NO SMTP)] ========\n"
#             f"To: {email}\n"
#             f"{verification_link}\n"
#             f"=====================================================\n"
#         )
#         return

#     message = EmailMessage()
#     message["Subject"] = "Verify your LogTriage AI account"
    
#     sender_address = SMTP_FROM_EMAIL if "@" in SMTP_FROM_EMAIL and "localhost" not in SMTP_FROM_EMAIL else SMTP_USERNAME
#     message["From"] = f"LogTriage AI <{sender_address}>"
#     message["To"] = email

#     # Plain text fallback
#     message.set_content(
#         f"Welcome to LogTriage AI.\n\n"
#         f"Verify your account by opening this link:\n{verification_link}\n\n"
#         f"This link expires in 24 hours."
#     )

#     # Rich HTML content with button
#     html_content = f"""
#     <html>
#       <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f9fafb; padding: 20px;">
#         <div style="max-width: 550px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 8px; border: 1px solid #e5e7eb;">
#           <h2 style="color: #0284c7; margin-top: 0;">Welcome to LogTriage AI</h2>
#           <p>Please verify your email address to activate your account:</p>
#           <p style="margin: 25px 0;">
#             <a href="{verification_link}" style="background-color: #0284c7; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Verify Email Address</a>
#           </p>
#           <p style="font-size: 0.85em; color: #6b7280;">Or copy and paste this link into your browser:<br>
#           <a href="{verification_link}" style="color: #0284c7;">{verification_link}</a></p>
#           <hr style="border: none; border-top: 1px solid #e5e7eb; margin-top: 30px;">
#           <p style="font-size: 0.8em; color: #9ca3af; margin-bottom: 0;">This link will expire in 24 hours.</p>
#         </div>
#       </body>
#     </html>
#     """
#     message.add_alternative(html_content, subtype="html")

#     # Send via Gmail / SMTP
#     with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
#         smtp.starttls()
#         if SMTP_USERNAME and SMTP_PASSWORD:
#             smtp.login(SMTP_USERNAME, SMTP_PASSWORD)
#         smtp.send_message(message)
    
#     print(f"[SUCCESS] Real verification email delivered to {email}")


# def get_current_user(
#     credentials: HTTPAuthorizationCredentials = Depends(security), 
#     db: Session = Depends(get_db)
# ) -> User:
#     """Dependency that decodes the bearer JWT and returns the authenticated user object."""
#     token = credentials.credentials
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         user_id: str = payload.get("sub")
#         if user_id is None:
#             raise credentials_exception
#     except (jwt.PyJWTError, jwt.ExpiredSignatureError):
#         raise credentials_exception

#     user = db.query(User).filter(User.id == int(user_id)).first()
#     if user is None or not user.is_active:
#         raise credentials_exception
#     return user
# def seed_starter_data(db: Session, user_id: int):
#     """Inserts 2 sample incident logs and 1 runbook for a newly registered user."""
#     try:
#         conn = sqlite3.connect(DATABASE_PATH)
#         cursor = conn.cursor()

#         # 2 default sample logs scoped to this user
#         sample_logs = [
#             (
#                 user_id,
#                 "welcome_db_health_check.log",
#                 "2026-07-26 09:00:01 UTC [postgres] FATAL: remaining connection slots are reserved\n"
#                 "2026-07-26 09:00:02 UTC [pgbouncer] WARN: pool exhausted — 100 clients connected",
#                 "PostgreSQL connection pool exhaustion detected",
#                 "MANDATORY",
#                 "NOT_CREATED",
#                 "Bypassed",
#             ),
#             (
#                 user_id,
#                 "welcome_auth_jwt_check.log",
#                 "2026-07-26 10:15:44 [WARN] auth.jwt: Clock skew +3200ms detected on node-02",
#                 "JWT clock skew warning — auth node out of sync",
#                 "LOW_PRIORITY",
#                 "NOT_CREATED",
#                 "Bypassed",
#             ),
#         ]

#         # Check if user_id column exists before inserting
#         cursor.execute("PRAGMA table_info(compliance_logs)")
#         col_names = [row[1] for row in cursor.fetchall()]
#         if "user_id" in col_names and "summary" in col_names:
#             cursor.executemany(
#                 "INSERT INTO compliance_logs (user_id, file_name, file_content, summary, status, jira_key, slack_status) "
#                 "VALUES (?, ?, ?, ?, ?, ?, ?)",
#                 sample_logs,
#             )
#         elif "user_id" in col_names:
#             # summary column doesn't exist — insert without it
#             simple_logs = [(uid, fn, fc, st, jk, ss) for uid, fn, fc, _, st, jk, ss in sample_logs]
#             cursor.executemany(
#                 "INSERT INTO compliance_logs (user_id, file_name, file_content, status, jira_key, slack_status) "
#                 "VALUES (?, ?, ?, ?, ?, ?)",
#                 simple_logs,
#             )

#         # 1 default runbook scoped to this user
#         cursor.execute(
#             "INSERT INTO knowledge_articles (user_id, title, category, author, content) VALUES (?, ?, ?, ?, ?)",
#             (
#                 user_id,
#                 "Getting Started: Enterprise Log Triage Guide",
#                 "RUNBOOK",
#                 "Platform Ops",
#                 "Welcome! Use the Triage Console to paste raw log traces or upload .log/.txt/.json files. "
#                 "The AI engine will classify severity, summarize anomalies, and optionally create Jira tickets. "
#                 "Escalate MANDATORY incidents from the Incident History tab for immediate action.",
#             ),
#         )

#         conn.commit()
#         conn.close()
#         print(f"[OK] [Onboarding] Seeded starter data for user_id={user_id}")
#     except Exception as e:
#         print(f"[WARNING] [Onboarding] Seeding failed for user_id={user_id}: {e}")


# @router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
# def signup(user_in: UserSignup, db: Session = Depends(get_db)):
#     """Registers a new user with a hashed password in SQLite."""
#     if db.query(User).filter(User.email == user_in.email).first():
#         raise HTTPException(status_code=400, detail="Email is already registered")
#     if db.query(User).filter(User.username == user_in.username).first():
#         raise HTTPException(status_code=400, detail="Username is already taken")

#     user = User(
#         email=user_in.email,
#         username=user_in.username,
#         hashed_password=get_password_hash(user_in.password),
#         full_name=user_in.full_name,
#         is_verified=False,
#     )
#     db.add(user)
#     db.commit()
#     db.refresh(user)

#     # Auto-seed starter sample data for onboarding experience
#     seed_starter_data(db, user.id)

#     token = create_email_verification_token(user)
#     verification_link = f"{FRONTEND_BASE_URL}/verify-email?token={token}"
#     try:
#         send_verification_email(user.email, verification_link)
#     except Exception as e:
#         print(f"[WARNING] [Email Verification] Failed to send verification email to {user.email}: {e}")

#     return user


# @router.get("/verify-email", response_model=VerificationResponse)
# def verify_email(token: str, db: Session = Depends(get_db)):
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#     except jwt.ExpiredSignatureError:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification link has expired")
#     except jwt.PyJWTError:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

#     if payload.get("purpose") != "email_verification":
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

#     user_id = payload.get("sub")
#     email = payload.get("email")
#     if not user_id or not email:
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

#     try:
#         user_id_int = int(user_id)
#     except (TypeError, ValueError):
#         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token")

#     user = db.query(User).filter(User.id == user_id_int, User.email == email).first()
#     if not user:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

#     if not user.is_verified:
#         user.is_verified = True
#         db.commit()

#     return {"message": "Email verified successfully! You can now log in."}

# @router.post("/login", response_model=Token)
# def login(credentials: UserLogin, db: Session = Depends(get_db)):
#     # Automatically resolve whichever identifier key was passed in
#     login_id = credentials.username_or_email or credentials.username or credentials.email

#     if not login_id:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail="Must provide a username or email to log in."
#         )

#     # Search for user by either email or username
#     user = db.query(User).filter(
#         (User.email == login_id) | 
#         (User.username == login_id)
#     ).first()

#     if not user or not verify_password(credentials.password, user.hashed_password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username/email or password"
#         )

#     # verified users
#     if not getattr(user, "is_verified", False):
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Please verify your email before logging in"
#         )

    
#     role_str = str(user.role.value) if hasattr(user.role, "value") else str(user.role or "USER")
#     token_claims = {
#         "sub": str(user.id),
#         "id": user.id,
#         "email": user.email,
#         "username": user.username,
#         "full_name": user.full_name or user.username or user.email.split("@")[0],
#         "department": getattr(user, "department", "General") or "General",
#         "avatar_color": getattr(user, "avatar_color", "from-cyan-500 to-blue-600") or "from-cyan-500 to-blue-600",
#         "role": role_str,
#     }
#     access_token = create_access_token(data=token_claims)
#     return Token(access_token=access_token, token_type="bearer", user=user)

# @router.post("/google", response_model=Token)
# def google_auth(request_data: GoogleLoginRequest, db: Session = Depends(get_db)):
#     """Authenticates a user via Google OAuth id_token."""
#     token = request_data.token
#     if not token:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Google ID token is required."
#         )

#     try:
#         # Verify the Google OAuth token
#         client_id = GOOGLE_CLIENT_ID if GOOGLE_CLIENT_ID else None
#         id_info = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=f"Invalid Google OAuth token: {str(e)}"
#         )

#     email = id_info.get("email")
#     if not email:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Email address not present in Google token payload."
#         )

#     name = id_info.get("name") or id_info.get("given_name") or email.split("@")[0]

#     # Look up existing user by email
#     user = db.query(User).filter(User.email == email).first()

#     if not user:
#         # Create a unique username based on email
#         base_username = email.split("@")[0]
#         username = base_username
#         counter = 1
#         while db.query(User).filter(User.username == username).first():
#             username = f"{base_username}{counter}"
#             counter += 1

#         # Create new user record
#         user = User(
#             email=email,
#             username=username,
#             hashed_password=get_password_hash(f"google_oauth_{email}_{token[:10]}"),
#             full_name=name,
#             is_verified=True
#         )
#         db.add(user)
#         db.commit()
#         db.refresh(user)

#         # Seed initial sample data for onboarding
#         seed_starter_data(db, user.id)

#     role_str = str(user.role.value) if hasattr(user.role, "value") else str(user.role or "USER")
#     token_claims = {
#         "sub": str(user.id),
#         "id": user.id,
#         "email": user.email,
#         "username": user.username,
#         "full_name": user.full_name or user.username or user.email.split("@")[0],
#         "department": getattr(user, "department", "General") or "General",
#         "avatar_color": getattr(user, "avatar_color", "from-cyan-500 to-blue-600") or "from-cyan-500 to-blue-600",
#         "role": role_str,
#     }
#     access_token = create_access_token(data=token_claims)
#     return Token(access_token=access_token, token_type="bearer", user=user)


# @router.get("/me", response_model=UserResponse)
# def get_me(current_user: User = Depends(get_current_user)):
#     """Returns the profile of the currently logged-in user."""
#     return current_user

# @router.delete("/me", status_code=status.HTTP_200_OK)
# def delete_my_account(
#     db: Session = Depends(get_db), 
#     current_user: User = Depends(get_current_user)
# ):
#     """Permanently deletes the current user's account and all associated data."""
#     user_id = current_user.id

#     try:
#         # 1. Clean up user-specific SQLite tables using raw SQL/ORM
#         conn = sqlite3.connect(DATABASE_PATH)
#         cursor = conn.cursor()
        
#         cursor.execute("DELETE FROM compliance_logs WHERE user_id = ?", (user_id,))
#         cursor.execute("DELETE FROM knowledge_articles WHERE user_id = ?", (user_id,))
#         cursor.execute("DELETE FROM knowledge_files WHERE user_id = ?", (user_id,))
#         conn.commit()
#         conn.close()

#         # 2. Delete user record
#         db.delete(current_user)
#         db.commit()

#         return {"message": "Account and all associated data deleted successfully."}
#     except Exception as e:
#         db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to delete account: {str(e)}"
#         )

# verify_token = get_current_user



import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import bcrypt
import jwt
import resend
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

# Imports from your project
from database import get_db
from models.user import User

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = str(BASE_DIR / "triage.db")

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
security = HTTPBearer()

# Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "guardcore-super-secret-key-change-me")
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:5173").rstrip("/")

# Resend Configuration
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.environ.get(
    "RESEND_FROM_EMAIL", "LogTriage AI <onboarding@resend.dev>"
)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 Hour Session
EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = 24


# --- Pydantic Request/Response Schemas ---
class UserSignup(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    username_or_email: Optional[str] = None
    password: str


class GoogleLoginRequest(BaseModel):
    token: str


class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    role: str
    department: Optional[str] = "General"
    avatar_color: Optional[str] = "from-cyan-500 to-blue-600"
    is_active: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class VerificationResponse(BaseModel):
    message: str


# --- Security Helper Functions ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8")[:72],
            hashed_password.encode("utf-8"),
        )
    except (TypeError, ValueError):
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_email_verification_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "purpose": "email_verification",
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def send_verification_email(email: str, verification_link: str) -> None:
    """Send a verification email via Resend HTTP API (Port 443 - Never blocked by cloud providers)."""
    if not RESEND_API_KEY:
        print(
            f"\n======== [EMAIL VERIFICATION LINK (NO RESEND API KEY SET)] ========\n"
            f"To: {email}\n"
            f"Link: {verification_link}\n"
            f"===================================================================\n"
        )
        return

    resend.api_key = RESEND_API_KEY

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f9fafb; padding: 20px;">
        <div style="max-width: 550px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 8px; border: 1px solid #e5e7eb;">
          <h2 style="color: #0284c7; margin-top: 0;">Welcome to LogTriage AI</h2>
          <p>Please verify your email address to activate your account:</p>
          <p style="margin: 25px 0;">
            <a href="{verification_link}" style="background-color: #0284c7; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Verify Email Address</a>
          </p>
          <p style="font-size: 0.85em; color: #6b7280;">Or copy and paste this link into your browser:<br>
          <a href="{verification_link}" style="color: #0284c7;">{verification_link}</a></p>
          <hr style="border: none; border-top: 1px solid #e5e7eb; margin-top: 30px;">
          <p style="font-size: 0.8em; color: #9ca3af; margin-bottom: 0;">This link will expire in 24 hours.</p>
        </div>
      </body>
    </html>
    """

    try:
        params: resend.Emails.SendParams = {
            "from": RESEND_FROM_EMAIL,
            "to": [email],
            "subject": "Verify your LogTriage AI account",
            "html": html_content,
        }
        response = resend.Emails.send(params)
        print(f"[SUCCESS] Verification email delivered via Resend to {email}: {response}")
    except Exception as e:
        print(f"[ERROR] [Email Verification] Resend API failed for {email}: {e}")
        print(f"[FALLBACK LINK FOR MANUAL VERIFICATION]: {verification_link}")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that decodes the bearer JWT and returns the authenticated user object."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (jwt.PyJWTError, jwt.ExpiredSignatureError):
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def seed_starter_data(db: Session, user_id: int):
    """Inserts 2 sample incident logs and 1 runbook for a newly registered user."""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        sample_logs = [
            (
                user_id,
                "welcome_db_health_check.log",
                "2026-07-26 09:00:01 UTC [postgres] FATAL: remaining connection slots are reserved\n"
                "2026-07-26 09:00:02 UTC [pgbouncer] WARN: pool exhausted — 100 clients connected",
                "PostgreSQL connection pool exhaustion detected",
                "MANDATORY",
                "NOT_CREATED",
                "Bypassed",
            ),
            (
                user_id,
                "welcome_auth_jwt_check.log",
                "2026-07-26 10:15:44 [WARN] auth.jwt: Clock skew +3200ms detected on node-02",
                "JWT clock skew warning — auth node out of sync",
                "LOW_PRIORITY",
                "NOT_CREATED",
                "Bypassed",
            ),
        ]

        cursor.execute("PRAGMA table_info(compliance_logs)")
        col_names = [row[1] for row in cursor.fetchall()]
        if "user_id" in col_names and "summary" in col_names:
            cursor.executemany(
                "INSERT INTO compliance_logs (user_id, file_name, file_content, summary, status, jira_key, slack_status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                sample_logs,
            )
        elif "user_id" in col_names:
            simple_logs = [(uid, fn, fc, st, jk, ss) for uid, fn, fc, _, st, jk, ss in sample_logs]
            cursor.executemany(
                "INSERT INTO compliance_logs (user_id, file_name, file_content, status, jira_key, slack_status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                simple_logs,
            )

        cursor.execute(
            "INSERT INTO knowledge_articles (user_id, title, category, author, content) VALUES (?, ?, ?, ?, ?)",
            (
                user_id,
                "Getting Started: Enterprise Log Triage Guide",
                "RUNBOOK",
                "Platform Ops",
                "Welcome! Use the Triage Console to paste raw log traces or upload .log/.txt/.json files. "
                "The AI engine will classify severity, summarize anomalies, and optionally create Jira tickets. "
                "Escalate MANDATORY incidents from the Incident History tab for immediate action.",
            ),
        )

        conn.commit()
        conn.close()
        print(f"[OK] [Onboarding] Seeded starter data for user_id={user_id}")
    except Exception as e:
        print(f"[WARNING] [Onboarding] Seeding failed for user_id={user_id}: {e}")


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(
    user_in: UserSignup,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Registers a new user with a hashed password in SQLite."""
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email is already registered")
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username is already taken")

    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    seed_starter_data(db, user.id)

    token = create_email_verification_token(user)
    verification_link = f"{FRONTEND_BASE_URL}/verify-email?token={token}"

    # Offload Resend API call to background task (Returns signup response instantly!)
    background_tasks.add_task(send_verification_email, user.email, verification_link)

    return user


@router.get("/verify-email", response_model=VerificationResponse)
def verify_email(token: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Verification link has expired"
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )

    if payload.get("purpose") != "email_verification":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )

    user_id = payload.get("sub")
    email = payload.get("email")
    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )

    try:
        user_id_int = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )

    user = db.query(User).filter(User.id == user_id_int, User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not user.is_verified:
        user.is_verified = True
        db.commit()

    return {"message": "Email verified successfully! You can now log in."}


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    login_id = credentials.username_or_email or credentials.username or credentials.email

    if not login_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Must provide a username or email to log in.",
        )

    user = (
        db.query(User)
        .filter((User.email == login_id) | (User.username == login_id))
        .first()
    )

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
        )

    if not getattr(user, "is_verified", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in",
        )

    role_str = str(user.role.value) if hasattr(user.role, "value") else str(user.role or "USER")
    token_claims = {
        "sub": str(user.id),
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name or user.username or user.email.split("@")[0],
        "department": getattr(user, "department", "General") or "General",
        "avatar_color": getattr(user, "avatar_color", "from-cyan-500 to-blue-600")
        or "from-cyan-500 to-blue-600",
        "role": role_str,
    }
    access_token = create_access_token(data=token_claims)
    return Token(access_token=access_token, token_type="bearer", user=user)


@router.post("/google", response_model=Token)
def google_auth(request_data: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Authenticates a user via Google OAuth id_token."""
    token = request_data.token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Google ID token is required."
        )

    try:
        client_id = GOOGLE_CLIENT_ID if GOOGLE_CLIENT_ID else None
        id_info = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google OAuth token: {str(e)}",
        )

    email = id_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address not present in Google token payload.",
        )

    name = id_info.get("name") or id_info.get("given_name") or email.split("@")[0]

    user = db.query(User).filter(User.email == email).first()

    if not user:
        base_username = email.split("@")[0]
        username = base_username
        counter = 1
        while db.query(User).filter(User.username == username).first():
            username = f"{base_username}{counter}"
            counter += 1

        user = User(
            email=email,
            username=username,
            hashed_password=get_password_hash(f"google_oauth_{email}_{token[:10]}"),
            full_name=name,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        seed_starter_data(db, user.id)

    role_str = str(user.role.value) if hasattr(user.role, "value") else str(user.role or "USER")
    token_claims = {
        "sub": str(user.id),
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name or user.username or user.email.split("@")[0],
        "department": getattr(user, "department", "General") or "General",
        "avatar_color": getattr(user, "avatar_color", "from-cyan-500 to-blue-600")
        or "from-cyan-500 to-blue-600",
        "role": role_str,
    }
    access_token = create_access_token(data=token_claims)
    return Token(access_token=access_token, token_type="bearer", user=user)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Returns the profile of the currently logged-in user."""
    return current_user


@router.delete("/me", status_code=status.HTTP_200_OK)
def delete_my_account(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Permanently deletes the current user's account and all associated data."""
    user_id = current_user.id

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM compliance_logs WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM knowledge_articles WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM knowledge_files WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

        db.delete(current_user)
        db.commit()

        return {"message": "Account and all associated data deleted successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}",
        )


verify_token = get_current_user