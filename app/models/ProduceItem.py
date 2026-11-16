from pydantic import BaseModel
from typing import Optional

class ProduceItem(BaseModel):
    predictedItem: str
    chosenItem: str
    createdAt: Optional[str] = None