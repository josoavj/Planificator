from kivy.config import Config
Config.set('graphics', 'resizable', False)

from kivy.uix.screenmanager import ScreenManager
from kivy.clock import Clock, mainthread
from kivy.lang import Builder
from kivy.core.window import Window

Window.size = (1300, 680)
Window.left = 30
Window.top = 80

Window.maxWidth = 1300
Window.maxHeight = 680

import asyncio
import threading
import locale
locale.setlocale(locale.LC_TIME, "fr_FR.utf8")  # Pour linux/MAC - Windows: French_France.1252

from datetime import datetime
from functools import partial

from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.dropdownitem import MDDropDownItem
from kivymd.uix.spinner import MDSpinner
from kivymd.toast import toast

from gestion_ecran import gestion_ecran, popup
from excel import generate_comprehensive_facture_excel, generer_facture_excel, generate_traitements_excel
from pagination_manager import TablePaginator, PaginationHelper


class MyDatatable(MDDataTable):
    def set_default_first_row(self, *args):
        pass

class Screen(MDApp):

    copyright = '©Copyright @APEXNova Labs 2025'
    name = 'Planificator'
    description = 'Logiciel de suivi et gestion de contrat'
    CLM = 'Assets/CLM.JPG'
    CL = 'Assets/CL.JPG'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        from setting_bd import DatabaseManager
        # Parametre de la base de données
        self.color_map = {
            "Effectué": '008000',
            "À venir": 'ff0000',
            "Classé sans suite": 'FFA500'
        }
        self.client_id_map = {}  # ✅ Mapping client_index -> client_id
        self.loop = asyncio.new_event_loop()
        self.database = DatabaseManager(self.loop)
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        self.calendar = None
        asyncio.run_coroutine_threadsafe(self.database.connect(), self.loop)
        self._screens_initialized = False  # Flag pour éviter d'initialiser 2x

    def _display_table_with_delay(self, place, table, delay=0.5):
        """
        Affiche un tableau avec un petit délai pour que le contenu se charge bien.
        
        Args:
            place: Le widget conteneur (BoxLayout)
            table: Le tableau à afficher (MDDataTable)
            delay: Délai avant affichage en secondes (défaut: 0.5s)
        """
        def add_table():
            if place and table:
                place.clear_widgets()
                place.add_widget(table)
                print(f"✅ Tableau ajouté après {delay}s")
        
        Clock.schedule_once(lambda dt: add_table(), delay)

    def on_start(self):
        # Ne rien appeler ici - attendre la connexion réussie
        pass

    def build(self):
        #Configuration de la fenêtre
        self.theme_cls.theme_style= 'Light'
        self.theme_cls.primary_palette = "BlueGray"
        self.icon = self.CLM
        self.title = 'Planificator'.upper()

        self.admin = False
        self.compte = None
        self.not_admin = None
        self.current_client = None
        self.card = None
        self.dialog = None

        # ✅ NOUVELLES: Paginateurs centralisés pour chaque tableau
        self.paginator_contract = TablePaginator(rows_per_page=8)
        self.paginator_client = TablePaginator(rows_per_page=8)
        self.paginator_planning = TablePaginator(rows_per_page=8)
        self.paginator_historic = TablePaginator(rows_per_page=8)
        self.paginator_treat = TablePaginator(rows_per_page=4)
        self.paginator_facture = TablePaginator(rows_per_page=5)
        self.paginator_select_planning = TablePaginator(rows_per_page=5)

        # ✅ LAZY LOADING: Tables créées à la demande au lieu du build()
        self.table_en_cours = None
        self.table_prevision = None
        self.liste_contrat = None
        self.all_treat = None
        self.liste_planning = None
        self.liste_client = None
        self.historique = None
        self.facture = None
        self.account = None
        self._tables_initialized = False
        self._popup_full_loaded = False

        self.popup = ScreenManager(size_hint=( None, None))
        popup(self.popup, init_only=True)  # ✅ Charger seulement les essentiels au démarrage

        #Pour les dropdown
        self.menu = None

        self.dialogue = None

        screen = ScreenManager()
        # ✅ Ajouter le loading screen AVANT les autres écrans
        screen.add_widget(Builder.load_file('screen/Loading.kv'))
        screen.add_widget(Builder.load_file('screen/main.kv'))
        screen.add_widget(Builder.load_file('screen/Login.kv'))
        screen.add_widget(Builder.load_file('screen/Signup.kv'))
        # ⏳ Sidebar.kv chargé APRÈS le login (async)
        
        # ✅ Afficher le loading screen en premier
        screen.current = 'loading'
        
        # ✅ Planifier le chargement du Login après un délai (le temps que le loading s'affiche)
        Clock.schedule_once(lambda dt: self._finish_loading(screen), 0.5)
        
        self._main_screens_loaded = False
        return screen

    def _finish_loading(self, screen):
        """Passer du loading screen à l'écran d'accueil"""
        screen.current = 'before login'
        print("✅ Application chargée, passage à l'écran d'accueil")

    def _initialize_tables(self):
        """Créer les tables à la demande (lazy loading) - appelé après le login"""
        if self._tables_initialized:
            return  # Éviter de créer les tables deux fois
        
        print("⏳ Initialisation des tableaux...")
        
        # ✅ Créer toutes les tables une seule fois
        self.table_en_cours = MDDataTable(
            use_pagination=True,
            rows_num=7,
            elevation=0,
            background_color_header='#56B5FB',
            column_data=[
                ("Date", dp(20)),
                ("Nom", dp(30)),
                ("État", dp(20)),
                ('Axe', dp(24)),
            ]
        )

        self.table_prevision = MDDataTable(
            use_pagination=True,
            rows_num=7,
            elevation=0,
            background_color_header='#56B5FB',
            column_data=[
                ("Date", dp(20)),
                ("Nom", dp(30)),
                ("État", dp(20)),
                ('Axe', dp(24)),
            ]
        )

        self.liste_contrat = MDDataTable(
            pos_hint={'center_x': 0.5, "center_y": 0.53},
            size_hint=(1, 1),
            background_color_header='#56B5FB',
            background_color='#56B5FB',
            rows_num=8,
            use_pagination= True,
            elevation=0,
            column_data=[
                ("Client concerné", dp(60)),
                ("Date du contrat", dp(35)),
                ("Type de traitement", dp(40)),
                ("Fréquence", dp(40)),
            ],
        )

        self.all_treat = MDDataTable(
            pos_hint={'center_x': 0.5, "center_y": 0.53},
            size_hint=(.7, 1),
            background_color_header='#56B5FB',
            background_color='#56B5FB',
            rows_num=4,
            use_pagination=True,
            elevation=0,
            column_data=[
                ("Date du traitement", dp(40)),
                ("Type de traitement", dp(50)),
                ("Fréquence", dp(40)),
            ],
        )

        self.liste_planning = MDDataTable(
            pos_hint={'center_x': .5, "center_y": .5},
            size_hint=(1, 1),
            background_color_header='#56B5FB',
            background_color='#56B5FB',
            rows_num=8,
            use_pagination=True,
            elevation=0,
            column_data=[
                ("Client", dp(50)),
                ("Type de traitement", dp(50)),
                ("Fréquence", dp(30)),
                ("Option", dp(45)),
            ]
        )

        self.liste_client = MDDataTable(
            pos_hint={'center_x': 0.5, "center_y": 0.53},
            size_hint=(1, 1),
            background_color_header='#56B5FB',
            background_color='#56B5FB',
            rows_num=8,
            use_pagination=True,
            elevation=0,
            column_data=[
                ("Client", dp(35)),
                ("Email", dp(60)),
                ("Adresse du client", dp(40)),
                ("Date de contrat du client", dp(40)),
            ]
        )

        self.historique = MDDataTable(
            pos_hint={'center_x': .5, "center_y": .53},
            size_hint=(1, 1),
            background_color_header='#56B5FB',
            background_color='#56B5FB',
            rows_num=8,
            use_pagination=True,
            elevation=0,
            column_data=[
                ("Client", dp(50)),
                ("Durée", dp(40)),
                ("Type de traitement", dp(40)),
                ("Remarques", dp(40))
            ]
        )
        
        self._tables_initialized = True
        print("✅ Tableaux initialisés avec succès")

    def login(self):
        """Gestion de l'action de connexion."""
        username = self.root.get_screen('login').ids.login_username.text
        password = self.root.get_screen('login').ids.login_password.text

        if not username or not password:
            Clock.schedule_once(lambda s: self.show_dialog('Erreur', 'Veuillez compléter tous les champs'), 0)
            return

        asyncio.run_coroutine_threadsafe(self.process_login(username, password), self.loop)

    async def process_login(self, username, password):
        import verif_password as vp

        try:
            result = await self.database.verify_user(username)

            if result and vp.reverse(password, result[5]):
                Clock.schedule_once(lambda dt: self.switch_to_main(), 0)
                Clock.schedule_once(lambda a: self.show_dialog("Succès", "Connexion réussie !"), 0)
                Clock.schedule_once(lambda cl: self.clear_fields('login'), 0.5)
                self.compte = result

                if result[6] == 'Administrateur':
                    self.admin = True

            else:
                Clock.schedule_once(
                    lambda dt: self.show_dialog("Erreur", "Aucun compte trouvé dans la base de données"))
        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_dialog("Erreur", f"Erreur : {str(e)}"))

    def sign_up(self):
        import verif_password as vp
        from email_verification import is_valid_email

        """Gestion de l'action d'inscription."""
        screen = self.root.get_screen('signup')
        nom = screen.ids.nom.text
        prenom = screen.ids.prenom.text
        email = screen.ids.Email.text
        type_compte = screen.ids.type.text
        username = screen.ids.signup_username.text
        password = screen.ids.signup_password.text
        confirm_password = screen.ids.confirm_password.text

        if not all([nom, prenom, email, username, password, confirm_password]):
            Clock.schedule_once(lambda dt: self.show_dialog("Erreur", "Veuillez compléter tous les champs"))
            return

        if not is_valid_email(email):
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Veuillez vérifier votre adresse email'))
            return

        is_password_valid, password_validation_message = vp.get_valid_password(nom, prenom, password, confirm_password)
        if not is_password_valid:
            Clock.schedule_once(lambda dt: self.show_dialog("Erreur", password_validation_message))
            return

        validated_password = password_validation_message
        asyncio.run_coroutine_threadsafe(
            self._add_user_and_handle_feedback(nom, prenom, email, username, validated_password, type_compte),
            self.loop
        )

    async def _add_user_and_handle_feedback(self, nom, prenom, email, username, password, type_compte):
        from aiomysql import OperationalError

        try:
            await self.database.add_user(nom, prenom, email, username, password, type_compte)
            Clock.schedule_once(lambda dt: self.switch_to_login())
            Clock.schedule_once(lambda dt: self.show_dialog("Succès", "Compte créé avec succès !"))
            Clock.schedule_once(lambda dt: self.clear_fields('signup'))

        except OperationalError as error:
            if len(error.args) >= 1 and error.args[0] == 1644:
                Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Un compte administrateur existe déjà'))

            else:
                error_message = error.args[1] if len(error.args) >= 2 else str(error)
                Clock.schedule_once(
                    lambda dt: self.show_dialog('Erreur', f"Erreur de base de données: {error_message}"))
            print(f"OperationalError: {error}")  # Pour le débogage

        except Exception as e:
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Une erreur inattendue est survenue.'))
            print(f"Erreur inattendue: {e}")

    def creer_contrat(self):
        from dateutil.relativedelta import relativedelta

        ecran = self.popup.get_screen('ajout_info_client')
        nom = ecran.ids.nom_client.text
        prenom = ecran.ids.responsable_client.text
        email = ecran.ids.email_client.text
        telephone = ecran.ids.telephone.text
        adresse = ecran.ids.adresse_client.text
        categorie_client = ecran.ids.cat_client.text
        axe = ecran.ids.axe_client.text
        date_ajout = ecran.ids.ajout_client.text
        nif = ecran.ids.nif.text if categorie_client == 'Société' else 0
        stat = ecran.ids.stat.text if categorie_client == 'Société' else 0

        numero_contrat = self.popup.get_screen('new_contrat').ids.num_new_contrat.text
        duree_contrat = self.popup.get_screen('new_contrat').ids.duree_new_contrat.text
        categorie_contrat = self.popup.get_screen('new_contrat').ids.cat_contrat.text
        date_contrat = self.popup.get_screen('new_contrat').ids.date_new_contrat.text
        date_debut = self.popup.get_screen('new_contrat').ids.debut_new_contrat.text
        date_fin = self.popup.get_screen('new_contrat').ids.date_new_contrat.text if duree_contrat == 'Déterminée' else 'Indéterminée'

        if date_fin == "Indéterminée":
            duree = 12
            fin_contrat = 'Indéterminée'
        else:
            fin_contrat_rev = self.reverse_date(date_fin)
            debut_rev = self.reverse_date(date_debut)

            fin_contrat = datetime.strptime(fin_contrat_rev, "%Y-%m-%d").date()
            debut_date = datetime.strptime(debut_rev, "%Y-%m-%d").date()

            diff = relativedelta(fin_contrat, debut_date)
            duree = diff.years * 12 + diff.months

        def maj():
            self.popup.get_screen('ajout_facture').ids.axe_client.text = axe
            self.popup.get_screen('ajout_planning').ids.axe_client.text = axe
            self.popup.get_screen('ajout_planning').ids.type_traitement.text = self.traitement[0]

        async def create():
            self.id_traitement = []
            try:
                # Afficher un spinner pendant la création
                Clock.schedule_once(lambda dt: self.loading_spinner('Sidebar', 'contrat', show=True), 0)
                
                self.traitement, self.categorie_trait = self.get_trait_from_form()

                client = await self.database.create_client(
                    nom, prenom, email, telephone, adresse,
                    self.reverse_date(date_ajout), categorie_client, axe, nif, stat
                )

                self.contrat = await self.database.create_contrat(
                    client,
                    numero_contrat,
                    self.reverse_date(date_contrat),
                    self.reverse_date(date_debut),
                    fin_contrat,
                    duree,
                    duree_contrat,
                    categorie_contrat
                )

                for i in range(len(self.traitement)):
                    type_traitement = await self.database.typetraitement(
                        self.categorie_trait[i], self.traitement[i]
                    )
                    traitement_id = await self.database.creation_traitement(self.contrat, type_traitement)
                    self.id_traitement.append(traitement_id)

                Clock.schedule_once(lambda dt: self.loading_spinner('Sidebar', 'contrat', show=False), 0)
                Clock.schedule_once(lambda dt: self.dismiss_popup(), 0)
                Clock.schedule_once(lambda dt: self.fermer_ecran(), 0)
                Clock.schedule_once(lambda dt: maj(), 0)
                Clock.schedule_once(lambda dt: self.fenetre_contrat('Ajout du planning', 'ajout_planning'), 0)
                Clock.schedule_once(lambda dt: self.show_dialog('Succès', 'Client et contrat créés avec succès'), 0)

            except Exception as e:
                Clock.schedule_once(lambda dt: self.loading_spinner('Sidebar', 'contrat', show=False), 0)
                print(f"❌ Erreur création contrat : {e}")
                import traceback
                traceback.print_exc()
                Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Erreur création contrat: {str(e)}'), 0)

        asyncio.run_coroutine_threadsafe(create(), self.loop)

    async def get_client(self):
        try:
            result = await self.database.get_client()
            if result:
                place = self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen('contrat').ids.tableau_contrat
                self.update_contract_table(place, result)

        except Exception as e:
            print(f"Erreur lors de la récupération des clients: {e}")
            self.show_dialog("Erreur", "Une erreur est survenue lors du chargement des clients.")

    def gestion_planning(self):
        ajout_planning_screen = self.popup.get_screen('ajout_planning')
        mois_fin = ajout_planning_screen.ids.mois_fin.text
        mois_debut = ajout_planning_screen.ids.mois_date.text
        date_prevu = ajout_planning_screen.ids.date_prevu.text
        fréquence = ajout_planning_screen.ids.red_trait.text

        bouton = self.popup.get_screen('ajout_facture').ids.accept

        if self.popup.current == 'ajout_planning':
            if self.verifier_mois(mois_debut) != 'Erreur':
                self.popup.get_screen('ajout_facture').ids.mois_fin.text = mois_fin
                self.popup.get_screen('ajout_facture').ids.montant.text = ''
                self.popup.get_screen('ajout_facture').ids.date_prevu.text = date_prevu
                self.popup.get_screen('ajout_facture').ids.red_trait.text = fréquence
                self.popup.get_screen('ajout_facture').ids.traitement_c.text = self.traitement[0]
                if len(self.traitement) == 1:
                    bouton.text = 'Enregistrer'

                self.fermer_ecran()
                self.fenetre_contrat('Ajout de la facture','ajout_facture')
                self.traitement.pop(0)
            else:
                Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Mot non reconnu comme mois, veuillez verifier'), 0)

        elif not self.traitement:
            self.dismiss_popup()
            self.fermer_ecran()
            Clock.schedule_once(lambda dt: asyncio.run_coroutine_threadsafe(self.populate_tables(), self.loop), 0.5)

            self.clear_fields('new_contrat')
            Clock.schedule_once(lambda dt: self.show_dialog('Enregistrement réussie', 'Le contrat a été bien enregistré'), 0)
            self.remove_tables('contrat')

        else:

            ajout_planning_screen.ids.get('mois_date').text = ''
            ajout_planning_screen.ids.get('mois_fin').text= 'Indéterminée' if mois_fin == 'Indéterminée' else ''
            ajout_planning_screen.ids.get('date_prevu').text = ''
            ajout_planning_screen.ids.get('red_trait').text = '1 mois'
            ajout_planning_screen.ids.type_traitement.text = self.traitement[0]
            self.fermer_ecran()
            self.fenetre_contrat('Ajout du planning','ajout_planning')

    def save_planning(self):
        from dateutil.relativedelta import relativedelta

        mois_debut = self.popup.get_screen('ajout_planning').ids.mois_date.text
        mois_fin = self.popup.get_screen('ajout_planning').ids.mois_fin.text
        date_prevu = self.popup.get_screen('ajout_planning').ids.date_prevu.text
        fréquence = self.popup.get_screen('ajout_planning').ids.red_trait.text
        duree_contrat = self.popup.get_screen('new_contrat').ids.duree_new_contrat.text
        date_debut = self.popup.get_screen('new_contrat').ids.debut_new_contrat.text
        temp = date_debut.split('-')
        date = datetime.strptime(f'{temp[0]}-{temp[1]}-{temp[2]}', "%d-%m-%Y")
        date_fin = date + relativedelta(month=+11)

        montant = self.popup.get_screen('ajout_facture').ids.montant.text
        axe_client = self.popup.get_screen('ajout_facture').ids.axe_client.text
        
        # ✅ CORRECTION: Extraire la redondance en MOIS (nombre entre traitements)
        # Logique:
        # - "une seule fois" → int_red = 0 (cas spécial: 1 seul traitement, pas de fréquence)
        # - "1 mois" → int_red = 1 (1 traitement CHAQUE mois pendant 12 mois)
        # - "2 mois" → int_red = 2 (1 traitement TOUS LES 2 MOIS pendant 12 mois)
        # - "3 mois" → int_red = 3 (1 traitement TOUS LES 3 MOIS pendant 12 mois)
        # - duree='Indéterminée' → la fréquence s'applique sur 12 mois
        if fréquence == 'une seule fois':
            int_red = 0  # Cas spécial: une SEULE date
        else:
            # Format: "X mois" → extraire le nombre X (intervalle en mois)
            int_red = int(fréquence.split(" ")[0])
        
        # duree_contrat ne change pas le calcul de int_red
        # Si duree='Déterminée', on utilise mois_debut et mois_fin
        # Si duree='Indéterminée', on génère sur 12 mois avec la fréquence int_red

        async def save():
            try:
                # ✅ CORRECTION: Vérifier que verifier_mois ne retourne pas 'Erreur'
                mois_debut_verif = self.verifier_mois(mois_debut)
                if mois_debut_verif == 'Erreur':
                    Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Mois de début invalide'), 0)
                    return
                
                debut = datetime.strptime(mois_debut_verif, "%B").month
                
                # ✅ CORRECTION: Vérifier mois_fin aussi
                # Si mois_fin est 'Indéterminée', fin = 0 (valeur spéciale pour indiquer pas de fin)
                fin = 0
                if mois_fin != 'Indéterminée':
                    mois_fin_verif = self.verifier_mois(mois_fin)
                    if mois_fin_verif == 'Erreur':
                        Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Mois de fin invalide'), 0)
                        return
                    fin = datetime.strptime(mois_fin_verif, "%B").month
                else:
                    # ✅ CORRECTION: Si duree est Déterminée mais mois_fin est Indéterminée = incohérence
                    if duree_contrat == 'Déterminée':
                        Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Si durée est déterminée, mois de fin est obligatoire'), 0)
                        return
                
                # ✅ CORRECTION: Vérifier que montant n'est pas vide
                if not montant:
                    Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Le montant est obligatoire'), 0)
                    return
                
                # ✅ CORRECTION: Afficher spinner pendant la création
                Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'ajout_planning', show=True), 0)
                
                # ✅ CORRECTION: Vérifier que self.contrat n'est pas None avant utilisation
                if int_red == 12 and self.contrat:
                    await self.database.un_jour(self.contrat)
                    self.contrat = None
                
                planning = await self.database.create_planning(self.id_traitement[0],
                                                               self.reverse_date(date_debut),
                                                               debut,
                                                               fin,
                                                               int_red,
                                                               date_fin)

                dates_planifiees = self.planning_per_year(date_prevu, int_red)
                
                # ✅ CORRECTION: Créer tous les détails de planning et factures
                factures_creees = 0
                for idx, date in enumerate(dates_planifiees):
                    try:
                        planning_detail = await self.database.create_planning_details(planning, date)
                        await self.database.create_facture(planning_detail,
                                                           int(montant) if ' ' not in montant else int(montant.replace(' ', '')),
                                                           date,
                                                           axe_client)
                        factures_creees += 1
                        print(f"✅ Facture {factures_creees}/{len(dates_planifiees)} créée pour {date}")

                    except Exception as e:
                        print(f"❌ Erreur création facture {idx+1}: {e}")
                        import traceback
                        traceback.print_exc()

                self.id_traitement.pop(0)
                Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'ajout_planning', show=False), 0.2)
                Clock.schedule_once(lambda dt: self.show_dialog('Succès', f'{factures_creees} facture(s) créée(s)'), 0.3)

            except Exception as e:
                Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'ajout_planning', show=False), 0)
                print(f"❌ Erreur save_planning: {e}")
                import traceback
                traceback.print_exc()
                Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Erreur planning: {str(e)}'), 0)

        asyncio.run_coroutine_threadsafe(save(), self.loop)
        self.gestion_planning()

    def planning_per_year(self, debut, fréquence):
        """Génère les dates de planning selon la fréquence
        
        fréquence = 0: Une seule fois → 1 date
        fréquence = 1: Chaque mois → 12 dates (0, 1, 2, ..., 11 mois)
        fréquence = 2: Tous les 2 mois → 6 dates (0, 2, 4, 6, 8, 10 mois)
        fréquence = 3: Tous les 3 mois → 4 dates (0, 3, 6, 9 mois)
        """
        from datetime import timedelta
        from tester_date import ajuster_si_weekend, jours_feries

        pas = int(fréquence)
        date = datetime.strptime(self.reverse_date(debut), "%Y-%m-%d").date()

        def ajouter_mois(date_depart, nombre_mois):
            import calendar
            """Ajoute un nombre de mois à une date."""
            mois = date_depart.month - 1 + nombre_mois
            annee = date_depart.year + mois // 12
            mois = mois % 12 + 1
            jour = min(date_depart.day, calendar.monthrange(annee, mois)[1])
            return datetime(annee, mois, jour).date()

        dates = []
        
        # ✅ CORRECTION: Cas spécial "une seule fois" (pas=0)
        if pas == 0:
            # Une seule date
            date_unique = ajuster_si_weekend(date)
            feries = jours_feries(date_unique.year)
            while date_unique in feries.values():
                date_unique += timedelta(days=1)
            dates.append(date_unique)
        else:
            # Cas normal: générer une date tous les pas mois pendant 12 mois
            # Pour pas=1 (chaque mois): génère 12 dates
            # Pour pas=2 (tous les 2 mois): génère 6 dates
            # Pour pas=3 (tous les 3 mois): génère 4 dates
            # Etc.
            for i in range(12 // pas):
                date_suivante = ajouter_mois(date, i * pas)
                date_suivante = ajuster_si_weekend(date_suivante)
                feries = jours_feries(date_suivante.year)
                while date_suivante in feries.values():
                    date_suivante += timedelta(days=1)
                dates.append(date_suivante)

        return dates

    async def get_all_planning(self):
        try:
            return await self.database.get_all_planning()
        except Exception as e:
            print('func get_all_planning', e)
            return []

    def update_account(self, nom, prenom, email, username, password, confirm):
        import verif_password as vp
        from email_verification import is_valid_email

        is_valid, valid_password = vp.get_valid_password(nom, prenom, password, confirm)

        if not all([nom, prenom, email, username, password, confirm]):
            Clock.schedule_once(lambda dt: self.show_dialog("Erreur", "Veuillez completer tous les champs."), 0)
            return

        if not is_valid_email(email):
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Veuillez verifier votre adresse email.'), 0)
            return

        if not is_valid:
            Clock.schedule_once(lambda dt: self.show_dialog("Erreur", valid_password), 0)
            return

        # ✅ Afficher spinner pendant modification
        Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'compte', show=True), 0)

        async def update_user_task():
            try:
                await self.database.update_user(nom, prenom, email, username, valid_password, self.compte[0])

                def _post_update_ui_actions():
                    Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'compte', show=False), 0)
                    Clock.schedule_once(lambda dt: self.show_dialog("Succes", "Les modifications ont ete enregistrees avec succes !"), 0)
                    Clock.schedule_once(lambda dt: self.clear_fields('modif_info_compte'), 0.2)
                    Clock.schedule_once(lambda dt: self.current_compte(), 0.2)
                    Clock.schedule_once(lambda dt: self.dismiss_popup(), 0.3)
                    Clock.schedule_once(lambda dt: self.fermer_ecran(), 0.3)

                _post_update_ui_actions()
            except Exception as error:
                print(f'❌ Erreur update_account: {error}')
                import traceback
                traceback.print_exc()
                Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'compte', show=False), 0)
                Clock.schedule_once(lambda dt: self.show_dialog("Erreur", f'Modification echouee: {str(error)}'), 0)

        asyncio.run_coroutine_threadsafe(update_user_task(), self.loop)

    def current_compte(self):
        ecran = 'compte' if self.admin else 'not_admin'
        target_screen = self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen(ecran)
        async def current():
            compte = await self.database.get_current_user(self.compte[0])
            target_screen.ids.nom.text = f'Nom : {compte[1]}'
            target_screen.ids.prenom.text = f'Prénom : {compte[2]}'
            target_screen.ids.email.text = f'Email : {compte[3]}'
            target_screen.ids.username.text = f"Nom d'utilisateur : {compte[4]}"

            self.compte = compte

        asyncio.run_coroutine_threadsafe(current(), self.loop)

    async def supprimer_client(self):
        try:
            # ✅ Afficher spinner pendant suppression
            Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'planning', show=True), 0)
            
            await self.database.delete_client(self.current_client[0])
            
            # ✅ CORRECTION: Attendre que la BD traite la suppression
            await asyncio.sleep(0.5)
            
            # ✅ CORRECTION: Lancer les rafraîchissements en PARALLÈLE et ATTENDRE
            await asyncio.gather(
                self.populate_tables(),
                self.all_clients()
            )
            
            Clock.schedule_once(lambda dt: self.remove_tables('contrat'), 0)
            Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'planning', show=False), 0)
            Clock.schedule_once(lambda dt: self.show_dialog('Suppression reussi', 'Le client a bien ete supprime'), 0)

        except Exception as e:
            print(f'❌ Erreur suppression client: {e}')
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'planning', show=False), 0)
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Suppression echouee: {str(e)}'), 0)

    def delete_client(self):
        self.fermer_ecran()
        self.dismiss_popup()
        
        # ✅ Vérifier que le screen 'planning' existe avant d'y accéder
        try:
            place = self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen('planning').ids.tableau_planning
            place.clear_widgets()
        except Exception as e:
            print(f"⚠️ Screen 'planning' non trouvé: {e}")
            return
        
        # ✅ Afficher spinner immediatement (avec gestion d'erreur)
        Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'planning', show=True), 0)

        def dlt():
            asyncio.run_coroutine_threadsafe(self.supprimer_client(), self.loop)

        Clock.schedule_once(lambda dt: dlt(), 0.1)

    def delete_account(self, admin_password):
        import verif_password as vp

        if vp.reverse(admin_password,self.compte[5]):
            # ✅ Afficher spinner pendant suppression
            Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'compte', show=True), 0)
            
            async def suppression():
                try:
                    await self.database.delete_user(self.not_admin[3])
                    Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'compte', show=False), 0)
                    Clock.schedule_once(lambda dt: self.dismiss_popup(), 0.1)
                    Clock.schedule_once(lambda dt: self.fermer_ecran(), 0.1)
                    Clock.schedule_once(lambda dt: self.show_dialog('', 'Suppression du compte reussie'), 0.2)
                    Clock.schedule_once(lambda dt: self.remove_tables('compte'), 0.5)

                except Exception as error:
                    print(f'❌ Erreur delete_account: {error}')
                    import traceback
                    traceback.print_exc()
                    Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'compte', show=False), 0)
                    Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Suppression echouee: {str(error)}'), 0)

            asyncio.run_coroutine_threadsafe(suppression(), self.loop)
        else:
            self.popup.get_screen('suppression_compte').ids.admin_password.helper_text = 'Verifier le mot de passe'
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f"Le mot de passe n'est pas correct"), 0)

    def get_trait_from_form(self):

        traitement = []
        categorie =[]
        dératisation = self.popup.get_screen('new_contrat').ids.deratisation.active
        désinfection = self.popup.get_screen('new_contrat').ids.desinfection.active
        désinsectisation = self.popup.get_screen('new_contrat').ids.desinsectisation.active
        nettoyage = self.popup.get_screen('new_contrat').ids.nettoyage.active
        fumigation = self.popup.get_screen('new_contrat').ids.fumigation.active
        ramassage = self.popup.get_screen('new_contrat').ids.ramassage.active
        anti_termite = self.popup.get_screen('new_contrat').ids.anti_ter.active

        if dératisation:
            traitement.append('Dératisation (PC)')
            categorie.append('PC')
        if désinfection:
            traitement.append('Désinfection (PC)')
            categorie.append('PC')
        if désinsectisation:
            categorie.append('PC')
            traitement.append('Désinsectisation (PC)')
        if nettoyage:
            categorie.append('NI: Nettoyage Industriel')
            traitement.append('Nettoyage industriel (NI)')
        if fumigation:
            categorie.append('PC')
            traitement.append('Fumigation (PC)')
        if ramassage:
            categorie.append("RO: Ramassage Ordures")
            traitement.append("Ramassage ordures (RO)")
        if anti_termite:
            categorie.append('AT: Anti termites')
            traitement.append('Anti termites (AT)')

        return traitement, categorie

    def search(self, text, search='False'):
        """if search:
            print(self.verifier_mois(text)) """
        self.fenetre_planning('', 'ajout_remarque')

    def on_check_press(self, active):
        ecran = self.popup.get_screen('ajout_remarque')
        label = ecran.ids.label_cheque
        label1 = ecran.ids.label_espece
        cheque = ecran.ids.cheque
        espece = ecran.ids.espece
        label_v = ecran.ids.label_virement
        virement = ecran.ids.virement
        label_m = ecran.ids.label_money
        mobile_money = ecran.ids.mobile_money
        num_fact = ecran.ids.numero_facture
        descri = ecran.ids.date_payement
        etab = ecran.ids.etablissement
        num_cheque = ecran.ids.num_cheque
        icon = ecran.ids.icon

        if active:
            label.opacity = 1
            label1.opacity = 1
            label_v.opacity = 1
            label_m.opacity = 1
            label.disabled = False
            label1.disabled = False
            label_v.disabled = False
            label_m.disabled = False
            num_fact.disabled = False
            etab.disabled = False
            num_cheque.disabled = False
            descri.disabled = False
            icon.disabled = False
            num_fact.opacity = 1
            icon.opacity = 1
            mobile_money.opacity = 1
            virement.opacity = 1
            cheque.opacity = 1
            espece.opacity = 1
            descri.opacity = 1
            etab.opacity = 1
            num_cheque.opacity = 1
            cheque.active = True
        else:
            label.opacity = 0
            label1.opacity = 0
            label_v.opacity = 0
            label_m.opacity = 0
            label.disabled = True
            label1.disabled = True
            label_v.disabled = True
            num_fact.disabled = True
            label_m.disabled = True
            etab.disabled = True
            num_cheque.disabled = True
            icon.disabled = True
            num_fact.opacity = 0
            icon.opacity = 0
            mobile_money.opacity = 0
            virement.opacity = 0
            cheque.opacity = 0
            espece.opacity = 0
            descri.opacity = 0
            etab.opacity = 0
            num_cheque.opacity = 0
            descri.disabled = True
            descri.text = ''
            num_fact.text = ''
            num_cheque.text = ''
            etab.text = ''

    def activate_descri(self, paye):
        ecran = self.popup.get_screen('ajout_remarque')
        cheque = ecran.ids.cheque.active
        virement = ecran.ids.virement.active
        etab = ecran.ids.etablissement
        num_cheque = ecran.ids.num_cheque
        if paye and cheque:
            etab.disabled = False
            etab.opacity = 1
            num_cheque.disabled = False
            num_cheque.opacity = 1
        else:
            etab.opacity = 0
            etab.disabled = True
            etab.text = ''
            num_cheque.opacity = 0
            num_cheque.disabled = True
            num_cheque.text = ''

    def verifier_mois(self, text ):
        from fuzzywuzzy import process

        mois_valides = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre"
        ]
        mot_corigees, score = process.extractOne(text.lower(), mois_valides)
        if score >= 80:
            return mot_corigees
        else:
            return 'Erreur'

    def show_dialog(self, titre, texte):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        if not hasattr(self, 'dialogue') or self.dialogue is None or titre != 'Déconnexion':
            self.dialogue = MDDialog(
                title=titre,
                text=texte,
                buttons=[
                    MDFlatButton(
                        text="OK",
                        on_release=lambda x: self.close_dialog()
                    )
                ],
            )
        if titre == 'Déconnexion':
            self.dialogue = MDDialog(
                title= titre,
                text= texte,
                buttons=[
                    MDFlatButton(
                        text='OUI',
                        on_release= lambda x: self.deconnexion()
                    ),
                    MDFlatButton(
                        text= 'NON',
                        on_release= lambda x: self.close_dialog()
                    )
                ]
            )
        self.dialogue.open()

    def deconnexion(self):
        self.close_dialog()
        self.root.current = 'before login'
        self.admin = False
        self.compte = None

    def close_dialog(self):
        self.dialogue.dismiss()

    def reverse_date(self, ex_date):
        if not ex_date:
            return 'N/A'
        date_str = str(ex_date).strip()
        parts = date_str.split('-')
        if len(parts) != 3:
            return date_str  # Return as-is if format is unexpected
        y, m, d = parts
        date = f'{d}-{m}-{y}'
        return date

    def calendrier(self, ecran, champ):
        from kivymd.uix.pickers import MDDatePicker

        if not self.calendar:
            if ecran == 'ecran_decalage' or ecran == 'modif_date':
                self.calendar = MDDatePicker(year=self.planning_detail[9].year,
                                             month=self.planning_detail[9].month,
                                             day=self.planning_detail[9].day,
                                             primary_color='#A5D8FD')
            else:
                self.calendar = MDDatePicker(primary_color='#A5D8FD')

        self.calendar.open()
        self.calendar.bind(on_save=partial(self.choix_date, ecran, champ))

    def choix_date(self, ecran, champ, instance, value, date_range):
        manager = self.popup
        manager.get_screen(ecran).ids[champ].text = ''
        manager.get_screen(ecran).ids[champ].text = str(self.reverse_date(value))
        self.calendar = None

    def fermer_ecran(self):
        self.dialog.dismiss()

    def fenetre_contrat(self, titre, ecran):
        from kivymd.uix.dialog import MDDialog

        self.popup.current = 'vide'
        self.popup.current = ecran
        contrat = MDDialog(
            md_bg_color='#56B5FB',
            title=titre,
            type='custom',
            size_hint=(.8, .85) if ecran == 'ajout_info_client' else (.8,.4) if ecran == 'save_info_client' else (.8, .75) if ecran == 'new_contrat' else (.8, .65) ,
            content_cls= self.popup,
            auto_dismiss=False
        )
        hauteur = '500dp' if ecran == 'option_contrat' else '430dp' if ecran == 'new_contrat' else '520dp' if ecran == 'ajout_info_client' else '300dp' if ecran == 'save_info_client' else '400dp'
        self.popup.height = hauteur
        self.popup.width = '1000dp'
        self.dialog = contrat
        self.dialog.bind(on_dismiss=self.dismiss_popup)

        self.dialog.open()

    def modifier_date(self, source=None):
        from kivymd.uix.dialog import MDDialog

        self.dismiss_popup()
        self.fermer_ecran()

        self.popup.current = 'modif_date'
        acceuil = MDDialog(
            md_bg_color='#56B5FB',
            type='custom',
            size_hint=(.5, .5),
            content_cls=self.popup,
            auto_dismiss=False
        )

        self.popup.height = '300dp'
        self.popup.width = '600dp'

        self.dialog = acceuil
        self.dialog.bind(on_dismiss=self.dismiss_popup)

        self.dialog.open()

    def changer_date(self):
        date = self.popup.get_screen('modif_date').ids.date_decalage.text

        if not date:
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Aucune date est choisie'), 0)
            return

        # ✅ Afficher spinner pendant modification
        Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'modif_date', show=True), 0)

        async def modifier(date_val):
            try:
                await self.database.modifier_date(self.planning_detail[8], self.reverse_date(date_val))
                Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'modif_date', show=False), 0)
                Clock.schedule_once(lambda dt: self.show_dialog('Succès', 'Date modifiée avec succès'), 0)
                Clock.schedule_once(lambda dt: self.dismiss_popup(), 0.5)
                Clock.schedule_once(lambda dt: self.fermer_ecran(), 0.5)
                Clock.schedule_once(lambda dt: self.remove_tables('planning'), 0.6)
            except Exception as e:
                print(f'❌ Erreur changer_date: {e}')
                import traceback
                traceback.print_exc()
                Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'modif_date', show=False), 0)
                Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Modification échouée: {str(e)}'), 0)

        asyncio.run_coroutine_threadsafe(modifier(date), self.loop)

    def changer_prix(self):
        # ✅ CORRECTION: Récupérer et valider les données
        old_price = self.popup.get_screen('modif_prix').ids.prix_init.text
        new_price = self.popup.get_screen('modif_prix').ids.new_price.text

        # ✅ CORRECTION: Validation du champ nouveau prix
        if not new_price or not new_price.strip():
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Veuillez entrer un nouveau prix'), 0)
            return
        
        # ✅ CORRECTION: Vérifier que self.date et self.current_client sont définis
        if not hasattr(self, 'date') or not self.date:
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Date non définie'), 0)
            return
        
        if not hasattr(self, 'current_client') or not self.current_client:
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Client non défini'), 0)
            return

        async def changer(old, new):
            try:
                # ✅ CORRECTION: Valider que old et new sont des nombres
                try:
                    old_val = int(old) if old else 0
                    new_val = int(new)
                except ValueError as e:
                    raise ValueError(f"Prix invalide: {e}")
                
                facture_id = await self.database.get_facture_id(self.current_client[0], self.date)
                
                if not facture_id:
                    raise ValueError("Facture non trouvée")
                
                await self.database.majMontantEtHistorique(facture_id, old_val, new_val)
                Clock.schedule_once(lambda dt: self.show_dialog('Succès', 'Changement de prix réussi'), 0)
                Clock.schedule_once(lambda dt: self.dismiss_popup(), 0.5)
                Clock.schedule_once(lambda dt: self.fermer_ecran(), 0.5)
                Clock.schedule_once(lambda dt: self.remove_tables('facture'), 0.6)
            except Exception as e:
                print(f'❌ Erreur changer_prix: {e}')
                import traceback
                traceback.print_exc()
                Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Modification de prix échouée: {str(e)}'), 0)

        # ✅ CORRECTION: Nettoyer les prix de manière cohérente
        old_clean = old_price.rstrip('Ar').replace(' ', '').strip()
        new_clean = new_price.rstrip('Ar').replace(' ', '').strip()
        
        asyncio.run_coroutine_threadsafe(changer(old_clean, new_clean), self.loop)

    def screen_modifier_prix(self, table, row):
        # ✅ Utiliser le paginateur pour les factures
        try:
            # ✅ Déterminer quelle colonne a été cliquée
            num_columns = len(table.column_data)
            row_num = PaginationHelper.calculate_row_num(row.index, num_columns)
            column_num = row.index % num_columns  # 0=Date, 1=Montant, 2=Etat
            
            print(f"🔹 Clic: row_num={row_num}, column={column_num} (colonne '{table.column_data[column_num][0]}')")
            
            # ✅ Permettre le clic sur n'importe quelle colonne (pas seulement le Montant)
            # Les trois colonnes sont: Date, Montant, Etat
            # On peut cliquer sur n'importe laquelle pour modifier le prix
            
            index_global = self.paginator_facture.get_global_index(row_num)
            
            # ✅ Vérifier que l'index est valide
            if not self.paginator_facture.is_valid_global_index(index_global):
                Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Ligne invalide'), 0)
                return
                
            row_value = table.row_data[index_global]
            
            # ✅ Vérifier que row_value est valide
            if not row_value or len(row_value) < 2:
                Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Données de ligne invalides'), 0)
                return
            
            # ✅ Stocker les données avant ouverture du dialog
            self.date = self.reverse_date(row_value[0])
            prix_initial = row_value[1]
            
            print(f"✅ Modification prix pour: {row_value[0]} (Prix: {prix_initial})")
            
            # ✅ Afficher d'abord la fenêtre de confirmation
            def ouvrir_confirmation(dt):
                try:
                    # ✅ Remplir les champs de confirmation
                    self.popup.get_screen('confirm_prix').ids.date_value.text = self.date
                    self.popup.get_screen('confirm_prix').ids.prix_actuel.text = prix_initial
                    
                    from kivymd.uix.dialog import MDDialog
                    
                    # ✅ Fermer seulement le popup précédent, pas l'écran
                    # (l'appel à fermer_ecran() sera fait quand l'utilisateur annule)
                    self.dismiss_popup()
                    
                    self.popup.current = 'confirm_prix'
                    confirmation_dialog = MDDialog(
                        md_bg_color='#56B5FB',
                        type='custom',
                        size_hint=(.5, .5),
                        content_cls=self.popup,
                        auto_dismiss=False
                    )
                    
                    self.popup.height = '300dp'
                    self.popup.width = '600dp'
                    
                    # ✅ Stocker le dialog
                    self.dialog = confirmation_dialog
                    self.dialog.bind(on_dismiss=self.dismiss_popup)
                    self.dialog.open()
                except Exception as e:
                    print(f'❌ Erreur ouverture dialog confirmation: {e}')
                    import traceback
                    traceback.print_exc()
                    Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Erreur ouverture confirmation: {str(e)}'), 0)
            
            Clock.schedule_once(ouvrir_confirmation, 0.2)
            
        except Exception as e:
            print(f'❌ Erreur screen_modifier_prix: {e}')
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'modif_prix', show=False), 0)
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Erreur accès ligne: {str(e)}'), 0)

    def proceed_to_modify_price(self):
        """Passe de la fenêtre de confirmation à la fenêtre de modification de prix"""
        try:
            # ✅ Récupérer les données depuis la fenêtre de confirmation
            date_value = self.popup.get_screen('confirm_prix').ids.date_value.text
            prix_initial = self.popup.get_screen('confirm_prix').ids.prix_actuel.text
            
            print(f"✅ Passage à la modification: {date_value} (Prix: {prix_initial})")
            
            # ✅ Ouvrir la fenêtre de modification
            def ouvrir_modif(dt):
                try:
                    self.popup.get_screen('modif_prix').ids.prix_init.text = prix_initial
                    self.popup.get_screen('modif_prix').ids.new_price.text = ''
                    
                    from kivymd.uix.dialog import MDDialog
                    
                    # ✅ Fermer les dialogs précédents avant d'en ouvrir un nouveau
                    self.fermer_ecran()
                    self.dismiss_popup()
                    
                    self.popup.current = 'modif_prix'
                    modification_dialog = MDDialog(
                        md_bg_color='#56B5FB',
                        type='custom',
                        size_hint=(.5, .5),
                        content_cls=self.popup,
                        auto_dismiss=False
                    )
                    
                    self.popup.height = '300dp'
                    self.popup.width = '600dp'
                    
                    # ✅ Stocker le dialog
                    self.dialog = modification_dialog
                    self.dialog.bind(on_dismiss=self.dismiss_popup)
                    self.dialog.open()
                except Exception as e:
                    print(f'❌ Erreur passage modification: {e}')
                    import traceback
                    traceback.print_exc()
                    Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Erreur ouverture modification: {str(e)}'), 0)
            
            Clock.schedule_once(ouvrir_modif, 0.2)
            
        except Exception as e:
            print(f'❌ Erreur proceed_to_modify_price: {e}')
            import traceback
            traceback.print_exc()

    def afficher_facture(self, titre ,ecran):
        from kivymd.uix.dialog import MDDialog

        self.fermer_ecran()
        self.dismiss_popup()

        self.popup.current = ecran
        acceuil = MDDialog(
            md_bg_color='#56B5FB',
            title=titre,
            type='custom',
            size_hint=(.7, .6),
            content_cls=self.popup,
            auto_dismiss=False
        )
        self.popup.height = '500dp'
        self.popup.width = '850dp'

        place = self.popup.get_screen('facture').ids.tableau_facture
        place.clear_widgets()
        self.dialog = acceuil
        self.dialog.bind(on_dismiss=self.dismiss_popup)
        
        # ✅ CORRECTION: Vérifier que current_client n'est pas None
        if self.current_client is None:
            print(f"❌ Erreur afficher_facture: current_client est None")
            self.show_dialog('Erreur', 'Erreur: Client non sélectionné')
            acceuil.dismiss()
            return
        
        self.popup.get_screen('facture').ids.titre.text = f'Les factures de {self.current_client[1]} pour {self.current_client[5]}'

        # ✅ Afficher spinner immediatement
        Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'facture', show=True), 0)

        def recup():
            asyncio.run_coroutine_threadsafe(self.recuperer_donnee(place), self.loop)

        Clock.schedule_once(lambda dt: recup(), 0.2)

        self.dialog.open()

    async def recuperer_donnee(self, place):
        try:
            facture, paye, non_paye = await self.database.get_facture(self.current_client[0], self.current_client[5])
            Clock.schedule_once(lambda dt: self.afficher_tableau_facture(place, facture, paye, non_paye), 0.2)
            Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'facture', show=False), 0.3)

        except Exception as e:
            print(f'❌ Erreur recuperation factures: {e}')
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'facture', show=False), 0)
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Erreur chargement factures: {str(e)}'), 0)

    def afficher_tableau_facture(self, place, result, paye, non_paye):
        if result:
            self.popup.get_screen('facture').ids.non_payé.text = f'Non payé :  {non_paye} AR'
            self.popup.get_screen('facture').ids.payé.text = f'Payé : {paye} AR'
            row_data = [(self.reverse_date(i[0]), f'{i[1]} Ar', i[2]) for i in result ]

            self.facture = MDDataTable(
                pos_hint={'center_x':.5, "center_y": .6},
                size_hint=(.75,.9),
                background_color_header = '#56B5FB',
                background_color= '#56B5FB',
                rows_num=5,
                elevation=0,
                use_pagination= True,
                column_data=[
                    ("Date", dp(50)),
                    ("Montant", dp(40)),
                    ("Etat", dp(30)),
                ]
            )
            
            # ✅ Initialiser le paginateur pour les factures
            self.paginator_facture.set_total_rows(len(row_data))
            self.paginator_facture.reset()

            pagination = self.facture.pagination

            btn_prev = pagination.ids.button_back
            btn_next = pagination.ids.button_forward

            def on_press_page(direction, instance=None):
                print(f"📄 Facture: {direction} | {self.paginator_facture.debug_info()}")
                if direction == 'moins':
                    self.paginator_facture.prev_page()
                elif direction == 'plus':
                    self.paginator_facture.next_page()

            btn_prev.bind(on_press=partial(on_press_page, 'moins'))
            btn_next.bind(on_press=partial(on_press_page, 'plus'))

            def _():
                self.facture.row_data = row_data

            self.facture.bind(on_row_press=lambda instance, row: self.screen_modifier_prix(instance, row))
            
            # ✅ Afficher avec délai pour que les données se chargent bien
            def set_and_display():
                self.facture.row_data = row_data
                self._display_table_with_delay(place, self.facture, delay=0.3)
            
            Clock.schedule_once(lambda dt: set_and_display(), 0)

    def fenetre_acceuil(self, titre, ecran, client, date,type_traitement, durée, debut_contrat, fin_prévu):
        from kivymd.uix.dialog import MDDialog

        self.popup.current = 'vide'
        self.popup.current = ecran
        acceuil = MDDialog(
            md_bg_color='#56B5FB',
            title=titre,
            type='custom',
            size_hint=(.7, .6),
            content_cls= self.popup,
            auto_dismiss=False
        )
        self.popup.height = '400dp'
        self.popup.width = '850dp'

        self.client_name = client
        asyncio.run_coroutine_threadsafe(self.current_client_info(client, date), self.loop)

        self.popup.get_screen('about_contrat').ids.titre.text =f" A propos du contrat de {client}"
        self.popup.get_screen('about_contrat').ids.date_contrat.text =f"Début du contrat : {date}"
        self.popup.get_screen('about_contrat').ids.debut_contrat.text =f"Début du contrat : {debut_contrat}"
        self.popup.get_screen('about_contrat').ids.fin_contrat.text =f"Fin du contrat : {fin_prévu}"
        self.popup.get_screen('about_contrat').ids.type_traitement.text =f"Type de traitement : {type_traitement}"
        self.popup.get_screen('about_contrat').ids.duree.text =f"Durée du contrat : {durée} mois"
        self.dialog = acceuil
        self.dialog.bind(on_dismiss=self.dismiss_popup)

        self.dialog.open()

    def fenetre_client(self, titre, ecran):
        from kivymd.uix.dialog import MDDialog

        # ✅ CORRECTION: Supprimer l'ancien parent du popup si existant
        if self.popup.parent:
            self.popup.parent.remove_widget(self.popup)
        
        self.popup.current = 'vide'
        self.popup.current = ecran
        client = MDDialog(
            md_bg_color='#56B5FB',
            title=titre,
            type='custom',
            size_hint=(.8, .65) if ecran == 'option_client' else (.8, .85),
            content_cls=self.popup,
            auto_dismiss=False
        )
        self.popup.height = '390dp' if ecran == 'option_client' else '550dp'
        self.popup.width = '1000dp'

        self.dialog = client
        self.dialog.bind(on_dismiss=self.dismiss_popup)

        self.dialog.open()

    def fenetre_planning(self, titre, ecran):
        from kivymd.uix.dialog import MDDialog

        self.popup.current = 'vide'
        self.dismiss_popup()
        if self.dialog != None:
            self.fermer_ecran()
        self.popup.current = ecran
        height = {"option_decalage": '200dp',
                  "ecran_decalage": '360dp',
                  "selection_planning": '500dp',
                  "rendu_planning": '450dp',
                  "selection_element_tableau": "300dp",
                  "ajout_remarque": "550dp"}

        size_tableau = {"option_decalage": (.6, .3),
                        "ecran_decalage": (.7, .6),
                        "selection_planning": (.8, .6),
                        "rendu_planning": (.8, .58),
                        "selection_element_tableau": (.6, .4),
                        "ajout_remarque": (.6, .65)}

        width = {"option_decalage": '700dp',
                        "ecran_decalage": '1000dp',
                        "selection_planning": '1000dp',
                        "rendu_planning": '1000dp',
                        "selection_element_tableau": '750dp',
                        "ajout_remarque": '750dp'}

        planning = MDDialog(
            md_bg_color='#56B5FB',
            title=titre,
            type='custom',
            size_hint=size_tableau[ecran],
            content_cls=self.popup,
            auto_dismiss=False
        )

        self.popup.height = height[ecran]
        self.popup.width = width[ecran]

        self.dialog = planning
        self.dialog.bind(on_dismiss=self.dismiss_popup)

        self.dialog.open()

    def fenetre_histo(self, titre, ecran):
        from kivymd.uix.dialog import MDDialog

        self.popup.current = 'vide'
        self.popup.current = ecran

        if self.popup.parent:
            self.popup.parent.remove_widget(self.popup)
            self.fermer_ecran()

        histo = MDDialog(
            md_bg_color='#56B5FB',
            title=titre,
            type='custom',
            size_hint=(.8, .65),
            content_cls=self.popup,
            auto_dismiss=False

        )
        self.popup.height ='500dp'
        self.popup.width = '1000dp'

        self.dialog = histo

        self.dialog.open()

    def fenetre_account(self, titre, ecran):
        from kivymd.uix.dialog import MDDialog

        self.popup.current = None
        self.popup.current = ecran
        compte = MDDialog(
            md_bg_color='#56B5FB',
            title=titre,
            type='custom',
            size_hint=(.5, .35) if ecran != 'modif_info_compte' else (.8, .73),
            content_cls=self.popup,
            auto_dismiss=False
        )
        height = '300dp' if ecran == 'suppression_compte' else '450dp' if ecran == 'modif_info_compte' else'200dp'
        width = '630dp' if ecran == 'suppression_compte' else '1000dp' if ecran == 'modif_info_compte' else '600dp'
        self.popup.height = height
        self.popup.width = width

        self.dialog = compte
        self.dialog.bind(on_dismiss=self.dismiss_popup)

        self.dialog.open()

    def dismiss_popup(self, *args):
        if self.popup.parent:
            self.popup.parent.remove_widget(self.popup)

    def dropdown_menu(self, button, menu_items, color):
        from kivymd.uix.menu import MDDropdownMenu

        self.menu = MDDropdownMenu(
            md_bg_color= color,
            items=menu_items,
            max_height = dp(146)
        )
        self.menu.caller = button
        self.menu.open()

    def menu_callback(self, text_item, name, screen, champ):
        if screen == 'contrat':
            self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen(screen).ids[champ].text = text_item
        elif screen == 'Home':
            self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen(screen).ids[champ].text = text_item
        else:
            self.root.get_screen('signup').ids['type'].text = text_item
        self.menu.dismiss()

    def clear_fields(self, screen):
        sign_up = ['nom','prenom','Email','type','signup_username','signup_password','confirm_password']
        modif_compte = ['nom','prenom','email','username','password','confirm_password']
        login = ['login_username', 'login_password']
        new_contrat = ['num_new_contrat','date_new_contrat', 'debut_new_contrat', 'fin_new_contrat']
        new_client = ['date_contrat_client', 'ajout_client', 'nom_client', 'email_client', 'adresse_client', 'responsable_client', 'telephone' ,'nif', 'stat']
        planning = ['mois_date', 'mois_fin', 'axe_client', 'type_traitement', 'date_prevu']
        facture = ['montant', 'mois_fin', 'axe_client', 'traitement_c', 'date_prevu', 'red_trait']
        signalement = ['motif', 'date_decalage', 'date_prevu']

        if screen == 'new_contrat':
            #pour l'ecran new_contrat
            self.popup.get_screen('new_contrat').ids['duree_new_contrat'].text = 'Déterminée'
            self.popup.get_screen('new_contrat').ids['fin_new_contrat'].pos_hint = {"center_x":.83,"center_y":.7}
            self.popup.get_screen('new_contrat').ids['label_fin'].text = 'Fin du contrat'
            self.popup.get_screen('new_contrat').ids['fin_icon'].pos_hint = {"center_x": .93, "center_y":.8}
            self.popup.get_screen('new_contrat').ids['cat_contrat'].text = 'Nouveau'

            #pour l'ecran ajout_client
            self.popup.get_screen('ajout_info_client').ids['axe_client'].text = 'Nord (N)'

            #pour l'ajout du planning
            self.popup.get_screen('ajout_planning').ids['red_trait'].text = '1 mois'

            for id in new_contrat:
                self.popup.get_screen('new_contrat').ids[id].text = ''
            for id in new_client:
                self.popup.get_screen('ajout_info_client').ids[id].text = ''
            for id in planning:
                self.popup.get_screen('ajout_planning').ids[id].text = ''
            for id in facture:
                self.popup.get_screen('ajout_facture').ids[id].text = ''

            self.popup.get_screen('new_contrat').ids.deratisation.active = False
            self.popup.get_screen('new_contrat').ids.desinfection.active = False
            self.popup.get_screen('new_contrat').ids.desinsectisation.active = False
            self.popup.get_screen('new_contrat').ids.nettoyage.active = False
            self.popup.get_screen('new_contrat').ids.fumigation.active = False
            self.popup.get_screen('new_contrat').ids.ramassage.active = False
            self.popup.get_screen('new_contrat').ids.anti_ter.active = False

        if screen == 'signup':
            for id in sign_up:
                self.root.get_screen('signup').ids[id].text = ''
        if screen == 'signalement':
            for id in signalement:
                self.popup.get_screen('ecran_decalage').ids[id].text = ''
        if screen == 'login':
            for id in login:
                self.root.get_screen('login').ids[id].text = ''
        if screen == 'modif_info_compte':
            for id in modif_compte:
                self.popup.get_screen('modif_info_compte').ids[id].text = ''

    def enregistrer_client(self,nom, prenom, email, telephone, adresse, date_ajout, categorie_client, axe , nif, stat):
        if not nom or not prenom or not email or not telephone or not adresse or not date_ajout or not axe:
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Veuillez remplir tous les champs'), 0)
            return
        if categorie_client == 'Société' and (not nif or not stat):
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Veuillez remplir tous les champs'), 0)
            return
        # ✅ Validation reussie - continuer
        # ✅ Mettre à jour la fenêtre de confirmation avec les infos client et contrat
        self.popup.get_screen('save_info_client').ids.titre.text = f'Enregistrement des informations sur {nom.capitalize()}'
        
        # ✅ Garder aussi les infos client en mémoire pour creer_contrat()
        self.nom_client_temp = nom
        self.prenom_client_temp = prenom
        self.email_client_temp = email
        self.telephone_client_temp = telephone
        self.adresse_client_temp = adresse
        self.date_ajout_temp = date_ajout
        self.categorie_client_temp = categorie_client
        self.axe_temp = axe
        self.nif_temp = nif
        self.stat_temp = stat
        
        self.dismiss_popup()
        self.fermer_ecran()
        self.fenetre_contrat('', 'save_info_client')

    def enregistrer_contrat(self, numero_contrat, date_contrat, date_debut, date_fin, duree_contrat, categorie_contrat):
        dératisation = self.popup.get_screen('new_contrat').ids.deratisation.active
        désinfection = self.popup.get_screen('new_contrat').ids.desinfection.active
        désinsectisation = self.popup.get_screen('new_contrat').ids.desinsectisation.active
        nettoyage = self.popup.get_screen('new_contrat').ids.nettoyage.active
        fumigation = self.popup.get_screen('new_contrat').ids.fumigation.active
        ramassage = self.popup.get_screen('new_contrat').ids.ramassage.active
        anti_termite = self.popup.get_screen('new_contrat').ids.anti_ter.active

        if not dératisation and not désinfection and not désinsectisation and not nettoyage and not fumigation and not ramassage and not anti_termite:
            Clock.schedule_once(lambda dt: self.show_dialog("Erreur", "Veuillez choisir au moins un traitement"), 0)
            return

        if not numero_contrat or not date_contrat or not date_debut or not duree_contrat or not categorie_contrat:
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Veuillez remplir tous les champs'), 0)
            return
        if duree_contrat == 'Déterminée' and not date_fin:
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Veuillez remplir tous les champs'), 0)
            return
        else:
            self.dismiss_popup()
            self.fermer_ecran()
            self.popup.get_screen('ajout_info_client').ids.ajout_client.text = date_contrat
            self.popup.get_screen('ajout_info_client').ids.date_contrat_client.text = date_contrat

            self.popup.get_screen('save_info_client').ids.date_contrat.text = f'Date du contrat : {date_contrat}'
            self.popup.get_screen('save_info_client').ids.debut_contrat.text = f'Début du contrat : {date_debut}'
            self.popup.get_screen('save_info_client').ids.fin_contrat.text = 'Fin du contrat : Indéterminée'  if date_fin == '' else f'Fin du contrat : {date_fin}'

            self.fenetre_contrat('Ajout des informations sur le clients', 'ajout_info_client')

    def retour_ajout_info_client(self):
        """Retourner à la fenêtre ajout_info_client depuis save_info_client (confirmation)"""
        # ✅ Fermer le dialog actuel avant d'en ouvrir un nouveau
        if hasattr(self, 'dialog') and self.dialog:
            self.dialog.dismiss()
        
        # ✅ Rouvrir ajout_info_client
        self.fenetre_contrat('Ajout des informations sur le clients', 'ajout_info_client')

    async def all_clients(self):
        place = self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen('client').ids.tableau_client
        try:
            client_data = await self.database.get_all_client()
            if client_data:
                Clock.schedule_once(lambda dt: self.update_client_table_and_switch(place, client_data), 0.1)
            else:
                Clock.schedule_once(lambda dt: self.show_dialog('Information', 'Aucun client trouvé.'), 0)

        except Exception as e:
            print(f"Erreur lors de la récupération des clients: {e}")
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Une erreur est survenue lors du chargement des clients.'), 0)

    def signaler(self):
        # ✅ CORRECTION: Valider les champs obligatoires
        motif = self.popup.get_screen('ecran_decalage').ids.motif.text
        date_decalage = self.popup.get_screen('ecran_decalage').ids.date_decalage.text
        decaler = self.popup.get_screen('ecran_decalage').ids.changer
        garder = self.popup.get_screen('ecran_decalage').ids.garder
        
        # ✅ CORRECTION: Vérifier que motif n'est pas vide
        if not motif:
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Veuillez entrer un motif'), 0)
            return
        
        # ✅ CORRECTION: Vérifier que date_decalage n'est pas vide
        if not date_decalage:
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Veuillez sélectionner une date'), 0)
            return
        
        # ✅ CORRECTION: Afficher spinner pendant enregistrement
        Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'ecran_decalage', show=True), 0)

        self.fermer_ecran()
        self.dismiss_popup()
        
        async def enregistrer_signalment():
            from dateutil.relativedelta import relativedelta

            try:
                # ✅ CORRECTION: Logique correcte des deux options
                # Option 1: CHANGER redondance = calculer intervalle et modifier TOUTES les dates futures
                # Option 2: GARDER redondance = modifier JUSTE la date sélectionnée
                
                if decaler.active:  # Changer la redondance
                    try:
                        date = datetime.strptime(self.reverse_date(date_decalage), '%Y-%m-%d')
                        newdate = abs(relativedelta(self.planning_detail[9], date))
                        print(f"📅 CHANGER redondance - intervalle: {newdate.months} mois pour TOUTES les dates futures")
                        await self.database.modifier_date_signalement(self.planning_detail[7], self.planning_detail[8], self.option.lower(), newdate.months)
                    except ValueError as e:
                        print(f'❌ Erreur parsing date: {e}')
                        raise
                elif garder.active:  # Garder la redondance
                    print(f"🔄 GARDER redondance - modifier JUSTE cette date")
                    await self.database.modifier_date(self.planning_detail[8], self.reverse_date(date_decalage))

                # Enregistrer le signalement
                await self.database.creer_signalment(self.planning_detail[8], motif, self.option.capitalize())
                
                # ✅ CORRECTION: Recharger planning_detail pour voir les changements
                self.planning_detail = await self.database.get_info_planning(self.planning_detail[7], self.reverse_date(self.planning_detail[9]))
                
                # ✅ CORRECTION: Refraîchir les tableaux AVANT de masquer le spinner
                # Attendre que les modifications soient écrites en BD
                await asyncio.sleep(0.5)
                await self.populate_tables()
                
                # ✅ CORRECTION: Masquer spinner et afficher succès
                Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'ecran_decalage', show=False), 0)
                Clock.schedule_once(lambda dt: self.show_dialog('Succès', f"Signalement d'un {self.option.lower()} effectué"), 0)
                Clock.schedule_once(lambda dt: self.clear_fields('signalement'), 0.5)
                Clock.schedule_once(lambda dt: self.remove_tables('planning'), 0.6)

            except Exception as e:
                print(f'❌ Erreur enregistrement signalement: {e}')
                import traceback
                traceback.print_exc()
                # ✅ CORRECTION: Masquer spinner et afficher erreur
                Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'ecran_decalage', show=False), 0)
                Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Enregistrement échoué: {str(e)}'), 0)

        asyncio.run_coroutine_threadsafe(enregistrer_signalment(), self.loop)

    def option_decalage(self, titre):
        self.popup.get_screen('ecran_decalage').ids.titre.text= f'Signalement d\'un {titre} pour {self.planning_detail[0]}'
        label = "l'avancement" if titre == 'avancement' else 'le décalage'
        self.popup.get_screen('ecran_decalage').ids.date_prevu.text = self.reverse_date(self.planning_detail[9])
        self.popup.get_screen('ecran_decalage').ids.label_decalage.text = f'Date pour {label}'
        self.option = titre
        self.fenetre_planning('', 'ecran_decalage')

    def switch_to_home(self):
        self.root.get_screen('Sidebar').ids['gestion_ecran'].current =  'Home'

    def switch_to_login(self):
        self.root.current = 'login'

    def switch_to_compte(self):
        ecran = 'compte' if self.admin else 'not_admin'
        self.root.get_screen('Sidebar').ids['gestion_ecran'].current =  ecran
        if self.admin:
            place = self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen('compte').ids.tableau_compte
            self.all_users(place)

        self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen(ecran).ids.nom.text = f'Nom : {self.compte[1]}'
        self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen(ecran).ids.prenom.text = f'Prénom : {self.compte[2]}'
        self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen(ecran).ids.email.text = f'Email : {self.compte[3]}'
        self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen(ecran).ids.username.text = f"Nom d'utilisateur : {self.compte[4]}"

    def switch_to_historique(self):
        self.root.get_screen('Sidebar').ids['gestion_ecran'].current ='choix_type'

    def switch_to_planning(self):
        root = self.root.get_screen('Sidebar').ids['gestion_ecran']
        place = root.get_screen('planning').ids.tableau_planning
        root.current = 'planning'

        Clock.schedule_once(lambda dt: self.loading_spinner('Sidebar', 'planning'), 0)

        future = asyncio.run_coroutine_threadsafe(self.get_all_planning(), self.loop)

        def handle_result(future):
            try:
                result = future.result()
                Clock.schedule_once(lambda dt: self.tableau_planning(place, result), 0.5)
            except Exception as e:
                print("Erreur de chargement planning :", e)

        threading.Thread(target=lambda: handle_result(future)).start()

    def switch_to_about(self):
        self.root.get_screen('Sidebar').ids['gestion_ecran'].current =  'about'

    def switch_to_main(self):
        # ✅ LAZY LOADING: Initialiser les tables à la demande
        if not self._tables_initialized:
            self._initialize_tables()
        
        # Initialiser les écrans une seule fois après authentification
        if not self._screens_initialized:
            gestion_ecran(self.root)
            self._screens_initialized = True
            asyncio.run_coroutine_threadsafe(self.populate_tables(), self.loop)
        
        # ✅ ÉTAPE 2 - Optimisation: Charger les écrans popup additionnels après login
        if not self._popup_full_loaded:
            self._load_additional_popup_screens()
        
        # ✅ ÉTAPE 3 - Optimisation: Charger main.kv et Sidebar.kv asynchronement après login
        if not self._main_screens_loaded:
            self._load_main_screens_async()
        
        self.root.current = 'Sidebar'
        self.root.get_screen('Sidebar').ids['gestion_ecran'].current =  'Home'
        self.reset()

    def _load_additional_popup_screens(self):
        """Charger les écrans popup additionnels après le login"""
        from gestion_ecran import popup
        popup(self.popup, init_only=False)  # Charge TOUS les écrans
        self._popup_full_loaded = True
        print("✅ Écrans popup additionnels chargés après login")

    def _load_main_screens_async(self):
        """Charger main.kv et Sidebar.kv de manière asynchrone après le login"""
        if self._main_screens_loaded:
            return  # Évite les doublons
        
        try:
            from kivy.lang import Builder
            
            # Charger les screens asynchronously
            main_screen = Builder.load_file('screen/main.kv')
            sidebar_screen = Builder.load_file('screen/Sidebar.kv')
            
            # Les ajouter au ScreenManager
            self.root.add_widget(main_screen)
            self.root.add_widget(sidebar_screen)
            
            self._main_screens_loaded = True
            print("✅ Screens main.kv et Sidebar.kv chargés asynchronement")
        except Exception as e:
            print(f"❌ Erreur lors du chargement asynchrone: {e}")

    def switch_to_contrat(self):
        self.root.get_screen('Sidebar').ids['gestion_ecran'].current = 'contrat'
        boutton = self.root.get_screen('Sidebar').ids.contrat
        self.choose_screen(boutton)
        if self.liste_contrat.parent:
            self.liste_contrat.parent.remove_widget(self.liste_contrat)

        def chargement_contrat():
            asyncio.run_coroutine_threadsafe(self.get_client(), self.loop)

        Clock.schedule_once(lambda dt: self.loading_spinner('Sidebar','contrat'), 0)
        Clock.schedule_once(lambda dt: chargement_contrat(), 0.5)

    def switch_to_client(self):
        self.root.get_screen('Sidebar').ids['gestion_ecran'].current = 'client'
        boutton = self.root.get_screen('Sidebar').ids.clients
        self.choose_screen(boutton)
        place = self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen('client').ids.tableau_client
        #place.clear_widgets()

        def chargement_client():
            asyncio.run_coroutine_threadsafe(self.all_clients(), self.loop)

        Clock.schedule_once(lambda dt: self.loading_spinner('Sidebar','client'), 0)
        Clock.schedule_once(lambda dt: chargement_client(), 0.5)

    def afficher_historique(self, type_trait):
        from kivy.uix.screenmanager import SlideTransition

        self.root.get_screen('Sidebar').ids['gestion_ecran'].transition = SlideTransition(direction='left')
        self.root.get_screen('Sidebar').ids['gestion_ecran'].current ='historique'
        self.root.get_screen('Sidebar').ids['gestion_ecran'].transition = SlideTransition(direction='up')
        if type_trait == 'AT':
            categorie = 'AT: Anti termites'
        if type_trait == 'PC':
            categorie = 'PC'
        if type_trait == 'NI':
            categorie = 'NI: Nettoyage Industriel'
        if type_trait == 'RO':
            categorie = 'RO: Ramassage Ordures'

        self.historique_par_categorie(categorie)

    def loading_spinner(self, manager, ecran, show=True):
        """Affiche/masque le spinner de chargement - ROBUSTE aux screens manquants"""
        gestion = None
        if manager == 'Sidebar':
            gestion = self.root.get_screen('Sidebar').ids['gestion_ecran']
        else:
            gestion = self.popup

        try:
            gestion.get_screen(ecran).ids.spinner.active = show
            gestion.get_screen(ecran).ids.spinner.opacity = 1 if show else 0
        except Exception as e:
            # Capture KeyError, AttributeError, ET ScreenManagerException
            # Le spinner n'existe pas ou l'écran n'existe pas, ignorer silencieusement
            print(f"⚠️ Spinner '{ecran}' non trouvé: {e}")
            pass

    def traitement_par_client(self, source):
        if not self.current_client:
            self.show_dialog('Erreur', 'Aucun client sélectionné ou contrat trouvé')
            return
        
        self.fermer_ecran()
        self.popup.get_screen('all_treatment').ids.titre.text = f'Tous les traitements de {self.current_client[1]}'
        place = self.popup.get_screen('all_treatment').ids.tableau_treat
        place.clear_widgets()

        self.dismiss_popup()

        Clock.schedule_once(lambda dt: self.switch_to_contrat(),0)
        Clock.schedule_once(lambda dt: self.fenetre_contrat('', 'all_treatment'), 0.5)

        def maj_ecran():
            asyncio.run_coroutine_threadsafe(self.liste_traitement_par_client(place, self.current_client[0]), self.loop)

        Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'all_treatment'), 0)
        Clock.schedule_once(lambda dt: maj_ecran(), 0.8)

    def voir_planning_par_traitement(self):
        if not self.current_client:
            self.show_dialog('Erreur', 'Aucun client sélectionné ou contrat trouvé')
            return
        
        self.dismiss_popup()
        self.fermer_ecran()
        btn_planning = self.root.get_screen('Sidebar').ids.planning
        self.choose_screen(btn_planning)
        self.fenetre_planning('', 'selection_planning')
        Clock.schedule_once(lambda dt: self.switch_to_planning(), 0)
        Clock.schedule_once(lambda dt: self.get_and_update(self.current_client[5], self.current_client[1],self.current_client[13]), 0)

    def voir_info_client(self,source, option):
        if not self.current_client:
            self.show_dialog('Erreur', 'Aucun client sélectionné ou contrat trouvé')
            return
        
        self.fermer_ecran()
        self.dismiss_popup()

        Clock.schedule_once(lambda dt: self.modification_client(self.current_client[1], option), 0.5)
        Clock.schedule_once(lambda dt: self.switch_to_client(),0)

    def dropdown_compte(self, button, name):
        type_compte = ['Administrateur', 'Utilisateur']
        compte = [
            {
                "text": i,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=f"{i}": self.menu_callback(x, name,'signup', 'type'),
            } for i in type_compte
        ]
        self.dropdown_menu(button, compte, 'white')

    def dropdown_homepage(self, button, name):
        type_tri = ['Contrats', 'Clients', 'Planning']
        home = [
            {
                "text": i,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=f"{i}": self.menu_callback(x, name,'Home', 'type_contrat'),
                "md_bg_color": (0.647, 0.847, 0.992, 1)
            } for i in type_tri
        ]
        self.dropdown_menu(button, home,  (0.647, 0.847, 0.992, 1))

    def dropdown_contrat(self, button, name):
        type_tri = ['Récents', 'Mois', 'Type de contrat']
        type_trait = ['Dératisation', 'Désinsectisation', 'Désinfection', 'Nettoyage industriel',"Ramassages d'ordures", 'Fumigation']
        menu = type_tri if name=='home' else type_trait
        screen = 'tri' if name == 'home' else 'tri_trait'
        home = [
            {
                "text": i,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=f"{i}": self.menu_callback(x, name,'contrat', screen),
            } for i in menu
        ]
        self.dropdown_menu(button, home, (0.647, 0.847, 0.992, 1))

    def dropdown_histo(self, button, name):
        tri = ['Récents', 'Mois', 'Type de contrat']
        tri_trait = ['Dératisation', 'Désinsectisation', 'Désinfection', 'Nettoyage industriel',"Ramassages d'ordures", 'Fumigation']
        menu = tri if name=='tri' else tri_trait
        home = [
            {
                "text": i,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=f"{i}": self.retour_histo(name,x),
            } for i in menu
        ]
        self.dropdown_menu(button, home, (0.647, 0.847, 0.992, 1))

    def retour_histo(self, champ, text):
        self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen('historique').ids[champ].text = text
        self.menu.dismiss()

    def dropdown_new_contrat(self,button,  champ, screen):
        axe = ['Nord (N)','Centre (C)', 'Sud (S)', 'Est (E)', 'Ouest (O)']
        durée = ['Déterminée', 'Indéterminée']
        categorie = ['Nouveau ', 'Renouvellement']
        type_client = ['Société', 'Organisation', 'Particulier']
        fréquence = ['une seule fois', '1 mois', '2 mois', '3 mois', '4 mois', '6 mois']

        item_menu = axe if champ == 'axe_client' else durée if champ == 'duree_new_contrat' else categorie if champ == "cat_contrat" else fréquence if champ == 'red_trait' else type_client
        menu = [
            {
                "text": i,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=f"{i}": self.retour_new(x, champ, screen),
            } for i in item_menu
        ]
        self.dropdown_menu(button, menu, 'white')

    def render_excel(self):
        self.fenetre_planning('', 'rendu_planning')
        asyncio.run_coroutine_threadsafe(self.get_all_client(), self.loop)

    async def get_all_client(self):
        self.all_client = []

        try:
            client_data = await self.database.get_all_client_name()

            if client_data:
                for row in client_data:
                    if isinstance(row, tuple) and len(row) > 0:
                        self.all_client.append(row[0])
                    else:
                        self.all_client.append(row)

        except Exception as e:
            print(f"Une erreur est survenue lors de la récupération des clients: {e}")

    def dropdown_rendu_excel(self,button,  champ):
        mois = ['Tous', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', "Décembre"]
        client = ['Tous']
        for i in self.all_client:
            client.append(i)
        categorie = ['Facture', 'Traitement']

        item_menu = mois if champ == 'mois_planning' else categorie if champ == 'categ_planning' else client
        menu = [
            {
                "text": i,
                "viewclass": "OneLineListItem",
                "on_release": lambda x=f"{i}": self.retour_planning(x, champ),
            } for i in item_menu
        ]
        self.dropdown_menu(button, menu, 'white')

    def retour_new(self,text,  champ, screen):
        categ_client = ['Organisation', 'Société', 'Particulier']
        if text == 'Indéterminée':
            self.popup.get_screen(screen).ids.fin_new_contrat.pos_hint = {"center_x": 0, "center_y": -10}
            self.popup.get_screen(screen).ids.label_fin.text = ''
            self.popup.get_screen(screen).ids.fin_icon.pos_hint = {"center_x": 0, "center_y": -10}

            #Ecran ajout planning
            self.popup.get_screen('ajout_planning').ids.mois_fin.pos_hint = {"center_x": 0, "center_y": -10}
            self.popup.get_screen('ajout_planning').ids.mois_fin.text = 'Indéterminée'
            self.popup.get_screen('ajout_planning').ids.label_fin_planning.text = ''

            #Ecran ajout facture
            self.popup.get_screen('ajout_facture').ids.mois_fin.pos_hint = {"center_x": 0, "center_y": -10}
            self.popup.get_screen('ajout_facture').ids.mois_fin.text = 'Indéterminée'
            self.popup.get_screen('ajout_facture').ids.label_fin_facture.text = ''

        elif text == 'Déterminée':
            self.popup.get_screen(screen).ids.fin_new_contrat.pos_hint = {"center_x": .83, "center_y": .7}
            self.popup.get_screen(screen).ids.fin_icon.pos_hint = {"center_x": .93, "center_y": .7}
            self.popup.get_screen(screen).ids.label_fin.text = 'Fin du contrat'

            #Ecran ajout planning
            self.popup.get_screen('ajout_facture').ids.mois_fin.text = ''
            self.popup.get_screen('ajout_planning').ids.mois_fin.pos_hint = {"center_x": .5, "center_y": .8}
            self.popup.get_screen('ajout_planning').ids.label_fin_planning.text = 'Mois de fin du traitement :'

            #Ecran ajout facture
            self.popup.get_screen('ajout_facture').ids.mois_fin.text = ''
            self.popup.get_screen('ajout_facture').ids.mois_fin.pos_hint = {"center_x": .5, "center_y": .8}
            self.popup.get_screen('ajout_facture').ids.label_fin_facture.text = 'Mois de fin du traitement :'

        elif text in categ_client:
            if text == 'Particulier':
                self.popup.get_screen(screen).ids.label_resp.text = 'Prénom'
            else:
                self.popup.get_screen(screen).ids.label_resp.text = 'Responsable'
            if text != 'Société':
                self.popup.get_screen(screen).ids.nif_label.text = ''
                self.popup.get_screen(screen).ids.stat_label.text = ''
                self.popup.get_screen(screen).ids.nif.pos_hint = {"center_x": 0, "center_y": -10}
                self.popup.get_screen(screen).ids.stat.pos_hint = {"center_x": 0, "center_y": -10}
            else:
                self.popup.get_screen(screen).ids.nif_label.text = 'Nif'
                self.popup.get_screen(screen).ids.stat_label.text = 'Stat'
                self.popup.get_screen(screen).ids.nif.pos_hint = {"center_x": .225, "center_y": .14}
                self.popup.get_screen(screen).ids.stat.pos_hint = {"center_x": .73, "center_y": .14}

        self.popup.get_screen(screen).ids[f'{champ}'].text = text
        self.menu.dismiss()

    def retour_planning(self,text,  champ):
        self.popup.get_screen('rendu_planning').ids[f'{champ}'].text = text
        if text == 'Traitement':
            self.popup.get_screen('rendu_planning').ids.label_trait.pos_hint = {"center_x": .55,'center_y':.55}
            self.popup.get_screen('rendu_planning').ids.type_traitement_planning.pos_hint = {"center_x":.17,"center_y":.43}
        if text == 'Facture':
            self.popup.get_screen('rendu_planning').ids.label_trait.pos_hint = {"center_x": -1,'center_y':-1}
            self.popup.get_screen('rendu_planning').ids.type_traitement_planning.pos_hint = {"center_x":-1,"center_y":-1}
            self.popup.get_screen('rendu_planning').ids.type_traitement_planning.text = 'Tous'

        self.menu.dismiss()

    def choose_screen(self, instance):
        if instance in self.root.get_screen('Sidebar').ids.values():
            current_id = list(self.root.get_screen('Sidebar').ids.keys())[list(self.root.get_screen('Sidebar').ids.values()).index(instance)]
            self.root.get_screen('Sidebar').ids[current_id].text_color = 'white'
            for ids, item in self.root.get_screen('Sidebar').ids.items():
                if ids != current_id:
                    self.root.get_screen('Sidebar').ids[ids].text_color = 'black'

    def reset(self):
        for ids, item in self.root.get_screen('Sidebar').ids.items():
            if ids == 'home':
                self.root.get_screen('Sidebar').ids[ids].text_color = 'white'
            else:
                self.root.get_screen('Sidebar').ids[ids].text_color = 'black'

    def remove_tables(self, screen):
        if screen == 'compte':
            place = self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen('compte').ids.tableau_compte
            place.remove_widget(self.account)

            self.all_users(place)

        elif screen == 'contrat':
            place1 = self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen('contrat').ids.tableau_contrat
            place1.remove_widget(self.liste_contrat)
            asyncio.run_coroutine_threadsafe(self.get_client(), self.loop)
            place2 = self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen(
                 'client').ids.tableau_client
            place2.remove_widget(self.liste_client)
            asyncio.run_coroutine_threadsafe(self.all_clients(), self.loop)

    @mainthread
    def update_contract_table(self, place, contract_data):
        from kivymd.uix.label import MDLabel

        if not contract_data:
            label = MDLabel(
                text="Aucune donnée de planning disponible",
                halign="center"
            )
            place.add_widget(label)
            return

        row_data = []
        client_id = []
        for item in contract_data:
            try:
                if len(item) >= 4:
                    client = item[0] if item[0] is not None else "N/A"
                    date = self.reverse_date(item[1]) if item[1] is not None else "N/A"
                    traitement = item[7] if item[7] is not None else "N/A"
                    # ✅ Format redondance: 0='1 jour', 1='1 mois', 2='2 mois', etc.
                    fréquence = ', '.join('1 jour' if int(val) == 0 else f'{val} mois' for val in item[3].split(',')) if item[3] is not None else '0 mois'

                    client_id.append(item[8])

                    row_data.append((client, date, traitement, fréquence ))
                else:
                    print(f"Warning: Planning item doesn't have enough elements: {item}")

            except Exception as e:
                print(f"Error processing planning item: {e}")

        try:

            # ✅ Initialiser le paginateur
            self.paginator_contract.set_total_rows(len(row_data))
            self.paginator_contract.reset()

            pagination = self.liste_contrat.pagination

            btn_prev = pagination.ids.button_back
            btn_next = pagination.ids.button_forward

            def on_press_page(direction, instance=None):
                print(f"📄 Contrat: {direction} | {self.paginator_contract.debug_info()}")
                if direction == 'moins':
                    self.paginator_contract.prev_page()
                elif direction == 'plus':
                    self.paginator_contract.next_page()

            btn_prev.bind(on_press=partial(on_press_page, 'moins'))
            btn_next.bind(on_press=partial(on_press_page, 'plus'))

            self.liste_contrat.row_data = row_data
            self.liste_contrat.bind(on_row_press=partial(self.get_traitement_par_client, client_id))
            
            # ✅ Afficher avec délai
            self._display_table_with_delay(place, self.liste_contrat, delay=0.3)

        except Exception as e:
            print(f"Error creating contract table: {e}")

    def get_traitement_par_client(self, client_id, table, row):
        # ✅ Utiliser le paginateur
        row_num = PaginationHelper.calculate_row_num(row.index, len(table.column_data))
        row_data = table.row_data[row_num]
        index_global = self.paginator_contract.get_global_index(row_num)

        if self.popup.parent:
            self.popup.parent.remove_widget(self.popup)
            self.fermer_ecran()

        place = self.popup.get_screen('all_treatment').ids.tableau_treat
        place.clear_widgets()
        row_value = None

        if 0 <= index_global < len(table.row_data):
            row_value = table.row_data[index_global]
            print(row_value)

        self.fenetre_contrat('', 'all_treatment')

        self.popup.get_screen('all_treatment').ids.titre.text = f'Tous les traitements de {row_value[0]}'
        self.client_name = row_value[0]

        def maj_ecran():
            # ✅ CORRECTION: Passer row_value[0] (nom_client) au lieu de client_id[row_num]
            asyncio.run_coroutine_threadsafe(self.liste_traitement_par_client(place, row_value[0]), self.loop)

        # ✅ CORRECTION: Loading spinner AVANT le chargement (délai 0), puis chargement après (délai 0.5s)
        Clock.schedule_once(lambda dt: self.loading_spinner(self.popup,'all_treatment'), 0)
        Clock.schedule_once(lambda dt: maj_ecran(), 0.5)

    async def liste_traitement_par_client(self, place, nom_client):
        try:
            # ⏱️ Petite attente pour laisser le loading spinner s'afficher
            await asyncio.sleep(0.3)
            result = await self.database.traitement_par_client(nom_client)
            if result:
                Clock.schedule_once(lambda dt : self.show_about_treatment(place, result), 0.1)
            else:
                # ✅ Si pas de résultat, arrêter le loading et afficher message
                Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'all_treatment'), 0)
                from kivymd.uix.label import MDLabel
                label = MDLabel(
                    text="Aucun traitement trouvé pour ce client",
                    halign="center"
                )
                Clock.schedule_once(lambda dt: place.add_widget(label) if place.parent else None, 0.1)

        except Exception as e:
            print('erreur get traitement'+ str(e))
            Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'all_treatment'), 0)

    def show_about_treatment(self, place, data):
        from kivymd.uix.label import MDLabel

        if self.all_treat.parent:
            self.all_treat.parent.remove_widget(self.all_treat)

        if not data:
            label = MDLabel(
                text="Aucune donnée de planning disponible",
                halign="center"
            )
            place.add_widget(label)
            return

        row_data = []
        for item in data:
            try:
                if len(item) >= 8:  # Vérifier qu'on a assez d'éléments
                    nom_client = item[0] if item[0] is not None else "N/A"
                    date = self.reverse_date(item[1]) if item[1] is not None else "N/A"
                    traitement = item[2] if item[2] is not None else "N/A"
                    redondance = item[7] if item[7] is not None else "N/A"

                    # ✅ Format redondance: 0='1 jour', 1='1 mois', 2='2 mois', etc.
                    if redondance == 0:
                        display_freq = '1 jour'
                    else:
                        display_freq = f'{redondance} mois'
                    
                    print(f"📋 Traitement {nom_client}: {date} - {traitement} ({display_freq})")
                    row_data.append((date, traitement, display_freq))
                else:
                    print(f"⚠️ Item insuffisant: {item}")
            except Exception as e:
                print(f"❌ Erreur traitement: {e}")

            try:
                # ✅ Initialiser le paginateur pour les traitements
                self.paginator_treat.set_total_rows(len(row_data))
                self.paginator_treat.reset()

                self.all_treat.row_data = row_data

                pagination = self.all_treat.pagination

                btn_prev = pagination.ids.button_back
                btn_next = pagination.ids.button_forward

                def on_press_page(direction, instance=None):
                    print(f"📄 Traitement: {direction} | {self.paginator_treat.debug_info()}")
                    if direction == 'moins':
                        self.paginator_treat.prev_page()
                    elif direction == 'plus':
                        self.paginator_treat.next_page()

                btn_prev.bind(on_press=partial(on_press_page, 'moins'))
                btn_next.bind(on_press=partial(on_press_page, 'plus'))

                self.all_treat.bind(on_row_press=self.row_pressed_contrat)

                # ✅ Afficher avec délai
                def set_and_display():
                    self.all_treat.row_data = row_data
                    self._display_table_with_delay(place, self.all_treat, delay=0.3)
                
                Clock.schedule_once(lambda dt: set_and_display(), 0)

            except Exception as e:
                print(f'Error creating traitement table: {e}')

    def row_pressed_contrat(self, table, row):
        # ✅ Utiliser le paginateur pour les traitements
        row_num = PaginationHelper.calculate_row_num(row.index, len(table.column_data))
        index_global = self.paginator_treat.get_global_index(row_num)
        row_value = None

        if self.paginator_treat.is_valid_global_index(index_global):
            row_value = table.row_data[index_global]

        print(f"🔹 row_pressed_contrat: {row_value} | {self.paginator_treat.debug_info()}")
        async def maj_ecran():
            try:
                self.current_client = await self.database.get_current_contrat(self.client_name,self.reverse_date(row_value[0]), row_value[1])
                if type(self.current_client) is None:
                    toast('Veuillez réessayer dans quelques secondes')
                    return
                else:
                    if self.current_client[3] == 'Particulier':
                        nom = self.current_client[1] + ' ' + self.current_client[2]
                    else:
                        nom = self.current_client[1]

                    if self.current_client[6] == 'Indeterminée':
                        fin = self.current_client[8]
                    else :
                        fin = self.reverse_date(self.current_client[8])

                    self.popup.get_screen('option_contrat').ids.titre.text = f'A propos de {nom}'
                    self.popup.get_screen(
                        'option_contrat').ids.date_contrat.text = f'Contrat du : {self.reverse_date(self.current_client[4])}'
                    self.popup.get_screen(
                        'option_contrat').ids.debut_contrat.text = f'Début du contrat : {self.reverse_date(self.current_client[7])}'
                    self.popup.get_screen(
                        'option_contrat').ids.fin_contrat.text = f'Fin du contrat : {fin}'
                    self.popup.get_screen(
                        'option_contrat').ids.type_traitement.text = f'Type de traitement : {self.current_client[5]}'
                    self.popup.get_screen(
                        'option_contrat').ids.duree.text = f'Durée du contrat : {self.current_client[6]}'
                    self.popup.get_screen(
                        'option_contrat').ids.axe.text = f'Axe du client: {self.current_client[11]}'

            except Exception as e:
                print(e)

        def ecran():
            asyncio.run_coroutine_threadsafe(maj_ecran(),self.loop)

        Clock.schedule_once(lambda x: ecran(), 0.5)

    @mainthread
    def update_client_table_and_switch(self, place, client_data):

        if self.liste_client.parent:
            self.liste_client.parent.remove_widget(self.liste_client)

        if client_data:
            # ✅ Créer un tuple pour affichage (4 colonnes) ET un mapping client_id
            row_data = [(i[1], i[2], i[3], self.reverse_date(i[4])) for i in client_data]
            # ✅ Stocker les IDs pour les récupérer dans row_pressed_client
            self.client_id_map = {idx: i[0] for idx, i in enumerate(client_data)}
            
            # ✅ Initialiser le paginateur avec le nombre total d'éléments
            self.paginator_client.set_total_rows(len(row_data))
            self.paginator_client.reset()

            pagination = self.liste_client.pagination

            btn_prev = pagination.ids.button_back
            btn_next = pagination.ids.button_forward

            def on_press_page(direction, instance=None):
                print(f"📄 Pagination client: {direction} | {self.paginator_client.debug_info()}")
                if direction == 'moins':
                    self.paginator_client.prev_page()
                elif direction == 'plus':
                    self.paginator_client.next_page()
                print(self.paginator_client.debug_info())

            btn_prev.bind(on_press=partial(on_press_page, 'moins'))
            btn_next.bind(on_press=partial(on_press_page, 'plus'))

            self.liste_client.row_data = row_data
            self.liste_client.bind(on_row_press=self.row_pressed_client)
            
            # ✅ Afficher avec délai pour que le contenu se charge bien
            self._display_table_with_delay(place, self.liste_client, delay=0.3)

    def historique_par_client(self, source):
        self.fermer_ecran()
        self.dismiss_popup()

        self.root.get_screen('Sidebar').ids['gestion_ecran'].current = 'historique'

        boutton = self.root.get_screen('Sidebar').ids.historique
        self.choose_screen(boutton)
        place = self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen('historique').ids.tableau_historic
        place.clear_widgets()

        async def get_histo():
            try:
                print(self.current_client)
                result = await self.database.get_historic_par_client(self.current_client[1])
                data = []
                id_planning = []

                if result:
                    for i in result:
                        data.append(i)
                        id_planning.append(i[4])
                else:
                    data.append(('Aucun', 'Aucun', 'Aucun', 'Aucun'))

                Clock.schedule_once(lambda dt: self.tableau_historic(place, data, id_planning), 0)

            except Exception as e:
                print('par client',e)

        def maj_ecran():
            asyncio.run_coroutine_threadsafe(get_histo(), self.loop)

        Clock.schedule_once(lambda dt: self.loading_spinner('Sidebar', 'historique'), 0)
        Clock.schedule_once(lambda dt: maj_ecran(), 0.5)

    async def current_client_info(self, nom_client, date):
        try:
            self.current_client = await self.database.get_current_client(nom_client,
                                                                        self.reverse_date(date))
        except Exception as e:
            print(e)

    def row_pressed_client(self, table, row):
        # ✅ Utiliser le paginateur pour calculer l'index global
        row_num = PaginationHelper.calculate_row_num(row.index, len(table.column_data))
        index_global = self.paginator_client.get_global_index(row_num)
        row_value = None
        client_id = None

        if self.paginator_client.is_valid_global_index(index_global):
            row_value = table.row_data[index_global]
            # ✅ Récupérer client_id du mapping
            client_id = self.client_id_map.get(index_global)
        
        print(f"🔹 row_pressed_client - client sélectionné: {row_value}, ID: {client_id} | {self.paginator_client.debug_info()}")
        
        if not client_id:
            print("❌ Erreur: client_id introuvable")
            self.show_dialog('Erreur', 'Impossible de récupérer l\'ID du client')
            return
        
        # ✅ Récupérer la date du contrat du client d'abord
        async def current_client_info_async(cid):
            try:
                # Étape 1: Récupérer la date du contrat actif/récent par CLIENT_ID
                print(f"🔍 Cherche contrat pour client_id: {cid}")
                contrat_date = await self.database.get_latest_contract_date_for_client(cid)
                print(f"📅 Date contrat trouvée: {contrat_date}")
                if not contrat_date:
                    print(f"⚠️ Aucun contrat trouvé pour client_id {cid}")
                    return
                # Étape 2: Récupérer les infos complètes du client avec cette date
                print(f"📥 Charger infos client pour client_id: {cid}, date: {contrat_date}")
                self.current_client = await self.database.get_current_client(cid, contrat_date)
                print(f"✅ current_client chargé: {self.current_client is not None}")
                if self.current_client:
                    print(f"   Nom: {self.current_client[1]} {self.current_client[2]}")
            except Exception as e:
                print(f"❌ Erreur row_pressed_client: {e}")
                import traceback
                traceback.print_exc()

        asyncio.run_coroutine_threadsafe(current_client_info_async(client_id), self.loop)

        def maj_ecran():
            print(f"🎨 maj_ecran - current_client: {self.current_client is not None}")
            if not self.current_client:
                print("⚠️ current_client est None! Aucun contrat trouvé pour ce client")
                Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Aucun contrat trouvé pour ce client'), 0)
                Clock.schedule_once(lambda dt: self.dismiss_popup(), 0.5)
                return
            else:
                print(f"✨ Affichage des infos client")
                if self.current_client[3] == 'Particulier':
                    nom = self.current_client[1] + ' ' + self.current_client[2]
                else:
                    nom = self.current_client[1]

                if self.current_client[6] == 'Indéterminée':
                    fin = self.reverse_date(self.current_client[8])
                else :
                    fin = self.current_client[8]

                self.popup.get_screen('option_client').ids.titre.text = f'A propos de {nom}'
                self.popup.get_screen('option_client').ids.date_contrat.text = f'Contrat du : {self.reverse_date(self.current_client[4])}'
                self.popup.get_screen('option_client').ids.debut_contrat.text = f'Début du contrat : {self.reverse_date(self.current_client[7])}'
                self.popup.get_screen('option_client').ids.fin_contrat.text = f'Fin du contrat : {fin}'
                self.popup.get_screen('option_client').ids.type_traitement.text = f'Type de traitement : {self.current_client[5]}'
                self.popup.get_screen('option_client').ids.duree.text = f'Durée du contrat : {self.current_client[6]}'

        # ⏱️ TIMING FIX: Ouvrir fenêtre après 0.1s (laisser async commencer)
        # Afficher infos après 1.0s (laisser requête terminer)
        Clock.schedule_once(lambda x: self.fenetre_client('', 'option_client'), 0.1)
        Clock.schedule_once(lambda x: maj_ecran(), 1.0)

    @mainthread
    def tableau_planning(self, place, result, dt=None):
        from kivymd.uix.label import MDLabel
        place.clear_widgets()

        if not result:
            label = MDLabel(
                text="Aucune donnée de planning disponible",
                halign="center"
            )
            place.add_widget(label)
            return

        row_data = []
        liste_id = []

        for item in result:
            try:
                if len(item) >= 4:
                    client = item[0] if item[0] is not None else "N/A"
                    traitement = item[1] if item[1] is not None else "N/A"
                    red = item[2] if item[2] is not None else "N/A"
                    id_planning = item[3] if item[3] is not None else 0

                    # ✅ Format redondance: 0='1 jour', 1='1 mois', 2='2 mois', etc.
                    display_red = '1 jour' if int(red) == 0 else f'{red} mois'
                    row_data.append((client, traitement, display_red, 'Aucun decalage'))
                    liste_id.append(id_planning)
                else:
                    print(f"Warning: Planning item doesn't have enough elements: {item}")
            except Exception as e:
                print(f"Error processing planning item: {e}")

        if not row_data:
            label = MDLabel(
                text="Données de planning invalides ou mal formatées",
                halign="center"
            )
            place.add_widget(label)
            return

        try:
            if self.liste_planning.parent:
                self.liste_planning.parent.remove_widget(self.liste_planning)

            # ✅ Initialiser le paginateur
            self.paginator_planning.set_total_rows(len(row_data))
            self.paginator_planning.reset()

            pagination = self.liste_planning.pagination

            btn_prev = pagination.ids.button_back
            btn_next = pagination.ids.button_forward

            def on_press_page(direction, instance=None):
                print(f"📄 Planning: {direction} | {self.paginator_planning.debug_info()}")
                if direction == 'moins':
                    self.paginator_planning.prev_page()
                elif direction == 'plus':
                    self.paginator_planning.next_page()

            btn_prev.bind(on_press=partial(on_press_page, 'moins'))
            btn_next.bind(on_press=partial(on_press_page, 'plus'))
            self.liste_planning.row_data = row_data

            self.liste_planning.bind(on_row_press= partial(self.row_pressed_planning, liste_id))

            # ✅ Afficher avec délai
            self._display_table_with_delay(place, self.liste_planning, delay=0.3)
            #del self.liste_planning
        except Exception as e:
            print(f"Error creating planning table: {e}")

    @mainthread
    def tableau_selection_planning(self, place, data, traitement):
        from kivymd.uix.label import MDLabel

        if hasattr(self, 'liste_select_planning') and self.liste_select_planning is not None:
            if self.liste_select_planning.parent:
                self.liste_select_planning.parent.remove_widget(self.liste_select_planning)

        place.clear_widgets()

        if not data:
            label = MDLabel(
                text="Aucune donnée de planning disponible",
                halign="center"
            )
            place.add_widget(label)
            return

        row_data = []
        for mois, item in enumerate(data):
            try:
                if len(item) >= 2:
                    date = self.reverse_date(item[0]) if item[0] is not None else "N/A"
                    etat = item[1] if item[1] is not None else "N/A"

                    # ✅ Format mois: 1='1er mois', 2='2e mois', 3='3e mois', etc.
                    mois_display = f'{mois + 1}er mois' if mois == 0 else f'{mois + 1}e mois'
                    row_data.append((date, mois_display , etat))
                else:
                    print(f"Warning: Planning item doesn't have enough elements: {item}")
            except Exception as e:
                print(f"Error processing planning item: {e}")

        try:
            self.liste_select_planning = MyDatatable(
                pos_hint={'center_x': .5, "center_y": .5},
                size_hint=(.6, .85),
                elevation=0,
                rows_num=5,
                use_pagination=True,
                column_data=[
                    ("Date", dp(35)),
                    ("Statistique", dp(35)),
                    ("Etat du traitement", dp(40)),
                ]
            )

            def _():
                self.liste_select_planning.row_data = row_data

            pagination = self.liste_select_planning.pagination
            btn_prev = pagination.ids.button_back
            btn_next = pagination.ids.button_forward

            # ✅ Initialiser le paginateur pour la sélection planning
            self.paginator_select_planning.set_total_rows(len(row_data))
            self.paginator_select_planning.reset()

            def on_press_page( direction, instance=None):
                print(f"📄 Select Planning: {direction} | {self.paginator_select_planning.debug_info()}")
                if direction == 'moins':
                    self.paginator_select_planning.prev_page()
                elif direction == 'plus':
                    self.paginator_select_planning.next_page()

            btn_prev.bind(on_press=partial(on_press_page,  'moins'))
            btn_next.bind(on_press=partial(on_press_page,  'plus'))

            self.liste_select_planning.bind(
                on_row_press=lambda instance, row: self.row_pressed_tableau_planning(traitement, instance, row))
            
            # ✅ Afficher avec délai
            def set_and_display():
                self.liste_select_planning.row_data = row_data
                self._display_table_with_delay(place, self.liste_select_planning, delay=0.3)
            
            place.add_widget(self.liste_select_planning)
            Clock.schedule_once(lambda dt :set_and_display(),0)


        except Exception as e:
            print(f'Error creating planning_detail table: {e}')

    def row_pressed_planning(self, list_id, table, row):
        # ✅ Utiliser le paginateur
        row_num = PaginationHelper.calculate_row_num(row.index, len(table.column_data))
        index_global = self.paginator_planning.get_global_index(row_num)

        row_value = None
        if self.paginator_planning.is_valid_global_index(index_global):
            row_value = table.row_data[index_global]

        self.fenetre_planning('', 'selection_planning')
        print(f"🔹 row_pressed_planning: {row_value} | {self.paginator_planning.debug_info()}")
        if row_value:
            Clock.schedule_once(lambda dt: self.get_and_update(row_value[1], row_value[0], list_id[index_global]), 0)

    def get_and_update(self, data1, data2, data3):
        asyncio.run_coroutine_threadsafe(self.planning_par_traitement(data1, data2, data3), self.loop)

    async def planning_par_traitement(self, traitement, client, id_traitement):
        titre = traitement.partition('(')[0].strip()
        screen = self.popup.get_screen('selection_planning')
        screen.ids.titre.text = f'Planning de {titre} pour {client}'

        place = screen.ids.tableau_select_planning
        Clock.schedule_once(lambda dt: place.clear_widgets(), 0)

        async def details():
            try:
                result = await self.database.get_details(id_traitement)
                if result:
                    threading.Thread(target=self.tableau_selection_planning(place, result, id_traitement)).start()
                    Clock.schedule_once(lambda dt :self.loading_spinner(self.popup, 'selection_planning', show=True))
            except Exception as e:
                print('misy erreur :', e)

        def maj_ecran():
            asyncio.run_coroutine_threadsafe(details(), self.loop)

        Clock.schedule_once(lambda ct: maj_ecran(), 0.5)

    def row_pressed_tableau_planning(self, traitement,  table, row):
        # ✅ Utiliser le paginateur pour la sélection planning
        row_num = PaginationHelper.calculate_row_num(row.index, len(table.column_data))
        index_global = self.paginator_select_planning.get_global_index(row_num)
        row_value = None

        if self.paginator_select_planning.is_valid_global_index(index_global):
            row_value = table.row_data[index_global]

        print(f"🔹 row_pressed_tableau_planning: {row_value} | {self.paginator_select_planning.debug_info()}")

        self.dismiss_popup()
        self.fermer_ecran()

        async def get():
            self.planning_detail = await self.database.get_info_planning(traitement, self.reverse_date(row_value[0]))
            print(self.planning_detail, type(self.planning_detail))

        asyncio.run_coroutine_threadsafe(get(), self.loop)

        if row.index % 3 == 0:
            self.popup.get_screen('modif_date').ids.date_prevu.text = row_value[0]
            self.popup.get_screen('modif_date').ids.date_decalage.text = ''
            self.modifier_date()
        else:
            # ⏱️ CORRECTION: Attendre que self.planning_detail soit chargé (0.5s) AVANT d'appeler maj_ui()
            Clock.schedule_once(lambda dt: self.fenetre_planning('', 'selection_element_tableau'), 0)
            Clock.schedule_once(lambda dt: self.maj_ui(row_value), 0.5)

    def maj_ui(self, row_value):
        """Affiche les infos du planning dans la fenêtre"""
        try:
            if not self.planning_detail:
                print('⚠️ planning_detail n\'est pas encore chargé')
                return
            
            print('Maj ui', self.planning_detail)
            titre = self.planning_detail[1].split(' ')
            self.popup.get_screen('selection_element_tableau').ids['titre'].text = f'{titre[0]} pour {self.planning_detail[0]}'
            self.popup.get_screen('ajout_remarque').ids['titre'].text = f'{titre[0]} pour {self.planning_detail[0]}'
            self.popup.get_screen('option_decalage').ids.client.text = f'Client: {self.planning_detail[0]}'

            self.popup.get_screen('selection_element_tableau').ids['contrat'].text = f'Contrat du {self.reverse_date(self.planning_detail[3])} au {self.planning_detail[4]}'

            self.popup.get_screen('selection_element_tableau').ids['mois'].text = f'Date du traitement : {row_value[0]}'
            self.popup.get_screen('ajout_remarque').ids['date'].text = f'Date du traitement : {row_value[0]}'

            self.popup.get_screen('selection_element_tableau').ids['mois_trait'].text = f'Mois du traitement: {row_value[1]}'
            self.popup.get_screen('ajout_remarque').ids['mois_trait'].text = f'Mois du traitement: {row_value[1]}'

            self.popup.get_screen('ajout_remarque').ids['duree'].text = f'Durée total du traitement : {self.planning_detail[2]}'

        except Exception as e:
            print(f'❌ affichage detail: {e}')
            import traceback
            traceback.print_exc()

    def afficher_ecran_remarque(self):
        self.fenetre_planning('', 'ajout_remarque')

        screen = self.popup.get_screen('ajout_remarque')
        screen.ids.remarque.text = ''
        screen.ids.probleme.text = ''
        screen.ids.action.text = ''
        screen.ids.paye_facture.active = False
        self.on_check_press(False)

    def create_remarque(self):
        try:
            screen = self.popup.get_screen('ajout_remarque')
            remarque = screen.ids.remarque.text
            probleme = screen.ids.probleme.text
            action = screen.ids.action.text
            numero = screen.ids.numero_facture.text
            descri = screen.ids.date_payement.text
            etab = screen.ids.etablissement.text
            num_cheque = screen.ids.num_cheque.text
            paye = bool(screen.ids.paye_facture.active)
            cheque = bool(screen.ids.cheque.active)
            espece = bool(screen.ids.espece.active)
            virement = bool(screen.ids.virement.active)
            mobile = bool(screen.ids.mobile_money.active)
            payement = None

            if paye:
                if not espece and not cheque and not virement and not mobile:
                    Clock.schedule_once(lambda dt: self.show_dialog('Attention', 'Veuillez choisir une mode de payement'), 0)
                    return
                if not numero or not descri:
                    Clock.schedule_once(lambda dt: self.show_dialog('Attention', 'Veuillez remplir tous les champs'), 0)
                    return
                if cheque:
                    if not etab or not num_cheque:
                        Clock.schedule_once(lambda dt: self.show_dialog('Attention', 'Veuillez remplir tous les champs'), 0)
                        return

            self.dismiss_popup()
            self.fermer_ecran()

            remarque_db = remarque if remarque else None
            probleme_db = probleme if probleme else None
            action_db = action if action else None

            async def remarque_async(etat_paye):
                try:
                    # ✅ Créer la remarque
                    await self.database.create_remarque(self.planning_detail[5],
                                                        self.planning_detail[8],
                                                        self.planning_detail[6],
                                                        remarque_db,
                                                        probleme_db,
                                                        action_db)
                    
                    # ✅ CORRECTION: Marquer comme effectué et vérifier le résultat
                    update_success = await self.database.update_etat_planning(self.planning_detail[8])
                    if not update_success:
                        print(f"⚠️ Impossible de marquer planning {self.planning_detail[8]} comme effectué")
                    
                    bnk = None
                    numero_cheque_val = None
                    if etat_paye:
                        if cheque:
                            payement = 'Cheque'
                            bnk = etab
                            numero_cheque_val = num_cheque
                        if espece:
                            payement = "Espece"
                        if virement:
                            payement = 'Virement'
                        if mobile:
                            payement = 'Mobile Money'

                        await self.database.update_etat_facture(self.planning_detail[6], numero, payement, bnk, self.reverse_date(descri), numero_cheque_val)

                    Clock.schedule_once(lambda dt: self.show_dialog('', 'Enregistrement réussi'), 0)
                    Clock.schedule_once(lambda dt: self.fermer_ecran(), 0.5)
                    Clock.schedule_once(lambda dt: self.dismiss_popup(), 0.5)
                    Clock.schedule_once(lambda dt: self.clear_remarque_fields(screen), 0.5)
                    # ✅ CORRECTION: Augmenter le délai à 0.8s pour laisser le temps à la BD de committer
                    Clock.schedule_once(lambda dt: asyncio.run_coroutine_threadsafe(self.populate_tables(), self.loop), 0.8)

                except Exception as e:
                    print(f'❌ Erreur creation remarque: {e}')
                    import traceback
                    traceback.print_exc()
                    Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'ajout_remarque', show=False), 0)
                    Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Enregistrement échoué: {str(e)}'), 0)

            asyncio.run_coroutine_threadsafe(remarque_async(paye), self.loop)

        except Exception as e:
            print(f'❌ Erreur create_remarque: {e}')
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Erreur validation: {str(e)}'), 0)

    def clear_remarque_fields(self, screen):
        """Nettoie les champs du formulaire"""
        screen.ids.remarque.text = ''
        screen.ids.probleme.text = ''
        screen.ids.action.text = ''
        screen.ids.paye_facture.active = False

    def historique_par_categorie(self, categorie):
        place = self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen('historique').ids.tableau_historic
        place.clear_widgets()

        datas = []
        id_planning = []
        async def get_histo():
            try:
                result = await self.database.get_historic(categorie)
                for i in result:
                    # ✅ CORRECTION: Ne garder que les lignes COMPLÈTES (pas de None)
                    # Si une ligne a None, elle n'a pas de remarque valide → ignorer
                    if None not in i:
                        datas.append(i)
                        id_planning.append(i[4])  # Ajoute planning_id

                Clock.schedule_once(lambda dt: self.tableau_historic(place, datas, id_planning))

            except Exception as e:
                print('histo par categ', e)

        def maj_ecran():
            asyncio.run_coroutine_threadsafe(get_histo(), self.loop)

        Clock.schedule_once(lambda dt: self.loading_spinner('Sidebar', 'historique'), 0)
        Clock.schedule_once(lambda dt: maj_ecran(), 0.5)

    def tableau_historic(self, place, data, planning_id):
        row_data = [(i[0], i[1], i[2], i[3] if i [3] != 'None' else 'pas de remarque') for i in data]
        if self.historique.parent:
            self.historique.parent.remove_widget(self.historique)

        # ✅ Initialiser le paginateur pour l'historique
        self.paginator_historic.set_total_rows(len(row_data))
        self.paginator_historic.reset()

        pagination = self.historique.pagination

        btn_prev = pagination.ids.button_back
        btn_next = pagination.ids.button_forward

        def on_press_page( direction, instance=None):
            print(f"📄 Historique: {direction} | {self.paginator_historic.debug_info()}")
            if direction == 'moins':
                self.paginator_historic.prev_page()
            elif direction == 'plus':
                self.paginator_historic.next_page()

        btn_prev.bind(on_press=partial(on_press_page,  'moins'))
        btn_next.bind(on_press=partial(on_press_page,  'plus'))

        # ✅ Afficher avec délai
        self.historique.bind(on_row_press=partial(self.row_pressed_histo, planning_id=planning_id))
        self._display_table_with_delay(place, self.historique, delay=0.3)

    def row_pressed_histo(self, table, row, planning_id):
        # ✅ Utiliser le paginateur pour l'historique
        row_num = PaginationHelper.calculate_row_num(row.index, len(table.column_data))
        index_global = self.paginator_historic.get_global_index(row_num)
        row_value = None

        if self.paginator_historic.is_valid_global_index(index_global):
            row_value = table.row_data[index_global]

        print(f"🔹 row_pressed_histo: {row_value} | {self.paginator_historic.debug_info()}")

        if row_value[0] == 'Aucun':
            return

        # ✅ CORRECTION: Vérifier que index_global est valide et que planning_id n'est pas None
        if not isinstance(planning_id, list):
            print(f"❌ Erreur: planning_id n'est pas une liste: {type(planning_id)}")
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Erreur: Historique non disponible'), 0)
            return
        
        if row_num >= len(planning_id):
            print(f"❌ Erreur: row_num={row_num} hors limites de planning_id (len={len(planning_id)})")
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Erreur: Historique non disponible'), 0)
            return
        
        if planning_id[row_num] is None:
            print(f"❌ Erreur: planning_id[{row_num}] est None")
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', 'Erreur: Cet historique n\'a pas de planning associé'), 0)
            return

        place = self.popup.get_screen('histo_remarque').ids.tableau_rem_histo
        place.clear_widgets()
        self.fenetre_histo('', 'histo_remarque')

        def get_data():
            asyncio.run_coroutine_threadsafe(self.historique_remarque(place, planning_id[row_num]), self.loop)

        Clock.schedule_once(lambda c: self.loading_spinner(self.popup, 'histo_remarque'), 0)
        Clock.schedule_once(lambda c: get_data(), 0)

    async def historique_remarque(self, place, planning_id):
        from kivymd.uix.label import MDLabel

        try:
            resultat = await self.database.get_historique_remarque(planning_id)
            Clock.schedule_once(lambda dt: self.tableau_rem_histo(place, resultat if resultat else []), 0.5)
        except Exception as e:
            print('Erreur lors de la récupération des remarques :', e)
            if place:
                place.clear_widgets()
                error_label = MDLabel(
                    text=f"Erreur lors du chargement de l'historique des remarques : {e}",
                    halign="center"
                )
                place.add_widget(error_label)
            else:
                print("Erreur: 'place' est None, impossible d'afficher le message d'erreur.")

    def tableau_rem_histo(self, place, data):
        from kivy.metrics import dp
        from kivymd.uix.label import MDLabel

        place.clear_widgets()

        row_data = []
        for item in data:
            try:
                if len(item) >= 2:
                    date = self.reverse_date(item[0]) if item[0] is not None else "N/A"
                    remarque = item[1] if item[1] is not None else "N/A"
                    avance = item[2] if item[2] is not None else 'Aucun'
                    decale = item[3] if item[3] is not None else 'Aucun'
                    probleme = item[4] if item[4] is not None else 'Aucun'
                    action = item[5] if item[5] is not None else 'Aucun'
                    print(remarque, probleme, action)
                    row_data.append((date, remarque, avance, decale,probleme, action))
                else:
                    print(f"Warning: L'élément de remarque historique n'a pas assez d'éléments (attendu 2+): {item}")
            except Exception as e:
                print(f"Erreur lors du traitement de l'élément de remarque historique : {e}")

        if not row_data:
            label = MDLabel(
                text="Aucune remarque d'historique disponible.",
                halign="center"
            )
            place.add_widget(label)
            return

        try:
            self.remarque_historique = MyDatatable(
                pos_hint={'center_x': .5, "center_y": .53},
                size_hint=(1, 1),
                rows_num=5,
                elevation=0,
                column_data=[
                    ("Date", dp(25)),
                    ("Remarque", dp(40)),
                    ("Avancement", dp(35)),
                    ("Décalage", dp(35)),
                    ("Probleme", dp(30)),
                    ("Action", dp(30)),
                ]
            )
            
            # ✅ Afficher avec délai
            def set_and_display():
                self.remarque_historique.row_data = row_data
                self._display_table_with_delay(place, self.remarque_historique, delay=0.3)
            
            Clock.schedule_once(lambda dt: set_and_display(), 0.1)

        except Exception as e:
            print(f'Erreur lors de la création du tableau des remarques historiques : {e}')

    def all_users(self, place):
        async def data_account():
            try:
                users = await self.database.get_all_user()
                if users:
                    Clock.schedule_once(lambda dt: self.tableau_compte(place, users))
            except Exception as e:
                print(e)
                self.show_dialog('erreur', 'Erreur !')

        asyncio.run_coroutine_threadsafe(data_account(), self.loop)

    def tableau_compte(self, place, data):
        self.account = MDDataTable(
            pos_hint={'center_x': .5, "center_y": .53},
            size_hint=(1, 1),
            background_color_header='#D9D9D9',
            rows_num=len(data),
            elevation=0,
            column_data=[
                ("Nom d'utilisateur", dp(62)),
                ("Email", dp(80)),
            ],
            row_data=data
        )
        self.account.bind(on_row_press=self.row_pressed_compte)
        place.add_widget(self.account)

    def maj_compte(self, compte):
        self.popup.get_screen('compte_abt').ids['titre'].text = f'A propos de {compte[4]}'
        self.popup.get_screen('compte_abt').ids['nom'].text = f'Nom : {compte[1]}'
        self.popup.get_screen('compte_abt').ids['prenom'].text = f'Prénom : {compte[2]}'
        self.popup.get_screen('compte_abt').ids['email'].text = f'Email : {compte[3]}'

    def row_pressed_compte(self, table, row):
        try:
            row_num = int(row.index / len(table.column_data))
            row_data = table.row_data[row_num]
            
            # ✅ Afficher spinner pendant chargement
            Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'compte', show=True), 0)

            async def about():
                try:
                    self.not_admin = await self.database.get_user(row_data[0])
                    Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'compte', show=False), 0)
                    Clock.schedule_once(lambda dt: self.dismiss_popup(), 0)
                    Clock.schedule_once(lambda dt: self.maj_compte(self.not_admin), 0)
                    Clock.schedule_once(lambda dt: self.fenetre_account('', 'compte_abt'), 0)
                except Exception as e:
                    print(f'❌ Erreur chargement compte: {e}')
                    import traceback
                    traceback.print_exc()
                    Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'compte', show=False), 0)
                    Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Erreur chargement: {str(e)}'), 0)

            asyncio.run_coroutine_threadsafe(about(), self.loop)
        
        except Exception as e:
            print(f'❌ Erreur row_pressed_compte: {e}')
            import traceback
            traceback.print_exc()
            Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Erreur: {str(e)}'), 0)

    def suppression_compte(self, username):
        nom = username.split(' ')
        self.popup.get_screen('suppression_compte').ids['titre'].text = f'Suppression du compte de {nom[3]}'
        self.dismiss_popup()
        self.fermer_ecran()
        self.fenetre_account('', 'suppression_compte')

    def modification_compte(self):
        self.dismiss_popup()

        titre = "Modification des informations de l'administrateur"  if self.compte[6] == 'Administrateur' else f"Modification des informations de {self.compte[4]}"
        self.popup.get_screen('modif_info_compte').ids.nom.text = self.compte[1]
        self.popup.get_screen('modif_info_compte').ids.prenom.text = self.compte[2]
        self.popup.get_screen('modif_info_compte').ids.email.text = self.compte[3]
        self.popup.get_screen('modif_info_compte').ids.username.text = self.compte[4]
        self.popup.get_screen('modif_info_compte').ids.titre_info.text = titre
        self.fenetre_account('', 'modif_info_compte')

    def modification_client(self ,nom,option ):
        self.dismiss_popup()
        self.fermer_ecran()

        btn_enregistrer = self.popup.get_screen('modif_client').ids.enregistrer
        btn_annuler = self.popup.get_screen('modif_client').ids.annuler

        if option == 'voir':
            btn_annuler.text = 'Fermer'
            btn_enregistrer.opacity = 0
        else:
            btn_annuler.text = 'Annuler'
            btn_enregistrer.opacity = 1

        if self.current_client[3] == 'Particulier':
            self.popup.get_screen('modif_client').ids.label_resp.text = 'Prenom'
            nom = self.current_client[1] + ' ' + self.current_client[2]
        else:
            self.popup.get_screen('modif_client').ids.label_resp.text = 'Responsable'
            nom = self.current_client[1]

        if self.current_client[3] == 'Société':
            self.popup.get_screen('modif_client').ids.nif.text = self.current_client[15]
            self.popup.get_screen('modif_client').ids.stat.text = self.current_client[16]
            self.popup.get_screen('modif_client').ids.stat_label.pos_hint = {'center_x': 1.005, 'center_y': .23}
            self.popup.get_screen('modif_client').ids.stat.pos_hint = {"center_x":.73,"center_y":.14}
            self.popup.get_screen('modif_client').ids.nif_label.pos_hint = {'center_x': .5, 'center_y': .23}
            self.popup.get_screen('modif_client').ids.nif.pos_hint = {"center_x":.225,"center_y":.14}
        else:
            self.popup.get_screen('modif_client').ids.nif.text = ''
            self.popup.get_screen('modif_client').ids.stat.text = ''
            self.popup.get_screen('modif_client').ids.stat_label.pos_hint = {'center_x':-1 , 'center_y': -1}
            self.popup.get_screen('modif_client').ids.stat.pos_hint = {"center_x":-1,"center_y":-1}
            self.popup.get_screen('modif_client').ids.nif_label.pos_hint = {'center_x': -1, 'center_y': -1}
            self.popup.get_screen('modif_client').ids.nif.pos_hint = {"center_x":-1,"center_y":-1}


        self.popup.get_screen('modif_client').ids.date_contrat_client.text = self.reverse_date(self.current_client[4])
        self.popup.get_screen('modif_client').ids.cat_client.text = self.current_client[3]
        self.popup.get_screen('modif_client').ids.nom_client.text = self.current_client[1]
        self.popup.get_screen('modif_client').ids.email_client.text = self.current_client[9]
        self.popup.get_screen('modif_client').ids.adresse_client.text = self.current_client[10]
        self.popup.get_screen('modif_client').ids.axe_client.text = self.current_client[11]
        self.popup.get_screen('modif_client').ids.resp_client.text = self.current_client[2]
        self.popup.get_screen('modif_client').ids.telephone.text = self.current_client[12]
        self.fenetre_client(f'Modifications des informartion sur {nom}', 'modif_client')

    def enregistrer_modif_client(self,btn, nom, prenom, email, telephone, adresse, categorie, axe, nif, stat):
        nif_bd = nif if nif else 0
        stat_bd = stat if stat else 0

        if btn.opacity == 1:
            # ✅ Afficher spinner pendant modification
            Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'modif_client', show=True), 0)
            
            async def save():
                try:
                    await self.database.update_client(self.current_client[0], nom, prenom, email, telephone, adresse, nif, stat, categorie, axe)
                    Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'modif_client', show=False), 0)
                    Clock.schedule_once(lambda dt: self.show_dialog('Enregistrements reussie', 'Les modifications sont enregistrees'), 0)
                    Clock.schedule_once(lambda dt: self.dismiss_popup(), 0.5)
                    Clock.schedule_once(lambda dt: self.fermer_ecran(), 0.5)
                    Clock.schedule_once(lambda dt: self.remove_tables('contrat'), 0.6)
                    self.current_client = None
                except Exception as e:
                    print(f'❌ Erreur enregistrer_modif_client: {e}')
                    import traceback
                    traceback.print_exc()
                    Clock.schedule_once(lambda dt: self.loading_spinner(self.popup, 'modif_client', show=False), 0)
                    Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Modification echouee: {str(e)}'), 0)

            asyncio.run_coroutine_threadsafe(save(), self.loop)

    def suppression_contrat(self):

        fin = self.reverse_date(self.current_client[8]) if self.current_client[8] != 'Indéterminée' else 'Indéterminée'
        self.popup.get_screen('suppression_contrat').ids.titre.text = f'Suppression du contrat de {self.current_client[1]}'
        self.popup.get_screen('suppression_contrat').ids.date_contrat.text = f'Date du contrat: {self.reverse_date(self.current_client[4])}'
        self.popup.get_screen('suppression_contrat').ids.debut_contrat.text = f'Début du contrat: {self.reverse_date(self.current_client[7])}'
        self.popup.get_screen('suppression_contrat').ids.fin_contrat.text = f'Fin du contrat: {fin}'

        self.dismiss_popup()
        self.fermer_ecran()
        self.fenetre_contrat('', 'suppression_contrat')

    async def populate_tables(self):
        """Charge les tableaux Home depuis la BD avec gestion d'erreur complète"""
        try:
            data_current = []
            data_next = []
            
            # Vérifier que Home existe avant de continuer
            try:
                home = self.root.get_screen('Sidebar').ids['gestion_ecran'].get_screen('Home')
                if not home:
                    print('❌ ERREUR: Écran Home introuvable')
                    return
            except Exception as e:
                print(f'❌ ERREUR: Impossible d\'accéder à Home: {e}')
                return
            
            now = datetime.now()
            
            # Récupère les données de la BD
            try:
                data_en_cours, data_prevision = await asyncio.gather(
                    self.database.traitement_en_cours(now.year, now.month),
                    self.database.traitement_prevision(now.year, now.month)
                )
            except Exception as e:
                print(f'❌ ERREUR BD populate_tables: {e}')
                Clock.schedule_once(
                    lambda dt: self.show_dialog('Erreur', 'Erreur lors du chargement des données')
                )
                return
            
            # Traite les données
            data_current = []
            check = []
            for i in data_en_cours:
                try:
                    color = self.color_map.get(i['etat'], "000000")
                    check.append((self.reverse_date(i['date']), i['traitement'], i['etat'], i['axe']))
                    data_current.append((
                        f"[color={color}]{self.reverse_date(i['date'])}[/color]",
                        f"[color={color}]{i['traitement']}[/color]",
                        f"[color={color}]{i['etat']}[/color]",
                        f"[color={color}]{i['axe']}[/color]"
                    ))
                except Exception as e:
                    print(f'⚠️ ERREUR traitement en_cours: {e}')
                    continue
            
            for i in data_prevision:
                try:
                    traitement_a_verifier = i['traitement']
                    traitement_existe = any(item[1] == traitement_a_verifier for item in check)
                    
                    if not traitement_existe:
                        row = (self.reverse_date(i["date"]), i["traitement"], i['etat'], i['axe'])
                        data_next.append(row)
                except Exception as e:
                    print(f'⚠️ ERREUR traitement prévision: {e}')
                    continue
            
            print(f'✅ populate_tables: {len(data_current)} en cours, {len(data_next)} à venir')
            
            # Appelle home_tables avec gestion d'erreur
            Clock.schedule_once(lambda dt: self._safe_home_tables(data_current, data_next, home))
            
        except Exception as e:
            print(f'❌ ERREUR CRITIQUE populate_tables: {e}')
            import traceback
            traceback.print_exc()
    
    def _safe_home_tables(self, current, next, home):
        """Affiche les tableaux avec gestion d'erreur complète"""
        try:
            if not home:
                print('❌ ERREUR: home est None')
                return
            
            if not hasattr(home.ids, 'box_current') or not hasattr(home.ids, 'box_next'):
                print('❌ ERREUR: box_current ou box_next introuvable')
                return
            
            def update_data():
                try:
                    self.table_en_cours.row_data = current
                    self.table_prevision.row_data = next
                    print('✅ Tableaux mis à jour avec succès')
                except Exception as e:
                    print(f'❌ ERREUR mise à jour row_data: {e}')
            
            # Nettoie les anciens tableaux
            try:
                if self.table_en_cours.parent:
                    self.table_en_cours.parent.remove_widget(self.table_en_cours)
                if self.table_prevision.parent:
                    self.table_prevision.parent.remove_widget(self.table_prevision)
                print('✅ Anciens tableaux supprimés')
            except Exception as e:
                print(f'⚠️ ERREUR suppression anciens tableaux: {e}')
            
            # Ajoute les nouveaux tableaux
            try:
                home.ids.box_current.add_widget(self.table_en_cours)
                home.ids.box_next.add_widget(self.table_prevision)
                print('✅ Nouveaux tableaux ajoutés')
            except Exception as e:
                print(f'❌ ERREUR ajout nouveaux tableaux: {e}')
                return
            
            # Met à jour les données
            Clock.schedule_once(lambda dt: update_data(), .2)
            
        except Exception as e:
            print(f'❌ ERREUR CRITIQUE home_tables: {e}')
            import traceback
            traceback.print_exc()

    def generer_excel(self):
        screen = self.popup.get_screen('rendu_planning')
        categorie = screen.ids.categ_planning.text
        traitement = screen.ids.type_traitement_planning.text
        mois = screen.ids.mois_planning.text
        client = screen.ids.client.text
        data = None
        print(categorie, traitement, mois, client)
        if "mme" in client.lower():
            nom = client.split('mme')[0]
        if "mr" in client.lower():
            nom = client.split('mr')[0]
        else:
            nom = client.split(' ')[0]

        if categorie == 'Facture':
            if mois == 'Tous':
                if client == 'Tous':
                    self.show_dialog('Attention', 'Veuillez specifier un client')
                    return
                else:
                    self.show_dialog('Attention', 'Veuillez choisir un mois spécifique')
                    return

                data = self.excel_database('facture par client', nom)
                generate_comprehensive_facture_excel(data, client)

            else:
                data = self.excel_database('facture par mois', nom, mois)
                generer_facture_excel(data, client, datetime.today().year, datetime.strptime(mois, "%B").month)

        if categorie == 'Traitement':
            if traitement == 'Tous' and client == 'Tous':
                if client != 'Tous':
                    self.show_dialog('Attention', 'Les traitements ne sont disponibles que pour tous les clients')
                    return
                if mois == 'Tous':
                    self.show_dialog('Attention', 'Veuillez choisir un mois')
                    return
                data = self.excel_database('traitement', mois=mois)
                generate_traitements_excel(data, datetime.today().year, datetime.strptime(mois, "%B").month)

        self.dismiss_popup()
        self.fermer_ecran()
        self.show_dialog('', 'Le fichier a été generé avec succes')
        print(data)

    def excel_database(self, option, client=None, mois=None):
        print(client)

        async def get_data():
            if option == 'facture par client':
                return await self.database.get_factures_data_for_client_comprehensive(client)

            elif option == 'facture par mois':
                return await self.database.obtenirDataFactureClient(
                    client, datetime.today().year, datetime.strptime(mois, "%B").month
                )

            elif option == 'traitement':
                return await self.database.get_traitements_for_month(
                    datetime.today().year, datetime.strptime(mois, "%B").month
                )

        future = asyncio.run_coroutine_threadsafe(get_data(), self.loop)
        return future.result()  # attend et renvoie la vraie valeur

    def resilier_contrat(self):
        # ✅ Afficher spinner pendant resiliation
        Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'contrat', show=True), 0)
        
        async def get_data():
            try:
                id, datee = await self.database.get_planningdetails_id(self.current_client[13])
                print(id, datee)
                await self.database.abrogate_contract(id)
                
                # ✅ CORRECTION: Attendre 0.5s pour que la BD traite la suppression
                await asyncio.sleep(0.5)
                
                # ✅ CORRECTION: Lancer les 3 rafraîchissements en PARALLÈLE et ATTENDRE
                await asyncio.gather(
                    self.populate_tables(),
                    self.get_client(),
                    self.all_clients()
                )
                
                # ✅ Fermer l'UI et afficher message success
                Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'contrat', show=False), 0)
                Clock.schedule_once(lambda dt: self.dismiss_popup(), 0.1)
                Clock.schedule_once(lambda dt: self.fermer_ecran(), 0.1)
                Clock.schedule_once(lambda dt: self.show_dialog('Operation effectue', 'Le contrat a ete resilie'), 0.2)
            except Exception as e:
                print(f'❌ Erreur resilier_contrat: {e}')
                import traceback
                traceback.print_exc()
                Clock.schedule_once(lambda dt: self.loading_spinner(self.root.get_screen('Sidebar'), 'contrat', show=False), 0)
                Clock.schedule_once(lambda dt: self.show_dialog('Erreur', f'Resiliation echouee: {str(e)}'), 0)

        asyncio.run_coroutine_threadsafe(get_data(), self.loop)

    def open_compte(self, dev):
        import webbrowser
        if dev == 'Mamy':
            webbrowser.open('https://github.com/AinaMaminirina18')
        else:
            webbrowser.open('https://github.com/josoavj')

    def on_stop(self):
        """Arrête proprement la boucle asyncio et le gestionnaire de base de données."""
        if not self.loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(self.database.close(), self.loop)
            future.result()

        self.loop.call_soon_threadsafe(self.loop.stop)


if __name__ == "__main__":
    from kivy.core.text import LabelBase

    LabelBase.register(name='poppins',
                       fn_regular='font/Poppins-Regular.ttf')
    LabelBase.register(name='poppins-bold',
                       fn_regular='font/Poppins-Bold.ttf')
    Screen().run()
