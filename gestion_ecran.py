import logging
from kivy.lang.builder import Builder
from kivy.uix.screenmanager import SlideTransition

logger = logging.getLogger(__name__)


def gestion_ecran(root):
    """Charger les écrans principaux (gestion_ecran ScreenManager)"""
    logger.info("📁 Chargement des écrans principaux...")
    try:
        root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/Home.kv'))
        root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/historique/historique.kv'))
        root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/historique/choix_traitement.kv'))
        root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/contrat/contrat.kv'))
        root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/planning/planning.kv'))
        root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/about.kv'))
        root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/client/Client.kv'))
        root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/compte/compte.kv'))
        root.get_screen('Sidebar').ids['gestion_ecran'].add_widget(Builder.load_file('screen/compte/compte_not_admin.kv'))

        root.get_screen('Sidebar').ids['gestion_ecran'].transition = SlideTransition(direction='up')
        logger.info("✅ Écrans principaux chargés avec succès")
    except Exception as e:
        logger.error(f"❌ Erreur chargement écrans principaux: {e}", exc_info=True)


def popup(manager):
    """Charger les écrans modaux/dialogs (popup ScreenManager)"""
    logger.info("📁 Chargement des écrans modaux...")
    try:
        vide = """
MDScreen:
    name: 'vide'
    pos_hint: {'center_x':.5, 'center_y':.5}
    """
        manager.add_widget(Builder.load_string(vide))
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

        manager.transition = SlideTransition(direction='left')
        logger.info(f"✅ Écrans modaux chargés - {len(manager.screens)} screens disponibles")
        logger.info(f"📊 Screens: {[s.name for s in manager.screens]}")
    except Exception as e:
        logger.error(f"❌ Erreur chargement écrans modaux: {e}", exc_info=True)

