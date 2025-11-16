import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Beauty Dropship API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Helpers ----------

def to_str_id(doc: dict) -> dict:
    if not doc:
        return doc
    d = {**doc}
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    # Convert any ObjectId nested (simple pass for now)
    return d


# ---------- Schemas (API payloads) ----------

class OrderItem(BaseModel):
    product_id: str
    quantity: int = Field(ge=1)

class Order(BaseModel):
    name: str
    email: EmailStr
    address: str
    city: str
    country: str
    items: List[OrderItem]
    notes: Optional[str] = None

class NewsletterSignup(BaseModel):
    email: EmailStr


# ---------- Basic Routes ----------

@app.get("/")
def read_root():
    return {"message": "Beauty Dropship Backend Running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


# ---------- Product Routes ----------

@app.get("/api/products")
def list_products():
    try:
        products = get_documents("product", {}, limit=None)
        return [to_str_id(p) for p in products]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    try:
        if db is None:
            raise Exception("Database not available")
        doc = db["product"].find_one({"_id": ObjectId(product_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Product not found")
        return to_str_id(doc)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------- Checkout / Leads ----------

@app.post("/api/orders")
def create_order(order: Order):
    try:
        order_dict = order.model_dump()
        order_id = create_document("order", order_dict)
        return {"id": order_id, "status": "received"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/newsletter")
def signup_newsletter(payload: NewsletterSignup):
    try:
        # Prevent duplicates basic check
        if db is None:
            raise Exception("Database not available")
        exists = db["newsletter"].find_one({"email": payload.email})
        if exists:
            return {"status": "already_subscribed"}
        doc_id = create_document("newsletter", payload.model_dump())
        return {"id": doc_id, "status": "subscribed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Diagnostics ----------

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
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
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
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Env check
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# ---------- Startup Seeder ----------

@app.on_event("startup")
def seed_products_if_empty():
    try:
        if db is None:
            return
        count = db["product"].count_documents({})
        if count > 0:
            return
        sample_products = [
            {
                "title": "Aurora Glass Perfume",
                "description": "A luminous, floral scent with notes of iris and pear. Minimal bottle, maximal compliments.",
                "price": 59.0,
                "category": "fragrance",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1523297730390-9f2d9e9a8f49?q=80&w=1200&auto=format&fit=crop",
                "badge": "Bestseller"
            },
            {
                "title": "Velvet Matte Lipstick",
                "description": "Feather-light, full-impact color. Long-wear without the dry feel.",
                "price": 21.0,
                "category": "makeup",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1585386959984-a41552231658?q=80&w=1200&auto=format&fit=crop",
                "badge": "New"
            },
            {
                "title": "Silk Glow Highlighter",
                "description": "Ultra-fine shimmer for a lit-from-within finish.",
                "price": 28.0,
                "category": "makeup",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1596464716121-d9f0d2f6f9b0?q=80&w=1200&auto=format&fit=crop",
                "badge": "Limited"
            },
            {
                "title": "Cloud Cleanser",
                "description": "pH-balanced gel cleanser that leaves skin soft and fresh.",
                "price": 19.0,
                "category": "skincare",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa808?q=80&w=1200&auto=format&fit=crop",
                "badge": "Award-winning"
            }
        ]
        for p in sample_products:
            create_document("product", p)
    except Exception:
        # Silently ignore seeding issues in dev
        pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
