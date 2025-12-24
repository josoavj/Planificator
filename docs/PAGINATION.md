# 📊 Pagination - Planificator

## 🎯 Concept clé

La pagination permet d'afficher de grandes listes dans **MDDataTable** sans charger toutes les données à la fois.

**Formula**: 
$$\text{index\_global} = (\text{page} - 1) \times \text{rows\_num} + \text{row\_num} - 1$$

---

## 📋 Exemple simple

### Tableau avec 45 clients, 15 par page

```
Page 1: rows 1-15
│
├─ row 1 → index_global = (1-1)*15 + 1 - 1 = 0 ✅
├─ row 2 → index_global = (1-1)*15 + 2 - 1 = 1 ✅
└─ row 15 → index_global = (1-1)*15 + 15 - 1 = 14 ✅

Page 2: rows 16-30
│
├─ row 1 → index_global = (2-1)*15 + 1 - 1 = 15 ✅
├─ row 2 → index_global = (2-1)*15 + 2 - 1 = 16 ✅
├─ row 3 → index_global = (2-1)*15 + 3 - 1 = 17 ✅
└─ row 15 → index_global = (2-1)*15 + 15 - 1 = 29 ✅

Page 3: rows 31-45
│
├─ row 1 → index_global = (3-1)*15 + 1 - 1 = 30 ✅
└─ row 15 → index_global = (3-1)*15 + 15 - 1 = 44 ✅
```

---

## 🔧 Implémentation

### 1. Récupérer les données

```python
async def fetch_all_clients(self):
    """Récupère TOUS les clients (pour pagination)"""
    query = "SELECT * FROM Clients ORDER BY client_id"
    clients = await self.db.fetch_clients()
    return clients
```

### 2. Créer la MDDataTable

```python
def create_client_table(self):
    """Crée la table avec pagination"""
    
    self.liste_client = MDDataTable(
        size_hint=(1, 0.9),
        pos_hint={'center_x': 0.5, 'center_y': 0.4},
        check=True,
        rows_num=15,  # 15 rows par page
        column_data=[
            ("ID", dp(30)),
            ("Nom", dp(100)),
            ("Prénom", dp(100)),
            ("Email", dp(150)),
            ("Action", dp(100)),
        ]
    )
    
    # Remplir avec données (voir section suivante)
    return self.liste_client
```

### 3. Remplir la table avec pagination

```python
async def populate_client_table(self):
    """Remplit table avec données paginées"""
    
    # 1. Récupérer tous les clients
    all_clients = await self.db.fetch_clients()
    
    # 2. Page actuelle (par défaut 1)
    current_page = 1
    rows_num = 15  # Défini dans MDDataTable
    
    # 3. Calculer range
    start_idx = (current_page - 1) * rows_num
    end_idx = start_idx + rows_num
    
    # 4. Filtrer la page courante
    page_data = all_clients[start_idx:end_idx]
    
    # 5. Convertir en format table
    table_data = [
        (str(c['client_id']), c['nom'], c['prenom'], c['email'], '')
        for c in page_data
    ]
    
    # 6. Ajouter à table
    self.liste_client.row_data = table_data
    
    # 7. Enregistrer pour accès ultérieur
    self.current_page_clients = page_data
    self.all_clients = all_clients
```

### 4. Gérer changement de page

```python
def on_page_changed(self, page_num):
    """Appelé quand MDDataTable change de page"""
    
    current_page = page_num
    rows_num = 15
    
    # Recalculer range
    start_idx = (current_page - 1) * rows_num
    end_idx = start_idx + rows_num
    
    # Filtrer et afficher
    page_data = self.all_clients[start_idx:end_idx]
    
    table_data = [
        (str(c['client_id']), c['nom'], c['prenom'], c['email'], '')
        for c in page_data
    ]
    
    self.liste_client.row_data = table_data
    self.current_page_clients = page_data
```

### 5. Gérer clics sur rows

```python
def on_row_press(self, table, row):
    """Appelé quand utilisateur clique sur une row"""
    
    # Récupérer le client cliqué
    # Note: row.index est dans la page actuelle
    client = self.current_page_clients[row.index]
    client_id = client['client_id']
    
    # Ouvrir modal modification
    self.open_edit_dialog(client_id)
```

---

## 🧮 Mathématiques de pagination

### Formules

```
Total items:      N
Items per page:   P
Total pages:      T = ceil(N / P)

Donné:  page (1-indexed), item_in_page (1-indexed)
Trouver: index_in_full_list (0-indexed)

Formula: index = (page - 1) * P + (item_in_page - 1)

Exemple: N=100, P=10
Page 5, item 3:
index = (5-1)*10 + (3-1) = 40 + 2 = 42 ✅ (correct, item 43 dans liste complète)
```

### Cas limites

```
Page 1, item 1:     index = 0 ✅
Page 1, item P:     index = P-1 ✅
Page 2, item 1:     index = P ✅
Page T, item 1:     index = (T-1)*P ✅
Page T, item last:  index = N-1 ✅
```

---

## 🐛 Erreurs courantes

### ❌ OFF-BY-ONE ERROR

```python
# MAUVAIS (décalé de 1)
index = page * rows_num + row_num  # Off!

# BON
index = (page - 1) * rows_num + row_num - 1
```

### ❌ Page 0-indexed vs 1-indexed

