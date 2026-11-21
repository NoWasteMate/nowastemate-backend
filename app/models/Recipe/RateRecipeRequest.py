from pydantic import BaseModel, Field

# FastAPI sends back a 422 for anything outside 1 to 5
class RateRecipeRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
