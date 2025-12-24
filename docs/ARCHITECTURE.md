# 🏗️ Architecture et Structure - Planificator

## 📁 Structure du projet (complète)

```
Planificator/
│
├── 📄 main.py (3478 lignes)
│   └── Point d'entrée, gestion UI principale, ScreenManager
│
├── 📄 setting_bd.py (1821 lignes)
│   └── Gestionnaire BD - requêtes SQL, asyncio, aiomysql
│
├── 📄 gestion_ecran.py
│   └── Gestion des écrans popup
│
├── 📄 calendrier.py
│   └── Logique calendrier pour fréquences
│
├── 📄 email_verification.py
│   ├── Vérification d'email
│   └── Envoi de notifications
│
├── 📄 excel.py
│   └── Export/Import données Excel
│
├── 📄 verif_password.py
│   └── Validation et hachage mot de passe
│
├── 📄 color.txt
├── 📄 config.json
└── 📄 requirements.txt
    └── Dependencies: kivy, kivymd, aiomysql, etc.

├── 📁 screen/ (40+ fichiers .kv)
│   ├── 📄 main.kv (écran principal)
│   ├── 📄 Sidebar.kv (menu latéral)
│   ├── 📄 Login.kv (authentification)
│   ├── 📄 Signup.kv (inscription)
│   ├── 📄 Home.kv (accueil)
│   ├── 📄 About.kv (à propos)
│   ├── 📄 Loading.kv (splash screen - NOUVEAU)
│   │
│   ├── 📁 client/
│   │   ├── Client.kv (liste clients)
│   │   ├── ajout_info_client.kv
│   │   ├── modification_client.kv
│   │   ├── option_client.kv
│   │   └── save_info_client.kv
│   │
│   ├── 📁 contrat/
│   │   ├── contrat.kv (liste contrats)
│   │   ├── new-contrat.kv
│   │   ├── option_contrat.kv
│   │   ├── suppr_contrat.kv
│   │   ├── facture_contrat.kv
│   │   ├── about_treatment.kv
│   │   ├── ajout_planning_contrat.kv
│   │   ├── modif_prix.kv
│   │   └── confirm_prix.kv
│   │
│   ├── 📁 planning/
│   │   ├── planning.kv (vue planning)
│   │   ├── rendu_planning.kv
│   │   ├── selection_planning.kv
│   │   ├── selection_tableau.kv
│   │   ├── ajout_remarque.kv
│   │   ├── option_decalage.kv
│   │   └── ecran_decalage.kv
│   │
│   ├── 📁 compte/
│   │   ├── compte.kv (profil utilisateur)
│   │   ├── compte_not_admin.kv
│   │   ├── modif_compte.kv
│   │   ├── suppr_compte.kv
│   │   └── about_compte.kv
│   │
│   ├── 📁 historique/
│   │   ├── historique.kv (historique traitements)
│   │   ├── histo_remarque.kv
│   │   └── option_histo.kv
│   │
│   └── 📄 modif_date.kv (modal dates)
│       └── Facture.kv (modal factures)
│
├── 📁 scripts/
│   ├── 📄 Planificator.sql (création BD)
│   └── 📄 Migration.sql (migrations)
│
├── 📁 Assets/
│   └── [Images, icons]
│
├── 📁 font/
│   └── [Polices personnalisées]
│
├── 📁 logs/
│   └── [Fichiers journaux runtime]
│
└── 📁 docs/ (documentation)
    ├── 📄 INDEX.md (vous êtes ici)
    ├── 📄 ARCHITECTURE.md
    ├── 📄 TECH_STACK.md
    ├── 📄 PERFORMANCE.md
    ├── 📄 DATABASE.md
    ├── 📄 FREQUENCY_SYSTEM.md
    ├── 📄 PAGINATION.md
    ├── 📄 BUGS_SOLUTIONS.md
    ├── 📄 GETTING_STARTED.md
    └── 📄 API_REFERENCE.md
```

---

## 🔄 Flux d'application

### 1️⃣ Démarrage
```
main.py start
    ↓
Display Loading.kv (splash screen)
    ├─ Show spinner (0.5s)
    └─ Load core screens:
        ├─ Login.kv
        ├─ Signup.kv
        └─ popup() with init_only=True
            ├─ modif_date.kv
            └─ Facture.kv
    ↓
Switch to Login screen
```

### 2️⃣ Authentification
```
Login screen
    ↓
verify_password() + BD query
    ├─ ✅ Success → switch_to_main()
    └─ ❌ Fail → Display error + stay on Login
```

### 3️⃣ Après login (switch_to_main)
```
switch_to_main():
    ├─ _initialize_tables() ← lazy load 7 tables
    │  ├─ table_en_cours
    │  ├─ table_prevision
    │  ├─ liste_contrat
    │  ├─ all_treat
    │  ├─ liste_planning
    │  ├─ liste_client
    │  ├─ historique
    │  └─ facture
    │
    ├─ _load_additional_popup_screens() ← lazy load 25 screens
    │
    ├─ _load_main_screens_async() ← async load main.kv + Sidebar.kv
    │
    ├─ populate_tables() ← async BD queries
    │  ├─ fetch clients
    │  ├─ fetch contrats
    │  ├─ fetch planning
    │  └─ fill MDDataTable with data
    │
    └─ Switch to 'Sidebar' screen
       └─ Display Home by default
```

