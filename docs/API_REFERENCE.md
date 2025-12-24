# 📖 API Reference - Planificator

## 🎯 Méthodes principales

### main.py - Class PlanificatorApp

#### Gestion navigation

```python
def switch_to_main(self)
    """Appelé après login, initialise tables/screens/data"""
    
def switch_to_client(self)
    """Navigue vers écran Client"""
    
def switch_to_contrat(self)
    """Navigue vers écran Contrat"""
    
def switch_to_planning(self)
    """Navigue vers écran Planning"""
    
def switch_to_historique(self)
    """Navigue vers écran Historique"""
    
def switch_to_facture(self)
    """Navigue vers écran Facture"""
    
def switch_to_compte(self)
    """Navigue vers écran Compte utilisateur"""
```

#### Lazy loading (optimisations)

```python
def _initialize_tables(self)
    """Crée 9 MDDataTable après login (lazy)"""
    # Crée: table_en_cours, table_prevision, liste_contrat, etc.
    
def _load_additional_popup_screens(self)
    """Charge 25 screens popup après login (lazy)"""
    # Appelle: popup(self.popup, init_only=False)
    
def _load_main_screens_async(self)
    """Charge main.kv et Sidebar.kv asynchronement"""
```

#### Data population

```python
async def populate_tables(self)
    """Remplit tables avec données BD (async)"""
    # Appelle: fetch_clients(), fetch_contracts(), etc.
    # Met à jour: MDDataTable widgets
    
async def update_table_on_change(self, table_name)
    """Rafraîchit une table après modification"""
```

#### Gestion erreurs

```python
def on_error(self, error_msg)
    """Affiche popup d'erreur utilisateur"""
    
def log_error(self, error, context="")
    """Log erreur en fichier + console"""
```

---

### setting_bd.py - Class DatabaseManager

#### CRUD Client

```python
async def insert_client(self, client_data: dict)
    """Crée nouveau client"""
    # Params: {'nom': str, 'prenom': str, 'email': str, ...}
    # Returns: client_id (int)
    
async def fetch_clients(self, filter_id=None)
    """Récupère liste clients"""
    # Params: filter_id=42 (optionnel, filtre par ID)
    # Returns: List[Client]
    
async def update_client(self, client_id: int, data: dict)
    """Modifie client existant"""
    # Params: client_id=42, data={'nom': 'Nouveau nom'}
    # Returns: True si succès
    
async def delete_client(self, client_id: int)
    """Supprime client"""
    # Params: client_id=42
    # Returns: True si succès
```

#### CRUD Contrat

```python
async def insert_contrat(self, contrat_data: dict)
    """Crée nouveau contrat"""
    # Params: {'client_id': int, 'type': str, 'prix': float, ...}
    
async def fetch_contrats(self, filter_client_id=None)
    """Récupère contrats"""
    # Params: filter_client_id=42 (optionnel)
    
async def update_contrat(self, contrat_id: int, data: dict)
    """Modifie contrat"""
    
async def delete_contrat(self, contrat_id: int)
    """Supprime contrat"""
```

#### CRUD Planning

```python
async def insert_planning(self, planning_data: dict)
    """Crée planning"""
    # Params: {'contrat_id': int, 'date_debut': date, ...}
    
async def fetch_planning(self, filter_contrat_id=None)
    """Récupère plannings"""
    
async def update_planning(self, planning_id: int, data: dict)
    """Modifie planning"""
    
async def delete_planning(self, planning_id: int)
    """Supprime planning"""
```

#### Requêtes spécialisées

```python
async def fetch_traitement_en_cours(self)
    """Récupère traitements actuels (non effectués)"""
    # Returns: List[Traitement]
    
async def fetch_traitement_prevision(self)
    """Récupère prévisions futures"""
    # Returns: List[Traitement]
    
async def filter_client(self, search_term)
    """Recherche clients par nom/prénom"""
    # Params: search_term="Dupont"
    # Returns: List[Client] matching
    
async def traitement_en_cours(self, page=1, rows_num=15)
    """Liste traitements actuels avec pagination"""
    # Returns: List[Traitement]
    
async def traitement_prevision(self, page=1, rows_num=15)
    """Liste prévisions avec pagination"""
```

