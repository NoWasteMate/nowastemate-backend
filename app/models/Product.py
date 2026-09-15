from pydantic import BaseModel
import firebase_admin
from firebase_admin import firestore
#reference: https://www.geeksforgeeks.org/python/make-every-field-optional-with-pydantic-in-python/
from typing import Optional
from pydantic import BaseModel
from datetime import datetime 

#subject to change
class Product(BaseModel):
    name: str
    quantity: int
    createdAt: str
    createdBy: Optional[str] = None
    dateExpiration: Optional[datetime] = None
    dateRemoved: Optional[str] = None
    usedInRecipe: Optional[str] = None
    category: str

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    category: Optional[str] = None
    dateExpiration: Optional[datetime] = None
    dateRemoved: Optional[str] = None
    usedInRecipe: Optional[str] = None

class ProductList(BaseModel):
    products: list[Product]
