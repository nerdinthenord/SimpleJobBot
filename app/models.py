from pydantic import BaseModel
from enum import Enum
from typing import Optional


class SeniorityHint(str, Enum):
    junior = "junior"
    intermediate = "intermediate"
    senior = "senior"
    lead = "lead"
    director = "director"
    executive = "executive"


class JobInput(BaseModel):
    resume_text: str
    company: str
    title: str
    location: Optional[str] = None
    job_description: str
    seniority_hint: Optional[SeniorityHint] = None
