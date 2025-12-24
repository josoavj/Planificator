# 📚 Documentation Planificator

Bienvenue dans la documentation complète de **Planificator** - application de gestion de planning et traitement de clients.

## 🎯 Par où commencer?

### 👤 Vous êtes...

**...nouveau développeur?**
1. Lire [INDEX.md](INDEX.md) (5 min)
2. Installer via [GETTING_STARTED.md](GETTING_STARTED.md) (15 min)
3. Consulter [ARCHITECTURE.md](ARCHITECTURE.md) pour comprendre la structure

**...responsable technique?**
- [PERFORMANCE.md](PERFORMANCE.md) - Optimisations récentes (67% plus rapide!)
- [BUGS_SOLUTIONS.md](BUGS_SOLUTIONS.md) - 18+ bugs résolus
- [ARCHITECTURE.md](ARCHITECTURE.md) - Vue d'ensemble système

**...besoin de corriger un bug?**
- Chercher dans [BUGS_SOLUTIONS.md](BUGS_SOLUTIONS.md)
- Si pagination: voir [PAGINATION.md](PAGINATION.md)
- Si fréquence: voir [FREQUENCY_SYSTEM.md](FREQUENCY_SYSTEM.md)
- Sinon: consulter [API_REFERENCE.md](API_REFERENCE.md)

**...ajout une feature?**
1. [ARCHITECTURE.md](ARCHITECTURE.md) - Comprendre flux
2. [API_REFERENCE.md](API_REFERENCE.md) - Méthodes disponibles
3. [DATABASE.md](DATABASE.md) - Schéma BD

---

## 📖 Structure documentation

| Fichier | Contenu | Durée |
|---------|---------|-------|
| **[INDEX.md](INDEX.md)** | Table des matières principale | 5 min |
| **[GETTING_STARTED.md](GETTING_STARTED.md)** | Installation et premier démarrage | 15 min |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Structure app, flux, couches | 20 min |
| **[API_REFERENCE.md](API_REFERENCE.md)** | Méthodes principales, exemples | 30 min |
| **[DATABASE.md](DATABASE.md)** | Schéma BD, requêtes critiques | 20 min |
| **[PAGINATION.md](PAGINATION.md)** | Système pagination MDDataTable | 15 min |
| **[FREQUENCY_SYSTEM.md](FREQUENCY_SYSTEM.md)** | Logique fréquence (0-6) | 10 min |
| **[PERFORMANCE.md](PERFORMANCE.md)** | Optimisations démarrage | 15 min |
| **[BUGS_SOLUTIONS.md](BUGS_SOLUTIONS.md)** | 18+ bugs corrigés | 30 min |

---

## 🚀 Démarrage rapide (2 min)

```bash
# 1. Cloner
git clone https://github.com/AinaMaminirina18/Planificator.git
cd Planificator

# 2. Installer
pip install -r requirements.txt

# 3. BD setup
mysql -u root -p < scripts/Planificator.sql

# 4. Lancer
python main.py
```

**✅ C'est tout!** Le splash screen de chargement s'affiche, puis le login.

---

## 📊 Points clés à retenir

### 🎯 Pagination
**Formula**: `index = (page - 1) × rows_num + row_num - 1`

### 🎯 Fréquence (0-6)
```
0 = une seule fois
1 = quotidienne
2 = hebdomadaire
3 = bihebdomadaire
4 = mensuelle
5 = trimestrielle
6 = semestrielle
```

### 🎯 Client ID (pas de doublons!)
Toujours utiliser `client_id` (clé primaire) jamais `nom` (peut être dupliqué)

### 🎯 Performance
**Startup**: 3.3s → 1.0s (67% ↓)
- Splash screen immédiat
- Lazy load tables
- Lazy load screens
- Async main.kv

---

## 🆘 Besoin d'aide?

1. **Chercher dans la doc** - Utiliser Ctrl+F dans le fichier
2. **[BUGS_SOLUTIONS.md](BUGS_SOLUTIONS.md)** - 18+ problèmes documentés
3. **[API_REFERENCE.md](API_REFERENCE.md)** - Méthodes et exemples
4. **[GETTING_STARTED.md](GETTING_STARTED.md)** - Troubleshooting section

---

## 📋 Technologies

- **Frontend**: Kivy 2.2.1 + KivyMD 0.104 (Python 3.13)
- **Backend**: MySQL 8.0+
- **BD Async**: aiomysql + asyncio
- **Email**: SMTP integration
- **Excel**: openpyxl

---

## ✅ État du projet

| Aspect | Status |
|--------|--------|
| **Stabilité** | ✅ Production-ready |
| **Performance** | ✅ Optimisée (67% ↓ startup) |
| **Bugs** | ✅ 18+ résolus |
| **Documentation** | ✅ À jour |
| **Tests** | ✅ Validés |
| **Déploiement** | ✅ Prêt |

---

## 🔄 Dernières optimisations (décembre 2025)

| # | Commit | Impact |
|----|--------|--------|
| 1 | 1f6fb6d | Splash screen immédiat |
| 2 | ea2d9c7 | -1.5s (tables lazy load) |
| 3 | fd32d8f | -0.7s (screens conditionnels) |
| 4 | 681c63f | -0.2s (async screens) |

**Total**: 3.3s → 1.0s ✨

---

## 🔗 Liens rapides

- **GitHub**: https://github.com/AinaMaminirina18/Planificator
- **Branch**: `correction` (dev) → merge vers `master`
- **Issues**: https://github.com/AinaMaminirina18/Planificator/issues

---

## 📝 Conventions projet

### Git
- Commits: `[TYPE]: Description` ex: `⚡ PERF:`, `🐛 FIX:`, `✨ FEAT:`
- Branches: `correction` (dev), `master` (prod)

### Code
- Python 3.13
- PEP 8 (relativement souple pour Kivy)
- Async/await pour BD
- ScreenManager pour navigation

### BD
- MySQL 8.0+
- Queries async (aiomysql)
- Timeout 5s par défaut
- Client_id = clé primaire

---

## 🎓 Pour apprendre Kivy/KivyMD

- [Kivy Tutorial](https://kivy.org/doc/current/guide/basic.html)
- [KivyMD Components](https://kivymd.readthedocs.io/)
- [ScreenManager Guide](https://kivy.org/doc/current/api-kivy.uix.screenmanager.html)

---

## 📞 Support

Pour questions techniques:
1. Vérifier [BUGS_SOLUTIONS.md](BUGS_SOLUTIONS.md)
2. Lancer avec logs: `python main.py 2>&1 | tee logs/app.log`
3. Consulter [GETTING_STARTED.md](GETTING_STARTED.md) Troubleshooting

---

**Documentation mise à jour**: 24 décembre 2025  
**Version**: 2.0.0  
**Status**: ✅ À jour et production-ready

```
 _____ _                 _  ___           _               
|  __ \| |               (_) / _ \         | |              
| |__) | | __ _ _ __  ___ _| | | |_ _  _ __| |_ ___  _ __
|  ___/| |/ _` | '_ \/ __| | | | | | | |/ __| __/ _ \| '__|
| |    | | (_| | | | \__ \ | |_| | |_| | (__| || (_) | |
|_|    |_|\__,_|_| |_|___/_|\__\_\\__,_|\___|\__\___/|_|
                    
   🚀 Ready to deploy!
```