### 4️⃣ Navigation principale
```
Sidebar (menu latéral)
    ├─ Home
    ├─ Client
    ├─ Contrat
    ├─ Planning
    ├─ Historique
    ├─ Facture
    ├─ Compte
    └─ Logout
```

---

## 🏗️ Couches d'architecture

### 1. Couche Présentation (Kivy + KivyMD)
```python
# main.py - Gestion UI
class PlanificatorApp(MDApp):
    def build(self):
        # Initialise ScreenManager avec 5 screens principaux
        screen = ScreenManager()
        screen.add_widget(Builder.load_file('screen/Loading.kv'))    # Splash
        screen.add_widget(Builder.load_file('screen/Login.kv'))      # Auth
        screen.add_widget(Builder.load_file('screen/Signup.kv'))     # Register
        # main.kv et Sidebar.kv chargés APRÈS login
        return screen
    
    # Méthodes principales
    def switch_to_main(self):              # After login
    def switch_to_client(self):            # Navigation
    def switch_to_contrat(self):
    def switch_to_planning(self):
    def _initialize_tables(self):          # Lazy load tables
    def _load_additional_popup_screens(self):  # Lazy load screens
    def populate_tables(self):             # Fetch + display data
```

**Responsabilités:**
- Gestion ScreenManager
- Affichage des écrans .kv
- Event handling (buttons, inputs)
- Appels vers BD via setting_bd.py

### 2. Couche Métier (setting_bd.py)
```python
# Fonctions principales (queries BD)
class DatabaseManager:
    async def insert_client(client_data)      # CREATE
    async def update_client(client_id, data)  # UPDATE
    async def delete_client(client_id)        # DELETE
    async def fetch_clients()                 # SELECT
    async def fetch_contracts()
    async def fetch_planning()
    
    # Logique métier
    def calculate_next_treatment_date(frequency, last_date)
    def get_treatment_status(planning_id)
```

**Responsabilités:**
- Requêtes SQL asynchrones (aiomysql)
- Validation des données
- Gestion des erreurs/timeouts
- Transactions DB

### 3. Couche Données (MySQL)
```sql
-- Tables principales
Clients (id, nom, prenom, email, ...)
Contrats (id, client_id, type, prix, ...)
Planning (id, contrat_id, date_debut, ...)
PlanningDetails (id, planning_id, statut, ...)
Traitement (id, planning_id, date, remarque, ...)
```

---

## 🔄 Flux données

### Exemple: Afficher liste clients

```
User clicks "Client" button
    ↓
switch_to_client() called (main.py)
    ↓
populate_tables() async (main.py)
    ↓
fetch_clients() async (setting_bd.py)
    ↓
SELECT * FROM Clients WHERE user_id = ? (MySQL)
    ↓
Return list of Client objects
    ↓
Fill MDDataTable widget (main.py)
    ↓
Display in UI (Kivy)
    ↓
User sees list with pagination (click page 2, 3, etc.)
    ↓
calculate_index_global() for filter
    ↓
Load different rows in table
```

---

## 🧩 Composants clés

### ScreenManager (main.py)
- Gère navigation entre écrans
- Conserve l'état des screens
- Utilisé pour transitions fluides

### MDDataTable (tables dynamiques)
- Affiche listes paginées
- Pagination: index_global = (page-1) * rows_num + row_num
- 9 tables différentes (clients, contrats, planning, etc.)

### asyncio + aiomysql
- Requêtes BD non-bloquantes
- Timeout 5s par requête
- Loop = asyncio.get_event_loop()

### Kivy Builder
- Charge .kv (interface markup)
- `Builder.load_file()` → widget hierarchy
- Lazy loading pour perf

---

## 📊 État de l'application

### Flags de contrôle
```python
self._tables_initialized = False        # Flag lazy load tables
self._popup_full_loaded = False         # Flag lazy load screens
self._main_screens_loaded = False       # Flag async screens
self._tables_updated = {}               # Track table updates
self.loop = asyncio.get_event_loop()    # BD event loop
```

### Sessions utilisateur
```python
self.current_user = {
    'id': int,
    'email': str,
    'role': 'admin' | 'user'
}
```

---

## 🔌 Intégrations

### Email (email_verification.py)
- SMTP pour envoi notifications
- Vérification adresses email
- Confirmation inscription

### Calendrier (calendrier.py)
- Calcul dates prochain traitement
- Logique fréquence 0-6
- Gestion jours fériés

### Excel (excel.py)
- Export données en .xlsx
- Import données depuis fichier
- Formatage automatique

---

## 🚀 Optimisations (décembre 2025)

| Phase | Technologie | Impact |
|-------|-------------|--------|
| 1 | Splash screen | UX immédiate |
| 2 | Lazy load tables | -1.5s |
| 3 | Popup conditionnelle | -0.7s |
| 4 | Async screens | -0.2s |
| **Total** | **Progressive loading** | **-2.4s (67%)** |

---

## 📌 Points importants

✅ **Client ID**: Toutes les requêtes utilisent `client_id` (clé primaire)  
✅ **Async**: Toutes les requêtes BD en asyncio pour non-blocking  
✅ **Pagination**: Formula = `(page-1) * rows_num + row_num`  
✅ **Fréquence**: System 0-6 pour intervalles traitement  
✅ **Splash**: Affichage immédiat puis contenu en arrière-plan  

---

**Dernier commit**: 681c63f (24 décembre 2025)  
**Documentation**: À jour avec code en branche `correction`
