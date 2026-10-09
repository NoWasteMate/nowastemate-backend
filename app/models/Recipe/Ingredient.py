from pydantic import BaseModel
from typing import Optional

class Ingredient(BaseModel):
    name: str
    quantity: float
    unit: str
    productId: Optional[str] = None
    productType: Optional[str] = None
