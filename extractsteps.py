from testlink import TestlinkAPIClient

# Connexion à TestLink

# Connexion
url = "http://localhost/testlink/testlink-1.9.20/lib/api/xmlrpc/v1/xmlrpc.php"
devKey = "66782e2ca0c3b440aca030c52c539bdb"
tlc = TestlinkAPIClient(url, devKey)

# Projets disponibles
projects = tlc.getProjects()
for project in projects:
    print(f"Projet : {project['name']} (ID: {project['id']})")

# Sélection du projet
project_name = input("Nom du projet : ")
project = tlc.getTestProjectByName(project_name)
project_id = project['id']

# Suites de test du projet
suites = tlc.getFirstLevelTestSuitesForTestProject(project_id)
for suite in suites:
    suite_name = suite['name']
    suite_id = suite['id']
    testcases = tlc.getTestCasesForTestSuite(testsuiteid=suite_id, deep=True)
    print(f"Suite: {suite_name} (ID: {suite_id}) Test cases récupérées: {len(testcases) if testcases else 0}")
suite_id=input("donner l'ID du testsuite à recupérer : ") 


    # Cas de test dans la suite
testcases = tlc.getTestCasesForTestSuite(testsuiteid=suite_id, deep=True)

if isinstance(testcases, list):
        for tc in testcases:
            print("\n===============")
            print(f"Test Case: {tc.get('name', 'Nom non trouvé')} (ID: {tc.get('id')})")

            # Récupération complète des détails
            try:
                full_tc = tlc.getTestCase(testcaseid=tc['id'])[0]  # La réponse est une liste
                print(f"Résumé   : {full_tc.get('summary', 'Résumé non disponible')}")

                steps = full_tc.get('steps', [])
                if steps:
                    for step in steps:
                        print(f"- Étape {step['step_number']}: {step['actions']}")
                        print(f"-Resultat Attendu: {step['expected_results']}")
                else:
                    print("Aucune étape.")
            except Exception as e:
                print("Erreur lors de la récupération du détail du test case :", e)
