from pydantic import BaseModel, Field

class CallTriggerIn(BaseModel):
    driver_name: str
    phone_number: str
    load_number: str
    language: str = "English"
    scenario: str = "Normal Check-in"
    note: str | None = None
    agent_id: int = 1

class CallOut(BaseModel):
    call_id: str = Field(..., description="Provider call id / internal id")
    status: str
