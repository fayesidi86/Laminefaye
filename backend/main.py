import os
import re
import logging
import secrets
import hashlib
import time
from typing import List, Optional
from collections import defaultdict

from fastapi import FastAPI, HTTPException, Query, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from starlette.middleware.base import BaseHTTPMiddleware

# =============================================================================
# LOGGING SÉCURISÉ
# =============================================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("faye-store")

# =============================================================================
# CONFIGURATION DEPUIS LES VARIABLES D'ENVIRONNEMENT
# =============================================================================
def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

ADMIN_EMAIL_HASH = os.environ.get("ADMIN_EMAIL_HASH", _sha256("laminefaye@gmail.com"))
ADMIN_PASS_HASH  = os.environ.get("ADMIN_PASS_HASH",  _sha256("lamine2026"))
ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", secrets.token_hex(32))

ALLOWED_ORIGINS_RAW = os.environ.get(
    "ALLOWED_ORIGINS",
    "https://laminefaye.vercel.app,http://localhost:3000,http://localhost:5173"
)
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS_RAW.split(",") if o.strip()]
ADMIN_TOKEN_TTL = int(os.environ.get("ADMIN_TOKEN_TTL", "3600"))

# Variables Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")  # service_role key

# =============================================================================
# LIMITES DE TAILLE
# =============================================================================
MAX_TITLE_LEN        = 200
MAX_DESC_LEN         = 5000
MAX_CATEGORY_NAME    = 80
MAX_IMAGES_COUNT     = 10
MAX_IMAGE_URL_LEN    = 2_000_000
MAX_PHONE_LEN        = 20
MAX_STORE_NAME_LEN   = 100
MAX_CURRENCY_LEN     = 10
MAX_PRODUCTS_TOTAL   = 500
MAX_CATEGORIES_TOTAL = 50
MAX_SEARCH_QUERY_LEN = 200

# =============================================================================
# CONNEXION SUPABASE (lazy, singleton)
# =============================================================================
_supabase_client = None

def get_supabase():
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(
            status_code=503,
            detail="Base de données non configurée. Contactez l'administrateur."
        )
    try:
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return _supabase_client
    except Exception as e:
        logger.error(f"Erreur connexion Supabase: {e}")
        raise HTTPException(status_code=503, detail="Erreur de connexion à la base de données.")

def _ensure_defaults():
    """Initialise les données par défaut si les tables sont vides."""
    try:
        sb = get_supabase()
        # Catégories par défaut
        cats = sb.table("categories").select("id").execute()
        if not cats.data:
            sb.table("categories").insert([
                {"id": "smartphones",  "name": "Smartphones & Téléphones"},
                {"id": "laptops",      "name": "Ordinateurs & PC Portables"},
                {"id": "audio",        "name": "Audio, Casques & Écouteurs"},
                {"id": "accessoires",  "name": "Accessoires & Connectique"},
                {"id": "montres",      "name": "Montres Connectées & Wearables"},
            ]).execute()
            logger.info("Catégories par défaut créées.")
        # Paramètres par défaut
        settings = sb.table("settings").select("key").eq("key", "main").execute()
        if not settings.data:
            sb.table("settings").insert({
                "key": "main",
                "whatsapp_phone": "22373022223",
                "store_name": "Faye Store",
                "currency": "FCFA"
            }).execute()
            logger.info("Paramètres par défaut créés.")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur init defaults: {e}")

# =============================================================================
# IN-MEMORY RATE LIMITER (par IP)
# =============================================================================
_rate_store: dict = defaultdict(lambda: {"count": 0, "reset": 0.0})

def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def _check_rate_limit(request: Request, limit: int, window: int) -> None:
    ip = _get_client_ip(request)
    now = time.time()
    bucket = _rate_store[ip]
    if now > bucket["reset"]:
        bucket["count"] = 0
        bucket["reset"] = now + window
    bucket["count"] += 1
    if bucket["count"] > limit:
        logger.warning(f"Rate limit exceeded for IP {ip}")
        raise HTTPException(status_code=429, detail="Trop de requêtes. Veuillez patienter.")

def rate_limit_public(request: Request):  _check_rate_limit(request, limit=60, window=60)
def rate_limit_write(request: Request):   _check_rate_limit(request, limit=30, window=60)
def rate_limit_auth(request: Request):    _check_rate_limit(request, limit=10, window=300)

