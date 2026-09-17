from pydantic import BaseModel
import firebase_admin
from firebase_admin import firestore
#reference: https://www.geeksforgeeks.org/python/make-every-field-optional-with-pydantic-in-python/
from typing import Optional
from pydantic import BaseModel
from datetime import datetime 

#reference for enums: https://fastapi.tiangolo.com/tutorial/path-params/#compare-enumeration-members
from enum import Enum

class ProductCategory(str, Enum):
    produce = "produce"
    dairy = "dairy"
    meat = "meat"
    grains = "grains"
    canned = "canned"
    frozen = "frozen"
    beverage = "beverage"
    other = "other"

#subject to change
class Product(BaseModel):
    name: str
    quantity: int
    createdAt: str
    createdBy: Optional[str] = None
    dateExpiration: Optional[datetime] = None
    dateRemoved: Optional[str] = None
    usedInRecipe: Optional[str] = None
    category: ProductCategory

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    category: Optional[ProductCategory] = None
    dateExpiration: Optional[datetime] = None
    dateRemoved: Optional[str] = None
    usedInRecipe: Optional[str] = None

class ProductList(BaseModel):
    products: list[Product]
