import json
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
# LOGGING SÉCURISÉ (jamais de stacktrace complète en prod)
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("faye-store")

# =============================================================================
# CONFIGURATION DEPUIS LES VARIABLES D'ENVIRONNEMENT
# Les secrets NE DOIVENT JAMAIS être en dur dans le code source.
# Définissez ces variables dans le dashboard Render.com :
#   ADMIN_EMAIL_HASH  = sha256 de l'email admin (en minuscules)
#   ADMIN_PASS_HASH   = sha256 du mot de passe admin
#   ADMIN_SECRET_KEY  = clé aléatoire longue (openssl rand -hex 32)
#   ALLOWED_ORIGINS   = origines autorisées séparées par des virgules
# =============================================================================
def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

# Valeurs de référence: si les variables d'env ne sont pas définies, on
# utilise des valeurs hachées par défaut (sécurisées à la définition, mais
# l'administrateur DOIT définir ses propres variables dans Render).
ADMIN_EMAIL_HASH = os.environ.get(
    "ADMIN_EMAIL_HASH",
    _sha256("laminefaye@gmail.com")   # sha256 de l'email par défaut
)
ADMIN_PASS_HASH = os.environ.get(
    "ADMIN_PASS_HASH",
    _sha256("lamine2026")             # sha256 du mot de passe par défaut
)
ADMIN_SECRET_KEY = os.environ.get(
    "ADMIN_SECRET_KEY",
    secrets.token_hex(32)             # clé éphémère si non définie (tokens invalidés à chaque redémarrage)
)

ALLOWED_ORIGINS_RAW = os.environ.get(
    "ALLOWED_ORIGINS",
    "https://laminefaye.vercel.app,http://localhost:3000,http://localhost:5173"
)
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS_RAW.split(",") if o.strip()]

# Durée de validité d'un token admin (secondes)
ADMIN_TOKEN_TTL = int(os.environ.get("ADMIN_TOKEN_TTL", "3600"))

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")

# =============================================================================
# LIMITES DE TAILLE DES DONNÉES (DoS / Storage Bomb Protection)
# =============================================================================
MAX_TITLE_LEN        = 200
MAX_DESC_LEN         = 5000
MAX_CATEGORY_NAME    = 80
MAX_IMAGES_COUNT     = 10
MAX_IMAGE_URL_LEN    = 2_000_000  # ~2MB pour les base64
MAX_PHONE_LEN        = 20
MAX_STORE_NAME_LEN   = 100
MAX_CURRENCY_LEN     = 10
MAX_PRODUCTS_TOTAL   = 500
MAX_CATEGORIES_TOTAL = 50
MAX_SEARCH_QUERY_LEN = 200

# =============================================================================
# IN-MEMORY RATE LIMITER (simple, par IP)
# =============================================================================
_rate_store: dict = defaultdict(lambda: {"count": 0, "reset": 0.0})

def _get_client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"

def _check_rate_limit(request: Request, limit: int, window: int) -> None:
    """Vérifie et incrémente le compteur de requêtes par IP."""
    ip = _get_client_ip(request)
    now = time.time()
    bucket = _rate_store[ip]
    if now > bucket["reset"]:
        bucket["count"] = 0
        bucket["reset"] = now + window
    bucket["count"] += 1
    if bucket["count"] > limit:
        logger.warning(f"Rate limit exceeded for IP {ip}")
        raise HTTPException(
            status_code=429,
            detail="Trop de requêtes. Veuillez patienter."
        )

# Dépendances pour les différents seuils
def rate_limit_public(request: Request):
    """Limite standard pour les endpoints publics."""
    _check_rate_limit(request, limit=60, window=60)

def rate_limit_write(request: Request):
    """Limite plus stricte pour les écritures publiques (likes)."""
    _check_rate_limit(request, limit=30, window=60)

def rate_limit_auth(request: Request):
    """Limite très stricte pour les tentatives d'authentification."""
    _check_rate_limit(request, limit=10, window=300)  # 10 tentatives / 5 minutes

