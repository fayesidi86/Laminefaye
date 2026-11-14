import os
import json
import pytest
import hashlib
import secrets
from fastapi.testclient import TestClient

# Hashes de test pour les identifiants de test uniquement
_TEST_EMAIL    = "admin@test.com"
_TEST_PASSWORD = "TestPassword_Security2026!"
_TEST_EMAIL_HASH = hashlib.sha256(_TEST_EMAIL.encode()).hexdigest()
_TEST_PASS_HASH  = hashlib.sha256(_TEST_PASSWORD.encode()).hexdigest()

# Injecter les variables d'env AVANT l'import de l'application
os.environ["ADMIN_EMAIL_HASH"] = _TEST_EMAIL_HASH
os.environ["ADMIN_PASS_HASH"]  = _TEST_PASS_HASH
os.environ["ADMIN_SECRET_KEY"] = secrets.token_hex(32)
os.environ["ALLOWED_ORIGINS"]  = "http://localhost:3000"

from main import app, DATA_FILE, _rate_store

client = TestClient(app)

# ===========================================================================
# Helpers
# ===========================================================================
def _reset_rate_limit():
    """Réinitialise les compteurs de rate limit entre les tests."""
    _rate_store.clear()

def _admin_token():
    """Obtient un token admin valide pour les tests."""
    _reset_rate_limit()
    res = client.post("/api/admin/login", json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["token"]

def _auth(token):
    return {"Authorization": f"Bearer {token}"}

# ===========================================================================
# Tests de santé
# ===========================================================================
def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_docs_disabled():
    """SÉCURITÉ : La documentation API ne doit pas être exposée en production."""
    assert client.get("/docs").status_code   == 404
    assert client.get("/redoc").status_code  == 404
    assert client.get("/openapi.json").status_code == 404

# ===========================================================================
# Tests d'authentification
# ===========================================================================
def test_admin_login_success():
    res = client.post("/api/admin/login", json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD})
    assert res.status_code == 200
    data = res.json()
    assert "token" in data
    assert "expires_in" in data
    assert len(data["token"]) > 20

def test_admin_login_wrong_password():
    res = client.post("/api/admin/login", json={"email": _TEST_EMAIL, "password": "mauvais_mdp"})
    assert res.status_code == 401

def test_admin_login_wrong_email():
    res = client.post("/api/admin/login", json={"email": "hacker@evil.com", "password": _TEST_PASSWORD})
    assert res.status_code == 401

def test_admin_login_empty():
    res = client.post("/api/admin/login", json={"email": "", "password": ""})
    assert res.status_code == 401

# ===========================================================================
# Tests de contrôle d'accès (IDOR / Accès non autorisé)
# ===========================================================================
def test_create_product_without_auth():
    """SÉCURITÉ CRITIQUE : Création de produit DOIT être refusée sans token."""
    res = client.post("/api/products", json={
        "title": "Produit Hacker", "category": "smartphones",
        "description": "Test", "price": 1.0, "images": ["https://test.com/img.jpg"]
    })
    assert res.status_code == 401, "FAILLE: création produit sans auth acceptée !"

def test_delete_product_without_auth():
    """SÉCURITÉ CRITIQUE : Suppression de produit DOIT être refusée sans token."""
    res = client.delete("/api/products/prod-quelconque")
    assert res.status_code == 401, "FAILLE: suppression produit sans auth acceptée !"

def test_create_category_without_auth():
    """SÉCURITÉ : Création catégorie DOIT être refusée sans token."""
    res = client.post("/api/categories", json={"name": "Cat Hacker"})
    assert res.status_code == 401, "FAILLE: création catégorie sans auth acceptée !"

def test_delete_category_without_auth():
    """SÉCURITÉ : Suppression catégorie DOIT être refusée sans token."""
    res = client.delete("/api/categories/smartphones")
    assert res.status_code == 401, "FAILLE: suppression catégorie sans auth acceptée !"

def test_update_settings_without_auth():
    """SÉCURITÉ CRITIQUE : Modification des paramètres WhatsApp DOIT être refusée sans token."""
    res = client.post("/api/settings", json={"whatsapp_phone": "00000000000"})
    assert res.status_code == 401, "FAILLE: modification settings sans auth acceptée !"

def test_invalid_token_rejected():
    """SÉCURITÉ : Un token inventé doit être rejeté."""
    fake_token = "ce_token_est_faux_" + secrets.token_hex(16)
    res = client.post("/api/products", json={
        "title": "Test", "category": "smartphones", "description": "Test",
        "price": 1.0, "images": ["https://test.com/img.jpg"]
    }, headers={"Authorization": f"Bearer {fake_token}"})
    assert res.status_code == 401

# ===========================================================================
# Tests de validation des données (Injection / DoS / XSS Stored)
# ===========================================================================
def test_xss_in_category_name_sanitized():
    """SÉCURITÉ : Les balises HTML doivent être filtrées avant stockage."""
    token = _admin_token()
    res = client.post("/api/categories",
        json={"name": "<script>alert(1)</script>"},
        headers=_auth(token)
    )
    if res.status_code == 201:
        created = res.json()
        assert "<script>" not in created["name"], "FAILLE XSS: balise script non filtrée!"
        # Nettoyage
        client.delete(f"/api/categories/{created['id']}", headers=_auth(token))

