from testlink import TestlinkAPIClient

# === Connexion TestLink ===
url = "http://localhost/testlink/testlink-1.9.20/lib/api/xmlrpc/v1/xmlrpc.php"
devKey = "66782e2ca0c3b440aca030c52c539bdb"
tlc = TestlinkAPIClient(url, devKey)
def extract_test_scripts(project_name=None, testplan_name=None):
    # 1. Identifier le projet
    projects = tlc.getProjects()
    project = next((p for p in projects if p['name'] == project_name), None)
    if not project:
        print(f"Projet '{project_name}' non trouvé. - f4.py:12")
        return

    project_id = project['id']
    print(f"Projet trouvé : {project_name} (ID: {project_id}) - f4.py:16")

    # 2. Récupérer les plans de test
    testplans = tlc.getProjectTestPlans(project_id)
    testplan = next((tp for tp in testplans if tp['name'] == testplan_name), None)
    if not testplan:
        print(f"Plan de test '{testplan_name}' non trouvé. - f4.py:22")
        return

    testplan_id = testplan['id']
    print(f"Plan de test trouvé : {testplan_name} (ID: {testplan_id}) - f4.py:26")

    # 3. Récupérer les cas de test associés
    # 3. Récupérer les cas de test associés
    testcases = tlc.getTestCasesForTestPlan(testplan_id)
    print(f"{len(testcases)} cas de test trouvés dans le plan '{testplan_name}': - f4.py:31")

# 4. Extraire et afficher les scripts
    if isinstance(testcases, list):
       for tc in testcases:
       
        print("ID: {tc.get('tc_id', 'N/A')} ")
        print(f"Nom: {tc.get('name', 'N/A')} ")
        print(f"Résumé: {tc.get('summary', 'N/A')} ")
        print(f"Étapes: {tc.get('steps', 'N/A')} ")
        print(f"Résultat attendu: {tc.get('expected_results', 'N/A')} ")
    else:
        print("Format inattendu des test cases : ", type(testcases))

extract_test_scripts(project_name="test", testplan_name="test_authentification")
