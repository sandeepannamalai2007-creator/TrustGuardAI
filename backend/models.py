from pydantic import BaseModel


class StartSessionRequest(BaseModel):
    user_id: str
    demo_mode: bool = True


class StartSessionResponse(BaseModel):
    session_id: str
    status: str
    message: str