#### Gestion fréquence/planning

```python
async def planning_per_year(self, year, redondance)
    """Génère dates pour une fréquence donnée"""
    # Params: year=2025, redondance=2 (hebdo)
    # Returns: List[datetime]
    
def get_frequency_label(self, frequency_code: int)
    """Convertit code fréquence en label français"""
    # Params: frequency_code=2
    # Returns: "hebdomadaire"
    
def calculate_next_date(self, last_date, frequency)
    """Calcule prochaine date traitement"""
```

#### Authentification

```python
async def authenticate(self, email: str, password: str)
    """Authentifie utilisateur"""
    # Returns: User object ou None si erreur
    
async def create_user(self, email, password, role='user')
    """Crée nouveau compte utilisateur"""
    
async def update_user(self, user_id, data)
    """Modifie données utilisateur"""
```

---

## 🔧 Utilitaires

### calendrier.py

```python
def generate_dates_for_frequency(start_date, frequency, num_years=1)
    """Génère liste dates selon fréquence"""
    # Params: start_date=Date(2025,1,1), frequency=1 (quotidien)
    # Returns: List[datetime]
    
def get_next_treatment_date(last_date, frequency)
    """Calcule prochaine date de traitement"""
    # Returns: datetime
```

### email_verification.py

```python
def send_verification_email(email: str, code: str)
    """Envoie email de confirmation"""
    
def verify_email_code(email: str, code: str)
    """Vérifie code de confirmation reçu"""
    # Returns: True/False
    
def send_notification(email: str, subject: str, body: str)
    """Envoie notification utilisateur"""
```

### verif_password.py

```python
def hash_password(password: str)
    """Hash password avec werkzeug"""
    # Returns: Hashed string
    
def verify_password(password: str, hashed: str)
    """Vérifie password contre hash"""
    # Returns: True/False
    
def validate_password_strength(password: str)
    """Valide force du password"""
    # Returns: (is_valid: bool, message: str)
```

### excel.py

```python
def export_to_excel(data: list, filename: str)
    """Exporte données en fichier .xlsx"""
    
def import_from_excel(filename: str)
    """Importe données depuis .xlsx"""
    # Returns: List[Dict]
    
def generate_report(data, report_type='summary')
    """Génère rapport Excel formaté"""
```

---

## 📊 Models & Data Structures

### Client
```python
{
    'client_id': int,           # PK
    'nom': str,
    'prenom': str,
    'email': str,
    'telephone': str,
    'adresse': str,
    'date_creation': datetime,
    'actif': bool
}
```

### Contrat
```python
{
    'contrat_id': int,          # PK
    'client_id': int,           # FK
    'type': str,
    'prix': float,
    'date_debut': date,
    'date_fin': date,
    'statut': str,              # 'actif', 'terminé', 'suspendu'
    'description': str
}
```

### Planning
```python
{
    'planning_id': int,         # PK
    'contrat_id': int,          # FK
    'date_debut': date,
    'date_fin': date,
    'redondance': int,          # 0-6 (fréquence)
    'statut': str
}
```

### Traitement
```python
{
    'traitement_id': int,       # PK
    'planning_id': int,         # FK
    'date': date,
    'statut': str,              # 'en attente', 'effectué'
    'remarque': str,
    'prix': float
}
```

### User
```python
{
    'user_id': int,             # PK
    'email': str,
    'mot_de_passe': str,        # Hashed!
    'role': str,                # 'admin', 'user'
    'date_inscription': datetime,
    'actif': bool
}
```

---

## 🔄 Patterns courants

### Ajouter un client

```python
async def on_add_client_button(self):
    """Event handler button 'Ajouter Client'"""
    
    # 1. Récupérer données du formulaire
    form_data = {
        'nom': self.root.get_screen('Client').ids.nom.text,
        'prenom': self.root.get_screen('Client').ids.prenom.text,
        'email': self.root.get_screen('Client').ids.email.text,
        # ...
    }
    
    # 2. Insérer en BD
    try:
        client_id = await self.db.insert_client(form_data)
        
        # 3. Rafraîchir table
        await self.populate_tables()
        
        # 4. Feedback utilisateur
        self.show_popup("✅ Client ajouté!")
    except Exception as e:
        self.show_popup(f"❌ Erreur: {e}")
```

