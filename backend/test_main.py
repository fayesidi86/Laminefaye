import os
import pytest
import hashlib
import secrets
import time
from collections import defaultdict
from fastapi.testclient import TestClient

# =============================================================================
# Config test AVANT import de l'app
# =============================================================================
_TEST_EMAIL    = "admin@test.com"
_TEST_PASSWORD = "TestPassword_Security2026!"
_TEST_EMAIL_HASH = hashlib.sha256(_TEST_EMAIL.encode()).hexdigest()
_TEST_PASS_HASH  = hashlib.sha256(_TEST_PASSWORD.encode()).hexdigest()

os.environ["ADMIN_EMAIL_HASH"] = _TEST_EMAIL_HASH
os.environ["ADMIN_PASS_HASH"]  = _TEST_PASS_HASH
os.environ["ADMIN_SECRET_KEY"] = secrets.token_hex(32)
os.environ["ALLOWED_ORIGINS"]  = "http://localhost:3000"
os.environ["SUPABASE_URL"]     = "https://mock.supabase.co"
os.environ["SUPABASE_KEY"]     = "mock-key"

# =============================================================================
# Mock Supabase en mémoire
# =============================================================================
class _MockResult:
    def __init__(self, data):
        self.data  = data if data else []
        self.count = len(self.data)

class _MockQuery:
    def __init__(self, store, table):
        self._store   = store
        self._table   = table
        self._op      = None
        self._payload = None
        self._filters = []   # list of (col, val)
        self._or      = None
        self._order_col = None
        self._order_desc = False

    # Fluent builders
    def select(self, columns="*", count=None):
        self._op = "select"
        return self

    def insert(self, data):
        self._op      = "insert"
        self._payload = data
        return self

    def update(self, data):
        self._op      = "update"
        self._payload = data
        return self

    def upsert(self, data):
        self._op      = "upsert"
        self._payload = data
        return self

    def delete(self):
        self._op = "delete"
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def or_(self, expr):
        self._or = expr
        return self

    def order(self, col, desc=False):
        self._order_col  = col
        self._order_desc = desc
        return self

    def _matches(self, row):
        for col, val in self._filters:
            if row.get(col) != val:
                return False
        return True

    def _filter(self, rows):
        filtered = [r for r in rows if self._matches(r)]
        # OR ilike search (titre/description)
        if self._or and "ilike" in self._or:
            parts = self._or.split(",")
            terms = []
            for part in parts:
                # format: "title.ilike.%term%"
                pieces = part.strip().split(".")
                if len(pieces) >= 3:
                    col  = pieces[0]
                    term = ".".join(pieces[2:]).strip("%")
                    terms.append((col, term.lower()))
            filtered = [
                r for r in filtered
                if any(term in str(r.get(col, "")).lower() for col, term in terms)
            ]
        return filtered

    def execute(self):
        table = self._store[self._table]

        if self._op == "select":
            rows = self._filter(list(table))
            if self._order_col:
                rows.sort(key=lambda r: r.get(self._order_col, 0), reverse=self._order_desc)
            return _MockResult([dict(r) for r in rows])

        elif self._op == "insert":
            if isinstance(self._payload, list):
                for item in self._payload:
                    table.append(dict(item))
                return _MockResult([dict(i) for i in self._payload])
            else:
                table.append(dict(self._payload))
                return _MockResult([dict(self._payload)])

        elif self._op == "update":
            updated = []
            for row in table:
                if self._matches(row):
                    row.update(self._payload)
                    updated.append(dict(row))
            return _MockResult(updated)

        elif self._op == "upsert":
            data = dict(self._payload)
            key  = data.get("key")
            for row in table:
                if row.get("key") == key:
                    row.update(data)
                    return _MockResult([dict(row)])
            table.append(data)
            return _MockResult([data])

        elif self._op == "delete":
            before = len(table)
            self._store[self._table] = [r for r in table if not self._matches(r)]
            return _MockResult([])

        return _MockResult([])


class _MockSupabase:
    def __init__(self):
        self._store = defaultdict(list)
        # Données par défaut pour les tests
        self._store["categories"] = [
            {"id": "smartphones", "name": "Smartphones & Téléphones"},
            {"id": "laptops",     "name": "Ordinateurs & PC Portables"},
        ]
        self._store["settings"] = [{
            "key": "main",
            "whatsapp_phone": "22373022223",
            "store_name": "Faye Store",
            "currency": "FCFA"
        }]

    def table(self, name):
        return _MockQuery(self._store, name)


# Injecter le mock dans le module main
_mock_sb = _MockSupabase()

import main as _main_module
_main_module.get_supabase = lambda: _mock_sb
_main_module.SUPABASE_URL = "https://mock.supabase.co"
_main_module.SUPABASE_KEY = "mock-key"

from main import app, _rate_store

client = TestClient(app)

# ===========================================================================
# Helpers
# ===========================================================================
def _reset():
    _rate_store.clear()

