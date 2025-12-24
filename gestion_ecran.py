from kivy.lang.builder import Builder
from kivy.uix.screenmanager import SlideTransition
from kivy.clock import Clock


def gestion_ecran_optimized(root):
    """
    ✅ OPTIMISATION: Charger uniquement Home.kv au démarrage.
    Les autres écrans se chargent en arrière-plan ou lazy-loaded.
    """
    try:
        # Charger immédiatement Home (essentiel pour l'affichage)
        root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/Home.kv'))
        print("✅ Home.kv chargé immédiatement")
        
        # Charger les autres écrans en arrière-plan (non-bloquant)
        def load_other_screens():
            try:
                root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/historique/historique.kv'))
                root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/historique/choix_traitement.kv'))
                root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/contrat/contrat.kv'))
                root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/planning/planning.kv'))
                root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/about.kv'))
                root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/client/Client.kv'))
                root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/compte/compte.kv'))
                root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/compte/compte_not_admin.kv'))
                print("✅ Tous les écrans gestion_ecran chargés en arrière-plan")
            except Exception as e:
                print(f"⚠️ Erreur chargement écrans en arrière-plan: {e}")
        
        # Planifier le chargement en arrière-plan avec un délai de 0.5s
        Clock.schedule_once(lambda dt: load_other_screens(), 0.5)
        
        root.get_screen('Sidebar').ids['gestion_ecran'].transition = SlideTransition(direction='up')
    except Exception as e:
        print(f"❌ Erreur gestion_ecran_optimized: {e}")


def gestion_ecran(root):
    """Version originale (non-optimisée) pour compatibilité"""
    gestion_ecran_optimized(root)


def popup(manager, init_only=True):
    """Charger les écrans popup - init_only=True pour démarrage rapide"""
    vide = """
MDScreen:
    name: 'vide'
    pos_hint: {'center_x':.5, 'center_y':.5}
    """
    manager.add_widget(Builder.load_string(vide))
    
    # ✅ ÉTAPE 2 - Optimisation: Charger seulement les essentiels au démarrage
    if init_only:
        # Écrans critiques au démarrage (utilisés pendant le login)
        manager.add_widget(Builder.load_file('screen/modif_date.kv'))
        manager.add_widget(Builder.load_file('screen/Facture.kv'))
        print("⏳ Popup chargé (mode minimal) - écrans additionnels à la demande")
        # Les autres écrans seront chargés par popup_load_additional()
    else:
        # Charger TOUS les écrans (appelé après login)
        manager.add_widget(Builder.load_file('screen/modif_date.kv'))
        manager.add_widget(Builder.load_file('screen/Facture.kv'))
        manager.add_widget(Builder.load_file(f'screen/client/option_client.kv'))
        manager.add_widget(Builder.load_file(f'screen/client/modification_client.kv'))
        manager.add_widget(Builder.load_file('screen/compte/about_compte.kv'))
        manager.add_widget(Builder.load_file('screen/compte/suppr_compte.kv'))
        manager.add_widget(Builder.load_file('screen/compte/modif_compte.kv'))
        manager.add_widget(Builder.load_file(f'screen/contrat/option_contrat.kv'))
        manager.add_widget(Builder.load_file(f'screen/contrat/new-contrat.kv'))
        manager.add_widget(Builder.load_file(f'screen/contrat/suppr_contrat.kv'))
        manager.add_widget(Builder.load_file(f'screen/client/ajout_info_client.kv'))
        manager.add_widget(Builder.load_file(f'screen/client/save_info_client.kv'))
        manager.add_widget(Builder.load_file(f'screen/contrat/ajout_planning_contrat.kv'))
        manager.add_widget(Builder.load_file(f'screen/contrat/confirm_prix.kv'))
        manager.add_widget(Builder.load_file(f'screen/contrat/modif_prix.kv'))
        manager.add_widget(Builder.load_file(f'screen/contrat/facture_contrat.kv'))
        manager.add_widget(Builder.load_file(f'screen/contrat/about_treatment.kv'))
        manager.add_widget(Builder.load_file(f'screen/historique/option_histo.kv'))
        manager.add_widget(Builder.load_file(f'screen/historique/histo_remarque.kv'))
        manager.add_widget(Builder.load_file(f'screen/planning/rendu_planning.kv'))
        manager.add_widget(Builder.load_file(f'screen/planning/option_decalage.kv'))
        manager.add_widget(Builder.load_file(f'screen/planning/ecran_decalage.kv'))
        manager.add_widget(Builder.load_file(f'screen/planning/selection_planning.kv'))
        manager.add_widget(Builder.load_file(f'screen/planning/selection_tableau.kv'))
        manager.add_widget(Builder.load_file(f'screen/planning/ajout_remarque.kv'))
        print("✅ Tous les écrans popup chargés")
    
    manager.transition = SlideTransition(direction='left')

