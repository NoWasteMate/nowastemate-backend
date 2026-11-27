from pydantic import BaseModel
import firebase_admin
from firebase_admin import firestore
#reference: https://www.geeksforgeeks.org/python/make-every-field-optional-with-pydantic-in-python/
from typing import Annotated, Optional
from pydantic import BaseModel, Field, StringConstraints
from datetime import datetime 

#reference for enums: https://fastapi.tiangolo.com/tutorial/path-params/#compare-enumeration-members
from enum import Enum

# reusable field types
# reference: https://docs.pydantic.dev/latest/concepts/fields/
ProductName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
ProductQuantity = Annotated[int, Field(ge=1, le=999)]

class ProductCategory(str, Enum):
    produce = "produce"
    dairy = "dairy"
    meat = "meat"
    grains = "grains"
    canned = "canned"
    frozen = "frozen"
    beverage = "beverage"
    other = "other"

class ProductOutcome(str, Enum):
    active = "active"
    consumed = "consumed"
    usedInRecipe = "usedInRecipe"
    wasted = "wasted"

class WasteReason(str, Enum):
    expired = "expired"
    spoiledEarly = "spoiledEarly"
    boughtTooMuch = "boughtTooMuch"
    other = "other"
    forgot = "forgot"
    badQuality = "badQuality"
    storedWrong = "storedWrong"
    addedByMistake = "addedByMistake"

#subject to change
class Product(BaseModel):
    name: str
    quantity: int
    createdAt: str
    createdBy: Optional[str] = None
    dateExpiration: Optional[datetime] = None
    #dateRemoved: Optional[str] = None
    #usedInRecipe: Optional[str] = None
    category: Optional[ProductCategory] = None
    productType: Optional[str] = None
    productTypeSource: Optional[str] = None
    categoryTags: Optional[list[str]] = None
    outcome: ProductOutcome = ProductOutcome.active
    outcomeAt: Optional[datetime] = None
    wasteReason: Optional[WasteReason] = None
    ownerId: Optional[str] = None
    ownerName: Optional[str] = None
    splitFrom: Optional[str] = None

#subject to change
class ProductUpdate(BaseModel):
    name: Optional[ProductName] = None
    quantity: Optional[ProductQuantity] = None
    category: Optional[ProductCategory] = None
    dateExpiration: Optional[datetime] = None
    #dateRemoved: Optional[str] = None
    #usedInRecipe: Optional[str] = None

class ProductOutcomeUpdate(BaseModel):
    outcome: ProductOutcome
    wasteReason: Optional[WasteReason] = None
    quantity: Optional[ProductQuantity] = None

class ProductList(BaseModel):
    products: list[Product]

# to check for POST method only
class ProductCreate(Product):
    name: ProductName
    quantity: ProductQuantity