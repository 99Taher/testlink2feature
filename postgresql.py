import psycopg2
from testlink import TestlinkAPIClient

# === Connexion TestLink ===
url = "http://localhost/testlink/testlink-1.9.20/lib/api/xmlrpc/v1/xmlrpc.php"
devKey = "66782e2ca0c3b440aca030c52c539bdb"
tlc = TestlinkAPIClient(url, devKey)

# === Connexion PostgreSQL ===
conn = psycopg2.connect(
    dbname="testlink_db",
    user="postgres",         # ⚠️ adapte selon ton user
    password="root", # ⚠️ adapte ton mot de passe
    host="localhost",
    port="5432",
    sslmode="disable"
)
cur = conn.cursor()

# === Créer la table testcases si elle n'existe pas ===
cur.execute('''
CREATE TABLE IF NOT EXISTS testcases (
    id TEXT PRIMARY KEY,
    name TEXT,
    summary TEXT,
    project_name TEXT,
    suite_name TEXT
)
''')

# === Récupération des projets ===
projects = tlc.getProjects()
print(f"Projets récupérés : {len(projects)}")
for project in projects:
    project_name = project['name']
    project_id = project['id']
    print(f"Projet: {project_name} (ID: {project_id})")

    suites = tlc.getFirstLevelTestSuitesForTestProject(project_id)
    print(f"Suites récupérées pour {project_name}: {len(suites)}")

    for suite in suites:
        suite_name = suite['name']
        suite_id = suite['id']
        print(f"Suite: {suite_name} (ID: {suite_id})")

        try:
            testcases = tlc.getTestCasesForTestSuite(testsuiteid=suite_id, deep=True)
            print(f"Test cases récupérées: {len(testcases) if testcases else 0}")

            if isinstance(testcases, dict):
                print("ffffffff")
                for _, case in testcases.items():
                    case_id = case['id']
                    name = case['name']
                    summary = case.get('summary', '')
                    print(f"Insertion : {case_id} - {name} - {summary[:30]}")
                    try:
                      cur.execute('''INSERT INTO testcases (id, name, summary, project_name, suite_name)
                        VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING''',
                      (case_id, name, summary, project_name, suite_name))
                    except Exception as e:
                       print(f"Erreur insertion test case {case_id}: {e}")
            elif isinstance(testcases, list):
              for case in testcases:
                    case_id = case['id']
                    name = case['name']
                    summary = case.get('summary', '')
                    print(f"Insertion : {case_id} - {name} - {summary[:30]}")
                    try:
                      cur.execute('''INSERT INTO testcases (id, name, summary, project_name, suite_name)
                        VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING''',
                      (case_id, name, summary, project_name, suite_name))
                    except Exception as e:
                       print(f"Erreur insertion test case {case_id}: {e}")           
        except Exception as e:
            print(f"Erreur pour la suite {suite_name} : {e}")


# === Sauvegarde et fermeture ===
conn.commit()
cur.close()
conn.close()

print(" Base PostgreSQL générée avec succès !")