from testlink import TestlinkAPIClient

def get_testcases_from_testlink(project_name):
    url = "http://localhost/testlink/testlink-1.9.20/lib/api/xmlrpc/v1/xmlrpc.php"
    devKey = "66782e2ca0c3b440aca030c52c539bdb"

    tlc = TestlinkAPIClient(url, devKey)

    # Récupération du projet
    try:
        project = tlc.getTestProjectByName(project_name)
        project_id = project['id']
        print(f"✅ Projet trouvé : {project['name']} (ID: {project_id})")
    except Exception as e:
        print(f"❌ Erreur projet : {e}")
        return []

    all_testcases = []

    # Récupération des suites de premier niveau
    test_suites = tlc.getFirstLevelTestSuitesForTestProject(project_id)
    print(f"🔍 Suites trouvées : {[suite['name'] for suite in test_suites]}")

    for suite in test_suites:
        suite_id = suite['id']
        suite_name = suite['name']

        try:
            test_cases = tlc.getTestCasesForTestSuite(testsuiteid=suite_id, deep=True)
            print(f"📦 Suite: {suite_name} → {len(test_cases)} cas")
            for tc in test_cases:
                all_testcases.append({
                    "suite_name": suite_name,
                    "testcase_name": tc["name"],
                    "testcase_id": tc["id"]
                })
        except Exception as e:
            print(f"❌ Erreur dans la suite {suite_name}: {e}")
    
    print(f"✅ Total cas de test trouvés : {len(all_testcases)}")
    return all_testcases

# Utilisation
t = get_testcases_from_testlink("test2")
print("Résultat final :", t)