# =============================================================================
# IN-MEMORY TOKEN STORE pour les sessions admin
# =============================================================================
_admin_tokens: dict = {}  # token -> expiry_timestamp

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
    """Extrait et valide le token admin depuis l'en-tête Authorization."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise."
        )
    token = auth[7:]
    if not _validate_admin_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expirée ou invalide. Veuillez vous reconnecter."
        )
    return token

# =============================================================================
# PERSISTANCE JSON
# =============================================================================
def load_data() -> dict:
    try:
        if not os.path.exists(DATA_FILE):
            initial_data = {
                "categories": [
                    {"id": "smartphones",  "name": "Smartphones & Téléphones"},
                    {"id": "laptops",      "name": "Ordinateurs & PC Portables"},
                    {"id": "audio",        "name": "Audio, Casques & Écouteurs"},
                    {"id": "accessoires",  "name": "Accessoires & Connectique"},
                    {"id": "montres",      "name": "Montres Connectées & Wearables"}
                ],
                "products": [],
                "settings": {
                    "whatsapp_phone": "22373022223",
                    "store_name": "Faye Store",
                    "currency": "FCFA"
                }
            }
            save_data(initial_data)
            return initial_data
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erreur lecture data.json: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur.")

def save_data(data: dict) -> None:
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Erreur écriture data.json: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur.")

# =============================================================================
# SANITISATION DES TEXTES (protection XSS Stored)
# =============================================================================
def _sanitize_text(text: str) -> str:
    """Supprime les balises HTML/script des champs textuels."""
    if not isinstance(text, str):
        return ""
    # Suppression des balises HTML
    cleaned = re.sub(r'<[^>]+>', '', text)
    return cleaned.strip()

def _validate_phone(phone: str) -> str:
    """Valide que le numéro de téléphone ne contient que des chiffres."""
    digits_only = re.sub(r'[^0-9]', '', phone)
    if len(digits_only) < 7 or len(digits_only) > MAX_PHONE_LEN:
        raise ValueError("Numéro de téléphone invalide (7-20 chiffres).")
    return digits_only

def _validate_image_url(url: str) -> str:
    """Accepte les URL https:// et les data URI base64."""
    url = url.strip()
    if url.startswith("data:image/"):
        if len(url) > MAX_IMAGE_URL_LEN:
            raise ValueError(f"Image base64 trop grande (max {MAX_IMAGE_URL_LEN // 1_000_000}MB).")
        return url
    if url.startswith("https://") or url.startswith("http://"):
        if len(url) > 2048:
            raise ValueError("URL d'image trop longue.")
        return url
    raise ValueError(f"URL d'image invalide: doit commencer par https:// ou être une image base64.")

# =============================================================================
# MODÈLES PYDANTIC (avec validation renforcée)
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
    title:            str   = Field(..., min_length=1,  max_length=MAX_TITLE_LEN)
    category:         str   = Field(..., min_length=1,  max_length=80)
    description:      str   = Field(..., min_length=0,  max_length=MAX_DESC_LEN)
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
        validated = []
        for url in imgs:
            validated.append(_validate_image_url(url))
        return validated