### Modifier un élément

```python
async def on_update_button(self, item_id):
    """Event handler button 'Modifier'"""
    
    # 1. Récupérer nouvelles données
    updated_data = {'nom': 'Nouveau nom', 'email': 'new@email.com'}
    
    # 2. Mettre à jour BD
    try:
        await self.db.update_client(item_id, updated_data)
        
        # 3. Rafraîchir immédiatement
        await self.populate_tables()
        
        # 4. Notification
        self.show_popup("✅ Modifié avec succès!")
    except Exception as e:
        self.show_popup(f"❌ Erreur: {e}")
```

### Pagination

```python
# Formule clé
index_global = (page - 1) * rows_num + row_num - 1

# Exemple d'implémentation
def on_page_change(self, new_page):
    """Appelé quand utilisateur change page"""
    rows_num = 15  # Rows par page
    
    # Calculer index de démarrage
    start_index = (new_page - 1) * rows_num
    end_index = start_index + rows_num
    
    # Filter données
    filtered_data = self.all_data[start_index:end_index]
    
    # Afficher dans table
    self.update_table_display(filtered_data)
```

---

## ⚠️ Pièges courants

### ❌ Utiliser nom au lieu de client_id

```python
# MAUVAIS - les Dupont vont se mélanger!
await self.db.fetch_clients(nom='Dupont')

# BON - clé primaire unique
await self.db.fetch_clients(client_id=42)
```

### ❌ Oublier async/await

```python
# MAUVAIS - va bloquer l'app
data = self.db.fetch_clients()

# BON - non-bloquant
data = await self.db.fetch_clients()
```

### ❌ Pas rafraîchir après modification

```python
# MAUVAIS - table ne se met pas à jour
await self.db.insert_client(data)
# Nothing... table obsolète!

# BON - rafraîchir
await self.db.insert_client(data)
await self.populate_tables()  # Rafraîchir UI
```

### ❌ Index global pagination

```python
# MAUVAIS - décalé
index = page * rows_num + row_num

# BON - off-by-one corrigé
index = (page - 1) * rows_num + row_num - 1
```

---

## 🧪 Exemples complets

### Exemple 1: Ajouter un client avec validation

```python
from verif_password import validate_password_strength

async def create_new_client(self, form_data):
    """Ajouter client avec validation complète"""
    
    # 1. Validation
    if not form_data['nom']:
        raise ValueError("Nom obligatoire")
    if not '@' in form_data['email']:
        raise ValueError("Email invalide")
    
    # 2. Insertion
    try:
        client_id = await self.db.insert_client(form_data)
        print(f"✅ Client {client_id} créé")
        
        # 3. Refresh
        await self.populate_tables()
        
        # 4. Notification
        return True
    except Exception as e:
        print(f"❌ Erreur création client: {e}")
        return False
```

### Exemple 2: Filtrer et afficher

```python
async def search_clients(self, search_term):
    """Recherche clients par nom"""
    
    results = await self.db.filter_client(search_term)
    
    # Mettre à jour table
    if results:
        self.display_table(results)
    else:
        self.show_popup(f"❌ Aucun client trouvé pour '{search_term}'")
```

### Exemple 3: Export Excel

```python
from excel import export_to_excel

async def export_clients_report(self):
    """Exporte tous les clients en Excel"""
    
    # 1. Récupérer données
    clients = await self.db.fetch_clients()
    
    # 2. Exporter
    filename = f"clients_export_{datetime.now().strftime('%Y%m%d')}.xlsx"
    export_to_excel(clients, filename)
    
    # 3. Notification
    self.show_popup(f"✅ Exporté vers {filename}")
```

---

## 📚 Documentation associée

- [ARCHITECTURE.md](ARCHITECTURE.md) - Vue d'ensemble
- [DATABASE.md](DATABASE.md) - Schéma BD
- [GETTING_STARTED.md](GETTING_STARTED.md) - Installation
- [PERFORMANCE.md](PERFORMANCE.md) - Optimisations

---

**Dernière mise à jour**: 24 décembre 2025  
**Version**: 2.0.0  
**Python**: 3.13+