# =============================================================================
# IN-MEMORY TOKEN STORE (sessions admin)
# =============================================================================
_admin_tokens: dict = {}

def _generate_admin_token() -> str:
    token = secrets.token_urlsafe(48)
    _admin_tokens[token] = time.time() + ADMIN_TOKEN_TTL
    return token

def _validate_admin_token(token: str) -> bool:
    exp = _admin_tokens.get(token)
    if exp is None:
        return False
    if time.time() > exp:
        _admin_tokens.pop(token, None)
        return False
    return True

def _get_admin_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise.")
    token = auth[7:]
    if not _validate_admin_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expirée ou invalide. Veuillez vous reconnecter.")
    return token

# =============================================================================
# SANITISATION & VALIDATION
# =============================================================================
def _sanitize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return re.sub(r'<[^>]+>', '', text).strip()

def _validate_phone(phone: str) -> str:
    digits_only = re.sub(r'[^0-9]', '', phone)
    if len(digits_only) < 7 or len(digits_only) > MAX_PHONE_LEN:
        raise ValueError("Numéro de téléphone invalide (7-20 chiffres).")
    return digits_only

def _validate_image_url(url: str) -> str:
    url = url.strip()
    if url.startswith("data:image/"):
        if len(url) > MAX_IMAGE_URL_LEN:
            raise ValueError(f"Image base64 trop grande (max {MAX_IMAGE_URL_LEN // 1_000_000}MB).")
        return url
    if url.startswith("https://") or url.startswith("http://"):
        if len(url) > 2048:
            raise ValueError("URL d'image trop longue.")
        return url
    raise ValueError("URL d'image invalide: doit commencer par https:// ou être une image base64.")

def _clean_product(p: dict) -> dict:
    """Retire les champs internes avant d'envoyer au frontend."""
    p.pop("created_at", None)
    return p

# =============================================================================
# MODÈLES PYDANTIC
# =============================================================================
class AdminLoginRequest(BaseModel):
    email: str = Field(..., max_length=254)
    password: str = Field(..., max_length=200)

class CategoryCreate(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=MAX_CATEGORY_NAME)

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        return _sanitize_text(v)

class ProductCreate(BaseModel):
    title:            str   = Field(..., min_length=1, max_length=MAX_TITLE_LEN)
    category:         str   = Field(..., min_length=1, max_length=80)
    description:      str   = Field(..., min_length=0, max_length=MAX_DESC_LEN)
    price:            float = Field(..., gt=0, le=100_000_000)
    discount_percent: float = Field(default=0.0, ge=0, le=100)
    images:           List[str] = Field(..., min_length=1, max_length=MAX_IMAGES_COUNT)
    stock:            int   = Field(default=10, ge=0, le=100_000)
    is_featured:      bool  = False

    @field_validator("title", "description", "category")
    @classmethod
    def sanitize_strings(cls, v: str) -> str:
        return _sanitize_text(v)

    @field_validator("images")
    @classmethod
    def validate_images(cls, imgs: List[str]) -> List[str]:
        return [_validate_image_url(url) for url in imgs]

