from fastapi import FastAPI

from app.routers import families, products, users, recipes, analytics

# Structure sourced from: https://fastapi.tiangolo.com/tutorial/bigger-applications/#the-main-fastapi

# Metadata implementation sourced from: https://fastapi.tiangolo.com/tutorial/metadata/#metadata-for-api

description = """
NoWasteMate Backend Built using FastAPI
"""

tags_metadata = [
    {
        "name": "Users",
        "description": "Operations with users"
    },
    {
        "name": "Families",
        "description": "Operations with families"
    },
    {
        "name": "Products",
        "description": "Operations with products"
    },
    {
        "name": "Recipes",
        "description": "Operations with recipes"
    },
    {
        "name": "Analytics",
        "description": "Operations with analytics"
    },
]

app = FastAPI (
    title="NoWasteMate-Backend",
    description=description,
    summary="Application for NoWasteMate",
    openapi_tags=tags_metadata
) 
  

app.include_router(families.router)
app.include_router(products.router)
app.include_router(users.router)
app.include_router(recipes.router)
app.include_router(analytics.router)