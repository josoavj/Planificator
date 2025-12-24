# 🚀 Getting Started - Planificator

## 📋 Pré-requis

### Système
- **OS**: Linux, macOS, Windows
- **Python**: 3.13+
- **MySQL**: 8.0+
- **RAM**: 4GB minimum
- **Disk**: 500MB

### Logiciels requis
```bash
python --version  # 3.13+
mysql --version   # 8.0+
```

---

## 🔧 Installation en 5 étapes

### 1️⃣ Cloner le repository

```bash
git clone https://github.com/AinaMaminirina18/Planificator.git
cd Planificator
```

### 2️⃣ Créer un environnement Python

```bash
# Option A: venv (recommandé)
python3.13 -m venv venv
source venv/bin/activate  # macOS/Linux
# OU sur Windows:
venv\Scripts\activate

# Option B: conda
conda create -n planificator python=3.13
conda activate planificator
```

### 3️⃣ Installer les dépendances

```bash
pip install -r requirements.txt

# Vérifier l'installation
python -c "import kivy; print(f'Kivy {kivy.__version__}')"
```

### 4️⃣ Configurer la BD

#### Créer la base de données

```bash
# Option A: Depuis MySQL CLI
mysql -u root -p < scripts/Planificator.sql

# Option B: Via GUI (MySQL Workbench)
# Ouvrir scripts/Planificator.sql et l'exécuter
```

#### Modifier config.json

```json
{
  "database": {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "votre_mot_de_passe",
    "database": "planificator"
  },
  "app": {
    "debug": true,
    "theme_color": "#56B5FB"
  }
}
```

### 5️⃣ Lancer l'application

```bash
python main.py
```

**Résultat attendu**:
- Loading screen avec spinner (0.5s)
- Login screen après chargement complet
- Vous êtes prêt à vous connecter! 🎉

---

## 📚 Structure du projet expliquée

### Fichiers principaux

```
main.py (3478 lignes)
├── Point d'entrée de l'app
├── Gestion ScreenManager
├── Event handlers (buttons, inputs)
├── Intégration async avec BD
└── Lazy loading optimisé

setting_bd.py (1821 lignes)
├── Gestionnaire de base de données
├── Requêtes SQL (SELECT, INSERT, UPDATE, DELETE)
├── Logique métier
├── Gestion des erreurs/timeouts
└── Async avec aiomysql

gestion_ecran.py
├── Chargement des écrans KV
├── Gestion des popups
└── Lazy loading screens
```

### Dossiers

| Dossier | Contenu |
|---------|---------|
| `screen/` | 40+ fichiers .kv (interfaces Kivy) |
| `scripts/` | SQL migrations |
| `docs/` | Documentation (vous êtes ici) |
| `logs/` | Fichiers de log runtime |
| `Assets/` | Images et ressources |
| `font/` | Polices personnalisées |

---

## 🧪 Premier test

### Créer un utilisateur test

```bash
mysql -u root -p planificator

INSERT INTO Comptes (email, mot_de_passe, role)
VALUES ('test@example.com', 'hashed_password', 'admin');
```

### Credentials test
```
Email: test@example.com
Password: (voir votre setting_bd.py)
```

---

## 🔐 Configuration sécurité

### 1. Environnement variables (recommandé)

```bash
# Créer .env
echo "DB_HOST=localhost" > .env
echo "DB_USER=root" >> .env
echo "DB_PASSWORD=secure_password" >> .env

# Modifier main.py pour charger .env
import dotenv
dotenv.load_dotenv()
DB_PASSWORD = os.getenv('DB_PASSWORD')
```

### 2. Protection mot de passe

```python
# verif_password.py
from werkzeug.security import generate_password_hash, check_password_hash

# Hash
hashed = generate_password_hash('password123')

# Verify
check_password_hash(hashed, 'password123')  # True
```

### 3. MySQL user permissions

```sql
-- Créer user dédié
CREATE USER 'planificator'@'localhost' IDENTIFIED BY 'secure_pass';

-- Permissions minimales
GRANT SELECT, INSERT, UPDATE, DELETE ON planificator.* 
TO 'planificator'@'localhost';

-- Pas de GRANT ou DROP
```

---

## 🚀 Commandes utiles

### Développement

```bash
# Lancer avec logs
python main.py 2>&1 | tee logs/app.log

# Lancer avec debug
python -u main.py  # Unbuffered output

# Syntax check
python -m py_compile main.py setting_bd.py

# PEP8 check
flake8 *.py --max-line-length=100
```

### BD

```bash
# Sauvegarde
mysqldump -u root -p planificator > backup.sql

# Restauration
mysql -u root -p planificator < backup.sql

# Réinitialiser (ATTENTION!)
mysql -u root -p -e "DROP DATABASE planificator;"
mysql -u root -p < scripts/Planificator.sql
```

