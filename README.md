# ⚡ Faye Store — E-Commerce Électronique & High-Tech

Une application web e-commerce moderne, rapide et responsive conçue avec **React** (Frontend) et **Python FastAPI** (Backend).

---

## 🌟 Fonctionnalités Implémentées

### Côté Client (Visiteur / Acheteur) :
- 🔍 **Barre de recherche instantanée** : Recherche dynamique par titre ou spécification technique (ex: iPhone, MacBook, Sony, 256GB...).
- 🏷️ **Filtres par catégories** : Navigation par pastilles défilables (Smartphones, Ordinateurs, Audio, Accessoires, Montres connectées, etc.).
- ❤️ **Système de "J'aime" et Favoris** : L'utilisateur peut liker les produits et les retrouver à tout moment dans l'onglet dédié **Favoris**.
- 🖼️ **Galerie multi-photos interactive** : Défilement des images d'un même produit avec miniatures cliquables et flèches de navigation.
- 🏷️ **Affichage des réductions** : Calcul automatique des remises en pourcentage avec prix barré et badge promotionnel.
- 🛒 **Panier complet d'achats** : Ajout d'articles, modification des quantités (+ / -), suppression et calcul en direct du sous-total.
- 📲 **Envoi de la commande par WhatsApp** : En un clic sur *"Envoyer ma commande sur WhatsApp"*, l'application génère un récapitulatif formaté complet avec la liste des articles, quantités, remises et le total final directement envoyé au numéro de téléphone configuré.

### Côté Administrateur :
- ➕ **Création de catégories dynamiques** : L'administrateur peut créer ses propres catégories de produits à la volée.
- 📝 **Publication de produits multi-images** : Ajout du nom, catégorie au choix, prix de base, pourcentage de réduction, description détaillée et plusieurs URLs d'images (une par ligne).
- 🏷️ **Gestion des promotions & Badge Top Vente** : Option pour afficher le produit en avant-première avec badge distinctif.
- ⚙️ **Paramétrage du numéro WhatsApp** : Mise à jour immédiate du numéro auquel les commandes sont transmises.

---

## 🏗️ Architecture du Projet

```
LAMINEFAYE/
├── backend/
│   ├── main.py              # Serveur FastAPI (Endpoints API REST, gestion data)
│   ├── test_main.py         # Tests unitaires automatisés (Pytest + HTTPX)
│   ├── data.json            # Base de données JSON
│   ├── requirements.txt     # Dépendances Python
│   └── venv/                # Environnement virtuel Python
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Interface React complète avec boutique, panier, admin
│   │   ├── api.js           # Client API avec fallback offline
│   │   ├── mockData.js      # Données initiales de la boutique
│   │   └── main.jsx         # Point d'entrée React
│   ├── package.json         # Dépendances Node.js (Vite, Tailwind, Lucide)
│   ├── vite.config.js       # Configuration Vite & Proxy
│   ├── vercel.json          # Configuration pour le déploiement Vercel
│   └── index.html           # Structure HTML & Tailwind CDN
│
├── .gitignore
└── README.md
```

---

## 🚀 Démarrage Rapide en Local

### 1. Lancer le Backend Python :
```powershell
cd backend
.\venv\Scripts\activate
uvicorn main:app --reload --port 8000
```
L'API sera accessible sur `http://localhost:8000` et la documentation interactive sur `http://localhost:8000/docs`.

### 2. Exécuter les tests du Backend :
```powershell
cd backend
.\venv\Scripts\pytest
```

### 3. Lancer le Frontend React :
```powershell
cd frontend
npm run dev
```
L'application s'ouvrira sur `http://localhost:3000`.

---

## 🌐 Déploiement sur GitHub et Vercel

### Pour GitHub :
1. Créez un nouveau dépôt sur [GitHub](https://github.com).
2. Dans votre terminal à la racine du projet :
```powershell
git init
git add .
git commit -m "Initial commit - ÉlectroTech Store Fullstack"
git branch -M main
git remote add origin https://github.com/VOTRE_NOM_UTILISATEUR/VOTRE_DEPOT.git
git push -u origin main
```

### Pour Vercel :
1. Connectez-vous sur [Vercel](https://vercel.com) avec votre compte GitHub.
2. Cliquez sur **"Add New Project"** et importez le dépôt GitHub.
3. Définissez le **Root Directory** sur `frontend`.
4. Le framework sera automatiquement détecté en **Vite**.
5. Cliquez sur **Deploy** ! Votre boutique en ligne sera accessible en direct gratuitement avec certificat SSL HTTPS.
