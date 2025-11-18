"""
Database Schemas for Recipe Blog

Each Pydantic model represents a collection in your MongoDB database.
Collection name is the lowercase of the class name.

Use these schemas for validation when creating documents.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl


class Recipe(BaseModel):
    """
    Recipes collection schema
    Collection name: "recipe"
    """
    title: str = Field(..., min_length=3, max_length=140, description="Recipe title")
    slug: Optional[str] = Field(None, description="URL-friendly identifier")
    summary: Optional[str] = Field(None, max_length=280, description="Short summary")
    ingredients: List[str] = Field(default_factory=list, description="List of ingredients")
    steps: List[str] = Field(default_factory=list, description="Cooking steps")
    category: Optional[str] = Field(None, description="Category name")
    cook_time_minutes: Optional[int] = Field(None, ge=0, le=1000, description="Estimated cook time")
    image_url: Optional[HttpUrl] = Field(None, description="Cover image URL")
    author: Optional[str] = Field(None, description="Author name")
    tags: List[str] = Field(default_factory=list, description="SEO tags")


class Comment(BaseModel):
    """
    Comments collection schema
    Collection name: "comment"
    """
    recipe_id: str = Field(..., description="Associated recipe id (string)")
    name: str = Field(..., min_length=2, max_length=60, description="Commenter name")
    message: str = Field(..., min_length=1, max_length=1000, description="Comment text")


class Category(BaseModel):
    """
    Categories collection schema
    Collection name: "category"
    """
    name: str = Field(..., min_length=2, max_length=60)
    description: Optional[str] = None