### Git

```bash
# Voir les optimisations récentes
git log --oneline | head -5

# Voir les changements
git diff correction master

# Merger optimisations
git checkout master
git merge correction
```

---

## 🐛 Troubleshooting

### ❌ "ModuleNotFoundError: No module named 'kivy'"

```bash
# Solution: Installer requirements
pip install -r requirements.txt

# Ou installer manuellement
pip install kivy kivymd aiomysql
```

### ❌ "MySQL connection refused"

```bash
# Vérifier MySQL running
sudo systemctl status mysql

# Démarrer MySQL
sudo systemctl start mysql

# Ou vérifier credentials dans config.json
```

### ❌ "Table doesn't exist"

```bash
# Réinitialiser BD
mysql -u root -p < scripts/Planificator.sql

# Vérifier import dans main.py
# Doit avoir: mysql -u root -p planificator < scripts/Planificator.sql
```

### ❌ "Event loop already running"

```bash
# Cause: Async/await mélangé
# Solution: Utiliser asyncio.run_coroutine_threadsafe()

# Voir: main.py, switch_to_main()
asyncio.run_coroutine_threadsafe(
    self.populate_tables(),
    self.loop
)
```

### ❌ App très lente au startup

```bash
# Vérifier logs pour messages ⏳
tail -f logs/app.log | grep -E "⏳|❌"

# Optimisations déjà appliquées (voir PERFORMANCE.md):
# ✅ Splash screen
# ✅ Lazy load tables
# ✅ Lazy load screens
# ✅ Async load main.kv/Sidebar.kv
```

---

## 💡 Conseils de développement

### 1. Comprendre la pagination

```python
# Formula importante!
index_global = (page - 1) * rows_num + row_num - 1

# Exemple:
# page=2, rows_num=15, row_num=3
# index = (2-1) * 15 + 3 - 1 = 17 (correct!)
```

### 2. Fréquence (Redondance)

```python
# Système 0-6
FREQUENCY = {
    0: "une seule fois",
    1: "quotidienne",
    2: "hebdomadaire",
    3: "bihebdomadaire",
    4: "mensuelle",
    5: "trimestrielle",
    6: "semestrielle"
}
```

### 3. Client ID (pas de doublons!)

```python
# TOUJOURS utiliser client_id (clé primaire)
# PAS le nom (peut être dupliqué)

# ✅ BON
SELECT * FROM Clients WHERE client_id = 42

# ❌ MAUVAIS
SELECT * FROM Clients WHERE nom = 'Dupont'
```

### 4. Async/await

```python
# Pattern correct:
# 1. Appeler du thread principal (Kivy)
def on_button_press(self):
    asyncio.run_coroutine_threadsafe(
        self.fetch_data(),
        self.loop
    )

# 2. Code async en arrière-plan
async def fetch_data(self):
    data = await self.db.query("SELECT ...")
    # Mettre à jour UI
```

---

## 📖 Ressources

### Documentation officielle
- **Kivy**: https://kivy.org/doc/current/
- **KivyMD**: https://kivymd.readthedocs.io/
- **aiomysql**: https://aiomysql.readthedocs.io/

### Docs du projet
- [ARCHITECTURE.md](ARCHITECTURE.md) - Structure complète
- [PERFORMANCE.md](PERFORMANCE.md) - Optimisations
- [DATABASE.md](DATABASE.md) - Schéma BD
- [API_REFERENCE.md](API_REFERENCE.md) - Méthodes principales
- [BUGS_SOLUTIONS.md](BUGS_SOLUTIONS.md) - Problèmes résolus

### Community
- Stack Overflow: Tag `kivy`
- GitHub Issues: https://github.com/AinaMaminirina18/Planificator/issues

---

## ✅ Checklist de démarrage

- [ ] Python 3.13 installé
- [ ] MySQL 8.0+ en cours d'exécution
- [ ] Repository cloné
- [ ] Venv créé et activé
- [ ] `pip install -r requirements.txt` exécuté
- [ ] Planificator.sql importé en BD
- [ ] config.json configuré
- [ ] `python main.py` lance l'app
- [ ] Loading screen affichée
- [ ] Login screen apparaît après chargement
- [ ] Vous pouvez vous connecter avec test user

---

## 🎉 Prêt!

Vous êtes maintenant prêt à développer! Consultez [ARCHITECTURE.md](ARCHITECTURE.md) pour comprendre la structure et [API_REFERENCE.md](API_REFERENCE.md) pour voir les méthodes principales.

**Bienvenue dans Planificator! 🚀**

---

**Dernière mise à jour**: 24 décembre 2025  
**Version**: 2.0.0  
**Support**: Voir [INDEX.md](INDEX.md#-besoin-daide)
