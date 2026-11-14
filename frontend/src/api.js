const API_URL = import.meta.env.VITE_API_URL || 'https://laminefaye.onrender.com/api';

export const api = {
  async getCategories() {
    try {
      const res = await fetch(`${API_URL}/categories`);
      if (!res.ok) throw new Error('API request failed');
      return await res.json();
    } catch {
      return null;
    }
  },

  async addCategory(name) {
    try {
      const res = await fetch(`${API_URL}/categories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
      });
      if (!res.ok) throw new Error('Failed to create category');
      return await res.json();
    } catch {
      return null;
    }
  },

  async deleteCategory(id) {
    try {
      const res = await fetch(`${API_URL}/categories/${id}`, { method: 'DELETE' });
      return res.ok;
    } catch {
      return false;
    }
  },

  async getProducts(category = null, q = null) {
    try {
      const params = new URLSearchParams();
      if (category && category !== 'all') params.append('category', category);
      if (q) params.append('q', q);
      const res = await fetch(`${API_URL}/products?${params.toString()}`);
      if (!res.ok) throw new Error('API request failed');
      return await res.json();
    } catch {
      return null;
    }
  },

  async addProduct(product) {
    try {
      const res = await fetch(`${API_URL}/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(product)
      });
      if (!res.ok) throw new Error('Failed to create product');
      return await res.json();
    } catch {
      return null;
    }
  },

  async deleteProduct(id) {
    try {
      const res = await fetch(`${API_URL}/products/${id}`, { method: 'DELETE' });
      return res.ok;
    } catch {
      return false;
    }
  },

  async toggleLike(id, action = 'like') {
    try {
      const res = await fetch(`${API_URL}/products/${id}/like?action=${action}`, {
        method: 'POST'
      });
      if (!res.ok) throw new Error('Like failed');
      return await res.json();
    } catch {
      return null;
    }
  },

  async getSettings() {
    try {
      const res = await fetch(`${API_URL}/settings`);
      if (!res.ok) throw new Error('Settings fetch failed');
      return await res.json();
    } catch {
      return null;
    }
  },

  async updateSettings(settings) {
    try {
      const res = await fetch(`${API_URL}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      if (!res.ok) throw new Error('Settings update failed');
      return await res.json();
    } catch {
      return null;
    }
  }
};
