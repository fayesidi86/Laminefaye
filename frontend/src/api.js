/**
 * api.js — Client API sécurisé pour Faye Store
 *
 * Architecture de sécurité :
 * - Les routes d'écriture (POST/PUT/DELETE) nécessitent un token admin Bearer
 * - Le token est stocké uniquement en mémoire (variable de module), jamais en
 *   localStorage ni en cookie, pour limiter la surface d'attaque XSS.
 * - Le token est effacé dès la déconnexion ou l'expiration de session.
 * - Toutes les requêtes passent par des try/catch pour éviter les crashes.
 */

const API_URL = import.meta.env.VITE_API_URL || 'https://laminefaye.onrender.com/api';

// Token admin stocké uniquement en mémoire (jamais persisté côté client)
let _adminToken = null;
let _adminTokenExpiry = 0;

/** Renvoie le token valide ou null si expiré. */
function _getToken() {
  if (_adminToken && Date.now() < _adminTokenExpiry) {
    return _adminToken;
  }
  _adminToken = null;
  return null;
}

/** Stocke le token admin en mémoire avec sa date d'expiration. */
export function _setAdminToken(token, expiresInSeconds) {
  _adminToken = token;
  _adminTokenExpiry = Date.now() + expiresInSeconds * 1000;
}

/** Efface le token admin (logout). */
export function _clearAdminToken() {
  _adminToken = null;
  _adminTokenExpiry = 0;
}

/** Vérifie si une session admin est actuellement active. */
export function isAdminSessionActive() {
  return !!_getToken();
}

/**
 * Fabrique les headers d'une requête authentifiée.
 * Lance une erreur si aucun token n'est disponible.
 */
function _authHeaders() {
  const token = _getToken();
  if (!token) throw new Error('SESSION_EXPIRED');
  return {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  };
}

/** Gestion centralisée des erreurs API. */
function _handleError(context, err) {
  if (err.message === 'SESSION_EXPIRED') {
    _clearAdminToken();
    console.warn(`[API] Session expirée lors de: ${context}`);
    return 'SESSION_EXPIRED';
  }
  console.warn(`[API] Erreur dans ${context}:`, err.message || err);
  return null;
}

export const api = {
  // ===========================================================================
  // AUTHENTIFICATION ADMIN
  // ===========================================================================
  async adminLogin(email, password) {
    try {
      const res = await fetch(`${API_URL}/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Identifiant ou mot de passe incorrect.');
      }
      const data = await res.json();
      _setAdminToken(data.token, data.expires_in || 3600);
      return { success: true };
    } catch (err) {
      return { success: false, error: err.message };
    }
  },

  async adminLogout() {
    const token = _getToken();
    if (token) {
      try {
        await fetch(`${API_URL}/admin/logout`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        });
      } catch { /* on vide le token même si la requête échoue */ }
    }
    _clearAdminToken();
  },

  // ===========================================================================
  // CATÉGORIES (lecture publique, écriture protégée)
  // ===========================================================================
  async getCategories() {
    try {
      const res = await fetch(`${API_URL}/categories`);
      if (!res.ok) throw new Error('API request failed');
      return await res.json();
    } catch (err) {
      return _handleError('getCategories', err);
    }
  },

  async addCategory(name) {
    try {
      const res = await fetch(`${API_URL}/categories`, {
        method: 'POST',
        headers: _authHeaders(),
        body: JSON.stringify({ name })
      });
      if (res.status === 401) return _handleError('addCategory', new Error('SESSION_EXPIRED'));
      if (!res.ok) throw new Error('Failed to create category');
      return await res.json();
    } catch (err) {
      return _handleError('addCategory', err);
    }
  },

  async deleteCategory(id) {
    try {
      const res = await fetch(`${API_URL}/categories/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: _authHeaders()
      });
      if (res.status === 401) { _handleError('deleteCategory', new Error('SESSION_EXPIRED')); return false; }
      return res.ok;
    } catch (err) {
      _handleError('deleteCategory', err);
      return false;
    }
  },

  // ===========================================================================
  // PRODUITS (lecture publique, écriture protégée)
  // ===========================================================================
  async getProducts(category = null, q = null) {
    try {
      const params = new URLSearchParams();
      if (category && category !== 'all') params.append('category', category);
      if (q) params.append('q', q);
      const res = await fetch(`${API_URL}/products?${params.toString()}`);
      if (!res.ok) throw new Error('API request failed');
      return await res.json();
    } catch (err) {
      return _handleError('getProducts', err);
    }
  },

  async addProduct(product) {
    try {
      const res = await fetch(`${API_URL}/products`, {
        method: 'POST',
        headers: _authHeaders(),
        body: JSON.stringify(product)
      });
      if (res.status === 401) return _handleError('addProduct', new Error('SESSION_EXPIRED'));
      if (!res.ok) {
        const e = await res.json().catch(() => ({}));
        throw new Error(e.detail || 'Failed to create product');
      }
      return await res.json();
    } catch (err) {
      return _handleError('addProduct', err);
    }
  },

  async deleteProduct(id) {
    try {
      const res = await fetch(`${API_URL}/products/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: _authHeaders()
      });
      if (res.status === 401) { _handleError('deleteProduct', new Error('SESSION_EXPIRED')); return false; }
      return res.ok;
    } catch (err) {
      _handleError('deleteProduct', err);
      return false;
    }
  },

  // ===========================================================================
  // LIKES (semi-public — pas de token requis)
  // ===========================================================================
  async toggleLike(id, action = 'like') {
    try {
      const safeAction = action === 'unlike' ? 'unlike' : 'like';
      const res = await fetch(
        `${API_URL}/products/${encodeURIComponent(id)}/like?action=${safeAction}`,
        { method: 'POST' }
      );
      if (!res.ok) throw new Error('Like failed');
      return await res.json();
    } catch (err) {
      return _handleError('toggleLike', err);
    }
  },

  // ===========================================================================
  // PARAMÈTRES (lecture publique, écriture protégée)
  // ===========================================================================
  async getSettings() {
    try {
      const res = await fetch(`${API_URL}/settings`);
      if (!res.ok) throw new Error('Settings fetch failed');
      return await res.json();
    } catch (err) {
      return _handleError('getSettings', err);
    }
  },

  async updateSettings(settings) {
    try {
      const res = await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: _authHeaders(),
        body: JSON.stringify(settings)
      });
      if (res.status === 401) return _handleError('updateSettings', new Error('SESSION_EXPIRED'));
      if (!res.ok) throw new Error('Settings update failed');
      return await res.json();
    } catch (err) {
      return _handleError('updateSettings', err);
    }
  }
};