def _admin_token():
    _reset()
    res = client.post("/api/admin/login", json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return res.json()["token"]

def _auth(token):
    return {"Authorization": f"Bearer {token}"}

# ===========================================================================
# Tests de santé
# ===========================================================================
def test_health():
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/health").json()["status"] == "ok"

def test_docs_disabled():
    assert client.get("/docs").status_code        == 404
    assert client.get("/redoc").status_code       == 404
    assert client.get("/openapi.json").status_code == 404

# ===========================================================================
# Tests d'authentification
# ===========================================================================
def test_admin_login_success():
    res = client.post("/api/admin/login", json={"email": _TEST_EMAIL, "password": _TEST_PASSWORD})
    assert res.status_code == 200
    assert "token" in res.json()
    assert len(res.json()["token"]) > 20

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
# Tests de contrôle d'accès
# ===========================================================================
def test_create_product_without_auth():
    res = client.post("/api/products", json={
        "title": "Hacker", "category": "smartphones",
        "description": "Test", "price": 1.0, "images": ["https://test.com/img.jpg"]
    })
    assert res.status_code == 401

def test_delete_product_without_auth():
    assert client.delete("/api/products/prod-quelconque").status_code == 401

def test_create_category_without_auth():
    assert client.post("/api/categories", json={"name": "Cat Hacker"}).status_code == 401

def test_delete_category_without_auth():
    assert client.delete("/api/categories/smartphones").status_code == 401

def test_update_settings_without_auth():
    assert client.post("/api/settings", json={"whatsapp_phone": "00000000000"}).status_code == 401

def test_invalid_token_rejected():
    fake = "ce_token_est_faux_" + secrets.token_hex(16)
    res = client.post("/api/products", json={
        "title": "Test", "category": "smartphones", "description": "Test",
        "price": 1.0, "images": ["https://test.com/img.jpg"]
    }, headers={"Authorization": f"Bearer {fake}"})
    assert res.status_code == 401

# ===========================================================================
# Tests de validation / sécurité
# ===========================================================================
def test_xss_in_category_name_sanitized():
    token = _admin_token()
    res = client.post("/api/categories",
        json={"name": "<script>alert(1)</script>"},
        headers=_auth(token)
    )
    if res.status_code == 201:
        assert "<script>" not in res.json()["name"]
        client.delete(f"/api/categories/{res.json()['id']}", headers=_auth(token))

def test_oversized_product_title_rejected():
    token = _admin_token()
    res = client.post("/api/products", json={
        "title": "T" * 201, "category": "smartphones",
        "description": "Test", "price": 1.0, "images": ["https://test.com/img.jpg"]
    }, headers=_auth(token))
    assert res.status_code == 422

def test_oversized_description_rejected():
    token = _admin_token()
    res = client.post("/api/products", json={
        "title": "Test", "category": "smartphones",
        "description": "D" * 5001, "price": 1.0, "images": ["https://test.com/img.jpg"]
    }, headers=_auth(token))
    assert res.status_code == 422

def test_too_many_images_rejected():
    token = _admin_token()
    res = client.post("/api/products", json={
        "title": "Test", "category": "smartphones",
        "description": "Test", "price": 1.0,
        "images": [f"https://test.com/img{i}.jpg" for i in range(11)]
    }, headers=_auth(token))
    assert res.status_code == 422

def test_negative_price_rejected():
    token = _admin_token()
    res = client.post("/api/products", json={
        "title": "Test", "category": "smartphones",
        "description": "Test", "price": -100.0, "images": ["https://test.com/img.jpg"]
    }, headers=_auth(token))
    assert res.status_code == 422

def test_invalid_phone_in_settings():
    token = _admin_token()
    res = client.post("/api/settings", json={"whatsapp_phone": "abc"}, headers=_auth(token))
    assert res.status_code == 422

def test_invalid_image_url_rejected():
    token = _admin_token()
    res = client.post("/api/products", json={
        "title": "Test", "category": "smartphones",
        "description": "Test", "price": 100.0,
        "images": ["javascript:alert(1)"]
    }, headers=_auth(token))
    assert res.status_code == 422

def test_product_id_path_traversal():
    res = client.get("/api/products/../../etc/passwd")
    assert res.status_code in [400, 404]

def test_like_action_validation():
    res = client.post("/api/products/some-id/like?action=DROP+TABLE")
    assert res.status_code in [400, 404, 422]

# ===========================================================================
# Tests fonctionnels
# ===========================================================================
def test_full_product_lifecycle():
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

    # Like
    _reset()
    like_res = client.post(f"/api/products/{prod_id}/like?action=like")
    assert like_res.status_code == 200
    assert like_res.json()["likes"] == 1

    # Unlike
    unlike_res = client.post(f"/api/products/{prod_id}/like?action=unlike")
    assert unlike_res.status_code == 200
    assert unlike_res.json()["likes"] == 0

    # Lecture
    get_res = client.get(f"/api/products/{prod_id}")
    assert get_res.status_code == 200

    # Suppression
    del_res = client.delete(f"/api/products/{prod_id}", headers=_auth(token))
    assert del_res.status_code == 200

    # Vérification
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
