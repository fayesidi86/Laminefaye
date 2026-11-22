-- ============================================================
-- FAYE STORE — Schéma Supabase
-- Colle ce SQL dans : Supabase > SQL Editor > New Query
-- ============================================================

-- Table des catégories
CREATE TABLE IF NOT EXISTS categories (
  id   TEXT PRIMARY KEY,
  name TEXT NOT NULL
);

-- Table des produits
CREATE TABLE IF NOT EXISTS products (
  id               TEXT PRIMARY KEY,
  title            TEXT NOT NULL,
  category         TEXT NOT NULL,
  description      TEXT DEFAULT '',
  price            FLOAT NOT NULL,
  discount_percent FLOAT DEFAULT 0,
  images           JSONB DEFAULT '[]',
  stock            INTEGER DEFAULT 10,
  is_featured      BOOLEAN DEFAULT FALSE,
  likes            INTEGER DEFAULT 0,
  created_at       TIMESTAMPTZ DEFAULT NOW()
);

-- Table des paramètres
CREATE TABLE IF NOT EXISTS settings (
  key             TEXT PRIMARY KEY,
  whatsapp_phone  TEXT,
  store_name      TEXT,
  currency        TEXT
);

-- ============================================================
-- Données par défaut (catégories + paramètres)
-- ============================================================
INSERT INTO categories (id, name) VALUES
  ('smartphones',  'Smartphones & Téléphones'),
  ('laptops',      'Ordinateurs & PC Portables'),
  ('audio',        'Audio, Casques & Écouteurs'),
  ('accessoires',  'Accessoires & Connectique'),
  ('montres',      'Montres Connectées & Wearables')
ON CONFLICT (id) DO NOTHING;

INSERT INTO settings (key, whatsapp_phone, store_name, currency)
VALUES ('main', '22377219028', 'Faye Store', 'FCFA')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- Désactiver RLS (Row Level Security) pour accès via service_role
-- Le backend utilise la clé service_role qui contourne le RLS,
-- mais on le désactive explicitement pour simplifier.
-- ============================================================
ALTER TABLE categories DISABLE ROW LEVEL SECURITY;
ALTER TABLE products   DISABLE ROW LEVEL SECURITY;
ALTER TABLE settings   DISABLE ROW LEVEL SECURITY;
