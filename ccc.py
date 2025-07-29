import psycopg2

def executer_requete(message):
    # Dictionnaire des mots-clés et leurs requêtes SQL associées
    commandes_sql = {
        "combien": "SELECT COUNT(DISTINCT suite_name) FROM testlinkdb WHERE testcase_name = '**';",
        "project": "SELECT DISTINCT project_name FROM testlinkdb;",
        "suite": "SELECT DISTINCT suite_name FROM testlinkdb;"
    }

    message = message.lower()
    mot_cle_trouve = None

    # On cherche si un mot-clé est dans la phrase
    for mot_cle in commandes_sql:
        if mot_cle in message:
            mot_cle_trouve = mot_cle
            break

    if mot_cle_trouve:
        try:
            conn = psycopg2.connect(
                dbname="testlink_db",
                user="postgres",
                password="root",
                host="localhost",
                port="5432"
            )
            cursor = conn.cursor()

            # Cas spécial : "combien" attend un nom de test dans la phrase
            if mot_cle_trouve == "combien":
                # Exemple : "combien pour le test LoginTest"
                mots = message.split()
                # On prend le dernier mot comme nom de test simple (à améliorer si besoin)
                nom_test = mots[-1]
                cursor.execute(commandes_sql["combien"], (nom_test,))
            else:
                cursor.execute(commandes_sql[mot_cle_trouve])

            resultats = cursor.fetchall()
            conn.close()
            return resultats

        except Exception as e:
            return f"❌ Erreur SQL : {str(e)}"

    else:
        return None