import json
import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")

def load_data():
    if not os.path.exists(DATA_FILE):
        initial_data = {
            "categories": [
                {"id": "smartphones", "name": "Smartphones & Téléphones"},
                {"id": "laptops", "name": "Ordinateurs & PC Portables"},
                {"id": "audio", "name": "Audio, Casques & Écouteurs"},
                {"id": "accessoires", "name": "Accessoires & Connectique"},
                {"id": "montres", "name": "Montres Connectées & Wearables"}
            ],
            "products": [
                {
                    "id": "prod-1",
                    "title": "iPhone 15 Pro Max 256GB - Titane Naturel",
                    "category": "smartphones",
                    "description": "Design en titane de qualité aérospatiale, puce A17 Pro révolutionnaire, bouton Action personnalisable et téléobjectif 5x exceptionnel. Écran Super Retina XDR 6,7 pouces avec ProMotion.",
                    "price": 1479.0,
                    "discount_percent": 10.0,
                    "images": [
                        "https://images.unsplash.com/photo-1695048133142-1a20484d2569?auto=format&fit=crop&w=800&q=80",
                        "https://images.unsplash.com/photo-1592750475338-74b7b21085ab?auto=format&fit=crop&w=800&q=80",
                        "https://images.unsplash.com/photo-1510557880182-3d4d3cba35a5?auto=format&fit=crop&w=800&q=80"
                    ],
                    "stock": 15,
                    "likes": 42,
                    "is_featured": True
                },
                {
                    "id": "prod-2",
                    "title": "MacBook Pro 16\" M3 Max (36GB RAM, 1TB SSD)",
                    "category": "laptops",
                    "description": "L'ordinateur portable ultime pour les créatifs et développeurs. Écran Liquid Retina XDR de référence, autonomie jusqu'à 22 heures, connectique professionnelle complète (HDMI, MagSafe, SDXC).",
                    "price": 3999.0,
                    "discount_percent": 5.0,
                    "images": [
                        "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?auto=format&fit=crop&w=800&q=80",
                        "https://images.unsplash.com/photo-1611186871348-b1ce696e52c9?auto=format&fit=crop&w=800&q=80"
                    ],
                    "stock": 8,
                    "likes": 56,
                    "is_featured": True
                },
                {
                    "id": "prod-3",
                    "title": "Sony WH-1000XM5 - Casque Sans Fil Réduction de Bruit",
                    "category": "audio",
                    "description": "Le leader de la réduction de bruit active. 30h d'autonomie avec charge rapide, 8 microphones pour des appels d'une clarté absolue et son haute résolution sans fil LDAC.",
                    "price": 419.0,
                    "discount_percent": 15.0,
                    "images": [
                        "https://images.unsplash.com/photo-1546435770-a3e426bf472b?auto=format&fit=crop&w=800&q=80",
                        "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?auto=format&fit=crop&w=800&q=80"
                    ],
                    "stock": 25,
                    "likes": 88,
                    "is_featured": True
                },
                {
                    "id": "prod-4",
                    "title": "Samsung Galaxy S24 Ultra 512GB AI",
                    "category": "smartphones",
                    "description": "Propulsé par Galaxy AI pour traduire en direct, retoucher et rechercher intelligemment. Cadre titane, stylet S Pen intégré et capteur photo principal 200MP.",
                    "price": 1569.0,
                    "discount_percent": 12.0,
                    "images": [
                        "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?auto=format&fit=crop&w=800&q=80",
                        "https://images.unsplash.com/photo-1580910051074-3eb694886505?auto=format&fit=crop&w=800&q=80"
                    ],
                    "stock": 19,
                    "likes": 34,
                    "is_featured": False
                },
                {
                    "id": "prod-5",
                    "title": "Apple Watch Ultra 2 GPS + Cellular 49mm",
                    "category": "montres",
                    "description": "Boîtier en titane ultra résistant, écran le plus lumineux jamais conçu (3000 nits), autonomie longue durée et bouton Action orange haute visibilité.",
                    "price": 899.0,
                    "discount_percent": 0.0,
                    "images": [
                        "https://images.unsplash.com/photo-1508685096489-7aacd43bd3b1?auto=format&fit=crop&w=800&q=80",
                        "https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=800&q=80"
                    ],
                    "stock": 12,
                    "likes": 29,
                    "is_featured": False
                },
                {
                    "id": "prod-6",
                    "title": "Station de Charge Sans Fil 3-en-1 MagSafe",
                    "category": "accessoires",
                    "description": "Rechargez simultanément votre iPhone, Apple Watch et AirPods avec une alimentation rapide 15W certifiée MagSafe. Design minimaliste en aluminium brossé.",
                    "price": 129.0,
                    "discount_percent": 20.0,
                    "images": [
                        "https://images.unsplash.com/photo-1583863788434-e58a36330cf0?auto=format&fit=crop&w=800&q=80"
                    ],
                    "stock": 40,
                    "likes": 17,
                    "is_featured": False
                }
            ],
            "settings": {
                "whatsapp_phone": "22373022223",
                "store_name": "Faye Store",
                "currency": "EUR"
            }
        }
        save_data(initial_data)
        return initial_data

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

