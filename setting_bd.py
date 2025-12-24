import asyncio
import datetime
import random
import logging
import sys

import aiomysql

import json
import os

# =====================================================
# LOGGING CONFIGURATION
# =====================================================
# Déterminer le répertoire de base (toujours le dossier du script)
if getattr(sys, 'frozen', False):
    # Exécutable PyInstaller (.exe)
    base_dir = os.path.dirname(sys.executable)
else:
    # Script Python normal - utiliser le répertoire du script, pas cwd
    base_dir = os.path.dirname(os.path.abspath(__file__))

# Créer le dossier 'logs' s'il n'existe pas
log_dir = os.path.join(base_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)

log_file = os.path.join(log_dir, 'planificator_db.log')

# Vérifier que le fichier de log peut être créé
try:
    with open(log_file, 'a') as f:
        pass  # Juste vérifier qu'on peut écrire
except Exception as e:
    print(f"❌ ERREUR: Impossible d'écrire dans {log_file}: {e}")
    log_file = os.path.join(os.path.expanduser('~'), 'planificator_db.log')
    print(f"📍 Utilisation de: {log_file}")

logging.basicConfig(
    level=logging.DEBUG,  # ← Changé de INFO à DEBUG pour plus de détails
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Aussi afficher dans console avec UTF-8
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"✅ LOGGING DÉMARRÉ - Fichier: {log_file}")

config_path = os.path.join(os.path.dirname(__file__), 'config.json')

with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)
    logger.info(f"Configuration chargée depuis {config_path}")

# =====================================================
# VALIDATION & ERROR HANDLING
# =====================================================

def validate_email(email):
    """Valide un email basique."""
    if not email or '@' not in email or '.' not in email.split('@')[1]:
        return False
    return True

def validate_phone(phone):
    """Valide un numéro de téléphone (enlève les caractères non-numériques)."""
    if not phone:
        return None
    cleaned = ''.join(filter(str.isdigit, str(phone)))
    return cleaned if len(cleaned) >= 7 else None

def validate_not_empty(value, field_name):
    """Vérifie qu'un champ n'est pas vide."""
    if not value or (isinstance(value, str) and not value.strip()):
        logger.warning(f"⚠️  Champ vide: {field_name}")
        raise ValueError(f"Le champ '{field_name}' ne peut pas être vide")
    return value

def validate_positive_number(value, field_name):
    """Vérifie qu'une valeur est un nombre positif."""
    try:
        num = float(value)
        if num < 0:
            raise ValueError(f"{field_name} doit être positif (valeur: {value})")
        return num
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} doit être un nombre valide (valeur: {value})")

