from datetime import datetime, timedelta, timezone
from enum import Enum
import hashlib
import hmac
import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, select, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session

SECRET_KEY = os.getenv("SECRET_KEY", "local-only-change-this-secret")
ALGORITHM = "HS256"
TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "720"))
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./foodbridge.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class Role(str, Enum):
    admin = "admin"
    donor = "donor"

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(30), default="")
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(20), default="donor")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Ashrama(Base):
    __tablename__ = "ashramas"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    city: Mapped[str] = mapped_column(String(100))
    district: Mapped[str] = mapped_column(String(100), default="")
    address: Mapped[str] = mapped_column(Text, default="")
    contact_name: Mapped[str] = mapped_column(String(120), default="")
    contact_phone: Mapped[str] = mapped_column(String(30), default="")
    capacity_meals: Mapped[int] = mapped_column(Integer, default=100)
    food_preferences: Mapped[str] = mapped_column(String(250), default="Vegetarian")
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Donation(Base):
    __tablename__ = "donations"
    id: Mapped[int] = mapped_column(primary_key=True)
    donor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    ashrama_id: Mapped[int] = mapped_column(ForeignKey("ashramas.id"))
    food_name: Mapped[str] = mapped_column(String(180))
    food_type: Mapped[str] = mapped_column(String(40))
    quantity: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(30), default="meals")
    prepared_at: Mapped[datetime] = mapped_column(DateTime)
    consume_before: Mapped[datetime] = mapped_column(DateTime)
    pickup_address: Mapped[str] = mapped_column(Text)
    allergens: Mapped[str] = mapped_column(String(500), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="submitted")
    admin_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class DonationEvent(Base):
    __tablename__ = "donation_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    donation_id: Mapped[int] = mapped_column(ForeignKey("donations.id"))
    status: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text, default="")
    actor: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(default="", max_length=30)
    password: str = Field(min_length=8, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class DonationIn(BaseModel):
    ashrama_id: int
    food_name: str = Field(min_length=2, max_length=180)
    food_type: str = Field(pattern="^(Vegetarian|Vegan|Non-vegetarian)$")
    quantity: float = Field(gt=0, le=100000)
    unit: str = Field(default="meals", max_length=30)
    prepared_at: datetime
    consume_before: datetime
    pickup_address: str = Field(min_length=5, max_length=1000)
    allergens: str = Field(default="", max_length=500)
    notes: str = Field(default="", max_length=2000)

class StatusIn(BaseModel):
    status: str
    note: str = Field(default="", max_length=1000)

class AshramaIn(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    city: str
    district: str = ""
    address: str = ""
    contact_name: str = ""
    contact_phone: str = ""
    capacity_meals: int = Field(default=100, gt=0)
    food_preferences: str = "Vegetarian"
    is_verified: bool = False

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str
    phone: str
    role: str
    is_active: bool

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
app = FastAPI(title="FoodBridge API", version="0.1.0", description="Food donation coordination API")
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)
    return salt.hex() + "$" + digest.hex()

def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$", 1)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 310000).hex()
        return hmac.compare_digest(actual, digest_hex)
    except (ValueError, TypeError):
        return False

def make_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": str(user.id), "role": user.role, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

def current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    unauthorized = HTTPException(status_code=401, detail="Invalid or expired login. Please sign in again.", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub", "0"))
    except (JWTError, ValueError, TypeError):
        raise unauthorized
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise unauthorized
    return user

def admin_user(user: User = Depends(current_user)) -> User:
    if user.role != Role.admin.value:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def donation_dict(d: Donation, db: Session):
    donor = db.get(User, d.donor_id)
    ashrama = db.get(Ashrama, d.ashrama_id)
    events = db.scalars(select(DonationEvent).where(DonationEvent.donation_id == d.id).order_by(DonationEvent.created_at)).all()
    return {
        "id": d.id, "donor_id": d.donor_id, "donor_name": donor.name if donor else "Unknown",
        "ashrama_id": d.ashrama_id, "ashrama_name": ashrama.name if ashrama else "Unknown",
        "ashrama_city": ashrama.city if ashrama else "", "food_name": d.food_name,
        "food_type": d.food_type, "quantity": d.quantity, "unit": d.unit,
        "prepared_at": d.prepared_at.isoformat(), "consume_before": d.consume_before.isoformat(),
        "pickup_address": d.pickup_address, "allergens": d.allergens, "notes": d.notes,
        "status": d.status, "admin_note": d.admin_note, "created_at": d.created_at.isoformat(),
        "events": [{"status": e.status, "note": e.note, "actor": e.actor, "created_at": e.created_at.isoformat()} for e in events]
    }

def ashrama_dict(a: Ashrama):
    return {"id": a.id, "name": a.name, "city": a.city, "district": a.district, "address": a.address,
            "contact_name": a.contact_name, "contact_phone": a.contact_phone, "capacity_meals": a.capacity_meals,
            "food_preferences": a.food_preferences, "is_verified": a.is_verified, "is_demo": a.is_demo}

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@foodbridge.local").lower()
        if not db.scalar(select(User).where(User.email == admin_email)):
            db.add(User(name="FoodBridge Admin", email=admin_email, password_hash=hash_password(os.getenv("ADMIN_PASSWORD", "ChangeMe123!")), role="admin"))
        if db.scalar(select(func.count(Ashrama.id))) == 0:
            demos = [
                ("Demo Seva Ashrama - Bengaluru", "Bengaluru", "Bengaluru Urban"),
                ("Demo Annadana Kendra - Mysuru", "Mysuru", "Mysuru"),
                ("Demo Janaseva Ashrama - Hubballi", "Hubballi", "Dharwad"),
                ("Demo Karuna Nilaya - Mangaluru", "Mangaluru", "Dakshina Kannada"),
                ("Demo Seva Nilaya - Tumakuru", "Tumakuru", "Tumakuru"),
            ]
            for name, city, district in demos:
                db.add(Ashrama(name=name, city=city, district=district, address="Demo address - replace after verification", capacity_meals=100, is_verified=True, is_demo=True))
        db.commit()

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "foodbridge-api"}

@app.post("/api/auth/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    email = str(data.email).lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(name=data.name.strip(), email=email, phone=data.phone, password_hash=hash_password(data.password), role="donor")
    db.add(user); db.commit(); db.refresh(user)
    return {"access_token": make_token(user), "token_type": "bearer", "user": UserOut.model_validate(user).model_dump()}

@app.post("/api/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == str(data.email).lower()))
    if not user or not verify_password(data.password, user.password_hash) or not user.is_active:
        raise HTTPException(401, "Incorrect email or password")
    return {"access_token": make_token(user), "token_type": "bearer", "user": UserOut.model_validate(user).model_dump()}

@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return UserOut.model_validate(user).model_dump()

@app.get("/api/ashramas")
def list_ashramas(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Ashrama).where(Ashrama.is_verified == True).order_by(Ashrama.city, Ashrama.name)).all()
    return [ashrama_dict(a) for a in rows]

@app.post("/api/donations")
def create_donation(data: DonationIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.role != "donor":
        raise HTTPException(403, "Only donor accounts can submit donations")
    ashrama = db.get(Ashrama, data.ashrama_id)
    if not ashrama or not ashrama.is_verified:
        raise HTTPException(400, "Please select an active, verified ashrama")
    prepared = data.prepared_at.replace(tzinfo=None)
    deadline = data.consume_before.replace(tzinfo=None)
    if deadline <= prepared:
        raise HTTPException(400, "Safe-consumption deadline must be after preparation time")
    if deadline < datetime.now():
        raise HTTPException(400, "The safe-consumption deadline has already passed")
    d = Donation(donor_id=user.id, ashrama_id=ashrama.id, food_name=data.food_name.strip(), food_type=data.food_type,
        quantity=data.quantity, unit=data.unit, prepared_at=prepared, consume_before=deadline,
        pickup_address=data.pickup_address, allergens=data.allergens, notes=data.notes, status="submitted")
    db.add(d); db.flush()
    db.add(DonationEvent(donation_id=d.id, status="submitted", note="Donation request submitted", actor=user.email))
    db.commit(); db.refresh(d)
    return donation_dict(d, db)

@app.get("/api/donations/mine")
def my_donations(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Donation).where(Donation.donor_id == user.id).order_by(Donation.created_at.desc())).all()
    return [donation_dict(d, db) for d in rows]

@app.get("/api/admin/dashboard")
def admin_dashboard(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return {
        "donors": db.scalar(select(func.count(User.id)).where(User.role == "donor")) or 0,
        "ashramas": db.scalar(select(func.count(Ashrama.id)).where(Ashrama.is_verified == True)) or 0,
        "donations": db.scalar(select(func.count(Donation.id))) or 0,
        "pending": db.scalar(select(func.count(Donation.id)).where(Donation.status == "submitted")) or 0,
        "delivered": db.scalar(select(func.count(Donation.id)).where(Donation.status.in_(["delivered", "confirmed"]))) or 0,
        "meals": db.scalar(select(func.coalesce(func.sum(Donation.quantity), 0)).where(Donation.status.in_(["delivered", "confirmed"]))) or 0
    }

@app.get("/api/admin/donations")
def admin_donations(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Donation).order_by(Donation.created_at.desc())).all()
    return [donation_dict(d, db) for d in rows]

@app.get("/api/admin/donors")
def admin_donors(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).where(User.role == "donor").order_by(User.created_at.desc())).all()
    return [UserOut.model_validate(u).model_dump() | {"created_at": u.created_at.isoformat()} for u in rows]

@app.get("/api/admin/ashramas")
def admin_ashramas(user: User = Depends(admin_user), db: Session = Depends(get_db)):
    return [ashrama_dict(a) for a in db.scalars(select(Ashrama).order_by(Ashrama.city)).all()]

@app.post("/api/admin/ashramas")
def add_ashrama(data: AshramaIn, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    a = Ashrama(**data.model_dump(), is_demo=False)
    db.add(a); db.commit(); db.refresh(a)
    return ashrama_dict(a)

@app.patch("/api/admin/ashramas/{ashrama_id}/verification")
def verify_ashrama(ashrama_id: int, verified: bool, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    a = db.get(Ashrama, ashrama_id)
    if not a: raise HTTPException(404, "Ashrama not found")
    a.is_verified = verified; db.commit()
    return ashrama_dict(a)

@app.patch("/api/admin/donations/{donation_id}/status")
def update_status(donation_id: int, data: StatusIn, user: User = Depends(admin_user), db: Session = Depends(get_db)):
    allowed = {"approved", "assigned", "picked_up", "in_transit", "delivered", "confirmed", "rejected", "cancelled"}
    if data.status not in allowed: raise HTTPException(400, "Unsupported donation status")
    d = db.get(Donation, donation_id)
    if not d: raise HTTPException(404, "Donation not found")
    if d.status in {"confirmed", "rejected", "cancelled"}: raise HTTPException(409, "This donation is already closed")
    if data.status == "confirmed" and d.status != "delivered":
        raise HTTPException(400, "Only delivered donations can be confirmed")
    d.status = data.status
    if data.note: d.admin_note = data.note
    db.add(DonationEvent(donation_id=d.id, status=data.status, note=data.note or f"Status updated to {data.status}", actor=user.email))
    db.commit(); db.refresh(d)
    return donation_dict(d, db)
