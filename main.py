import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Recipe, Comment, Category


app = FastAPI(title="Recipe Blog API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Utility: convert ObjectId to str for JSON

def serialize_doc(doc: dict) -> dict:
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert nested ObjectIds if any
    for k, v in list(d.items()):
        if isinstance(v, ObjectId):
            d[k] = str(v)
    return d


@app.get("/")
def root():
    return {"message": "Recipe Blog API running"}


# Recipes
@app.post("/api/recipes", response_model=dict)
def create_recipe(recipe: Recipe):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Generate slug if not provided
    slug = recipe.slug or "-".join(recipe.title.lower().split())
    data = recipe.model_dump()
    data["slug"] = slug
    inserted_id = create_document("recipe", data)
    return {"id": inserted_id}


@app.get("/api/recipes", response_model=List[dict])
def list_recipes(q: Optional[str] = None, tag: Optional[str] = None, limit: int = Query(20, ge=1, le=100)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    filter_dict: dict = {}
    if q:
        filter_dict["title"] = {"$regex": q, "$options": "i"}
    if tag:
        filter_dict["tags"] = {"$in": [tag]}
    docs = get_documents("recipe", filter_dict, limit)
    return [serialize_doc(d) for d in docs]


@app.get("/api/recipes/{slug}", response_model=dict)
def get_recipe(slug: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    doc = db["recipe"].find_one({"slug": slug})
    if not doc:
        raise HTTPException(status_code=404, detail="Recipe not found")
    return serialize_doc(doc)


# Comments
@app.post("/api/recipes/{recipe_id}/comments", response_model=dict)
def add_comment(recipe_id: str, comment: Comment):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    # ensure recipe exists
    try:
        _id = ObjectId(recipe_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid recipe id")
    exists = db["recipe"].find_one({"_id": _id})
    if not exists:
        raise HTTPException(status_code=404, detail="Recipe not found")

    data = comment.model_dump()
    data["recipe_id"] = recipe_id
    inserted_id = create_document("comment", data)
    return {"id": inserted_id}


@app.get("/api/recipes/{recipe_id}/comments", response_model=List[dict])
def list_comments(recipe_id: str, limit: int = Query(50, ge=1, le=200)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    docs = get_documents("comment", {"recipe_id": recipe_id}, limit)
    return [serialize_doc(d) for d in docs]


# Categories
@app.post("/api/categories", response_model=dict)
def create_category(category: Category):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    inserted_id = create_document("category", category)
    return {"id": inserted_id}


@app.get("/api/categories", response_model=List[dict])
def list_categories(limit: int = Query(50, ge=1, le=200)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    docs = get_documents("category", {}, limit)
    return [serialize_doc(d) for d in docs]


# SEO helper endpoint for sitemap
@app.get("/sitemap.xml", response_class=None)
def sitemap():
    base = os.getenv("FRONTEND_URL", "")
    urls = []
    for r in db["recipe"].find({}, {"slug": 1}).limit(500):
        urls.append(f"  <url><loc>{base}/recipe/{r['slug']}</loc></url>")
    xml = "\n".join([
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">",
        *urls,
        "</urlset>",
    ])
    from fastapi.responses import Response
    return Response(content=xml, media_type="application/xml")


# AI: simple live update suggestion endpoint (mocked deterministic)
class AISuggestRequest(BaseModel):
    title: str
    ingredients: List[str]


@app.post("/api/ai/suggest", response_model=dict)
def ai_suggest(data: AISuggestRequest):
    # Very simple heuristic suggestion instead of external API
    tips = []
    ings = ", ".join(data.ingredients)
    if "salt" not in ings.lower():
        tips.append("Add a pinch of salt to enhance flavors.")
    if "lemon" in ings.lower() or "lime" in ings.lower():
        tips.append("A squeeze of citrus at the end brightens the dish.")
    if "garlic" in ings.lower():
        tips.append("Saute garlic gently; burnt garlic turns bitter.")
    if not tips:
        tips.append("Taste as you cook and adjust seasoning gradually.")
    return {"tips": tips[:3]}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        from database import db

        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os as _os
    response["database_url"] = "✅ Set" if _os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if _os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