def safe_execute(func_name):
    """Décorateur pour wrapper les erreurs critiques."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"❌ ERREUR CRITIQUE dans {func_name}: {e}", exc_info=True)
                raise
        return wrapper
    return decorator

class DatabaseManager:
    """Gestionnaire de la base de données utilisant aiomysql."""
    def __init__(self, loop):
        self.loop = loop
        self.pool = None
        self.lock = asyncio.Lock()

    async def connect(self):
        try:
            """Crée un pool de connexions à la base de données avec support réseau."""
            # Configuration pour réseau/distante
            pool_config = {
                'host': config['host'],
                'port': config['port'],
                'user': config['user'],
                'password': config['password'],
                'db': "Planificator",
                'loop': self.loop,
                'autocommit': False,
                'echo': False,
            }
            
            # Ajouter timeouts si c'est une connexion réseau (pas localhost)
            if config['host'] != 'localhost' and config['host'] != '127.0.0.1':
                pool_config['connect_timeout'] = 10  # 10 sec pour se connecter
                logger.warning(f"⚠️  Connexion réseau détectée ({config['host']}:{config['port']}) - timeout 10s activé")
            
            self.pool = await aiomysql.create_pool(**pool_config)
            logger.info(f"✅ Connexion BD réussie - Pool créé (host={config['host']}, port={config['port']}, db=Planificator)")
        except Exception as e:
            logger.error(f"❌ Erreur connexion BD: {e}", exc_info=True)
            raise
    
    async def reconnect(self):
        """Reconnecte la pool en cas de déconnexion."""
        try:
            logger.warning("🔄 Tentative de reconnexion BD...")
            if self.pool is not None:
                self.pool.close()
                await self.pool.wait_closed()
            
            await self.connect()
            logger.info("✅ Reconnexion réussie")
            return True
        except Exception as e:
            logger.error(f"❌ Reconnexion échouée: {e}", exc_info=True)
            return False
    
    async def get_pool_status(self):
        """Retourne l'état de la connection pool."""
        if self.pool is None:
            return {"status": "disconnected", "message": "Pool non initialisée"}
        
        try:
            free_size = self.pool._free_size if hasattr(self.pool, '_free_size') else 0
            size = self.pool._size if hasattr(self.pool, '_size') else 0
            
            status = {
                "status": "connected",
                "total_connections": size,
                "free_connections": free_size,
                "active_connections": size - free_size,
                "pool_healthy": free_size > 0
            }
            
            logger.debug(f"Pool status: {status}")
            
            if free_size == 0:
                logger.warning("⚠️  ALERTE: Aucune connexion libre dans la pool!")
            
            return status
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la pool: {e}")
            return {"status": "error", "message": str(e)}
    
    async def health_check(self, auto_reconnect=True):
        """Vérifie la santé de la connexion BD avec reconnexion automatique si réseau."""
        try:
            if self.pool is None:
                logger.error("❌ Health check échoué: Pool non initialisée")
                if auto_reconnect and config['host'] != 'localhost':
                    logger.warning("🔄 Tentative reconnexion automatique...")
                    return await self.reconnect()
                return False
            
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    result = await cur.fetchone()
                    
                    if result:
                        pool_status = await self.get_pool_status()
                        logger.info(f"✅ Health check OK - Pool: {pool_status['active_connections']}/{pool_status['total_connections']} connexions actives")
                        return True
                    else:
                        logger.error("❌ Health check échoué: Requête SELECT 1 sans résultat")
                        return False
        except Exception as e:
            logger.error(f"❌ Health check échoué: {e}", exc_info=True)
            
            # Détécter les erreurs réseau et reconnecter automatiquement
            error_msg = str(e).lower()
            is_network_error = any(err in error_msg for err in ['connection', 'timeout', 'refused', 'lost', 'closed'])
            
            if is_network_error and auto_reconnect and config['host'] != 'localhost':
                logger.warning(f"🌐 Erreur réseau détectée ({error_msg}), tentative reconnexion...")
                return await self.reconnect()
            
            return False
    
    async def check_latency(self):
        """Mesure la latence réseau vers la BD."""
        import time
        try:
            if self.pool is None:
                return {"status": "disconnected", "latency_ms": None}
            
            start = time.time()
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
            latency_ms = (time.time() - start) * 1000
            
            status = "good"
            if latency_ms > 500:
                status = "slow"
                logger.warning(f"⚠️  Latence réseau élevée: {latency_ms:.2f}ms")
            elif latency_ms > 200:
                status = "moderate"
                logger.debug(f"Latence réseau: {latency_ms:.2f}ms")
            else:
                logger.debug(f"✅ Latence réseau OK: {latency_ms:.2f}ms")
            
            return {
                "status": status,
                "latency_ms": latency_ms,
                "host": config['host'],
                "is_network": config['host'] != 'localhost'
            }
        except Exception as e:
            logger.error(f"❌ Erreur mesure latence: {e}")
            return {"status": "error", "latency_ms": None}
    
    async def diagnose(self):
        """Diagnostic complet de la BD et de la pool avec latence réseau."""
        try:
            health = await self.health_check()
            pool_status = await self.get_pool_status()
            latency = await self.check_latency()
            
            diagnosis = {
                "health": health,
                "pool": pool_status,
                "latency": latency,
                "timestamp": datetime.datetime.now().isoformat(),
                "network_connection": config['host'] != 'localhost'
            }
            
            logger.info(f"📊 Diagnostic BD: {diagnosis}")
            return diagnosis
        except Exception as e:
            logger.error(f"❌ Diagnostic échoué: {e}", exc_info=True)
            return {"error": str(e)}

    async def add_user(self, nom, prenom, email, username,  password, type_compte):
        """Ajoute un utilisateur dans la base de données."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO Account (nom, prenom, email, username, password, type_compte) VALUES (%s, %s, %s, %s, %s, %s)",
                    (nom, prenom, email, username, password, type_compte)
                )
                await conn.commit()

    async def update_user(self,new_nom, new_prenom, new_email, new_username, new_password, id):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await conn.begin()
                await cur.execute(
                    "UPDATE Account SET nom = %s, prenom= %s, email=%s, username=%s, password=%s WHERE id_compte = %s",
                    (new_nom, new_prenom, new_email, new_username, new_password, id)
                )
                await conn.commit()

    async def delete_user(self, email):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM Account WHERE email = %s",
                    email
                )
                await conn.commit()

    async def get_facture(self, client_id, traitement):
        def format_montant(montant):
            return f"{montant:,}".replace(",", " ")

        factures = []
        total_paye = 0
        total_non_paye = 0
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    await cursor.execute("""SELECT  pdl.date_planification,
                                                    f.montant,
                                                    f.etat
                                            FROM
                                                Client c
                                            JOIN
                                                Contrat co ON c.client_id = co.client_id
                                            JOIN
                                                Traitement t ON co.contrat_id = t.contrat_id
                                            JOIN
                                                Planning p ON t.traitement_id = p.traitement_id
                                            JOIN
                                                TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                                            JOIN
                                                PlanningDetails pdl ON p.planning_id = pdl.planning_id 
                                            JOIN
                                                Facture f ON pdl.planning_detail_id = f.planning_detail_id
                                            WHERE
                                                c.client_id = %s
                                            AND
                                                tt.typeTraitement = %s
                                            ORDER BY 
                                                pdl.date_planification""", (client_id,traitement))

                    resultat = await cursor.fetchall()

                    for row in resultat:
                        date, montant, etat = row
                        factures.append((date, format_montant(montant), etat))

                        if etat == 'Payé':
                            total_paye += montant
                        else:
                            total_non_paye += montant
                    return factures, format_montant(total_paye), format_montant(total_non_paye)
                except Exception as e:
                    logger.error(f"❌ Erreur get_facture_id: {e}", exc_info=True)

    async def verify_user(self, username):
        """Vérifie si un utilisateur existe - retourne toutes les colonnes nécessaires."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                logger.debug(f"🔍 Vérification utilisateur: {username}")
                await cursor.execute(
                    "SELECT id_compte, nom, prenom, email, username, password, type_compte FROM Account WHERE username = %s", (username,)
                )
                result = await cursor.fetchone()
                return result

    async def get_all_user(self):
        """Récupère tous les non-administrateurs."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    logger.debug("📅 Récupération tous utilisateurs")
                    await cursor.execute(
                        "SELECT id_compte, username, email, type_compte FROM Account WHERE type_compte != 'Administrateur' ORDER BY username ASC"
                    )
                    resultat = await cursor.fetchall()
                    logger.info(f"✅ {len(resultat)} utilisateurs récupérés")
                    return resultat
                except Exception as e:
                    logger.error(f"❌ Erreur get_all_user: {e}", exc_info=True)
                    return []

    async def get_current_user(self, id_compte):
        """Récupère l'utilisateur courant par ID."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    logger.debug(f"🔍 Récupération utilisateur ID={id_compte}")
                    await cursor.execute(
                        "SELECT id_compte, nom, prenom, email, username, type_compte FROM Account WHERE id_compte = %s",
                        (id_compte,)
                    )
                    current = await cursor.fetchone()
                    return current
                except Exception as e:
                    logger.error(f"❌ Erreur get_current_user: {e}", exc_info=True)
                    return None

    async def get_user(self, username):
        """Récupère un utilisateur par username."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    logger.debug(f"🔍 Récupération utilisateur: {username}")
                    await cursor.execute(
                        "SELECT id_compte, nom, prenom, email, username, password, type_compte FROM Account WHERE username = %s",
                        (username,)
                    )
                    current = await cursor.fetchone()
                    return current
                except Exception as e:
                    logger.error(f"❌ Erreur get_user: {e}", exc_info=True)
                    return None

    async def create_contrat(self, client_id,numero_contrat,  date_contrat, date_debut, date_fin, duree, duree_contrat, categorie,
                             max_retries=3):
        logger.info(f"📋 Création contrat - client_id={client_id}, ref={numero_contrat}, categorie={categorie}")
        
        for attempt in range(max_retries + 1):
            try:
                async with self.lock:
                    async with self.pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                "INSERT INTO Contrat (client_id,reference_contrat, date_contrat, date_debut, date_fin, duree_contrat, duree, categorie) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                                (client_id, numero_contrat, date_contrat, date_debut, date_fin, duree, duree_contrat, categorie)
                            )
                            await conn.commit()
                            contrat_id = cur.lastrowid
                            logger.info(f"✅ Contrat créé - ID={contrat_id}")
                            return contrat_id

            except Exception as e:
                logger.warning(f"⚠️  Tentative {attempt + 1} échouée pour create_contrat: {e}")
                await conn.rollback()

                if attempt == max_retries:
                    logger.error(f"❌ Échec définitif après {max_retries + 1} tentatives pour client_id={client_id}", exc_info=True)
                    raise e

                base_delay = 2 ** attempt
                jitter = random.uniform(0, 0.1 * base_delay)
                delay = base_delay + jitter

                logger.debug(f"Retry dans {delay:.2f}s...")
                await asyncio.sleep(delay)

        return None

    async def create_client(self, nom, prenom, email, telephone, adresse, date_ajout, categorie, axe, nif, stat,
                            max_retries=3):
        for attempt in range(max_retries + 1):
            try:
                async with self.lock:
                    async with self.pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                "INSERT INTO Client (nom, prenom, email, telephone, adresse, nif, stat, date_ajout, categorie, axe) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                                (nom, prenom, email, telephone, adresse, nif, stat, date_ajout, categorie, axe)
                            )
                            await conn.commit()
                            return cur.lastrowid

            except Exception as e:
                logger.warning(f"⚠️  Tentative {attempt + 1} échouée pour create_client: {e}")
                await conn.rollback()

                if attempt == max_retries:
                    logger.error(f"❌ Échec définitif après {max_retries + 1} tentatives pour create_client", exc_info=True)
                    raise e

                base_delay = 2 ** attempt
                jitter = random.uniform(0, 0.1 * base_delay)
                delay = base_delay + jitter

                logger.debug(f"Retry dans {delay:.2f}s...")
                await asyncio.sleep(delay)

        return None

    async def get_all_client(self, limit=5000):
        """Récupère tous les clients avec leur date de contrat le plus récent."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    logger.info(f"📋 Récupération tous clients (limite: {limit})")
                    await cur.execute(f"""
                        SELECT c.client_id, 
                               CONCAT(c.nom, ' ', c.prenom) AS nom_complet,
                               c.email, 
                               c.adresse,
                               COALESCE(MAX(co.date_contrat), '') AS date_contrat
                        FROM Client c
                        LEFT JOIN Contrat co ON c.client_id = co.client_id
                        GROUP BY c.client_id, c.nom, c.prenom, c.email, c.adresse
                        ORDER BY c.nom ASC 
                        LIMIT {int(limit)}
                    """)
                    result = await cur.fetchall()
                    logger.info(f"✅ {len(result)} clients récupérés")
                    return result
                except Exception as e:
                    logger.error(f"❌ Erreur get_all_client: {e}", exc_info=True)
                    return []

    async def typetraitement(self, categorie, type, max_retries=3):
        for attempt in range(max_retries + 1):
            try:
                async with self.lock:
                    async with self.pool.acquire() as conn:
                        async with conn.cursor() as cursor:
                            await cursor.execute(
                                "INSERT INTO TypeTraitement (categorieTraitement, typeTraitement) VALUES (%s, %s)",
                                (categorie, type)
                            )
                            await conn.commit()
                            return cursor.lastrowid

            except Exception as e:
                logger.warning(f"⚠️  Tentative {attempt + 1} échouée pour create_type_traitement: {e}")
                await conn.rollback()

                if attempt == max_retries:
                    logger.error(f"❌ Échec définitif après {max_retries + 1} tentatives pour create_type_traitement", exc_info=True)
                    raise e

                base_delay = 2 ** attempt
                jitter = random.uniform(0, 0.1 * base_delay)
                delay = base_delay + jitter

                logger.debug(f"Retry dans {delay:.2f}s...")
                await asyncio.sleep(delay)

        return None

    async def creation_traitement(self, contrat_id, id_type_traitement, max_retries=3):
        async with self.lock:
            # Boucle de retry
            for attempt in range(max_retries):
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        try:
                            await conn.begin()
                            await cur.execute("""
                                INSERT INTO Traitement (contrat_id, id_type_traitement) 
                                VALUES (%s, %s)
                            """, (contrat_id, id_type_traitement))

                            await conn.commit()
                            print(f"✅ Traitement créé avec succès, ID: {cur.lastrowid}")
                            return cur.lastrowid

                        except Exception as e:
                            await conn.rollback()
                            print(f'creation_traitement tentative {attempt + 1}/{max_retries}: {e}')

                            # Erreurs retryables
                            retryable_errors = [
                                "Record has changed",
                                "Deadlock found",
                                "Connection lost",
                                "Lost connection to MySQL server",
                                "MySQL server has gone away"
                            ]

                            is_retryable = any(error in str(e) for error in retryable_errors)

                            if is_retryable and attempt < max_retries - 1:
                                wait_time = 0.1 * (2 ** attempt)  # Backoff exponentiel
                                print(f"🔄 Retry dans {wait_time} seconde...")
                                await asyncio.sleep(wait_time)
                                continue

                            # Dernière tentative ou erreur non-retryable
                            print("🚫 Abandon, erreur finale")
                            raise e

    async def create_planning(self, traitement_id, date_debut, mois_debut, mois_fin, redondance, date_fin,
                              max_retries=3):

        for attempt in range(max_retries):
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    try:
                        await conn.begin()
                        await cur.execute("""
                            INSERT INTO Planning (traitement_id, date_debut_planification, mois_debut, mois_fin, redondance, date_fin_planification) 
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (traitement_id, date_debut, mois_debut, mois_fin, redondance, date_fin))

                        await conn.commit()
                        planning_id = cur.lastrowid

                        print(f"✅ Planning créé avec succès, ID: {planning_id}")
                        return planning_id

                    except Exception as e:
                        await conn.rollback()
                        print(f'create_planning tentative {attempt + 1}/{max_retries}: {e}')

                        # Erreurs retryables
                        retryable_errors = [
                            "Record has changed",
                            "Deadlock found",
                            "Connection lost",
                            "Lost connection to MySQL server",
                            "MySQL server has gone away"
                        ]

                        is_retryable = any(error in str(e) for error in retryable_errors)

                        if is_retryable and attempt < max_retries - 1:
                            wait_time = 0.1 * (2 ** attempt)  # Backoff exponentiel
                            print(f"🔄 Retry dans {wait_time} seconde...")
                            await asyncio.sleep(wait_time)
                            continue

                        # Dernière tentative ou erreur non-retryable
                        print("🚫 Abandon, erreur finale")
                        raise e

    async def traitement_en_cours(self, year, month):
        async with self.lock:
            async with self.pool.acquire() as conn:
                traitements = []
                async with conn.cursor() as curseur:
                    try:
                        await curseur.execute(
                            """SELECT c.nom AS nom_client,
                                      tt.typeTraitement AS type_traitement,
                                      pdl.statut,
                                      pdl.date_planification,
                                      p.planning_id,
                                      c.axe
                                   FROM
                                      Client c
                                   JOIN
                                      Contrat co ON c.client_id = co.client_id
                                   JOIN
                                      Traitement t ON co.contrat_id = t.contrat_id
                                   JOIN
                                      TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                                   JOIN
                                      Planning p ON t.traitement_id = p.traitement_id
                                   JOIN
                                      PlanningDetails pdl ON p.planning_id = pdl.planning_id
                                   WHERE
                                      MONTH(pdl.date_planification) = %s
                                   AND
                                      YEAR(pdl.date_planification) = %s
                                   AND
                                      pdl.statut != 'Classé sans suite'
                                   ORDER BY
                                      pdl.date_planification; """,
                            (month,year)
                        )
                        rows = await curseur.fetchall()
                        for nom, traitement, statut, date_str, idplanning, axe in rows:
                            traitements.append({
                                "traitement": f'{traitement.partition("(")[0].strip()} pour {nom}',
                                "date": date_str,
                                'etat': statut,
                                'axe': axe
                            })
                        logger.info(f"✅ Traitements en cours récupérés - {len(traitements)} items")
                        return traitements
                    except Exception as e:
                        logger.error(f"❌ Erreur traitement_en_cours: {e}", exc_info=True)
                        return []

    async def traitement_prevision(self, year, month):
        """✅ Récupère les traitements prévus (à venir) pour un mois spécifique"""
        async with self.lock:
            async with self.pool.acquire() as conn:
                traitements = []
                async with conn.cursor() as curseur:
                    try:
                        # ✅ CORRECTION: Requête pour les traitements à venir (futurs plannings)
                        await curseur.execute(
                            """SELECT c.nom AS nom_client,
                                      tt.typeTraitement AS type_traitement,
                                      pdl.statut,
                                      MIN(pdl.date_planification) AS min_date,
                                      p.planning_id,
                                      c.axe
                                   FROM
                                      Client c
                                   JOIN
                                      Contrat co ON c.client_id = co.client_id
                                   JOIN
                                      Traitement t ON co.contrat_id = t.contrat_id
                                   JOIN
                                      TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                                   JOIN
                                      Planning p ON t.traitement_id = p.traitement_id
                                   JOIN
                                      PlanningDetails pdl ON p.planning_id = pdl.planning_id
                                   WHERE p.planning_id NOT IN (
                                        SELECT DISTINCT p.planning_id
                                        FROM Planning p
                                        JOIN PlanningDetails pdl ON p.planning_id = pdl.planning_id
                                        WHERE MONTH(pdl.date_planification) = %s
                                        AND YEAR(pdl.date_planification) = %s
                                   )
                                   AND pdl.date_planification >= CURDATE()
                                   AND p.redondance != 1
                                   AND pdl.statut != 'Classé sans suite'
                                   GROUP BY p.planning_id
                                   ORDER BY min_date""",
                            (month, year)
                        )
                        rows = await curseur.fetchall()
                        for nom, traitement, statut, date_str, idplanning, axe in rows:
                            traitements.append({
                                "traitement": f'{traitement.partition("(")[0].strip()} pour {nom}',
                                "date": date_str,
                                'etat': statut,
                                'axe': axe
                            })
                        logger.info(f"✅ Traitements à venir récupérés - {len(traitements)} items")
                        return traitements
                    except Exception as e:
                        logger.error(f"❌ Erreur traitement_prevision: {e}", exc_info=True)
                        return []

    async def create_planning_details(self, planning_id, date, statut='À venir', max_retries=3):
        for attempt in range(max_retries + 1):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cur:
                        try:
                            await conn.begin()
                            await cur.execute(
                                "INSERT INTO PlanningDetails (planning_id, date_planification, statut) VALUES (%s, %s, %s)",
                                (planning_id, date, statut)
                            )
                            await conn.commit()
                            return cur.lastrowid
                        except Exception as e:
                            await conn.rollback()

            except Exception as e:
                print(f"Tentative {attempt + 1} échouée pour create_planning_details: {e}")
                await conn.rollback()

                if attempt == max_retries:
                    print(f"Échec définitif après {max_retries + 1} tentatives")
                    raise e

                base_delay = 2 ** attempt  # 1s, 2s, 4s, 8s...
                jitter = random.uniform(0, 0.1 * base_delay)
                delay = base_delay + jitter

                print(f"Retry dans {delay:.2f}s...")
                await asyncio.sleep(delay)

        return None
    
    async def get_all_planning(self, limit=5000):
        """Récupère tous les plannings avec LIMIT et avec logging."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    logger.info(f"📅 Récupération tous plannings (limite: {limit})")
                    await cursor.execute(
                        f"""SELECT c.nom AS nom_client,
                                  tt.typeTraitement AS type_traitement,
                                  p.redondance ,
                                  p.planning_id
                           FROM
                              Client c
                           JOIN
                              Contrat co ON c.client_id = co.client_id
                           JOIN
                              Traitement t ON co.contrat_id = t.contrat_id
                           JOIN
                              Planning p ON t.traitement_id = p.traitement_id
                           JOIN
                              TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                           ORDER BY
                              c.nom ASC
                           LIMIT {int(limit)}"""
                    )
                    result = await cursor.fetchall()
                    logger.info(f"✅ {len(result)} plannings récupérés")
                    return result
                except Exception as e:
                    logger.error(f"❌ Erreur récupération plannings: {e}", exc_info=True)
                    return []

    async def get_details(self, planning_id):
        """Récupère les détails d'un planning spécifique."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    logger.debug(f"🔍 Récupération détails planning_id={planning_id}")
                    await cursor.execute("""SELECT
                                                date_planification, statut
                                            FROM
                                                PlanningDetails
                                            WHERE
                                                planning_id = %s""", (planning_id,))
                    result = await cursor.fetchall()
                    logger.debug(f"✅ {len(result)} détails trouvés")
                    return result
                except Exception as e:
                    logger.error(f"❌ Erreur récupération détails: {e}", exc_info=True)
                    return []


    async def get_info_planning(self, planning_id, date, max_retries=3):
        for attempt in range(max_retries + 1):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.cursor() as cursor:
                        try:
                            await cursor.execute("""SELECT c.nom AS nom_client,
                                                      tt.typeTraitement AS type_traitement,
                                                      p.duree_traitement,
                                                      co.date_debut,
                                                      co.date_fin,
                                                      c.client_id,
                                                      f.facture_id,
                                                      p.planning_id,
                                                      pdl.planning_detail_id,
                                                      pdl.date_planification

                                                FROM
                                                    Client c
                                                JOIN
                                                    Contrat co ON c.client_id = co.client_id
                                                JOIN
                                                    Traitement t ON co.contrat_id = t.contrat_id
                                                JOIN
                                                    Planning p ON t.traitement_id = p.traitement_id
                                                JOIN
                                                    TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                                                JOIN
                                                    PlanningDetails pdl ON p.planning_id = pdl.planning_id
                                                JOIN
                                                    Facture f ON pdl.planning_detail_id = f.planning_detail_id
                                                WHERE
                                                    p.planning_id = %s AND pdl.date_planification = %s""",
                                                 (planning_id, date))
                            resultat = await cursor.fetchone()
                            return resultat
                        except Exception as e:
                            print('get_info', e)

            except Exception as e:
                print(f'tentive {attempt +1 } échouée pour get info planning: {e}')

                await conn.rollback()
                if attempt == max_retries:
                    print(f"Échec définitif après {max_retries + 1} tentatives")
                raise e

                base_delay = 2 ** attempt
                jitter = random.uniform(0, 0.1 * base_delay)
                delay = base_delay + jitter

                print(f"Retry dans {delay:.2f}s...")
                await asyncio.sleep(delay)

        return None

    async def modifier_date_signalement(self,planning_id, planning_detail_id, option, interval):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    avancement = """UPDATE PlanningDetails 
                                    SET 
                                        date_planification =DATE_SUB(date_planification, INTERVAL %s MONTH)
                                    WHERE
                                        planning_id = %s
                                    AND
                                        planning_detail_id >= %s"""

                    décalage = """UPDATE PlanningDetails 
                                  SET 
                                     date_planification =DATE_ADD(date_planification, INTERVAL %s MONTH)
                                  WHERE
                                     planning_id = %s
                                  AND
                                     planning_detail_id >= %s"""

                    requete = décalage if option == 'décalage' else avancement
                    await conn.begin()
                    await cur.execute(requete, (interval, planning_id, planning_detail_id))
                    await conn.commit()

                except Exception as e:
                    await conn.rollback()
                    print('Changement de date', e)

    async def modifier_date(self, planning_detail_id, new_date):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    await cur.execute('''UPDATE PlanningDetails
                                   SET
                                      date_planification = %s
                                   WHERE
                                      planning_detail_id = %s''', (new_date, planning_detail_id))
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()

    async def create_remarque(self,client, planning_details, facture, contenu, probleme, action):
        logger.info(f"💬 Création remarque - client_id={client}, planning_detail_id={planning_details}, facture_id={facture}")
        
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    await cur.execute(
                    "INSERT INTO Remarque (client_id, planning_detail_id, facture_id, contenu, issue, action) VALUES (%s, %s, %s, %s,%s, %s)",
                    (client, planning_details, facture, contenu, probleme, action))
                    await conn.commit()
                    logger.info(f"✅ Remarque créée - client_id={client}")
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"❌ Erreur création remarque: {e}", exc_info=True)

    async def get_historique_remarque(self, planning_id, limit=1000):
        """Récupère l'historique des remarques pour un planning avec LIMIT."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    logger.info(f"📜 Récupération historique remarques - planning_id={planning_id}")
                    await cur.execute(
                        f""" SELECT
                                pdl.date_planification AS Date, 
                                COALESCE(NULLIF(r.contenu, ''), 'Aucune remarque') AS Remarque, 
                                COALESCE(sa.motif, 'Aucun') AS Avancement, 
                                COALESCE(sd.motif, 'Aucun') AS Décalage, 
                                COALESCE(NULLIF(r.issue, ''), 'Aucun problème') AS probleme, 
                                COALESCE(NULLIF(r.action, ''), 'Aucune action') AS action
                            FROM
                               Client c
                            JOIN
                               Contrat co ON c.client_id = co.client_id
                            JOIN
                               Traitement t ON co.contrat_id = t.contrat_id
                            JOIN
                               TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                            JOIN
                               Planning p ON t.traitement_id = p.traitement_id
                            JOIN
                               PlanningDetails pdl ON p.planning_id = pdl.planning_id
                            LEFT JOIN
                               Remarque r ON pdl.planning_detail_id = r.planning_detail_id
                            LEFT JOIN
                                Signalement sa ON r.planning_detail_id = sa.planning_detail_id AND sa.type = 'Avancement'
                            LEFT JOIN
                                Signalement sd ON r.planning_detail_id = sd.planning_detail_id AND sd.type = 'Décalage'
                            WHERE
                                p.planning_id = %s
                            LIMIT {int(limit)};""", (planning_id,))
                    result = await cur.fetchall()
                    logger.info(f"✅ {len(result)} remarques récupérées")
                    return result

                except Exception as e:
                    logger.error(f"❌ Erreur historique remarque: {e}", exc_info=True)
                    return []

    async def update_etat_facture(self, facture, reference, payement, etablissement, date, num_cheque):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    await cur.execute(
                        """ UPDATE Facture 
                            SET reference_facture = %s,
                                etablissement_payeur = %s, 
                                date_cheque = %s, 
                                numero_cheque = %s, 
                                etat = %s, 
                                mode = %s 
                            WHERE facture_id = %s ;""", (reference, etablissement, date, num_cheque, 'Payé', payement, facture))
                    await conn.commit()
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"❌ Erreur mise à jour facture: {e}", exc_info=True)

    async def update_etat_planning(self, details_id):
        """✅ Marque un planning detail comme 'Effectué' avec retour du statut"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await conn.begin()
                    # ✅ CORRECTION: Mettre à jour le statut
                    await cur.execute(
                        "UPDATE PlanningDetails SET statut = %s WHERE planning_detail_id = %s",
                        ('Effectué', details_id)
                    )
                    # ✅ CORRECTION: Vérifier que la mise à jour s'est bien faite
                    rows_affected = cur.rowcount
                    if rows_affected == 0:
                        logger.warning(f"⚠️ Aucune ligne trouvée avec planning_detail_id={details_id}")
                        await conn.rollback()
                        return False
                    
                    await conn.commit()
                    logger.info(f"✅ Planning detail {details_id} marqué comme 'Effectué'")
                    return True
                except Exception as e:
                    await conn.rollback()
                    logger.error(f"❌ Erreur mise à jour planning detail {details_id}: {e}", exc_info=True)
                    return False

    async def verify_planning_status(self, details_id):
        """✅ Vérifie que le statut d'un planning detail a bien été mis à jour"""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(
                        "SELECT statut FROM PlanningDetails WHERE planning_detail_id = %s",
                        (details_id,)
                    )
                    result = await cur.fetchone()
                    if result:
                        statut = result[0]
                        logger.info(f"✅ Planning detail {details_id} a le statut: {statut}")
                        return statut
                    else:
                        logger.warning(f"⚠️ Planning detail {details_id} non trouvé")
                        return None
                except Exception as e:
                    logger.error(f"❌ Erreur vérification statut planning {details_id}: {e}", exc_info=True)
                    return None

    async def creer_signalment(self,planning_detail, motif, option):
        async with self.pool.acquire() as conn:
            try:
                async with conn.cursor() as cursor:
                    await conn.begin()
                    await cursor.execute("""INSERT INTO Signalement (planning_detail_id, motif, type) VALUES (%s, %s, %s)""",
                                   (planning_detail, motif, option))
                    await conn.commit()
            except Exception as e:
                await conn.rollback()
                logger.error(f"❌ Erreur création signalement: {e}", exc_info=True)

    async def get_historic_par_client(self, nom, limit=1000):
        """Récupère l'historique par client - requête corrigée avec GROUP BY valide."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    logger.info(f"📊 Récupération historique client - nom={nom}")
                    await cursor.execute(f""" SELECT c.nom,
                                                co.duree,
                                                tt.typeTraitement,
                                                count(r.remarque_id) as nb_remarques,
                                                p.planning_id
                                             FROM
                                                Client c
                                             JOIN
                                                Contrat co ON c.client_id = co.client_id
                                             JOIN
                                                Traitement t ON co.contrat_id = t.contrat_id
                                             JOIN
                                                TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                                             JOIN
                                                Planning p ON t.traitement_id = p.traitement_id
                                             JOIN
                                                PlanningDetails pdl ON p.planning_id = pdl.planning_id
                                             LEFT JOIN
                                                Remarque r ON pdl.planning_detail_id = r.planning_detail_id
                                             WHERE
                                                c.nom = %s
                                             GROUP BY
                                                c.client_id, c.nom, co.duree, tt.typeTraitement, p.planning_id
                                             LIMIT {int(limit)}
                                                """, (nom,))
                    result = await cursor.fetchall()
                    logger.info(f"✅ {len(result)} résultats trouvés pour client {nom}")
                    return result
                except Exception as e:
                    logger.error(f"❌ Erreur historique par client: {e}", exc_info=True)
                    return []

    async def get_historic(self, categorie, limit=1000):
        """Récupère l'historique par catégorie - requête corrigée."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    logger.info(f"📈 Récupération historique par catégorie - {categorie}")
                    await cursor.execute(f""" SELECT c.nom,
                                                co.duree,
                                                tt.typeTraitement,
                                                count(r.remarque_id) as nb_remarques,
                                                p.planning_id
                                             FROM
                                                Client c
                                             JOIN
                                                Contrat co ON c.client_id = co.client_id
                                             JOIN
                                                Traitement t ON co.contrat_id = t.contrat_id
                                             JOIN
                                                TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                                             JOIN
                                                Planning p ON t.traitement_id = p.traitement_id
                                             JOIN
                                                PlanningDetails pdl ON p.planning_id = pdl.planning_id
                                             LEFT JOIN
                                                Remarque r ON pdl.planning_detail_id = r.planning_detail_id
                                             WHERE
                                                tt.categorieTraitement = %s
                                             GROUP BY
                                                c.client_id, c.nom, co.duree, tt.typeTraitement, p.planning_id
                                             LIMIT {int(limit)}
                                                """, (categorie,))
                    result = await cursor.fetchall()
                    logger.info(f"✅ {len(result)} résultats trouvés pour catégorie {categorie}")
                    return result
                except Exception as e:
                    logger.error(f"❌ Erreur historique par catégorie: {e}", exc_info=True)
                    return []
                    
    async def get_current_contrat(self, client, date, traitement):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    logger.debug(f"🔍 get_current_contrat - {client}, {date}, {traitement}")
                    await cursor.execute("""SELECT c.client_id AS id,
                                  c.nom AS nom_client,
                                  c.prenom AS prenom_client,
                                  c.categorie AS categorie,
                                  co.date_contrat,
                                  tt.typeTraitement AS type_traitement,
                                  co.duree AS duree_contrat,
                                  co.date_debut AS debut_contrat,
                                  co.date_fin AS fin_contrat,
                                  c.email,
                                  c.adresse,
                                  c.axe,
                                  c.telephone,
                                  p.planning_id,
                                  f.facture_id,
                                  c.nif,
                                  c.stat
                           FROM
                              Client c
                           JOIN
                              Contrat co ON c.client_id = co.client_id
                           JOIN
                              Traitement t ON co.contrat_id = t.contrat_id
                           JOIN
                              TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                           JOIN
                               Planning p ON t.traitement_id = p.traitement_id
                           JOIN
                               PlanningDetails pld ON p.planning_id = pld.planning_id
                           JOIN
                               Facture f ON pld.planning_detail_id = f.planning_detail_id
                           WHERE
                              c.nom = %s AND co.date_contrat = %s AND tt.typeTraitement = %s; """, (client, date, traitement))
                    resultat = await cursor.fetchone()
                    if resultat:
                        logger.info(f"✅ Contrat trouvé - {resultat[1]}")
                    return resultat
                except Exception as e:
                    logger.error(f"❌ Erreur get_current_contrat: {e}", exc_info=True)
                    return None

    async def delete_client(self, id_contrat):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    logger.info(f"📝 Suppression client - id={id_contrat}")
                    await conn.begin() #commencer une transaction
                    await cursor.execute("""DELETE FROM Client where client_id = %s""", (id_contrat,))
                    await conn.commit()
                    logger.info(f"✅ Client supprimé - id={id_contrat}")
                except Exception as e:
                    await conn.rollback() #rollback en cas d'erreur
                    logger.error(f"❌ Erreur delete_client: {e}", exc_info=True)
                    print("Delete",e)

    async def get_latest_contract_date_for_client(self, client_id):
        """Récupère la date du contrat ACTIF/PLUS RÉCENT du client par client_id."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    logger.debug(f"🔍 Recherche dernier contrat pour client_id: {client_id}")
                    await cursor.execute("""
                        SELECT co.date_contrat
                        FROM Contrat co
                        WHERE co.client_id = %s
                        ORDER BY co.date_contrat DESC
                        LIMIT 1
                    """, (client_id,))
                    resultat = await cursor.fetchone()
                    if resultat:
                        logger.debug(f"✅ Date contrat trouvée: {resultat[0]}")
                        return resultat[0]
                    else:
                        logger.warning(f"⚠️ Aucun contrat trouvé pour client_id {client_id}")
                        return None
                except Exception as e:
                    logger.error(f"❌ Erreur get_latest_contract_date: {e}", exc_info=True)
                    return None

    async def get_current_client(self, client_name, date):
        """Récupère les infos client avec tous les JOINs nécessaires par nom du client et date de contrat."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    logger.debug(f"🔍 Récupération client: {client_name}, date: {date}")
                    
                    # ✅ Requête simplifiée: juste Client + Contrat + TypeTraitement (si existe)
                    # Sans les Planning/PlanningDetails/Facture qui causent des NULL
                    await cursor.execute("""SELECT 
                                  c.client_id AS id,
                                  c.nom AS nom_client,
                                  c.prenom AS prenom_client,
                                  c.categorie AS categorie,
                                  co.date_contrat,
                                  COALESCE(tt.typeTraitement, 'Non défini') AS type_traitement,
                                  co.duree AS duree_contrat,
                                  co.date_debut AS debut_contrat,
                                  co.date_fin AS fin_contrat,
                                  c.email,
                                  c.adresse,
                                  c.axe,
                                  c.telephone,
                                  NULL AS planning_id,
                                  NULL AS facture_id,
                                  c.nif,
                                  c.stat
                           FROM
                              Client c
                           JOIN
                              Contrat co ON c.client_id = co.client_id
                           LEFT JOIN
                              Traitement t ON co.contrat_id = t.contrat_id
                           LEFT JOIN
                              TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                           WHERE
                              c.nom = %s AND co.date_contrat = %s
                           LIMIT 1; """, (client_name, date))
                    resultat = await cursor.fetchone()
                    if resultat:
                        logger.debug(f"✅ Client trouvé: {resultat[1]}")
                    else:
                        logger.warning(f"⚠️ Client '{client_name}' avec contrat du {date} introuvable")
                    return resultat
                except Exception as e:
                    logger.error(f"❌ Erreur get_current_client: {e}", exc_info=True)
                    return None
                    
    async def get_client(self):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    await cursor.execute(
                        """SELECT DISTINCT c.nom ,
                                  co.date_contrat,
                                  tt.typeTraitement,
                                  GROUP_CONCAT(DISTINCT p.redondance),
                                  co.date_debut ,
                                  co.date_fin ,
                                  c.categorie ,
                                  count(t.traitement_id),
                                  c.client_id
                           FROM
                              Client c
                           JOIN
                              Contrat co ON c.client_id = co.client_id
                           JOIN
                              Traitement t ON co.contrat_id = t.contrat_id
                           JOIN
                              TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                           JOIN
                              Planning p ON t.traitement_id = p.traitement_id
                           GROUP BY
                              c.client_id
                           ORDER BY
                              c.nom ASC;"""
                    )
                    result = await cursor.fetchall()
                    return result
                except Exception as e:
                    print(e)
                    
    async def traitement_par_client(self, nom_client_ou_id):
        """Récupère tous les traitements d'un client (par nom ou ID)"""
        async with self.pool.acquire() as conn :
            async with conn.cursor() as cursor:
                try:
                    # ✅ CORRECTION: Accepter SOIT un nom (string) SOIT un ID (int)
                    if isinstance(nom_client_ou_id, str):
                        # Si c'est un string, chercher par nom
                        logger.debug(f"🔍 Traitement par client - nom='{nom_client_ou_id}'")
                        sql = """SELECT c.nom AS nom_client,
                                        co.date_contrat,
                                        tt.typeTraitement AS type_traitement,
                                        co.duree_contrat AS duree_contrat,
                                        co.date_debut AS debut_contrat,
                                        co.date_fin AS fin_contrat,
                                        c.categorie AS categorie,
                                        p.redondance
                                 FROM
                                    Client c
                                 JOIN
                                    Contrat co ON c.client_id = co.client_id
                                 JOIN
                                    Traitement t ON co.contrat_id = t.contrat_id
                                 JOIN
                                    TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                                 JOIN
                                    Planning p ON t.traitement_id = p.traitement_id
                                 WHERE
                                    c.nom = %s;"""
                        param = nom_client_ou_id
                    else:
                        # Si c'est un nombre, chercher par ID
                        logger.debug(f"🔍 Traitement par client - client_id={nom_client_ou_id}")
                        sql = """SELECT c.nom AS nom_client,
                                        co.date_contrat,
                                        tt.typeTraitement AS type_traitement,
                                        co.duree_contrat AS duree_contrat,
                                        co.date_debut AS debut_contrat,
                                        co.date_fin AS fin_contrat,
                                        c.categorie AS categorie,
                                        p.redondance
                                 FROM
                                    Client c
                                 JOIN
                                    Contrat co ON c.client_id = co.client_id
                                 JOIN
                                    Traitement t ON co.contrat_id = t.contrat_id
                                 JOIN
                                    TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                                 JOIN
                                    Planning p ON t.traitement_id = p.traitement_id
                                 WHERE
                                    c.client_id = %s;"""
                        param = nom_client_ou_id
                    
                    await cursor.execute(sql, (param,))
                    result = await cursor.fetchall()
                    logger.info(f"✅ Traitements trouvés - {len(result)} items")
                    return result
                except Exception as e:
                    logger.error(f"❌ Erreur traitement_par_client: {e}", exc_info=True)
                    return []

    import asyncio
    import random
    from typing import Optional

    async def create_facture(self, planning_detail_id, montant, date, axe, etat='Non payé', max_retries=3):
        """
        Crée une facture avec retry automatique et backoff exponentiel

        Args:
            planning_detail_id: ID du détail de planning
            montant: Montant de la facture
            date: Date de traitement
            axe: Axe de la facture
            etat: État de la facture (défaut: 'Non payé')
            max_retries: Nombre maximum de tentatives (défaut: 3)

        Returns:
            ID de la facture créée ou None en cas d'échec
        """
        logger.info(f"📝 Création facture - detail_id={planning_detail_id}, montant={montant}, axe={axe}")
        
        for attempt in range(max_retries + 1):
            try:
                async with self.lock:
                    async with self.pool.acquire() as conn:
                        async with conn.cursor() as cur:
                            await conn.begin()
                            await cur.execute(
                                "INSERT INTO Facture (planning_detail_id, montant, date_traitement, etat, axe) VALUES (%s, %s, %s, %s, %s)",
                                (planning_detail_id, montant, date, etat, axe)
                            )
                            await conn.commit()
                            facture_id = cur.lastrowid
                            logger.info(f"✅ Facture créée - ID={facture_id}")
                            return facture_id

            except Exception as e:
                logger.warning(f"⚠️  Tentative {attempt + 1} échouée pour create_facture: {e}")
                await conn.rollback()

                # Si c'est la dernière tentative, on lève l'exception
                if attempt == max_retries:
                    logger.error(f"❌ Échec définitif après {max_retries + 1} tentatives pour facture detail_id={planning_detail_id}", exc_info=True)
                    raise e

                # Calcul du délai avec backoff exponentiel + jitter
                base_delay = 2 ** attempt  # 1s, 2s, 4s, 8s...
                jitter = random.uniform(0, 0.1 * base_delay)  # Ajoute un peu d'aléatoire
                delay = base_delay + jitter

                logger.debug(f"Retry dans {delay:.2f}s...")
                await asyncio.sleep(delay)

        return None

    async def un_jour(self, contrat_id):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await conn.begin()
                await cur.execute(
                    "UPDATE Contrat SET duree_contrat = 1 WHERE contrat_id = %s",
                    (contrat_id, ))
                await conn.commit()

    async def get_all_client_name(self, limit=5000):
        """Récupère tous les noms de clients avec LIMIT pour éviter les surcharges."""
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    logger.info(f"📋 Récupération liste clients (limite: {limit})")
                    await cur.execute(
                        f"""SELECT DISTINCT CONCAT(nom , ' ', prenom) as full_name From Client LIMIT {int(limit)}"""
                    )
                    result = await cur.fetchall()
                    logger.info(f"✅ {len(result)} clients récupérés")
                    return result
                except Exception as e:
                    logger.error(f"❌ Erreur récupération clients: {e}", exc_info=True)
                    return []

    async def get_facture_id(self, client_id, date):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    logger.debug(f"🔍 get_facture_id - client_id={client_id}, date={date}")
                    await cursor.execute(
                        """SELECT f.facture_id
                           FROM Facture f
                           JOIN PlanningDetails pd ON f.planning_detail_id = pd.planning_detail_id
                           JOIN Planning p ON pd.planning_id = p.planning_id
                           JOIN Traitement t ON p.traitement_id = t.traitement_id
                           JOIN Contrat c ON t.contrat_id = c.contrat_id
                           WHERE c.client_id = %s
                           AND pd.date_planification = %s;""", (client_id, date)
                    )
                    result = await cursor.fetchone()
                    logger.debug(f"✅ Facture trouvée: {result}")
                    return result
                except Exception as e:
                    logger.error(f"❌ Erreur get_facture_id: {e}", exc_info=True)
                    return None

    async def majMontantEtHistorique(self, facture_id: int, old_amount: float, new_amount: float,
                                     changed_by: str = 'System'):
        """
        Met à jour le montant d'une facture et enregistre l'ancien/nouveau montant
        dans la table d'historique.
        ✅ CORRECTION: Change AUSSI tous les prix futurs du MÊME traitement/client
        """
        logger.info(f"📝 Maj montant facture - id={facture_id}, {old_amount} → {new_amount}")
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    # Commencer une transaction explicite
                    await conn.begin()

                    # 0. Récupérer la facture pour connaître la date et le traitement
                    await cursor.execute("""
                        SELECT f.facture_id, pdl.date_planification, pdl.planning_detail_id, p.planning_id
                        FROM Facture f
                        JOIN PlanningDetails pdl ON f.planning_detail_id = pdl.planning_detail_id
                        JOIN Planning p ON pdl.planning_id = p.planning_id
                        WHERE f.facture_id = %s
                    """, (facture_id,))
                    current_facture = await cursor.fetchone()
                    
                    if not current_facture:
                        raise ValueError(f"Facture {facture_id} non trouvée")
                    
                    current_date = current_facture[1]
                    planning_id = current_facture[3]
                    
                    # 1. Mettre à jour le montant de LA facture actuelle
                    update_query = "UPDATE Facture SET montant = %s WHERE facture_id = %s;"
                    await cursor.execute(update_query, (new_amount, facture_id))

                    # 2. Insérer l'entrée d'historique pour la facture actuelle
                    insert_history_query = """
                        INSERT INTO Historique_prix
                        (facture_id, old_amount, new_amount, change_date, changed_by)
                        VALUES (%s, %s, %s, %s, %s);
                    """
                    await cursor.execute(insert_history_query,
                                         (facture_id, old_amount, new_amount, datetime.datetime.now(), changed_by))

                    # ✅ CORRECTION: Mettre à jour TOUS les prix futurs du MÊME planning
                    # Récupérer toutes les factures du même planning après cette date
                    await cursor.execute("""
                        SELECT f.facture_id, f.montant
                        FROM Facture f
                        JOIN PlanningDetails pdl ON f.planning_detail_id = pdl.planning_detail_id
                        WHERE pdl.planning_id = %s 
                        AND pdl.date_planification > %s
                    """, (planning_id, current_date))
                    future_factures = await cursor.fetchall()
                    
                    # Mettre à jour chaque facture future
                    for future_facture_id, future_montant in future_factures:
                        await cursor.execute(
                            "UPDATE Facture SET montant = %s WHERE facture_id = %s;",
                            (new_amount, future_facture_id)
                        )
                        # Enregistrer dans l'historique
                        await cursor.execute(
                            insert_history_query,
                            (future_facture_id, future_montant, new_amount, datetime.datetime.now(), f"{changed_by} (update massif)")
                        )
                    
                    logger.info(f"✅ Montant facture mis à jour + {len(future_factures)} factures futures")

                    # Valider la transaction
                    await conn.commit()
                    return True

                except Exception as e:
                    # Annuler la transaction en cas d'erreur
                    await conn.rollback()
                    logger.error(f"❌ Erreur majMontantEtHistorique: {e}", exc_info=True)
                    return False

    #Pour les excels

    async def get_factures_data_for_client_comprehensive(self, client_name: str, start_date: datetime.date = None,
                                                         end_date: datetime.date = None):
        conn = None
        try:
            conn = await self.pool.acquire()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                        SELECT cl.nom                  AS client_nom,
                               COALESCE(cl.prenom, '') AS client_prenom,
                               cl.adresse              AS client_adresse,
                               cl.telephone            AS client_telephone,
                               cl.categorie            AS client_categorie,
                               cl.axe                  AS client_axe,
                               co.contrat_id,
                               co.reference_contrat    AS `Référence Contrat`,
                               co.date_contrat,
                               co.date_debut           AS contrat_date_debut,
                               co.date_fin             AS contrat_date_fin,
                               co.statut_contrat,
                               co.duree                AS contrat_duree_type,
                               f.reference_facture     AS `Numéro Facture`,
                               tt.typeTraitement       AS `Type de Traitement`,
                               pd.date_planification   AS `Date de Planification`,
                               pd.statut               AS `Etat du Planning`,
                               p.redondance            AS `Redondance (Mois)`,
                               f.date_traitement       AS `Date de Facturation`,
                               f.etat                  AS `Etat de Paiement`,
                               f.mode                  AS `Mode de Paiement`,
                               f.date_cheque         AS `Date de Paiement`,
                               f.numero_cheque         AS `Numéro du Chèque`,
                               f.etablissement_payeur   AS `Établissement Payeur`,
                               COALESCE(
                                       (SELECT hp.new_amount
                                        FROM Historique_prix hp
                                        WHERE hp.facture_id = f.facture_id
                                        ORDER BY hp.change_date DESC, hp.history_id DESC
                                        LIMIT 1),
                                       f.montant
                               )                       AS `Montant Facturé`
                        FROM Client cl
                                 JOIN Contrat co ON cl.client_id = co.client_id
                                 JOIN Traitement tr ON co.contrat_id = tr.contrat_id
                                 JOIN TypeTraitement tt ON tr.id_type_traitement = tt.id_type_traitement
                                 JOIN Planning p ON tr.traitement_id = p.traitement_id
                                 INNER JOIN PlanningDetails pd ON p.planning_id = pd.planning_id
                                 INNER JOIN Facture f ON pd.planning_detail_id = f.planning_detail_id
                        WHERE cl.nom = %s
                        """
                params = [client_name]

                if start_date and end_date:
                    query += " AND f.date_traitement BETWEEN %s AND %s"
                    params.append(start_date)
                    params.append(end_date)
                elif start_date:
                    query += " AND f.date_traitement >= %s"
                    params.append(start_date)
                elif end_date:
                    query += " AND f.date_traitement <= %s"
                    params.append(end_date)

                query += " ORDER BY `Date de Planification` ASC, `Date de Facturation` ASC;"

                await cursor.execute(query, tuple(params))
                result = await cursor.fetchall()
                return result
        except Exception as e:
            print(f"Erreur lors de la récupération des données de facture complètes : {e}")
            return []
        finally:
            if conn:
                self.pool.release(conn)


    async def obtenirDataFactureClient(self, client_name: str, year: int, month: int):
        conn = None
        try:
            conn = await self.pool.acquire()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                        SELECT cl.nom                  AS client_nom,
                               COALESCE(cl.prenom, '') AS client_prenom,
                               cl.adresse              AS client_adresse,
                               cl.telephone            AS client_telephone,
                               cl.categorie            AS client_categorie,
                               cl.axe                  AS client_axe,
                               co.reference_contrat    AS `Référence Contrat`,
                               f.reference_facture     AS `Numéro Facture`,
                               f.date_traitement       AS `Date de traitement`,
                               tt.typeTraitement       AS `Traitement (Type)`,
                               pd.statut               AS `Etat traitement`,
                               f.etat                  AS `Etat paiement (Payée ou non)`,
                               f.mode                  AS `Mode de Paiement`,
                               f.date_cheque         AS `Date de Paiement`,
                               f.numero_cheque         AS `Numéro du Chèque`,
                               f.etablissement_payeur   AS `Établissement Payeur`,
                               COALESCE(
                                       (SELECT hp.new_amount
                                        FROM Historique_prix hp
                                        WHERE hp.facture_id = f.facture_id
                                        ORDER BY hp.change_date DESC, hp.history_id DESC
                                        LIMIT 1),
                                       f.montant
                               )                       AS montant_facture
                        FROM Facture f
                                 JOIN PlanningDetails pd ON f.planning_detail_id = pd.planning_detail_id
                                 JOIN Planning p ON pd.planning_id = p.planning_id
                                 JOIN Traitement tr ON p.traitement_id = tr.traitement_id
                                 JOIN TypeTraitement tt ON tr.id_type_traitement = tt.id_type_traitement
                                 JOIN Contrat co ON tr.contrat_id = co.contrat_id
                                 JOIN Client cl ON co.client_id = cl.client_id
                        WHERE cl.nom = %s
                          AND YEAR(f.date_traitement) = %s
                          AND MONTH(f.date_traitement) = %s
                        ORDER BY f.date_traitement;
                        """
                await cursor.execute(query, (client_name, year, month))
                result = await cursor.fetchall()
                logger.info(f"✅ Données factures récupérées - {len(result)} items")
                return result
        except Exception as e:
            logger.error(f"❌ Erreur obtenirDataFactureClient: {e}", exc_info=True)
            return []
        finally:
            if conn:
                self.pool.release(conn)

    async def get_traitements_for_month(self, year: int, month: int):
        conn = None
        try:
            conn = await self.pool.acquire()
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                        SELECT pd.date_planification        AS `Date du traitement`,
                               tt.typeTraitement            AS `Traitement concerné`,
                               tt.categorieTraitement       AS `Catégorie du traitement`,
                               CONCAT(c.nom, ' ', c.prenom) AS `Client concerné`,
                               c.categorie                  AS `Catégorie du client`,
                               c.axe                        AS `Axe du client`,
                               pd.statut                    AS `Etat traitement` -- AJOUT DE CETTE COLONNE
                        FROM PlanningDetails pd
                                 JOIN
                             Planning p ON pd.planning_id = p.planning_id
                                 JOIN
                             Traitement t ON p.traitement_id = t.traitement_id
                                 JOIN
                             TypeTraitement tt ON t.id_type_traitement = tt.id_type_traitement
                                 JOIN
                             Contrat co ON t.contrat_id = co.contrat_id
                                 JOIN
                             Client c ON co.client_id = c.client_id
                        WHERE YEAR(pd.date_planification) = %s
                          AND MONTH(pd.date_planification) = %s
                        ORDER BY pd.date_planification;
                        """
                await cursor.execute(query, (year, month))
                result = await cursor.fetchall()
                return result
        except Exception as e:
            print(f"Erreur lors de la récupération des traitements : {e}")
            return []
        finally:
            if conn:
                self.pool.release(conn)

    #Abrogation contrat
    async def get_planningdetails_id(self, planning_id):
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                try:
                    await cursor.execute("""SELECT pdl.planning_detail_id,pdl.date_planification
                                            FROM PlanningDetails pdl
                                            JOIN Planning p ON pdl.planning_id = p.planning_id
                                            WHERE p.planning_id = %s 
                                            AND pdl.date_planification >= %s;""",
                                         (planning_id, datetime.datetime.today()))
                    result = await cursor.fetchone()
                    return result
                except Exception as e:
                    print('Get details', e)

    async def get_planning_detail_info(self, planning_detail_id: int):
        """
        Récupère les informations détaillées d'un planning_detail spécifique,
        incluant les IDs du planning, traitement et contrat associés.
        Prend le pool de connexions en argument.
        """
        conn = None
        try:
            conn = await self.pool.acquire()  # Obtenir une connexion du pool
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                query = """
                        SELECT pd.planning_detail_id, \
                               pd.planning_id, \
                               pd.date_planification, \
                               pd.statut, \
                               p.traitement_id, \
                               t.contrat_id
                        FROM PlanningDetails pd \
                                 JOIN \
                             Planning p ON pd.planning_id = p.planning_id \
                                 JOIN \
                             Traitement t ON p.traitement_id = t.traitement_id
                        WHERE pd.planning_detail_id = %s; \
                        """
                await cursor.execute(query, (planning_detail_id,))
                result = await cursor.fetchone()
                return result
        except Exception as e:
            print(f"Erreur lors de la récupération des informations du planning_detail {planning_detail_id}: {e}")
            return None
        finally:
            if conn:
                self.pool.release(conn)  # Relâcher la connexion dans le pool

    async def abrogate_contract(self, planning_detail_id: int):
        """
        Abroge un contrat à partir d'une date de résiliation.
        Supprime les traitements futurs et marque le contrat comme 'Terminé'.
        Marque aussi le planning et les PlanningDetails comme 'Classé sans suite'.
        """
        date = datetime.date.today()
        conn = None
        try:
            logger.info(f"📝 Abrogation contrat - planning_detail_id={planning_detail_id}")
            conn = await self.pool.acquire()
            # 1. Récupérer les informations initiales pour obtenir planning_id et contrat_id
            detail_info = await self.get_planning_detail_info(planning_detail_id)
            if not detail_info:
                logger.error(f"❌ Planning detail non trouvé: {planning_detail_id}")
                return False

            current_planning_id = detail_info['planning_id']
            current_contrat_id = detail_info['contrat_id']
            logger.debug(f"🔍 Contrat={current_contrat_id}, Planning={current_planning_id}")

            async with conn.cursor() as cursor:
                await conn.begin()
                
                # 2. Marquer TOUS les PlanningDetails comme 'Classé sans suite' (incluant les passés)
                try:
                    mark_planning_details_query = """
                                                  UPDATE PlanningDetails
                                                  SET statut = 'Classé sans suite'
                                                  WHERE planning_id = %s;
                                                  """
                    await cursor.execute(mark_planning_details_query, (current_planning_id,))
                    marked_count = cursor.rowcount
                    logger.info(f"✅ {marked_count} PlanningDetails marqués comme 'Classé sans suite'")
                except Exception as e:
                    logger.error(f"❌ Erreur marquage PlanningDetails: {e}", exc_info=True)
                    await conn.rollback()
                    return False

                # 3. Marquer tous les PlanningDetails comme 'Classé sans suite'
                try:
                    mark_planning_query = """
                                         UPDATE PlanningDetails
                                         SET statut = 'Classé sans suite'
                                         WHERE planning_id = %s;
                                         """
                    await cursor.execute(mark_planning_query, (current_planning_id,))
                    logger.info(f"✅ Planning marqué comme 'Classé sans suite' - id={current_planning_id}")
                except Exception as e:
                    logger.error(f"❌ Erreur marquage Planning: {e}", exc_info=True)
                    await conn.rollback()
                    return False

                # 4. Mettre à jour le statut du contrat
                try:
                    update_contract_query = """
                                            UPDATE Contrat
                                            SET statut_contrat = 'Terminé', 
                                                date_fin       = %s, 
                                                duree          = 'Déterminée'
                                            WHERE contrat_id = %s; 
                                            """
                    await cursor.execute(update_contract_query, (date, current_contrat_id))
                    logger.info(f"✅ Contrat abrogé - id={current_contrat_id}")
                except Exception as e:
                    logger.error(f"❌ Erreur abrogation contrat: {e}", exc_info=True)
                    await conn.rollback()
                    return False

                await conn.commit()
                return True

        except Exception as e:
            print(f"❌ Erreur lors de l'abrogation du contrat: {e}")
            import traceback
            traceback.print_exc()
            if conn:
                await conn.rollback()
            return False
        finally:
            if conn:
                self.pool.release(conn)

    async def close(self):
        """Ferme le pool de connexions."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()