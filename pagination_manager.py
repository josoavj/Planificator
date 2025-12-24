"""
Module de gestion centralisée de la pagination pour les tableaux MDDataTable.
Évite la répétition de code et les erreurs de calcul d'index.
"""

class TablePaginator:
    """
    Gestionnaire de pagination pour un tableau MDDataTable.
    
    Gère:
    - Le numéro de page actuelle
    - Le calcul du nombre de pages totales
    - La conversion row_index → index_global dans les données complètes
    - L'avancement/retour de page avec vérifications de limites
    
    Exemple:
    ```python
    paginator = TablePaginator(rows_per_page=8)
    
    # Mettre à jour les données
    paginator.set_total_rows(25)
    
    # Avancer de page
    paginator.next_page()  # → True si succès, False si déjà à la dernière page
    
    # Obtenir l'index global pour un clic
    index = paginator.get_global_index(row_num=2)  # (page-1)*8 + 2
    ```
    """
    
    def __init__(self, rows_per_page=8, initial_page=1):
        """
        Initialise le paginateur.
        
        Args:
            rows_per_page: Nombre de lignes affichées par page (8, 4, 5, etc.)
            initial_page: Numéro de page de départ (défaut: 1)
        """
        self.rows_per_page = rows_per_page
        self.current_page = initial_page
        self.total_rows = 0
    
    def set_total_rows(self, total):
        """
        Définit le nombre total de lignes/éléments.
        Utilisé pour calculer le nombre de pages.
        """
        self.total_rows = total
    
    @property
    def total_pages(self):
        """Calcule le nombre total de pages."""
        if self.total_rows == 0:
            return 1
        return (self.total_rows - 1) // self.rows_per_page + 1
    
    @property
    def is_first_page(self):
        """Vérifie si on est à la première page."""
        return self.current_page == 1
    
    @property
    def is_last_page(self):
        """Vérifie si on est à la dernière page."""
        return self.current_page >= self.total_pages
    
    def next_page(self):
        """
        Avance à la page suivante.
        
        Returns:
            True si l'avancement a réussi, False si déjà à la dernière page
        """
        if self.current_page < self.total_pages:
            self.current_page += 1
            return True
        return False
    
    def prev_page(self):
        """
        Retourne à la page précédente.
        
        Returns:
            True si le retour a réussi, False si déjà à la première page
        """
        if self.current_page > 1:
            self.current_page -= 1
            return True
        return False
    
    def goto_page(self, page_num):
        """
        Va à une page spécifique.
        
        Args:
            page_num: Numéro de page cible (1-indexed)
        
        Returns:
            True si succès, False si le numéro de page est invalide
        """
        if 1 <= page_num <= self.total_pages:
            self.current_page = page_num
            return True
        return False
    
    def get_global_index(self, row_num):
        """
        Convertit le numéro de ligne visible en index global.
        
        Formula: index_global = (current_page - 1) × rows_per_page + row_num
        
        Args:
            row_num: Numéro de ligne visible sur la page actuelle (0-indexed)
        
        Returns:
            Index global dans le tableau de données complet (0-indexed)
            
        Exemple:
            Page 2, 8 lignes/page, clic ligne 3:
            → (2-1) × 8 + 3 = 11 ✅
        """
        return (self.current_page - 1) * self.rows_per_page + row_num
    
    def is_valid_global_index(self, global_index):
        """
        Vérifie si un index global est valide.
        
        Args:
            global_index: L'index à valider
        
        Returns:
            True si 0 <= global_index < total_rows
        """
        return 0 <= global_index < self.total_rows
    
    def reset(self):
        """Réinitialise le paginateur à la page 1."""
        self.current_page = 1
        self.total_rows = 0
    
    def debug_info(self):
        """Retourne les informations de debug sous forme de chaîne."""
        return (
            f"Page {self.current_page}/{self.total_pages} | "
            f"Lignes/page: {self.rows_per_page} | "
            f"Total: {self.total_rows} éléments"
        )


class PaginationHelper:
    """
    Classe utilitaire pour les opérations courantes de pagination.
    À utiliser pour les calculs et validations.
    """
    
    @staticmethod
    def calculate_row_num(row_index, num_columns):
        """
        Calcule le numéro de ligne visible à partir de row.index de Kivy.
        
        Args:
            row_index: row.index fourni par MDDataTable.on_row_press
            num_columns: Nombre de colonnes du tableau
        
        Returns:
            Numéro de ligne (0-indexed)
        """
        return int(row_index / num_columns)
    
    @staticmethod
    def calculate_total_pages(total_rows, rows_per_page):
        """
        Calcule le nombre total de pages.
        
        Args:
            total_rows: Nombre total d'éléments
            rows_per_page: Nombre de lignes par page
        
        Returns:
            Nombre de pages
        """
        if total_rows == 0:
            return 1
        return (total_rows - 1) // rows_per_page + 1
    
    @staticmethod
    def calculate_global_index(current_page, rows_per_page, row_num):
        """
        Calcule l'index global (formule de pagination).
        
        Args:
            current_page: Numéro de page actuelle (1-indexed)
            rows_per_page: Nombre de lignes par page
            row_num: Numéro de ligne visible (0-indexed)
        
        Returns:
            Index global (0-indexed)
        """
        return (current_page - 1) * rows_per_page + row_num
