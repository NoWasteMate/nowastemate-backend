from enum import Enum
from typing import Optional
from pydantic import BaseModel

class Leftovers(str, Enum):
    none = "none"
    little = "little"
    lots = "lots"

class AddRecipeFeedbackRequest(BaseModel):
    productIds: list[str]
    makeAgain: Optional[bool] = None
    leftovers: Optional[Leftovers] = None
