from datetime import datetime
import uuid

from pydantic import BaseModel

class Measure(BaseModel):
    name: str
    score: float
    time: datetime = datetime.now()
    feature_pid: uuid.UUID | None = None