class SettingsUpdate(BaseModel):
    whatsapp_phone: Optional[str] = Field(None, max_length=MAX_PHONE_LEN)
    store_name:     Optional[str] = Field(None, max_length=MAX_STORE_NAME_LEN)
    currency:       Optional[str] = Field(None, max_length=MAX_CURRENCY_LEN)

    @field_validator("whatsapp_phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_phone(v)
        return v

    @field_validator("store_name", "currency")
    @classmethod
    def sanitize_settings(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _sanitize_text(v)
        return v

# =============================================================================
# APPLICATION FASTAPI
# =============================================================================
app = FastAPI(
    title="Faye Store API",
    version="2.0.0",
    # Désactivation de la documentation automatique en production
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

# -----------------------------------------------------------------------------
# MIDDLEWARE: En-têtes de sécurité HTTP
# -----------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["X-Frame-Options"]           = "DENY"
        response.headers["X-XSS-Protection"]          = "1; mode=block"
        response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]        = "geolocation=(), microphone=(), camera=()"
        response.headers["Cache-Control"]             = "no-store, no-cache, must-revalidate"
        # HSTS activé uniquement en production (Render utilise HTTPS)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# -----------------------------------------------------------------------------
# CORS: origines strictement définies
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,       # jamais "*" en production
    allow_credentials=False,             # pas de cookies cross-origin
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# =============================================================================
# ROUTES PUBLIQUES (lecture)
# =============================================================================
@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/categories", dependencies=[Depends(rate_limit_public)])
def get_categories():
    data = load_data()
    return data.get("categories", [])

@app.get("/api/products", dependencies=[Depends(rate_limit_public)])
def get_products(
    category: Optional[str] = Query(None, max_length=80),
    q:        Optional[str] = Query(None, max_length=MAX_SEARCH_QUERY_LEN)
):
    data = load_data()
    products = data.get("products", [])
    if category and category != "all":
        # Nettoyage du filtre catégorie (évite les injections)
        safe_cat = _sanitize_text(category)
        products = [p for p in products if p.get("category") == safe_cat]
    if q:
        query_str = _sanitize_text(q).lower()
        products = [
            p for p in products
            if query_str in p.get("title", "").lower()
            or query_str in p.get("description", "").lower()
        ]
    return products

@app.get("/api/products/{product_id}", dependencies=[Depends(rate_limit_public)])
def get_product_by_id(product_id: str):
    if not re.match(r'^[a-zA-Z0-9_-]{1,80}$', product_id):
        raise HTTPException(status_code=400, detail="Identifiant produit invalide.")
    data = load_data()
    for p in data.get("products", []):
        if p["id"] == product_id:
            return p
    raise HTTPException(status_code=404, detail="Produit non trouvé.")

@app.get("/api/settings", dependencies=[Depends(rate_limit_public)])
def get_settings():
    data = load_data()
    s = data.get("settings", {})
    # On ne renvoie que les champs nécessaires au frontend
    return {
        "whatsapp_phone": s.get("whatsapp_phone", "22373022223"),
        "store_name":     s.get("store_name", "Faye Store"),
        "currency":       s.get("currency", "FCFA")
    }

# =============================================================================
# ROUTE D'AUTHENTIFICATION ADMIN
# =============================================================================
@app.post("/api/admin/login", dependencies=[Depends(rate_limit_auth)])
def admin_login(payload: AdminLoginRequest):
    """
    Authentification de l'administrateur.
    Compare les hash SHA-256 — les identifiants en clair ne transitent pas
    dans les logs et ne sont pas stockés côté serveur.
    """
    email_hash = _sha256(payload.email.strip().lower())
    pass_hash  = _sha256(payload.password)

    # Comparaison résistante aux attaques temporelles
    email_ok = secrets.compare_digest(email_hash, ADMIN_EMAIL_HASH)
    pass_ok  = secrets.compare_digest(pass_hash,  ADMIN_PASS_HASH)

    if not (email_ok and pass_ok):
        logger.warning("Tentative de connexion admin échouée.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiant ou mot de passe incorrect."
        )

    token = _generate_admin_token()
    logger.info("Connexion admin réussie.")
    return {"token": token, "expires_in": ADMIN_TOKEN_TTL}

@app.post("/api/admin/logout")
def admin_logout(token: str = Depends(_get_admin_token)):
    _admin_tokens.pop(token, None)
    return {"message": "Déconnecté."}

# =============================================================================
# ROUTES PROTÉGÉES (écriture — nécessitent un token admin valide)
# =============================================================================
@app.post("/api/categories", status_code=status.HTTP_201_CREATED)
def create_category(
    category: CategoryCreate,
    _token: str = Depends(_get_admin_token)
):
    data = load_data()
    if len(data["categories"]) >= MAX_CATEGORIES_TOTAL:
        raise HTTPException(status_code=400, detail="Nombre maximum de catégories atteint.")
    cat_id = category.id or re.sub(r'[^a-z0-9-]', '', category.name.lower().replace(" ", "-"))[:60]
    if not cat_id:
        raise HTTPException(status_code=400, detail="Nom de catégorie invalide.")
    for c in data["categories"]:
        if c["id"] == cat_id:
            raise HTTPException(status_code=400, detail="Catégorie déjà existante.")
    new_cat = {"id": cat_id, "name": category.name}
    data["categories"].append(new_cat)
    save_data(data)
    return new_cat

@app.delete("/api/categories/{category_id}")
def delete_category(
    category_id: str,
    _token: str = Depends(_get_admin_token)
):
    if not re.match(r'^[a-zA-Z0-9_-]{1,80}$', category_id):
        raise HTTPException(status_code=400, detail="Identifiant catégorie invalide.")
    data = load_data()
    data["categories"] = [c for c in data["categories"] if c["id"] != category_id]
    save_data(data)
    return {"message": "Catégorie supprimée avec succès."}

@app.post("/api/products", status_code=status.HTTP_201_CREATED)
def create_product(
    product: ProductCreate,
    _token: str = Depends(_get_admin_token)
):
    data = load_data()
    if len(data["products"]) >= MAX_PRODUCTS_TOTAL:
        raise HTTPException(status_code=400, detail="Nombre maximum de produits atteint.")
    new_id = f"prod-{int(time.time())}-{os.urandom(3).hex()}"
    new_prod = product.model_dump()
    new_prod["id"]    = new_id
    new_prod["likes"] = 0
    data["products"].insert(0, new_prod)
    save_data(data)
    logger.info(f"Produit créé: {new_id}")
    return new_prod

@app.put("/api/products/{product_id}")
def update_product(
    product_id: str,
    product: ProductCreate,
    _token: str = Depends(_get_admin_token)
):
    if not re.match(r'^[a-zA-Z0-9_-]{1,80}$', product_id):
        raise HTTPException(status_code=400, detail="Identifiant produit invalide.")
    data = load_data()
    for idx, p in enumerate(data.get("products", [])):
        if p["id"] == product_id:
            updated = product.model_dump()
            updated["id"]    = product_id
            updated["likes"] = p.get("likes", 0)
            data["products"][idx] = updated
            save_data(data)
            return updated
    raise HTTPException(status_code=404, detail="Produit non trouvé.")

@app.delete("/api/products/{product_id}")
def delete_product(
    product_id: str,
    _token: str = Depends(_get_admin_token)
):
    if not re.match(r'^[a-zA-Z0-9_-]{1,80}$', product_id):
        raise HTTPException(status_code=400, detail="Identifiant produit invalide.")
    data = load_data()
    initial_len = len(data["products"])
    data["products"] = [p for p in data["products"] if p["id"] != product_id]
    if len(data["products"]) == initial_len:
        raise HTTPException(status_code=404, detail="Produit non trouvé.")
    save_data(data)
    logger.info(f"Produit supprimé: {product_id}")
    return {"message": "Produit supprimé avec succès."}

@app.post("/api/settings")
def update_settings(
    settings: SettingsUpdate,
    _token: str = Depends(_get_admin_token)
):
    data = load_data()
    if "settings" not in data:
        data["settings"] = {}
    if settings.whatsapp_phone is not None:
        data["settings"]["whatsapp_phone"] = settings.whatsapp_phone
    if settings.store_name is not None:
        data["settings"]["store_name"] = settings.store_name
    if settings.currency is not None:
        data["settings"]["currency"] = settings.currency
    save_data(data)
    return data["settings"]

# =============================================================================
# ROUTE DE LIKE (semi-publique — limitée mais sans auth)
# =============================================================================
@app.post("/api/products/{product_id}/like", dependencies=[Depends(rate_limit_write)])
def toggle_like_product(
    product_id: str,
    action: str = Query("like", pattern="^(like|unlike)$")
):
    if not re.match(r'^[a-zA-Z0-9_-]{1,80}$', product_id):
        raise HTTPException(status_code=400, detail="Identifiant produit invalide.")
    data = load_data()
    for p in data.get("products", []):
        if p["id"] == product_id:
            current_likes = p.get("likes", 0)
            p["likes"] = current_likes + 1 if action == "like" else max(0, current_likes - 1)
            save_data(data)
            return {"id": product_id, "likes": p["likes"]}
    raise HTTPException(status_code=404, detail="Produit non trouvé.")

# =============================================================================
# GESTIONNAIRE D'ERREURS GLOBAL (pas de stacktrace en production)
# =============================================================================
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erreur interne: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur."}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
