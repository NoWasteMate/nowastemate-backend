from pydantic import BaseModel
from typing import Optional

class Ingredient(BaseModel):
    name: str
    quantity: float
    unit: str
    product_id: Optional[str]