app = FastAPI(title="ElectroTech API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CategoryCreate(BaseModel):
    id: Optional[str] = None
    name: str

class ProductCreate(BaseModel):
    title: str
    category: str
    description: str
    price: float = Field(..., gt=0)
    discount_percent: float = Field(default=0.0, ge=0, le=100)
    images: List[str] = Field(..., min_length=1)
    stock: int = Field(default=10, ge=0)
    is_featured: bool = False

class SettingsUpdate(BaseModel):
    whatsapp_phone: Optional[str] = None
    store_name: Optional[str] = None
    currency: Optional[str] = None

@app.get("/api/health")
def health():
    return {"status": "ok", "message": "Backend operational"}

@app.get("/api/categories")
def get_categories():
    data = load_data()
    return data.get("categories", [])

@app.post("/api/categories", status_code=status.HTTP_201_CREATED)
def create_category(category: CategoryCreate):
    data = load_data()
    cat_id = category.id or category.name.lower().strip().replace(" ", "-")
    for c in data["categories"]:
        if c["id"] == cat_id:
            raise HTTPException(status_code=400, detail="Catégorie déjà existante")
    new_cat = {"id": cat_id, "name": category.name}
    data["categories"].append(new_cat)
    save_data(data)
    return new_cat

@app.delete("/api/categories/{category_id}")
def delete_category(category_id: str):
    data = load_data()
    data["categories"] = [c for c in data["categories"] if c["id"] != category_id]
    save_data(data)
    return {"message": "Catégorie supprimée avec succès"}

@app.get("/api/products")
def get_products(category: Optional[str] = None, q: Optional[str] = None):
    data = load_data()
    products = data.get("products", [])
    
    if category and category != "all":
        products = [p for p in products if p.get("category") == category]
        
    if q:
        query_str = q.lower().strip()
        products = [
            p for p in products
            if query_str in p.get("title", "").lower() or query_str in p.get("description", "").lower()
        ]
        
    return products

@app.get("/api/products/{product_id}")
def get_product_by_id(product_id: str):
    data = load_data()
    for p in data.get("products", []):
        if p["id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail="Produit non trouvé")

@app.post("/api/products", status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate):
    data = load_data()
    new_id = f"prod-{len(data['products']) + 1}-{os.urandom(2).hex()}"
    new_prod = product.model_dump()
    new_prod["id"] = new_id
    new_prod["likes"] = 0
    data["products"].insert(0, new_prod)
    save_data(data)
    return new_prod

@app.put("/api/products/{product_id}")
def update_product(product_id: str, product: ProductCreate):
    data = load_data()
    for idx, p in enumerate(data.get("products", [])):
        if p["id"] == product_id:
            updated = product.model_dump()
            updated["id"] = product_id
            updated["likes"] = p.get("likes", 0)
            data["products"][idx] = updated
            save_data(data)
            return updated
    raise HTTPException(status_code=404, detail="Produit non trouvé")

@app.delete("/api/products/{product_id}")
def delete_product(product_id: str):
    data = load_data()
    initial_len = len(data["products"])
    data["products"] = [p for p in data["products"] if p["id"] != product_id]
    if len(data["products"]) == initial_len:
        raise HTTPException(status_code=404, detail="Produit non trouvé")
    save_data(data)
    return {"message": "Produit supprimé avec succès"}

@app.post("/api/products/{product_id}/like")
def toggle_like_product(product_id: str, action: str = Query("like")):
    data = load_data()
    for p in data.get("products", []):
        if p["id"] == product_id:
            current_likes = p.get("likes", 0)
            if action == "like":
                p["likes"] = current_likes + 1
            else:
                p["likes"] = max(0, current_likes - 1)
            save_data(data)
            return {"id": product_id, "likes": p["likes"]}
    raise HTTPException(status_code=404, detail="Produit non trouvé")

@app.get("/api/settings")
def get_settings():
    data = load_data()
    return data.get("settings", {
        "whatsapp_phone": "221770000000",
        "store_name": "ÉlectroTech Store",
        "currency": "EUR"
    })

@app.post("/api/settings")
def update_settings(settings: SettingsUpdate):
    data = load_data()
    if "settings" not in data:
        data["settings"] = {}
    if settings.whatsapp_phone is not None:
        data["settings"]["whatsapp_phone"] = settings.whatsapp_phone.strip()
    if settings.store_name is not None:
        data["settings"]["store_name"] = settings.store_name.strip()
    if settings.currency is not None:
        data["settings"]["currency"] = settings.currency.strip()
    save_data(data)
    return data["settings"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
