from pydantic import BaseModel
import firebase_admin
from firebase_admin import firestore

#subject to change
class Product(BaseModel):
    name: str
    quantity: int
    #created_at: firestore.SERVER_TIMESTAMP
    category: str

class ProductList(BaseModel):
    products: list[Product]
