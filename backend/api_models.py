from pydantic import BaseModel, Field

# ==========================
# Student Models
# ==========================

class StudentCreate(BaseModel):
    student_id: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=100)


class StudentResponse(BaseModel):
    student_id: str
    name: str
    email: str
    message: str


# ==========================
# Session Models
# ==========================

class StartSessionRequest(BaseModel):
    user_id: str = Field(..., min_length=2, max_length=50)
    demo_mode: bool = True
    admin_pin: str | None = None


class StartSessionResponse(BaseModel):
    session_id: str
    status: str
    message: str
    access_token: str | None = None
    token_type: str = "bearer"


class AdminLoginRequest(BaseModel):
    admin_pin: str = Field(..., min_length=1, max_length=50)




# ==========================
# Feature Models
# ==========================

class FeatureRequest(BaseModel):
    session_id: str

    avg_dwell_time_ms: float = Field(..., ge=0)
    std_dwell_time_ms: float = Field(..., ge=0)

    avg_flight_time_ms: float = Field(..., ge=0)
    std_flight_time_ms: float = Field(..., ge=0)

    typing_speed_cps: float = Field(..., ge=0)

    avg_mouse_velocity_px_s: float = Field(..., ge=0)

    click_count: int = Field(..., ge=0)
    keystroke_count: int = Field(default=0, ge=0)
    pause_count: int = Field(default=0, ge=0)

    session_duration_s: float = Field(..., ge=0)



class FeatureResponse(BaseModel):
    status: str
    message: str
    trust_score: float
    security_state: str = "NORMAL"
    step_up_required: bool = False
    adaptive_threshold: float = 50.0
    explanations: list[str] = []


# ==========================
# Priority C API Request Models
# ==========================

class StepUpVerifyRequest(BaseModel):
    session_id: str
    pin: str = Field(..., min_length=1, max_length=10)


class OverrideLockRequest(BaseModel):
    session_id: str
    admin_pin: str = Field(..., min_length=1, max_length=10)


class OverrideUnlockRequest(BaseModel):
    session_id: str
    admin_pin: str = Field(..., min_length=1, max_length=10)