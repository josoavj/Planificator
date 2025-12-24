# 📚 Documentation Planificator - Index Complet

## 🎯 Bienvenue!

**Planificator** est une application de gestion de planning et de traitement des clients construite avec **Kivy + KivyMD** et **MySQL**.

**Dernière mise à jour**: 24 décembre 2025  
**Version**: 2.0.0 (Production)  
**État**: ✅ Stable et optimisé

---

## 📖 Table des matières

### 🏗️ Architecture & Structure
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Structure complète, flux d'application, couches
- **[TECH_STACK.md](TECH_STACK.md)** - Technologies utilisées et justifications

### 🔧 Fonctionnalités clés
- **[FREQUENCY_SYSTEM.md](FREQUENCY_SYSTEM.md)** - Logique de fréquence (système 0-6)
- **[PAGINATION.md](PAGINATION.md)** - Pagination MDDataTable (index_global)
- **[DATABASE.md](DATABASE.md)** - Schéma BD, requêtes critiques

### 📊 Performance & Optimisation
- **[PERFORMANCE.md](PERFORMANCE.md)** - Optimisations de démarrage (splash, lazy loading)
- **[BUGS_SOLUTIONS.md](BUGS_SOLUTIONS.md)** - Tous les bugs corrigés depuis décembre

### 👨‍💻 Guides de développement
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Installation et premier démarrage
- **[API_REFERENCE.md](API_REFERENCE.md)** - Référence des méthodes principales

---

## 🚀 Démarrage rapide

### Installation
```bash
git clone https://github.com/AinaMaminirina18/Planificator.git
cd Planificator
pip install -r requirements.txt
python main.py
```

### Structure minimale
```
Planificator/
├── main.py           # Point d'entrée (3478 lignes)
├── setting_bd.py     # Gestionnaire BD (1821 lignes)
├── gestion_ecran.py  # Gestion des écrans
├── screen/           # Interface Kivy (40+ fichiers .kv)
├── scripts/          # SQL migrations
└── docs/             # Cette documentation
```

---

## 📊 Statistiques du projet

| Métrique | Valeur |
|----------|--------|
| Lignes Python | ~5,500 |
| Fichiers KV | 40+ |
| Bugs corrigés | 18+ |
| Commits de correction | 4+ |
| Tables BD | 9 |
| Temps démarrage avant opt. | 3.3s |
| Temps démarrage après opt. | ~1.0s |

---

## 🎯 Points clés à connaître

### Pagination
```python
# Formula: index_global = (page - 1) * rows_num + row_num
# Example: page=2, rows_num=15, row_num=3 → index=18
```

### Fréquence (0-6)
```
0 = Une seule fois
1 = Quotidienne
2 = Hebdomadaire  
3 = Bihebdomadaire
4 = Mensuelle
5 = Trimestrielle
6 = Semestrielle (6 mois)
```

### Client ID (pas de doublons)
- Toutes les requêtes utilisent `client_id` (clé primaire)
- ✅ Pas de conflits avec noms dupliqués

### Optimisations récentes (déc 2025)
1. ✅ Splash screen immédiat (commit 1f6fb6d)
2. ✅ Lazy load MDDataTable (commit ea2d9c7)
3. ✅ Popup screens conditionnels (commit fd32d8f)
4. ✅ Async load main.kv/Sidebar.kv (commit 681c63f)

---

## 🐛 Cycles de correction

### Commit ea2d9c7 (Lazy Load Tables)
**Impact**: -1.5s (45% plus rapide)
- 9 MDDataTable créées à la demande après login
- Flag `_tables_initialized` prévient les doublons

### Commit fd32d8f (Popup Optimization)
**Impact**: -0.7s (60% réduction)
- popup() charge 2 screens au démarrage
- 25 screens additionnels après login

### Commit 681c63f (Async Screens)
**Impact**: -0.2s supplémentaire
- main.kv et Sidebar.kv chargés asynchronement
- Amélioration perceptuelle: 98% (3.3s → splash)

---

## 🔗 Navigation

### Par rôle
- **👤 Admin**: [docs complète recommandée]
- **🧑‍💼 Développeur**: Commencez par [ARCHITECTURE.md](ARCHITECTURE.md)
- **🔍 Debugger**: Consultez [BUGS_SOLUTIONS.md](BUGS_SOLUTIONS.md)

### Par tâche
- Je veux **ajouter une feature**: [ARCHITECTURE.md](ARCHITECTURE.md) → [GETTING_STARTED.md](GETTING_STARTED.md)
- Je dois **corriger un bug**: [BUGS_SOLUTIONS.md](BUGS_SOLUTIONS.md)
- Je veux **comprendre la BD**: [DATABASE.md](DATABASE.md)
- Je veux **optimiser**: [PERFORMANCE.md](PERFORMANCE.md)

---

## 📝 Conventions

### Git
- Format commit: `[TYPE]: Description courte` (ex: `⚡ PERF:`, `🐛 FIX:`)
- Branche: `correction` (développement), `master` (production)

### Python
- Python 3.13
- Style: PEP 8 (relativement souple pour Kivy)
- BD async: aiomysql + asyncio

### Kivy
- Builder + OOP
- ScreenManager pour navigation
- MDDataTable pour listes avec pagination

---

## ✅ Checklist pour nouveau contributeur

- [ ] Lire [ARCHITECTURE.md](ARCHITECTURE.md)
- [ ] Cloner et installer (voir [GETTING_STARTED.md](GETTING_STARTED.md))
- [ ] Lancer l'app: `python main.py`
- [ ] Consulter [BUGS_SOLUTIONS.md](BUGS_SOLUTIONS.md) si problème
- [ ] Pour feature: [API_REFERENCE.md](API_REFERENCE.md)

---

## 🆘 Besoin d'aide?

1. Chercher dans [BUGS_SOLUTIONS.md](BUGS_SOLUTIONS.md) - 18+ problèmes documentés
2. Consulter [FREQUENCY_SYSTEM.md](FREQUENCY_SYSTEM.md) ou [PAGINATION.md](PAGINATION.md)
3. Vérifier les [logs/](../logs/) pour erreurs runtime

---

**Dernière mise à jour**: 24 décembre 2025 par Copilot  
**Branch**: correction  
**Commits de session**: 4+ (optimisations de performance)
