import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  Search, ShoppingCart, Heart, Tag, SlidersHorizontal, Plus, 
  Trash2, X, Check, Phone, ArrowRight, ShieldCheck, 
  Truck, Clock, Sparkles, ChevronLeft, ChevronRight, Eye, RefreshCw, Send,
  Upload, Image as ImageIcon, Bookmark
} from 'lucide-react';
import { INITIAL_DATA } from './mockData';
import { api } from './api';

export default function App() {
  // --- States ---
  const [categories, setCategories] = useState(() => {
    const saved = localStorage.getItem('electrotech_categories');
    return saved ? JSON.parse(saved) : INITIAL_DATA.categories;
  });
  
  const [products, setProducts] = useState(() => {
    const saved = localStorage.getItem('electrotech_products');
    return saved ? JSON.parse(saved) : INITIAL_DATA.products;
  });

  const [settings, setSettings] = useState(() => {
    const saved = localStorage.getItem('electrotech_settings');
    const parsed = saved ? JSON.parse(saved) : INITIAL_DATA.settings;
    return { ...parsed, store_name: 'Faye Store', currency: 'FCFA' };
  });

  const [cart, setCart] = useState(() => {
    const saved = localStorage.getItem('electrotech_cart');
    return saved ? JSON.parse(saved) : [];
  });

  const [favorites, setFavorites] = useState(() => {
    const saved = localStorage.getItem('electrotech_favorites');
    return saved ? JSON.parse(saved) : [];
  });

  const [likedProducts, setLikedProducts] = useState(() => {
    const saved = localStorage.getItem('electrotech_liked');
    return saved ? JSON.parse(saved) : [];
  });

  const [selectedCategory, setSelectedCategory] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState('catalog'); // 'catalog' | 'favorites' | 'admin'
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [viewProductModal, setViewProductModal] = useState(null);
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const categoriesScrollRef = useRef(null);

  const scrollCategories = (direction) => {
    if (categoriesScrollRef.current) {
      const scrollAmount = direction === 'left' ? -220 : 220;
      categoriesScrollRef.current.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    }
  };

  // Admin Form States
  const [newCatName, setNewCatName] = useState('');
  const [inlineNewCategory, setInlineNewCategory] = useState('');
  const [uploadedGalleryImages, setUploadedGalleryImages] = useState([]);
  const [prodForm, setProdForm] = useState({
    title: '',
    category: '',
    price: '',
    discount_percent: 0,
    description: '',
    imagesText: '',
    stock: 10,
    is_featured: false
  });
  const [whatsappPhoneInput, setWhatsappPhoneInput] = useState(settings.whatsapp_phone || '221770000000');
  const [notification, setNotification] = useState(null);

  // Sync to localStorage
  useEffect(() => {
    localStorage.setItem('electrotech_categories', JSON.stringify(categories));
  }, [categories]);

  useEffect(() => {
    localStorage.setItem('electrotech_products', JSON.stringify(products));
  }, [products]);

  useEffect(() => {
    localStorage.setItem('electrotech_cart', JSON.stringify(cart));
  }, [cart]);

  useEffect(() => {
    localStorage.setItem('electrotech_favorites', JSON.stringify(favorites));
  }, [favorites]);

  useEffect(() => {
    localStorage.setItem('electrotech_liked', JSON.stringify(likedProducts));
  }, [likedProducts]);

  useEffect(() => {
    localStorage.setItem('electrotech_settings', JSON.stringify(settings));
  }, [settings]);

  // Try fetching from backend on mount
  useEffect(() => {
    async function loadBackendData() {
      const cats = await api.getCategories();
      if (cats && cats.length > 0) {
        setCategories([{ id: 'all', name: 'Tous les produits' }, ...cats]);
      }
      const prods = await api.getProducts();
      if (prods && prods.length > 0) {
        setProducts(prods);
      }
      const sett = await api.getSettings();
      if (sett) {
        setSettings(sett);
        setWhatsappPhoneInput(sett.whatsapp_phone);
      }
    }
    loadBackendData();
  }, []);

  const showNotification = (msg) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 3500);
  };

  // --- Valid Favorites Count & Items (synchronisés avec les produits existants) ---
  const validFavoriteProducts = useMemo(() => {
    return products.filter((p) => favorites.includes(p.id));
  }, [products, favorites]);

  const validFavoritesCount = validFavoriteProducts.length;

  // Nettoyage automatique des IDs orphelins si des produits ont été supprimés
  useEffect(() => {
    const existingProductIds = new Set(products.map((p) => p.id));
    const cleaned = favorites.filter((id) => existingProductIds.has(id));
    if (cleaned.length !== favorites.length) {
      setFavorites(cleaned);
    }
  }, [products, favorites]);
  const cartSubtotal = useMemo(() => {
    return cart.reduce((total, item) => {
      const finalPrice = item.price * (1 - (item.discount_percent || 0) / 100);
      return total + finalPrice * item.quantity;
    }, 0);
  }, [cart]);

  const cartTotalItems = useMemo(() => {
    return cart.reduce((acc, item) => acc + item.quantity, 0);
  }, [cart]);

  // --- Filtering Products ---
  const filteredProducts = useMemo(() => {
    return products.filter((p) => {
      const matchesCategory = selectedCategory === 'all' || p.category === selectedCategory;
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch = !q || p.title.toLowerCase().includes(q) || p.description.toLowerCase().includes(q);
      const matchesTab = activeTab === 'favorites' ? favorites.includes(p.id) : true;
      return matchesCategory && matchesSearch && matchesTab;
    });
  }, [products, selectedCategory, searchQuery, activeTab, favorites]);

  // --- Cart Handlers ---
  const addToCart = (product) => {
    setCart((prev) => {
      const exists = prev.find((item) => item.id === product.id);
      if (exists) {
        return prev.map((item) =>
          item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
        );
      }
      return [...prev, { ...product, quantity: 1 }];
    });
    showNotification(`"${product.title.slice(0, 25)}..." ajouté au panier !`);
  };

  const updateCartQuantity = (id, delta) => {
    setCart((prev) =>
      prev
        .map((item) => {
          if (item.id === id) {
            const newQty = item.quantity + delta;
            return newQty > 0 ? { ...item, quantity: newQty } : null;
          }
          return item;
        })
        .filter(Boolean)
    );
  };

  const removeFromCart = (id) => {
    setCart((prev) => prev.filter((item) => item.id !== id));
  };

  // --- Distinct Like & Favorite Handlers ---
  const toggleLike = (productId) => {
    const isLiked = likedProducts.includes(productId);
    const updatedLiked = isLiked
      ? likedProducts.filter((id) => id !== productId)
      : [...likedProducts, productId];
    setLikedProducts(updatedLiked);

    setProducts((prev) =>
      prev.map((p) => {
        if (p.id === productId) {
          const newLikes = isLiked ? Math.max(0, (p.likes || 1) - 1) : (p.likes || 0) + 1;
          api.toggleLike(productId, isLiked ? 'unlike' : 'like');
          return { ...p, likes: newLikes };
        }
        return p;
      })
    );

    if (viewProductModal && viewProductModal.id === productId) {
      setViewProductModal((prev) => ({
        ...prev,
        likes: isLiked ? Math.max(0, (prev.likes || 1) - 1) : (prev.likes || 0) + 1
      }));
    }

    showNotification(isLiked ? "Like retiré" : "Vous aimez cet article ! ❤️");
  };

  const toggleFavorite = (productId) => {
    setFavorites((prev) => {
      const isFav = prev.includes(productId);
      const updated = isFav ? prev.filter((id) => id !== productId) : [...prev, productId];
      showNotification(isFav ? "Retiré des favoris" : "Enregistré dans vos favoris ⭐");
      return updated;
    });
  };

  // --- Send Order via WhatsApp ---
  const sendOrderToWhatsApp = () => {
    if (cart.length === 0) return;

    let message = `*COMMANDE ÉLECTRONIQUE - ${settings.store_name}*\n\n`;
    message += `Bonjour, je souhaite passer la commande suivante :\n\n`;

    cart.forEach((item, index) => {
      const finalPrice = item.price * (1 - (item.discount_percent || 0) / 100);
      message += `${index + 1}. *${item.title}*\n`;
      message += `   - Quantité: ${item.quantity}\n`;
      message += `   - Prix unitaire: ${finalPrice.toLocaleString()} ${settings.currency || 'FCFA'}`;
      if (item.discount_percent > 0) {
        message += ` (Remise de ${item.discount_percent}%)`;
      }
      message += `\n   - Total: ${(finalPrice * item.quantity).toLocaleString()} ${settings.currency || 'FCFA'}\n\n`;
    });

    message += `-------------------------------\n`;
    message += `*TOTAL À PAYER : ${cartSubtotal.toLocaleString()} ${settings.currency || 'FCFA'}*\n`;
    message += `-------------------------------\n`;
    message += `Merci de me confirmer la disponibilité et les modalités de livraison !`;

    const encoded = encodeURIComponent(message);
    const phone = (settings.whatsapp_phone || '').replace(/[^0-9]/g, '');
    const whatsappUrl = `https://wa.me/${phone}?text=${encoded}`;
    window.open(whatsappUrl, '_blank');
  };

  // --- Admin Handlers ---
  const handleAddCategory = async (e) => {
    e.preventDefault();
    if (!newCatName.trim()) return;

    const catId = newCatName.toLowerCase().trim().replace(/\s+/g, '-');
    const newCategory = { id: catId, name: newCatName.trim() };

    setCategories((prev) => [...prev, newCategory]);
    await api.addCategory(newCatName.trim());
    setNewCatName('');
    showNotification("Catégorie ajoutée avec succès !");
  };

  const handleDeleteCategory = async (id) => {
    if (id === 'all') return;
    if (window.confirm("Voulez-vous vraiment supprimer cette catégorie ?")) {
      setCategories((prev) => prev.filter((c) => c.id !== id));
      await api.deleteCategory(id);
      showNotification("Catégorie supprimée");
    }
  };

  // --- Image Upload Handler (Galerie / Fichiers locaux) ---
  const handleImageFilesUpload = (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    files.forEach((file) => {
      const reader = new FileReader();
      reader.onload = (event) => {
        setUploadedGalleryImages((prev) => [...prev, event.target.result]);
      };
      reader.readAsDataURL(file);
    });

    showNotification(`${files.length} photo(s) chargée(s) depuis votre galerie !`);
  };

  const removeGalleryImage = (indexToRemove) => {
    setUploadedGalleryImages((prev) => prev.filter((_, idx) => idx !== indexToRemove));
  };

  const handleAddProduct = async (e) => {
    e.preventDefault();
    
    // Si l'administrateur a saisi une nouvelle catégorie directement lors de la publication
    let selectedCat = prodForm.category;
    if (prodForm.category === '__new__' && inlineNewCategory.trim()) {
      const catId = inlineNewCategory.toLowerCase().trim().replace(/\s+/g, '-');
      const newCatObj = { id: catId, name: inlineNewCategory.trim() };
      setCategories((prev) => [...prev, newCatObj]);
      api.addCategory(inlineNewCategory.trim());
      selectedCat = catId;
    }

    if (!prodForm.title || !prodForm.price || !selectedCat || selectedCat === '__new__') {
      alert("Veuillez remplir au moins le titre, le prix et choisir/créer une catégorie valide.");
      return;
    }

    const textUrls = prodForm.imagesText
      .split('\n')
      .map((url) => url.trim())
      .filter((url) => url.length > 0);

    // Combiner les images de la galerie locale et les URLs textuelles
    const combinedImages = [...uploadedGalleryImages, ...textUrls];

    const fallbackImg = "https://images.unsplash.com/photo-1550009158-9ebf69173e03?auto=format&fit=crop&w=800&q=80";

    const newProd = {
      id: `prod-${Date.now()}`,
      title: prodForm.title,
      category: selectedCat,
      price: parseFloat(prodForm.price),
      discount_percent: parseFloat(prodForm.discount_percent) || 0,
      description: prodForm.description,
      images: combinedImages.length > 0 ? combinedImages : [fallbackImg],
      stock: parseInt(prodForm.stock) || 10,
      likes: 0,
      is_featured: prodForm.is_featured
    };

    setProducts((prev) => [newProd, ...prev]);
    await api.addProduct(newProd);

    // Reset Form
    setProdForm({
      title: '',
      category: '',
      price: '',
      discount_percent: 0,
      description: '',
      imagesText: '',
      stock: 10,
      is_featured: false
    });
    setInlineNewCategory('');
    setUploadedGalleryImages([]);

    showNotification("Produit publié avec succès avec ses photos !");
  };

  const handleDeleteProduct = async (id) => {
    if (window.confirm("Supprimer ce produit de la boutique ?")) {
      setProducts((prev) => prev.filter((p) => p.id !== id));
      setFavorites((prev) => prev.filter((favId) => favId !== id));
      setLikedProducts((prev) => prev.filter((likeId) => likeId !== id));
      await api.deleteProduct(id);
      showNotification("Produit retiré du catalogue");
    }
  };

  const handleUpdateSettings = async (e) => {
    e.preventDefault();
    const updated = { ...settings, whatsapp_phone: whatsappPhoneInput };
    setSettings(updated);
    await api.updateSettings(updated);
    showNotification("Numéro WhatsApp et paramètres enregistrés !");
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Toast Notification */}
      {notification && (
        <div className="fixed bottom-6 right-6 z-50 bg-slate-900 text-white px-5 py-3 rounded-2xl shadow-2xl flex items-center gap-3 animate-bounce">
          <Sparkles className="w-5 h-5 text-amber-400" />
          <span className="text-sm font-medium">{notification}</span>
        </div>
      )}

      {/* Top Banner */}
      <header className="bg-slate-900 text-slate-300 text-xs py-2 px-4 border-b border-slate-800">
        <div className="max-w-7xl mx-auto flex flex-wrap justify-between items-center gap-2">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-emerald-400 font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Boutique Ouverte 24/7
            </span>
            <span className="hidden md:inline text-slate-400">•</span>
            <span className="hidden md:flex items-center gap-1 text-slate-300">
              <Truck className="w-3.5 h-3.5 text-blue-400" /> Livraison Express et Sécurisée
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1 text-slate-300 font-medium">
              <Phone className="w-3.5 h-3.5 text-emerald-400" />
              WhatsApp Commande : <strong className="text-white ml-1">+{settings.whatsapp_phone}</strong>
            </span>
          </div>
        </div>
      </header>

      {/* Main Compact Navbar */}
      <nav className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200 shadow-xs">
        <div className="max-w-7xl mx-auto px-3 sm:px-6 py-2">
          <div className="flex items-center justify-between gap-3">
            {/* Logo Compact */}
            <div 
              onClick={() => { setActiveTab('catalog'); setSelectedCategory('all'); }}
              className="flex items-center gap-2 cursor-pointer group flex-shrink-0"
            >
              <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-700 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
                <Sparkles className="w-4 h-4" />
              </div>
              <div className="leading-tight">
                <h1 className="text-base font-extrabold tracking-tight bg-gradient-to-r from-slate-900 to-blue-900 bg-clip-text text-transparent">
                  {settings.store_name}
                </h1>
                <p className="text-[10px] font-semibold text-blue-600 hidden sm:block">High-Tech</p>
              </div>
            </div>

            {/* Search Bar Compact */}
            <div className="flex-1 max-w-md mx-2">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Rechercher un produit (iPhone, MacBook, Casque...)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-100 hover:bg-slate-50 focus:bg-white text-slate-900 pl-9 pr-8 py-1.5 rounded-full border border-slate-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 transition-all outline-none text-xs placeholder:text-slate-400"
                />
                {searchQuery && (
                  <button 
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Actions Compact */}
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <button
                onClick={() => setActiveTab(activeTab === 'favorites' ? 'catalog' : 'favorites')}
                className={`relative p-2 rounded-lg border transition-all flex items-center gap-1.5 text-xs ${
                  activeTab === 'favorites'
                    ? 'bg-rose-50 border-rose-200 text-rose-600'
                    : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
                title="Favoris"
              >
                <Heart className={`w-4 h-4 ${activeTab === 'favorites' ? 'fill-rose-500 text-rose-500' : ''}`} />
                {validFavoritesCount > 0 && (
                  <span className="bg-rose-500 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center">
                    {validFavoritesCount}
                  </span>
                )}
                <span className="hidden md:inline font-semibold">Favoris</span>
              </button>

              <button
                onClick={() => setActiveTab(activeTab === 'admin' ? 'catalog' : 'admin')}
                className={`p-2 rounded-lg border transition-all flex items-center gap-1.5 text-xs font-semibold ${
                  activeTab === 'admin'
                    ? 'bg-blue-600 text-white border-blue-600 shadow-sm'
                    : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                }`}
                title="Administration"
              >
                <SlidersHorizontal className="w-4 h-4" />
                <span className="hidden md:inline">Admin</span>
              </button>

              <button
                onClick={() => setIsCartOpen(true)}
                className="relative bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-3 py-1.5 rounded-lg font-bold text-xs flex items-center gap-1.5 shadow-sm hover:shadow transition-all hover:scale-[1.02] active:scale-[0.98]"
              >
                <ShoppingCart className="w-4 h-4" />
                <span className="hidden sm:inline">Panier</span>
                {cartTotalItems > 0 && (
                  <span className="bg-white text-blue-600 font-extrabold w-4 h-4 rounded-full flex items-center justify-center text-[10px]">
                    {cartTotalItems}
                  </span>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Categories Bar avec Défilement Fluide + Boutons Flèches Gauche/Droite */}
        {activeTab !== 'admin' && (
          <div className="border-t border-slate-100 bg-slate-50/90 py-1.5 relative">
            <div className="max-w-7xl mx-auto px-2 sm:px-4 flex items-center gap-1.5">
              {/* Flèche Gauche */}
              <button
                onClick={() => scrollCategories('left')}
                className="p-1 rounded-full bg-white border border-slate-200 text-slate-600 hover:text-blue-600 hover:bg-slate-100 shadow-xs flex-shrink-0 transition-colors"
                title="Défiler vers la gauche"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              {/* Conteneur de Défilement Horizontal */}
              <div
                ref={categoriesScrollRef}
                className="flex items-center gap-1.5 overflow-x-auto scroll-smooth no-scrollbar py-0.5 flex-1"
                style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
              >
                {categories.map((cat) => {
                  const isActive = selectedCategory === cat.id;
                  return (
                    <button
                      key={cat.id}
                      onClick={() => setSelectedCategory(cat.id)}
                      className={`whitespace-nowrap px-3.5 py-1 rounded-full text-xs font-semibold transition-all flex-shrink-0 ${
                        isActive
                          ? 'bg-blue-600 text-white shadow-xs font-bold'
                          : 'bg-white text-slate-600 border border-slate-200 hover:border-slate-300 hover:bg-slate-100'
                      }`}
                    >
                      {cat.name}
                    </button>
                  );
                })}
              </div>

              {/* Flèche Droite */}
              <button
                onClick={() => scrollCategories('right')}
                className="p-1 rounded-full bg-white border border-slate-200 text-slate-600 hover:text-blue-600 hover:bg-slate-100 shadow-xs flex-shrink-0 transition-colors"
                title="Défiler vers la droite"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Banner Hero Vitrine */}
        {activeTab === 'catalog' && selectedCategory === 'all' && !searchQuery && (
          <div className="relative mb-10 rounded-3xl overflow-hidden bg-gradient-to-r from-slate-900 via-indigo-950 to-blue-900 text-white shadow-2xl p-8 sm:p-12">
            <div className="relative z-10 max-w-2xl">
              <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/20 text-blue-300 border border-blue-400/30 text-xs font-bold uppercase tracking-wider mb-4">
                <Sparkles className="w-3.5 h-3.5 text-blue-400" /> Nouveautés High-Tech 2026
              </span>
              <h2 className="text-3xl sm:text-5xl font-extrabold tracking-tight leading-tight">
                Le meilleur de l'électronique à portée de clic.
              </h2>
              <p className="mt-4 text-slate-300 text-sm sm:text-base leading-relaxed">
                Explorez notre catalogue de smartphones, ordinateurs haut de gamme, accessoires et montres connectées. Commandez instantanément par WhatsApp avec calcul automatique de vos prix.
              </p>
              <div className="mt-6 flex flex-wrap gap-4">
                <button
                  onClick={() => {
                    const el = document.getElementById('products-section');
                    if (el) el.scrollIntoView({ behavior: 'smooth' });
                  }}
                  className="px-6 py-3 rounded-2xl bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm shadow-lg shadow-blue-600/40 flex items-center gap-2 transition-all"
                >
                  Découvrir les offres
                  <ArrowRight className="w-4 h-4" />
                </button>
                <div className="flex items-center gap-2 text-xs text-slate-300 px-4 py-2 rounded-2xl bg-white/10 backdrop-blur-md">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  Garantie Produit & Facture Incluses
                </div>
              </div>
            </div>
            {/* Background glowing sphere */}
            <div className="absolute -top-20 -right-20 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl pointer-events-none"></div>
          </div>
        )}

        {/* --- VIEW: CATALOG & FAVORITES --- */}
        {(activeTab === 'catalog' || activeTab === 'favorites') && (
          <div id="products-section">
            <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
              <div>
                <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                  {activeTab === 'favorites' ? 'Mes Favoris' : 'Catalogue Produits'}
                  <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-slate-200 text-slate-700">
                    {filteredProducts.length} articles
                  </span>
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  {selectedCategory !== 'all' 
                    ? `Filtré par: ${categories.find(c => c.id === selectedCategory)?.name || selectedCategory}`
                    : 'Défilez pour découvrir nos articles ou affinez par catégorie'}
                </p>
              </div>

              {searchQuery && (
                <div className="text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 px-3 py-1.5 rounded-lg flex items-center gap-2">
                  Résultats pour : "{searchQuery}"
                  <button onClick={() => setSearchQuery('')} className="hover:text-blue-900 font-bold">×</button>
                </div>
              )}
            </div>

            {/* Empty State */}
            {filteredProducts.length === 0 ? (
              <div className="bg-white rounded-3xl p-12 text-center border border-slate-200 shadow-sm max-w-md mx-auto my-12">
                <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400 mb-4">
                  <Search className="w-8 h-8" />
                </div>
                <h4 className="text-base font-bold text-slate-800">Aucun produit trouvé</h4>
                <p className="text-xs text-slate-500 mt-2">
                  {activeTab === 'favorites' 
                    ? "Vous n'avez pas encore ajouté de produit à vos favoris."
                    : "Essayez de modifier votre recherche ou sélectionnez une autre catégorie."}
                </p>
                <button
                  onClick={() => { setSelectedCategory('all'); setSearchQuery(''); setActiveTab('catalog'); }}
                  className="mt-6 px-5 py-2.5 rounded-xl bg-blue-600 text-white text-xs font-bold shadow-md hover:bg-blue-700 transition-all"
                >
                  Voir tous les produits
                </button>
              </div>
            ) : (
              /* Product Grid */
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
                {filteredProducts.map((product) => {
                  const finalPrice = product.price * (1 - (product.discount_percent || 0) / 100);
                  const isFav = favorites.includes(product.id);
                  const isLiked = likedProducts.includes(product.id);

                  return (
                    <div
                      key={product.id}
                      className="group bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-xl hover:border-blue-200 transition-all duration-300 flex flex-col relative"
                    >
                      {/* Top Badges */}
                      <div className="absolute top-3 left-3 z-10 flex flex-col gap-1.5">
                        {product.discount_percent > 0 && (
                          <span className="bg-rose-500 text-white text-[11px] font-extrabold px-2.5 py-1 rounded-full shadow-md">
                            -{product.discount_percent}%
                          </span>
                        )}
                        {product.is_featured && (
                          <span className="bg-amber-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow">
                            Top Vente
                          </span>
                        )}
                      </div>

                      {/* Top Right Action Buttons: Like & Favori */}
                      <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5">
                        {/* Bouton Like avec compteur */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleLike(product.id);
                          }}
                          className={`flex items-center gap-1 px-2 py-1 rounded-full backdrop-blur-md transition-all shadow-md text-xs font-bold ${
                            isLiked
                              ? 'bg-rose-500 text-white hover:scale-105 shadow-rose-500/30'
                              : 'bg-white/90 text-slate-700 hover:text-rose-600 hover:bg-white'
                          }`}
                          title={isLiked ? "Je n'aime plus" : "J'aime cet article"}
                        >
                          <Heart className={`w-3.5 h-3.5 ${isLiked ? 'fill-white text-white' : 'text-slate-600'}`} />
                          <span className="text-[11px]">{product.likes || 0}</span>
                        </button>

                        {/* Bouton Favori / Bookmark */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleFavorite(product.id);
                          }}
                          className={`p-1.5 rounded-full backdrop-blur-md transition-all shadow-md ${
                            isFav
                              ? 'bg-amber-500 text-white hover:scale-105 shadow-amber-500/30'
                              : 'bg-white/90 text-slate-700 hover:text-amber-500 hover:bg-white'
                          }`}
                          title={isFav ? "Retirer des favoris" : "Ajouter aux favoris"}
                        >
                          <Bookmark className={`w-3.5 h-3.5 ${isFav ? 'fill-white text-white' : 'text-slate-600'}`} />
                        </button>
                      </div>

                      {/* Image Preview & Carousel click */}
                      <div 
                        onClick={() => { setViewProductModal(product); setActiveImageIndex(0); }}
                        className="relative h-56 bg-slate-100 overflow-hidden cursor-pointer"
                      >
                        <img
                          src={product.images?.[0] || 'https://via.placeholder.com/400'}
                          alt={product.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                          loading="lazy"
                        />
                        {product.images && product.images.length > 1 && (
                          <span className="absolute bottom-2 right-2 bg-slate-900/70 text-white text-[10px] font-semibold px-2 py-0.5 rounded-md backdrop-blur-sm">
                            +{product.images.length - 1} photos
                          </span>
                        )}
                      </div>

                      {/* Product Info */}
                      <div className="p-4 flex-1 flex flex-col justify-between">
                        <div>
                          <span className="text-[10px] uppercase font-bold tracking-wider text-blue-600">
                            {categories.find(c => c.id === product.category)?.name || product.category}
                          </span>
                          <h4 
                            onClick={() => { setViewProductModal(product); setActiveImageIndex(0); }}
                            className="font-bold text-slate-900 text-sm mt-1 line-clamp-2 hover:text-blue-600 cursor-pointer"
                            title={product.title}
                          >
                            {product.title}
                          </h4>
                          <p className="text-xs text-slate-500 mt-1 line-clamp-2">
                            {product.description}
                          </p>
                        </div>

                        {/* Price and Cart Action */}
                        <div className="mt-4 pt-3 border-t border-slate-100">
                          <div className="flex items-baseline gap-2">
                            <span className="text-lg font-extrabold text-slate-900">
                              {finalPrice.toLocaleString()} {settings.currency || 'FCFA'}
                            </span>
                            {product.discount_percent > 0 && (
                              <span className="text-xs text-slate-400 line-through">
                                {product.price.toLocaleString()} {settings.currency || 'FCFA'}
                              </span>
                            )}
                          </div>

                          <div className="mt-3 grid grid-cols-2 gap-2">
                            <button
                              onClick={() => { setViewProductModal(product); setActiveImageIndex(0); }}
                              className="px-3 py-2 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
                            >
                              <Eye className="w-3.5 h-3.5" />
                              Détails
                            </button>
                            <button
                              onClick={() => addToCart(product)}
                              className="px-3 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-md shadow-blue-500/20 transition-all hover:scale-[1.02] active:scale-[0.98]"
                            >
                              <ShoppingCart className="w-3.5 h-3.5" />
                              Ajouter
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* --- VIEW: ADMIN PANEL --- */}
        {activeTab === 'admin' && (
          <div className="space-y-8 animate-fadeIn">
            <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
              <div>
                <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                  <SlidersHorizontal className="w-5 h-5 text-blue-600" />
                  Espace Gestion & Administration de la Vitrine
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Ajoutez vos catégories, publiez des produits avec plusieurs photos et remises, et paramétrez votre numéro WhatsApp.
                </p>
              </div>
              <button
                onClick={() => setActiveTab('catalog')}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition-all"
              >
                ← Retour au catalogue
              </button>
            </div>

            {/* Quick Settings: WhatsApp Number */}
            <div className="bg-gradient-to-r from-emerald-50 via-white to-blue-50 p-6 sm:p-7 rounded-3xl border-2 border-emerald-300 shadow-lg">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-emerald-600 flex items-center justify-center text-white shadow-md">
                    <Phone className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-base font-extrabold text-slate-900">
                      Numéro WhatsApp de réception des commandes
                    </h4>
                    <p className="text-xs text-slate-500">
                      Les paniers validés par les clients et les totaux seront envoyés directement à ce numéro.
                    </p>
                  </div>
                </div>
                <span className="text-xs font-bold px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                  Actif : +{settings.whatsapp_phone}
                </span>
              </div>

              <form onSubmit={handleUpdateSettings} className="mt-4 flex flex-col sm:flex-row items-stretch gap-3">
                <div className="relative flex-1">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <span className="text-slate-400 font-bold text-sm">+</span>
                  </div>
                  <input
                    type="text"
                    placeholder="Ex: 22373022223 (code pays + numéro sans espace ni tiret)"
                    value={whatsappPhoneInput}
                    onChange={(e) => setWhatsappPhoneInput(e.target.value)}
                    className="w-full pl-8 pr-4 py-3.5 rounded-2xl bg-white border-2 border-slate-300 focus:border-emerald-500 focus:ring-4 focus:ring-emerald-100 text-slate-900 text-base sm:text-lg font-bold tracking-wider placeholder:font-normal placeholder:text-slate-400 shadow-sm transition-all outline-none"
                  />
                </div>
                <button
                  type="submit"
                  className="px-6 py-3.5 rounded-2xl bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 text-white font-extrabold text-sm shadow-md shadow-emerald-600/30 hover:shadow-lg transition-all flex items-center justify-center gap-2 flex-shrink-0"
                >
                  <Check className="w-5 h-5" />
                  Sauvegarder le numéro
                </button>
              </form>
              <p className="text-[11px] text-slate-500 mt-2 font-medium">
                💡 Exemple : pour le Mali <code className="bg-white px-1.5 py-0.5 rounded border text-emerald-700 font-bold">22373022223</code>, pour le Sénégal <code className="bg-white px-1.5 py-0.5 rounded border text-emerald-700 font-bold">221770000000</code>.
              </p>
            </div>

            {/* Manage Categories Section */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
                <h4 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
                  <Plus className="w-4 h-4 text-blue-600" />
                  Ajouter une catégorie
                </h4>
                <form onSubmit={handleAddCategory} className="space-y-3">
                  <input
                    type="text"
                    placeholder="Nom (Ex: Téléviseurs 4K, Drones...)"
                    value={newCatName}
                    onChange={(e) => setNewCatName(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="submit"
                    className="w-full py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-md transition-all"
                  >
                    Créer la catégorie
                  </button>
                </form>

                <div className="mt-6">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Catégories existantes ({categories.length - 1})
                  </span>
                  <div className="mt-2 space-y-2 max-h-56 overflow-y-auto pr-1">
                    {categories.filter(c => c.id !== 'all').map((c) => (
                      <div key={c.id} className="flex items-center justify-between p-2 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                        <span className="font-semibold text-slate-700">{c.name}</span>
                        <button
                          onClick={() => handleDeleteCategory(c.id)}
                          className="text-slate-400 hover:text-rose-600 p-1"
                          title="Supprimer la catégorie"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Create Product Form */}
              <div className="md:col-span-2 bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
                <h4 className="text-sm font-bold text-slate-900 mb-4 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-600" />
                  Publier un nouveau produit avec photos & réduction
                </h4>

                <form onSubmit={handleAddProduct} className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Nom du produit *</label>
                      <input
                        type="text"
                        placeholder="Ex: Écran Gamer 27 pouces 165Hz"
                        value={prodForm.title}
                        onChange={(e) => setProdForm({ ...prodForm, title: e.target.value })}
                        required
                        className="w-full px-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Catégorie cible *</label>
                      <select
                        value={prodForm.category}
                        onChange={(e) => setProdForm({ ...prodForm, category: e.target.value })}
                        required
                        className="w-full px-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                      >
                        <option value="">Sélectionner une catégorie existante...</option>
                        {categories.filter(c => c.id !== 'all').map((c) => (
                          <option key={c.id} value={c.id}>{c.name}</option>
                        ))}
                        <option value="__new__" className="text-blue-600 font-bold">
                          ➕ + Créer une nouvelle catégorie directement...
                        </option>
                      </select>

                      {/* Champ pour nouvelle catégorie directement dans la publication */}
                      {prodForm.category === '__new__' && (
                        <div className="mt-2 animate-fadeIn">
                          <input
                            type="text"
                            placeholder="Entrez le nom de la nouvelle catégorie..."
                            value={inlineNewCategory}
                            onChange={(e) => setInlineNewCategory(e.target.value)}
                            required
                            className="w-full px-4 py-2 rounded-xl border-2 border-blue-500 bg-blue-50/40 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-900 font-medium"
                          />
                          <p className="text-[11px] text-blue-600 mt-1">
                            Cette catégorie sera automatiquement créée et ajoutée à la boutique !
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Prix de base ({settings.currency}) *</label>
                      <input
                        type="number"
                        placeholder="Ex: 250000"
                        value={prodForm.price}
                        onChange={(e) => setProdForm({ ...prodForm, price: e.target.value })}
                        required
                        className="w-full px-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Réduction (%) optionnelle</label>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        placeholder="Ex: 15"
                        value={prodForm.discount_percent}
                        onChange={(e) => setProdForm({ ...prodForm, discount_percent: e.target.value })}
                        className="w-full px-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-slate-700 mb-1">Stock disponible</label>
                      <input
                        type="number"
                        placeholder="Ex: 10"
                        value={prodForm.stock}
                        onChange={(e) => setProdForm({ ...prodForm, stock: e.target.value })}
                        className="w-full px-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">Description détaillée du produit</label>
                    <textarea
                      rows="3"
                      placeholder="Spécifications techniques, processeur, mémoire, autonomie..."
                      value={prodForm.description}
                      onChange={(e) => setProdForm({ ...prodForm, description: e.target.value })}
                      className="w-full px-4 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    ></textarea>
                  </div>

                  {/* Photos du produit : Upload depuis la Galerie Locale + Liens URLs */}
                  <div className="space-y-3 p-4 rounded-2xl bg-slate-50 border border-slate-200">
                    <div>
                      <label className="block text-xs font-bold text-slate-800 mb-1 flex items-center gap-2">
                        <Upload className="w-4 h-4 text-blue-600" />
                        Option 1 : Ajouter des photos directement depuis votre galerie / téléphone / PC
                      </label>
                      <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-dashed border-blue-300 hover:border-blue-500 rounded-2xl cursor-pointer bg-white hover:bg-blue-50/50 transition-all">
                        <div className="flex flex-col items-center justify-center pt-2 pb-2">
                          <ImageIcon className="w-8 h-8 text-blue-500 mb-1" />
                          <p className="text-xs text-slate-700 font-semibold">
                            Cliquez pour choisir des photos de votre galerie
                          </p>
                          <p className="text-[11px] text-slate-400">
                            Sélection multiple possible (PNG, JPG, JPEG, WEBP)
                          </p>
                        </div>
                        <input
                          type="file"
                          multiple
                          accept="image/*"
                          onChange={handleImageFilesUpload}
                          className="hidden"
                        />
                      </label>

                      {/* Aperçu des photos sélectionnées depuis la galerie */}
                      {uploadedGalleryImages.length > 0 && (
                        <div className="mt-3">
                          <span className="text-[11px] font-bold text-slate-600">
                            Photos sélectionnées depuis votre galerie ({uploadedGalleryImages.length}) :
                          </span>
                          <div className="flex flex-wrap gap-2 mt-1.5">
                            {uploadedGalleryImages.map((imgSrc, idx) => (
                              <div key={idx} className="relative w-16 h-16 rounded-xl overflow-hidden border border-slate-300 group shadow-xs">
                                <img src={imgSrc} alt="" className="w-full h-full object-cover" />
                                <button
                                  type="button"
                                  onClick={() => removeGalleryImage(idx)}
                                  className="absolute top-1 right-1 bg-rose-600 text-white rounded-full p-0.5 shadow-sm opacity-90 hover:opacity-100"
                                  title="Retirer cette photo"
                                >
                                  <X className="w-3 h-3" />
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="pt-2 border-t border-slate-200">
                      <label className="block text-xs font-semibold text-slate-700 mb-1">
                        Option 2 : Ou ajouter des liens d'images en ligne (URLs)
                      </label>
                      <textarea
                        rows="2"
                        placeholder="https://images.unsplash.com/...&#10;https://..."
                        value={prodForm.imagesText}
                        onChange={(e) => setProdForm({ ...prodForm, imagesText: e.target.value })}
                        className="w-full px-4 py-2 rounded-xl border border-slate-200 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                      ></textarea>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="is_featured"
                      checked={prodForm.is_featured}
                      onChange={(e) => setProdForm({ ...prodForm, is_featured: e.target.checked })}
                      className="w-4 h-4 text-blue-600 rounded border-slate-300 focus:ring-blue-500"
                    />
                    <label htmlFor="is_featured" className="text-xs font-medium text-slate-700">
                      Mettre en avant sur la vitrine (Badge Top Vente)
                    </label>
                  </div>

                  <button
                    type="submit"
                    className="w-full py-3 rounded-2xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-bold text-sm shadow-md shadow-blue-500/30 hover:shadow-lg transition-all"
                  >
                    Publier l'article dans la boutique
                  </button>
                </form>
              </div>
            </div>

            {/* List & Delete Products in Admin */}
            <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm">
              <h4 className="text-sm font-bold text-slate-900 mb-4">
                Articles publiés ({products.length})
              </h4>
              <div className="divide-y divide-slate-100">
                {products.map((p) => (
                  <div key={p.id} className="py-3 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <img
                        src={p.images?.[0] || 'https://via.placeholder.com/80'}
                        alt=""
                        className="w-12 h-12 rounded-xl object-cover border border-slate-200"
                      />
                      <div>
                        <h5 className="font-bold text-xs text-slate-800 line-clamp-1">{p.title}</h5>
                        <p className="text-[11px] text-slate-400">
                          {categories.find(c => c.id === p.category)?.name || p.category} • {p.price.toLocaleString()} {settings.currency}
                          {p.discount_percent > 0 && ` (-${p.discount_percent}%)`}
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeleteProduct(p.id)}
                      className="p-2 text-rose-600 hover:bg-rose-50 rounded-xl transition-colors"
                      title="Supprimer ce produit"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* --- CART DRAWER / MODAL --- */}
      {isCartOpen && (
        <div className="fixed inset-0 z-50 overflow-hidden">
          <div 
            onClick={() => setIsCartOpen(false)}
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm transition-opacity"
          ></div>

          <div className="fixed inset-y-0 right-0 max-w-full flex pl-10">
            <div className="w-screen max-w-md bg-white shadow-2xl flex flex-col">
              {/* Cart Header */}
              <div className="p-6 border-b border-slate-200 flex items-center justify-between bg-slate-50">
                <div className="flex items-center gap-2">
                  <ShoppingCart className="w-5 h-5 text-blue-600" />
                  <h3 className="font-extrabold text-slate-900 text-lg">Mon Panier</h3>
                  <span className="text-xs bg-blue-100 text-blue-700 font-bold px-2 py-0.5 rounded-full">
                    {cartTotalItems} articles
                  </span>
                </div>
                <button
                  onClick={() => setIsCartOpen(false)}
                  className="p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Cart List */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                {cart.length === 0 ? (
                  <div className="text-center py-16 text-slate-400">
                    <ShoppingCart className="w-12 h-12 mx-auto stroke-1 text-slate-300 mb-3" />
                    <p className="font-semibold text-sm text-slate-600">Votre panier est vide</p>
                    <p className="text-xs text-slate-400 mt-1">Découvrez nos produits pour remplir votre panier !</p>
                  </div>
                ) : (
                  cart.map((item) => {
                    const finalPrice = item.price * (1 - (item.discount_percent || 0) / 100);
                    return (
                      <div key={item.id} className="flex gap-4 p-3 rounded-2xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors">
                        <img
                          src={item.images?.[0] || 'https://via.placeholder.com/80'}
                          alt={item.title}
                          className="w-16 h-16 rounded-xl object-cover border border-slate-200"
                        />
                        <div className="flex-1 flex flex-col justify-between">
                          <div>
                            <h5 className="text-xs font-bold text-slate-800 line-clamp-1">{item.title}</h5>
                            <span className="text-xs font-extrabold text-blue-600">
                              {finalPrice.toLocaleString()} {settings.currency || 'FCFA'}
                            </span>
                          </div>

                          <div className="flex items-center justify-between mt-2">
                            <div className="flex items-center border border-slate-200 rounded-lg bg-white">
                              <button
                                onClick={() => updateCartQuantity(item.id, -1)}
                                className="px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100 rounded-l"
                              >
                                -
                              </button>
                              <span className="px-2 text-xs font-bold text-slate-800">{item.quantity}</span>
                              <button
                                onClick={() => updateCartQuantity(item.id, 1)}
                                className="px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-100 rounded-r"
                              >
                                +
                              </button>
                            </div>
                            <button
                              onClick={() => removeFromCart(item.id)}
                              className="text-slate-400 hover:text-rose-500 p-1"
                              title="Retirer"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Cart Footer */}
              {cart.length > 0 && (
                <div className="p-6 border-t border-slate-200 bg-slate-50 space-y-4">
                  <div className="space-y-1.5 text-sm">
                    <div className="flex justify-between text-slate-500 text-xs">
                      <span>Sous-total articles :</span>
                      <span>{cartSubtotal.toLocaleString()} {settings.currency || 'FCFA'}</span>
                    </div>
                    <div className="flex justify-between text-slate-500 text-xs">
                      <span>Frais de confirmation :</span>
                      <span className="text-emerald-600 font-semibold">Gratuit</span>
                    </div>
                    <div className="flex justify-between text-slate-900 font-extrabold text-base pt-2 border-t border-slate-200">
                      <span>TOTAL DE LA COMMANDE :</span>
                      <span className="text-blue-600">{cartSubtotal.toLocaleString()} {settings.currency || 'FCFA'}</span>
                    </div>
                  </div>

                  {/* Send to WhatsApp button */}
                  <button
                    onClick={sendOrderToWhatsApp}
                    className="w-full py-3.5 px-4 rounded-2xl bg-gradient-to-r from-emerald-500 to-green-600 hover:from-emerald-600 hover:to-green-700 text-white font-bold text-sm shadow-lg shadow-emerald-500/30 flex items-center justify-center gap-2 transition-all hover:scale-[1.01] active:scale-[0.99]"
                  >
                    <Send className="w-4 h-4" />
                    Envoyer ma commande sur WhatsApp
                  </button>

                  <p className="text-[11px] text-center text-slate-400">
                    Envoi instantané du récapitulatif détaillé et du prix total au numéro <strong>+{settings.whatsapp_phone}</strong>.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* --- MULTI-IMAGE & DETAILS PRODUCT MODAL --- */}
      {viewProductModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/70 backdrop-blur-sm">
          <div className="bg-white rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 shadow-2xl relative animate-scaleUp">
            {/* Close Button */}
            <button
              onClick={() => setViewProductModal(null)}
              className="absolute top-4 right-4 z-20 p-2 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 p-6 sm:p-8">
              {/* Multi-image Gallery */}
              <div className="space-y-4">
                <div className="relative h-72 sm:h-80 rounded-2xl overflow-hidden bg-slate-100 border border-slate-200">
                  <img
                    src={viewProductModal.images?.[activeImageIndex] || viewProductModal.images?.[0]}
                    alt={viewProductModal.title}
                    className="w-full h-full object-cover"
                  />
                  {viewProductModal.images && viewProductModal.images.length > 1 && (
                    <>
                      <button
                        onClick={() =>
                          setActiveImageIndex((prev) =>
                            prev === 0 ? viewProductModal.images.length - 1 : prev - 1
                          )
                        }
                        className="absolute left-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-white/80 hover:bg-white text-slate-700 shadow-md backdrop-blur-sm"
                      >
                        <ChevronLeft className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() =>
                          setActiveImageIndex((prev) =>
                            (prev + 1) % viewProductModal.images.length
                          )
                        }
                        className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-full bg-white/80 hover:bg-white text-slate-700 shadow-md backdrop-blur-sm"
                      >
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </>
                  )}
                </div>

                {/* Thumbnails */}
                {viewProductModal.images && viewProductModal.images.length > 1 && (
                  <div className="flex gap-2 overflow-x-auto pb-1">
                    {viewProductModal.images.map((img, idx) => (
                      <button
                        key={idx}
                        onClick={() => setActiveImageIndex(idx)}
                        className={`w-16 h-16 rounded-xl overflow-hidden border-2 flex-shrink-0 transition-all ${
                          activeImageIndex === idx ? 'border-blue-600 scale-105' : 'border-slate-200 opacity-60'
                        }`}
                      >
                        <img src={img} alt="" className="w-full h-full object-cover" />
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Product Details */}
              <div className="flex flex-col justify-between">
                <div>
                  <span className="text-xs uppercase font-extrabold tracking-wider text-blue-600">
                    {categories.find(c => c.id === viewProductModal.category)?.name || viewProductModal.category}
                  </span>
                  <h3 className="text-xl font-extrabold text-slate-900 mt-1">
                    {viewProductModal.title}
                  </h3>

                  {/* Likes and Stock */}
                  <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <Heart className="w-4 h-4 fill-rose-500 text-rose-500" />
                      {viewProductModal.likes || 0} personnes aiment ce produit
                    </span>
                    <span>•</span>
                    <span className="text-emerald-600 font-semibold">
                      En stock ({viewProductModal.stock || 10} restants)
                    </span>
                  </div>

                  {/* Pricing */}
                  <div className="mt-4 p-4 rounded-2xl bg-slate-50 border border-slate-100 flex items-baseline gap-3">
                    <span className="text-2xl font-extrabold text-slate-900">
                      {(
                        viewProductModal.price *
                        (1 - (viewProductModal.discount_percent || 0) / 100)
                      ).toLocaleString()}{' '}
                      {settings.currency || 'FCFA'}
                    </span>
                    {viewProductModal.discount_percent > 0 && (
                      <>
                        <span className="text-sm text-slate-400 line-through">
                          {viewProductModal.price.toLocaleString()} {settings.currency || 'FCFA'}
                        </span>
                        <span className="bg-rose-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                          -{viewProductModal.discount_percent}% de réduction
                        </span>
                      </>
                    )}
                  </div>

                  {/* Description */}
                  <div className="mt-4">
                    <h5 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Description :</h5>
                    <p className="text-sm text-slate-600 mt-2 leading-relaxed whitespace-pre-line">
                      {viewProductModal.description}
                    </p>
                  </div>
                </div>

                {/* Actions Modal */}
                <div className="mt-6 pt-4 border-t border-slate-100 flex items-center gap-3">
                  {/* Bouton Like dans la modal */}
                  <button
                    onClick={() => toggleLike(viewProductModal.id)}
                    className={`px-4 py-3 rounded-2xl border transition-all flex items-center gap-2 font-bold text-xs ${
                      likedProducts.includes(viewProductModal.id)
                        ? 'bg-rose-50 border-rose-200 text-rose-600'
                        : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                    }`}
                    title="J'aime ce produit"
                  >
                    <Heart
                      className={`w-4 h-4 ${
                        likedProducts.includes(viewProductModal.id) ? 'fill-rose-500 text-rose-500' : 'text-slate-600'
                      }`}
                    />
                    <span>{viewProductModal.likes || 0} J'aime</span>
                  </button>

                  {/* Bouton Favori dans la modal */}
                  <button
                    onClick={() => toggleFavorite(viewProductModal.id)}
                    className={`p-3 rounded-2xl border transition-all ${
                      favorites.includes(viewProductModal.id)
                        ? 'bg-amber-50 border-amber-200 text-amber-600'
                        : 'border-slate-200 text-slate-700 hover:bg-slate-50'
                    }`}
                    title={favorites.includes(viewProductModal.id) ? "Retirer des favoris" : "Ajouter aux favoris"}
                  >
                    <Bookmark
                      className={`w-4 h-4 ${
                        favorites.includes(viewProductModal.id) ? 'fill-amber-500 text-amber-500' : 'text-slate-600'
                      }`}
                    />
                  </button>

                  <button
                    onClick={() => {
                      addToCart(viewProductModal);
                      setViewProductModal(null);
                      setIsCartOpen(true);
                    }}
                    className="flex-1 py-3.5 rounded-2xl bg-blue-600 hover:bg-blue-700 text-white font-bold text-sm shadow-lg shadow-blue-500/30 flex items-center justify-center gap-2 transition-all"
                  >
                    <ShoppingCart className="w-5 h-5" />
                    Ajouter au panier & Commander
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Footer Moderne & Épuré */}
      <footer className="bg-slate-900 text-slate-400 py-12 mt-20 border-t border-slate-800 text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-10">
            {/* Col 1: Store Branding */}
            <div className="md:col-span-2 space-y-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md font-bold">
                  <Sparkles className="w-5 h-5" />
                </div>
                <span className="text-xl font-extrabold text-white tracking-tight">{settings.store_name}</span>
              </div>
              <p className="text-slate-400 text-xs leading-relaxed max-w-sm">
                Votre destination de confiance pour les smartphones, ordinateurs portables, casques audio et accessoires électroniques de dernière génération.
              </p>
            </div>

            {/* Col 2: Services & Engagement */}
            <div className="space-y-2.5">
              <h5 className="font-bold text-white text-sm uppercase tracking-wider">Engagements</h5>
              <ul className="space-y-1.5 text-xs text-slate-400">
                <li className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  Produits 100% Authentiques
                </li>
                <li className="flex items-center gap-2">
                  <Truck className="w-4 h-4 text-blue-400" />
                  Livraison Rapide à Domicile
                </li>
                <li className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-amber-400" />
                  Service Client & Suivi 7j/7
                </li>
              </ul>
            </div>

            {/* Col 3: Contact & Commande */}
            <div className="space-y-2.5">
              <h5 className="font-bold text-white text-sm uppercase tracking-wider">Contact Direct</h5>
              <p className="text-xs text-slate-400">
                Passez vos commandes ou posez vos questions en direct sur WhatsApp :
              </p>
              <a
                href={`https://wa.me/${(settings.whatsapp_phone || '').replace(/[^0-9]/g, '')}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition-colors shadow-md"
              >
                <Phone className="w-4 h-4" />
                +{settings.whatsapp_phone}
              </a>
            </div>
          </div>

          <div className="pt-8 border-t border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-4 text-slate-500 text-xs">
            <p>© {new Date().getFullYear()} {settings.store_name}. Tous droits réservés.</p>
            <div className="flex items-center gap-6">
              <span>Smartphones</span>
              <span>•</span>
              <span>Ordinateurs</span>
              <span>•</span>
              <span>Accessoires</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
