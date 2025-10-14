from pydantic import BaseModel

class AgentCreate(BaseModel):
    name: str
    language: str = "English"
    voice_type: str = "Male"

class AgentOut(BaseModel):
    id: int
    name: str
    language: str
    voice_type: str
    active: bool
