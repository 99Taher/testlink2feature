from testlink import TestlinkAPIClient

# Connexion à TestLink
url = "http://localhost/testlink/testlink-1.9.20/lib/api/xmlrpc/v1/xmlrpc.php"
devKey = "66782e2ca0c3b440aca030c52c539bdb"
tlc = TestlinkAPIClient(url, devKey)

# Récupération du projet
project_name = input("Nom du projet : ")
project = tlc.getTestProjectByName(project_name)
project_id = project['id']

# Création du plan de test
testplan_name = input("Nom du plan de test : ")
testplan_notes = "Plan créé automatiquement via API"
is_active = 1     # 1 = actif
is_public = 1     # 1 = public

try:
    result = tlc.createTestPlan(
        testplan_name,
        project_name,
        notes=testplan_notes,
        active=is_active,
        public=is_public
    )
    print(" Plan de test créé :", result)
except Exception as e:
    print("Erreur lors de la création du plan de test :", e)