from pydantic import BaseModel
from typing import Optional
from datetime import datetime 


class ProduceItem(BaseModel):
    predictedProduce: str
    chosenProduce: str
    createdAt: Optional[datetime] = None
    createdBy: Optional[str] = None