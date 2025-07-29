# ce code permet la creation d'une testsuite avec ses testcases ou la creation d'une testcase dans une testsuite existante 
from testlink import TestlinkAPIClient
from adddb import add_db  # Assure-toi que ce fichier contient bien la fonction add_db

url = "http://localhost/testlink/testlink-1.9.20/lib/api/xmlrpc/v1/xmlrpc.php"
devKey = "66782e2ca0c3b440aca030c52c539bdb"
tlc = TestlinkAPIClient(url, devKey)


def create_testsuite(resul, project_i, project_name, suite_name):
    if isinstance(resul, list):
        suite_id = resul[0]['id']
    elif isinstance(resul, dict):
        suite_id = resul['id']
    else:
        print("Format inattendu pour resul")
        return

    print(f"🔧 Suite créée : {suite_name} (ID: {suite_id})")  # Debug

    testcase = input("Créer un test case ? (yes/no) : ")
    if testcase.lower() == "yes":
        testcasename = input("Le nom du test case : ")
        tc_summary = "Résumé du test case"

        steps = [{
            'step_number': 1,
            'actions': input("Donner les actions de test : "),
            'expected_results': input("Donner le résultat attendu : "),
            'execution_type': 1
        }]

        try:
            tlc.createTestCase(
                testcasename,
                suite_id,
                project_i,
                "admin",
                tc_summary,
                steps=steps
            )
            print('✅ Test case créé avec succès.')

            testcases = tlc.getTestCasesForTestSuite(testsuiteid=suite_id, deep=True)
            last_case = list(testcases.values())[-1] if isinstance(testcases, dict) else testcases[-1]
            case_id = last_case["id"]
            case_name = last_case["name"]

            
            add_db(project_i, project_name, suite_id, suite_name, case_id, case_name)

        except Exception as e:
            print("❌ Erreur lors de la création du test case :", e)
    else:
        
        add_db(project_i, project_name, suite_id, suite_name, f'no_tc_{suite_id}', '**')
        print("✅ Suite ajoutée sans test case.")

# --------- Programme principal ----------
project_name = input("Donner le nom du projet : ")
project = tlc.getTestProjectByName(project_name)
project_id = project['id']

verif = input("Créer un testsuite ? (yes/no) : ")
if verif.lower() == "yes":
    suite_name = input("Donner le nom du testsuite : ")
    new_suite_details = "Suite ajoutée via l’API TestLink"

    try:
        result = tlc.createTestSuite(project_id, suite_name, new_suite_details)
        print("✅ Test Suite créée :", result)
        create_testsuite(result, project_id, project_name, suite_name)  # <-- suite_name passé ici
    except Exception as e:
        print("❌ Erreur lors de la création de la Test Suite :", e)

else:
    t = input("Créer un testcase dans un testsuite existant ? (yes/no) : ")
    if t.lower() == "yes":
        f = int(input("Combien de testcases voulez-vous créer ? : "))
        suites = tlc.getFirstLevelTestSuitesForTestProject(project_id)

        print("📋 Suites disponibles :")
        for suite in suites:
            print(f"Suite: {suite['name']} | ID: {suite['id']}")

        suite_choisie_id = input("ID de la testsuite pour créer les test cases : ")
        suite_valide = any(str(s['id']) == suite_choisie_id for s in suites)

        if suite_valide:
            suite_name = next(s['name'] for s in suites if str(s['id']) == suite_choisie_id)

            for i in range(f):
                nom_testcase = input(f"Nom du test case {i+1} : ")
                somme_testcase = input(f"Résumé du test case {i+1} : ")
                actions = input(f"Étapes : ")
                resultat_attendu = input("Résultat attendu : ")

                steps = [{
                    'step_number': 1,
                    'actions': actions,
                    'expected_results': resultat_attendu,
                    'execution_type': 1
                }]

                try:
                    tlc.createTestCase(
                        testcasename=nom_testcase,
                        testsuiteid=suite_choisie_id,
                        testprojectid=project_id,
                        authorlogin="admin",
                        summary=somme_testcase,
                        steps=steps
                    )
                    print(f"✅ Test case {i+1} créé.")

                    testcases = tlc.getTestCasesForTestSuite(testsuiteid=suite_choisie_id, deep=True)
                    last_case = list(testcases.values())[-1] if isinstance(testcases, dict) else testcases[-1]
                    case_id = last_case["id"]
                    case_name = last_case["name"]

                    add_db(project_id, project_name, int(suite_choisie_id), suite_name, case_id, case_name)

                except Exception as e:
                    print(f"❌ Erreur test case {i+1} :", e)
        else:
            print("❌ ID de testsuite invalide.")
    else:
        print("*** FIN ***")