def test_oversized_product_title_rejected():
    """SÉCURITÉ : Titre trop long (>200 chars) doit être rejeté."""
    token = _admin_token()
    res = client.post("/api/products", json={
        "title": "T" * 201, "category": "smartphones",
        "description": "Test", "price": 1.0, "images": ["https://test.com/img.jpg"]
    }, headers=_auth(token))
    assert res.status_code == 422, "FAILLE DoS: titre trop long accepté !"

def test_oversized_description_rejected():
    """SÉCURITÉ : Description trop longue (>5000 chars) doit être rejetée."""
    token = _admin_token()
    res = client.post("/api/products", json={
        "title": "Test", "category": "smartphones",
        "description": "D" * 5001, "price": 1.0, "images": ["https://test.com/img.jpg"]
    }, headers=_auth(token))
    assert res.status_code == 422, "FAILLE DoS: description trop longue acceptée !"

def test_too_many_images_rejected():
    """SÉCURITÉ : Plus de 10 images doit être rejeté."""
    token = _admin_token()
    res = client.post("/api/products", json={
        "title": "Test", "category": "smartphones",
        "description": "Test", "price": 1.0,
        "images": [f"https://test.com/img{i}.jpg" for i in range(11)]
    }, headers=_auth(token))
    assert res.status_code == 422, "FAILLE DoS: trop d'images acceptées !"

def test_negative_price_rejected():
    """SÉCURITÉ : Prix négatif doit être rejeté."""
    token = _admin_token()
    res = client.post("/api/products", json={
        "title": "Test", "category": "smartphones",
        "description": "Test", "price": -100.0, "images": ["https://test.com/img.jpg"]
    }, headers=_auth(token))
    assert res.status_code == 422

def test_invalid_phone_in_settings():
    """SÉCURITÉ : Numéro de téléphone invalide (trop court ou lettres) doit être rejeté."""
    token = _admin_token()
    res = client.post("/api/settings",
        json={"whatsapp_phone": "abc"},
        headers=_auth(token)
    )
    assert res.status_code == 422, "FAILLE: numéro de tel invalide accepté !"

def test_invalid_image_url_rejected():
    """SÉCURITÉ : URL d'image invalide (ni https:// ni data:image/) doit être rejetée."""
    token = _admin_token()
    res = client.post("/api/products", json={
        "title": "Test", "category": "smartphones",
        "description": "Test", "price": 100.0,
        "images": ["javascript:alert(1)"]
    }, headers=_auth(token))
    assert res.status_code == 422, "FAILLE XSS: URL javascript: acceptée dans images !"

def test_product_id_path_traversal():
    """SÉCURITÉ : Tentative de path traversal via l'ID produit."""
    res = client.get("/api/products/../../etc/passwd")
    assert res.status_code in [400, 404]

def test_like_action_validation():
    """SÉCURITÉ : L'action like doit être strictement 'like' ou 'unlike'."""
    res = client.post("/api/products/some-id/like?action=DROP+TABLE")
    assert res.status_code in [400, 404, 422]

# ===========================================================================
# Tests fonctionnels (avec authentification)
# ===========================================================================
def test_full_product_lifecycle():
    """Test complet du cycle de vie d'un produit avec authentification."""
    token = _admin_token()

    # Création
    res = client.post("/api/products", json={
        "title": "iPhone Test Sécurité",
        "category": "smartphones",
        "description": "Produit de test",
        "price": 850000.0,
        "discount_percent": 10.0,
        "images": ["https://images.unsplash.com/photo-test"],
        "stock": 5,
        "is_featured": False
    }, headers=_auth(token))
    assert res.status_code == 201
    prod = res.json()
    prod_id = prod["id"]
    assert prod["title"] == "iPhone Test Sécurité"
    assert prod["likes"] == 0

    # Like (sans auth)
    like_res = client.post(f"/api/products/{prod_id}/like?action=like")
    assert like_res.status_code == 200
    assert like_res.json()["likes"] == 1

    # Unlike (sans auth)
    unlike_res = client.post(f"/api/products/{prod_id}/like?action=unlike")
    assert unlike_res.status_code == 200
    assert unlike_res.json()["likes"] == 0

    # Lecture publique
    get_res = client.get(f"/api/products/{prod_id}")
    assert get_res.status_code == 200

    # Suppression (avec auth)
    del_res = client.delete(f"/api/products/{prod_id}", headers=_auth(token))
    assert del_res.status_code == 200

    # Vérification suppression
    assert client.get(f"/api/products/{prod_id}").status_code == 404

def test_get_categories_public():
    res = client.get("/api/categories")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_get_settings_public():
    res = client.get("/api/settings")
    assert res.status_code == 200
    data = res.json()
    assert "whatsapp_phone" in data
    assert "store_name" in data
    assert "currency" in data
