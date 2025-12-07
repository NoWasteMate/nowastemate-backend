from pydantic import BaseModel
import firebase_admin
from firebase_admin import firestore
#reference: https://www.geeksforgeeks.org/python/make-every-field-optional-with-pydantic-in-python/
from typing import Optional
from pydantic import BaseModel

#subject to change
class Product(BaseModel):
    name: str
    quantity: int
    createdAt: Optional[str] = None
    createdBy: Optional[str] = None
    dateExpiredUserSet: Optional[str] = None
    dateRemoved: Optional[str] = None
    usedInRecipe: Optional[str] = None
    category: str

class ProductList(BaseModel):
    products: list[Product]