```python
# MDDataTable retourne page 1-indexed
# Attention: ne pas recalculer

# Mauvais:
if page == 0:  # MDDataTable n'envoie JAMAIS 0
    start = 0
    
# Bon:
# MDDataTable envoie 1, 2, 3, ...
start = (page - 1) * rows_num  # Correct!
```

### ❌ Oublier - 1 pour row_num

```python
# MAUVAIS (row_num est 1-indexed)
index = (page - 1) * rows_num + row_num

# BON (convertir 1-indexed → 0-indexed)
index = (page - 1) * rows_num + row_num - 1
```

---

## 🔄 Patterns

### Pattern 1: Pagination simple

```python
class ClientScreen:
    def __init__(self):
        self.all_data = []          # Cache complet
        self.current_page = 1       # Page courante
        self.rows_per_page = 15
    
    async def load_data(self):
        """Charger une fois"""
        self.all_data = await db.fetch_clients()
    
    def display_page(self, page_num):
        """Afficher page spécifique"""
        start = (page_num - 1) * self.rows_per_page
        end = start + self.rows_per_page
        
        page_data = self.all_data[start:end]
        self.table.row_data = self._format_for_table(page_data)
        self.current_page = page_num
```

### Pattern 2: Pagination avec filtre

```python
class FilteredClientScreen:
    def __init__(self):
        self.all_data = []
        self.filtered_data = []     # Après filter
        self.current_page = 1
        self.rows_per_page = 15
    
    async def load_data(self):
        self.all_data = await db.fetch_clients()
        self.filtered_data = self.all_data
    
    def apply_filter(self, search_term):
        """Filter + reset page 1"""
        self.filtered_data = [
            c for c in self.all_data 
            if search_term.lower() in c['nom'].lower()
        ]
        self.current_page = 1
        self.display_page(1)
    
    def display_page(self, page_num):
        """Utilise filtered_data au lieu de all_data"""
        start = (page_num - 1) * self.rows_per_page
        end = start + self.rows_per_page
        
        page_data = self.filtered_data[start:end]
        self.table.row_data = self._format_for_table(page_data)
```

### Pattern 3: Lazy pagination (virtualization)

```python
# Pour très grandes listes (10k+ items)
# Charger données à la demande par page

class LazyPaginatedTable:
    async def fetch_page(self, page_num):
        """Fetch juste cette page de BD"""
        rows_num = 15
        offset = (page_num - 1) * rows_num
        
        # BD query avec LIMIT/OFFSET
        query = f"""
            SELECT * FROM Clients 
            ORDER BY client_id
            LIMIT {rows_num} OFFSET {offset}
        """
        return await db.execute_query(query)
    
    async def display_page(self, page_num):
        """Afficher page (fetched on-demand)"""
        page_data = await self.fetch_page(page_num)
        self.table.row_data = self._format_for_table(page_data)
```

---

## 📊 MDDataTable API

### Attributs

```python
table = MDDataTable(
    rows_num=15,              # Rows par page
    check=True,               # Affiche checkboxes
    size_hint=(1, 0.9),       # Taille
    column_data=[             # Définition colonnes
        ("ID", dp(30)),
        ("Nom", dp(100)),
    ]
)

# Accès
table.row_data = [(...), (...)]     # Setter
table.row_data                      # Getter
table.sorted_data                   # Après sort
table.selection_mode_multiple       # Boolean
```

### Événements

```python
# Lors que page change
table.bind(current_pagination_value=self.on_page_change)

# Lors que row est cliquée
table.bind(on_row_press=self.on_row_press)

# Lors que checkbox est coché
table.bind(selected_row=self.on_row_selected)
```

### Fonctions utiles

```python
# Récupérer rows sélectionnées
selected_rows = table.get_checked_row_data()

# Récupérer page courante
current_page = table.current_pagination_value

# Filtrer les données
table.row_data = filtered_data  # MDDataTable gère pagination auto

# Rafraîchir
table.row_data = new_data  # Trigger re-render
```

---

## ✅ Checklist pagination

- [ ] Formula `(page-1)*rows_num + row_num - 1` comprise
- [ ] MDDataTable rows_num défini
- [ ] Page change event connecté
- [ ] Row press event connecté
- [ ] Index global calculé correctement
- [ ] Pas d'off-by-one errors
- [ ] Filtre reset page à 1
- [ ] Rafraîchir après modification
- [ ] Large datasets → lazy load

---

## 🧪 Test pagination

```python
# Test formula
def test_pagination():
    assert index_for(page=1, row=1) == 0
    assert index_for(page=1, row=15) == 14
    assert index_for(page=2, row=1) == 15
    assert index_for(page=2, row=3) == 17
    assert index_for(page=3, row=1) == 30
    print("✅ Tous les tests passent")

def index_for(page, row):
    return (page - 1) * 15 + row - 1

test_pagination()
```

---

## 📚 Références

- [ARCHITECTURE.md](ARCHITECTURE.md) - MDDataTable dans architecture
- [API_REFERENCE.md](API_REFERENCE.md) - Méthodes MDDataTable
- [DATABASE.md](DATABASE.md) - Requêtes avec LIMIT/OFFSET

---

**Dernier commit**: 681c63f (24 décembre 2025)  
**Python**: 3.13+  
**Kivy**: 2.2.1+
