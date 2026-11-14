import os
import json
import pytest
from fastapi.testclient import TestClient
from main import app, DATA_FILE, load_data

client = TestClient(app)

def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_get_categories():
    response = client.get("/api/categories")
    assert response.status_code == 200
    cats = response.json()
    assert isinstance(cats, list)
    assert len(cats) >= 1

def test_create_and_delete_category():
    # Create category
    response = client.post("/api/categories", json={"name": "Drones & Caméras"})
    assert response.status_code == 201
    cat = response.json()
    assert cat["name"] == "Drones & Caméras"
    cat_id = cat["id"]

    # Delete category
    del_res = client.delete(f"/api/categories/{cat_id}")
    assert del_res.status_code == 200

def test_get_products_and_search():
    # Insert temporary test product to ensure test isolation
    test_prod = {
        "title": "Apple iPhone 15 Pro Test",
        "category": "smartphones",
        "description": "Test description",
        "price": 850000.0,
        "discount_percent": 0.0,
        "images": ["https://images.unsplash.com/photo-test"],
        "stock": 5,
        "is_featured": False
    }
    create_res = client.post("/api/products", json=test_prod)
    assert create_res.status_code == 201
    prod_id = create_res.json()["id"]

    # Test all
    res = client.get("/api/products")
    assert res.status_code == 200
    products = res.json()
    assert len(products) > 0

    # Test search query
    res_search = client.get("/api/products?q=iphone")
    assert res_search.status_code == 200
    assert any("iphone" in p["title"].lower() for p in res_search.json())

    # Test category filter
    res_cat = client.get("/api/products?category=smartphones")
    assert res_cat.status_code == 200
    assert all(p["category"] == "smartphones" for p in res_cat.json())

    # Cleanup test product
    client.delete(f"/api/products/{prod_id}")

def test_create_product_with_multi_images_and_discount():
    new_product_data = {
        "title": "Souris Ergonomique Sans Fil Pro",
        "category": "accessoires",
        "description": "Capteur ultra-précis 4000 DPI et molette magnétique silencieuse.",
        "price": 89.99,
        "discount_percent": 15.0,
        "images": [
            "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?auto=format&fit=crop&w=800&q=80",
            "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=800&q=80"
        ],
        "stock": 50,
        "is_featured": True
    }
    create_res = client.post("/api/products", json=new_product_data)
    assert create_res.status_code == 201
    created_prod = create_res.json()
    assert created_prod["title"] == new_product_data["title"]
    assert len(created_prod["images"]) == 2
    assert created_prod["discount_percent"] == 15.0
    prod_id = created_prod["id"]

    # Like product
    like_res = client.post(f"/api/products/{prod_id}/like?action=like")
    assert like_res.status_code == 200
    assert like_res.json()["likes"] == 1

    # Unlike product
    unlike_res = client.post(f"/api/products/{prod_id}/like?action=unlike")
    assert unlike_res.status_code == 200
    assert unlike_res.json()["likes"] == 0

    # Delete product
    delete_res = client.delete(f"/api/products/{prod_id}")
    assert delete_res.status_code == 200

def test_settings_update():
    res = client.post("/api/settings", json={"whatsapp_phone": "221781234567"})
    assert res.status_code == 200
    assert res.json()["whatsapp_phone"] == "221781234567"
