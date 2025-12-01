from fastapi import FastAPI

from app.routers import families, products, users

# Structure sourced from: https://fastapi.tiangolo.com/tutorial/bigger-applications/#the-main-fastapi
app = FastAPI()

app.include_router(families.router)
app.include_router(products.router)
app.include_router(users.router)