class SettingsUpdate(BaseModel):
    whatsapp_phone: Optional[str] = Field(None, max_length=MAX_PHONE_LEN)
    store_name:     Optional[str] = Field(None, max_length=MAX_STORE_NAME_LEN)
    currency:       Optional[str] = Field(None, max_length=MAX_CURRENCY_LEN)

    @field_validator("whatsapp_phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone(v) if v is not None else v

    @field_validator("store_name", "currency")
    @classmethod
    def sanitize_settings(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_text(v) if v is not None else v

# =============================================================================
# APPLICATION FASTAPI
# =============================================================================
app = FastAPI(
    title="Faye Store API",
    version="3.0.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["X-Frame-Options"]           = "DENY"
        response.headers["X-XSS-Protection"]          = "1; mode=block"
        response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]        = "geolocation=(), microphone=(), camera=()"
        response.headers["Cache-Control"]             = "no-store, no-cache, must-revalidate"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# =============================================================================
# ROUTES PUBLIQUES
# =============================================================================
@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/categories", dependencies=[Depends(rate_limit_public)])
def get_categories():
    sb = get_supabase()
    result = sb.table("categories").select("id, name").execute()
    return result.data or []

@app.get("/api/products", dependencies=[Depends(rate_limit_public)])
def get_products(
    category: Optional[str] = Query(None, max_length=80),
    q:        Optional[str] = Query(None, max_length=MAX_SEARCH_QUERY_LEN)
):
    sb = get_supabase()
    query = sb.table("products").select(
        "id, title, category, description, price, discount_percent, images, stock, is_featured, likes"
    ).order("created_at", desc=True)

    if category and category != "all":
        safe_cat = _sanitize_text(category)
        query = query.eq("category", safe_cat)

    if q:
        safe_q = _sanitize_text(q)
        query = query.or_(f"title.ilike.%{safe_q}%,description.ilike.%{safe_q}%")

    result = query.execute()
    return result.data or []

@app.get("/api/products/{product_id}", dependencies=[Depends(rate_limit_public)])
def get_product_by_id(product_id: str):
    if not re.match(r'^[a-zA-Z0-9_-]{1,80}$', product_id):
        raise HTTPException(status_code=400, detail="Identifiant produit invalide.")
    sb = get_supabase()
    result = sb.table("products").select(
        "id, title, category, description, price, discount_percent, images, stock, is_featured, likes"
    ).eq("id", product_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Produit non trouvé.")
    return result.data[0]

@app.get("/api/settings", dependencies=[Depends(rate_limit_public)])
def get_settings():
    sb = get_supabase()
    result = sb.table("settings").select("whatsapp_phone, store_name, currency").eq("key", "main").execute()
    s = result.data[0] if result.data else {}
    return {
        "whatsapp_phone": s.get("whatsapp_phone", "22373022223"),
        "store_name":     s.get("store_name", "Faye Store"),
        "currency":       s.get("currency", "FCFA"),
    }

# =============================================================================
# AUTHENTIFICATION ADMIN
# =============================================================================
@app.post("/api/admin/login", dependencies=[Depends(rate_limit_auth)])
def admin_login(payload: AdminLoginRequest):
    email_hash = _sha256(payload.email.strip().lower())
    pass_hash  = _sha256(payload.password)
    email_ok = secrets.compare_digest(email_hash, ADMIN_EMAIL_HASH)
    pass_ok  = secrets.compare_digest(pass_hash,  ADMIN_PASS_HASH)
    if not (email_ok and pass_ok):
        logger.warning("Tentative de connexion admin échouée.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Identifiant ou mot de passe incorrect.")
    token = _generate_admin_token()
    logger.info("Connexion admin réussie.")
    return {"token": token, "expires_in": ADMIN_TOKEN_TTL}

@app.post("/api/admin/logout")
def admin_logout(token: str = Depends(_get_admin_token)):
    _admin_tokens.pop(token, None)
    return {"message": "Déconnecté."}

# =============================================================================
# ROUTES PROTÉGÉES (écriture)
# =============================================================================
@app.post("/api/categories", status_code=status.HTTP_201_CREATED)
def create_category(category: CategoryCreate, _token: str = Depends(_get_admin_token)):
    sb = get_supabase()
    count = len(sb.table("categories").select("id").execute().data or [])
    if count >= MAX_CATEGORIES_TOTAL:
        raise HTTPException(status_code=400, detail="Nombre maximum de catégories atteint.")
    cat_id = category.id or re.sub(r'[^a-z0-9-]', '', category.name.lower().replace(" ", "-"))[:60]
    if not cat_id:
        raise HTTPException(status_code=400, detail="Nom de catégorie invalide.")
    existing = sb.table("categories").select("id").eq("id", cat_id).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="Catégorie déjà existante.")
    new_cat = {"id": cat_id, "name": category.name}
    result = sb.table("categories").insert(new_cat).execute()
    return result.data[0] if result.data else new_cat

@app.delete("/api/categories/{category_id}")
def delete_category(category_id: str, _token: str = Depends(_get_admin_token)):
    if not re.match(r'^[a-zA-Z0-9_-]{1,80}$', category_id):
        raise HTTPException(status_code=400, detail="Identifiant catégorie invalide.")
    sb = get_supabase()
    sb.table("categories").delete().eq("id", category_id).execute()
    return {"message": "Catégorie supprimée avec succès."}

@app.post("/api/products", status_code=status.HTTP_201_CREATED)
def create_product(product: ProductCreate, _token: str = Depends(_get_admin_token)):
    sb = get_supabase()
    count = len(sb.table("products").select("id").execute().data or [])
    if count >= MAX_PRODUCTS_TOTAL:
        raise HTTPException(status_code=400, detail="Nombre maximum de produits atteint.")
    new_id = f"prod-{int(time.time())}-{os.urandom(3).hex()}"
    new_prod = product.model_dump()
    new_prod["id"]    = new_id
    new_prod["likes"] = 0
    result = sb.table("products").insert(new_prod).execute()
    created = result.data[0] if result.data else new_prod
    _clean_product(created)
    logger.info(f"Produit créé: {new_id}")
    return created

@app.put("/api/products/{product_id}")
def update_product(product_id: str, product: ProductCreate, _token: str = Depends(_get_admin_token)):
    if not re.match(r'^[a-zA-Z0-9_-]{1,80}$', product_id):
        raise HTTPException(status_code=400, detail="Identifiant produit invalide.")
    sb = get_supabase()
    existing = sb.table("products").select("id, likes").eq("id", product_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Produit non trouvé.")
    updated = product.model_dump()
    updated["id"]    = product_id
    updated["likes"] = existing.data[0].get("likes", 0)
    result = sb.table("products").update(updated).eq("id", product_id).execute()
    prod = result.data[0] if result.data else updated
    _clean_product(prod)
    return prod

@app.delete("/api/products/{product_id}")
def delete_product(product_id: str, _token: str = Depends(_get_admin_token)):
    if not re.match(r'^[a-zA-Z0-9_-]{1,80}$', product_id):
        raise HTTPException(status_code=400, detail="Identifiant produit invalide.")
    sb = get_supabase()
    existing = sb.table("products").select("id").eq("id", product_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Produit non trouvé.")
    sb.table("products").delete().eq("id", product_id).execute()
    logger.info(f"Produit supprimé: {product_id}")
    return {"message": "Produit supprimé avec succès."}

@app.post("/api/settings")
def update_settings(settings: SettingsUpdate, _token: str = Depends(_get_admin_token)):
    sb = get_supabase()
    update_fields = {}
    if settings.whatsapp_phone is not None:
        update_fields["whatsapp_phone"] = settings.whatsapp_phone
    if settings.store_name is not None:
        update_fields["store_name"] = settings.store_name
    if settings.currency is not None:
        update_fields["currency"] = settings.currency
    sb.table("settings").upsert({"key": "main", **update_fields}).execute()
    result = sb.table("settings").select("whatsapp_phone, store_name, currency").eq("key", "main").execute()
    s = result.data[0] if result.data else {}
    return {
        "whatsapp_phone": s.get("whatsapp_phone", "22373022223"),
        "store_name":     s.get("store_name", "Faye Store"),
        "currency":       s.get("currency", "FCFA"),
    }

# =============================================================================
# ROUTE DE LIKE (semi-publique)
# =============================================================================
@app.post("/api/products/{product_id}/like", dependencies=[Depends(rate_limit_write)])
def toggle_like_product(
    product_id: str,
    action: str = Query("like", pattern="^(like|unlike)$")
):
    if not re.match(r'^[a-zA-Z0-9_-]{1,80}$', product_id):
        raise HTTPException(status_code=400, detail="Identifiant produit invalide.")
    sb = get_supabase()
    existing = sb.table("products").select("id, likes").eq("id", product_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Produit non trouvé.")
    current_likes = existing.data[0].get("likes", 0)
    new_likes = current_likes + 1 if action == "like" else max(0, current_likes - 1)
    sb.table("products").update({"likes": new_likes}).eq("id", product_id).execute()
    return {"id": product_id, "likes": new_likes}

# =============================================================================
# GESTIONNAIRE D'ERREURS GLOBAL
# =============================================================================
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur interne: {type(exc).__name__}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur."})

# =============================================================================
# DÉMARRAGE
# =============================================================================
@app.on_event("startup")
def startup_event():
    logger.info("Démarrage Faye Store API v3.0 (Supabase)")
    if SUPABASE_URL and SUPABASE_KEY:
        _ensure_defaults()
    else:
        logger.warning("SUPABASE_URL/SUPABASE_KEY non configurés — base de données indisponible.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
