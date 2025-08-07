import psycopg2
import xmlrpc.client
import xml.etree.ElementTree as ET
from testlink import TestlinkAPIClient
import os

# Configuration globale
TESTLINK_URL = "http://localhost/testlink/testlink-1.9.20/lib/api/xmlrpc/v1/xmlrpc.php"
TESTLINK_DEVKEY = "66782e2ca0c3b440aca030c52c539bdb"
DB_CONFIG = {
    'dbname': 'testlink_db',
    'user': 'postgres',
    'password': 'root',
    'host': 'localhost',
    'port': '5432'
}
AUTHOR_LOGIN = "admin"
def extract_steps(testcase_elem):
    """Extrait les étapes d'un test case XML"""
    steps = []
    for step_elem in testcase_elem.findall(".//step"):
        try:
            step_number = int(step_elem.find("step_number").text.strip())
            actions = (step_elem.find("actions").text or "").strip()
            expected = (step_elem.find("expectedresults").text or "").strip()
            
            steps.append({
                "step_number": step_number,
                "actions": actions,
                "expectedresults": expected,
                "execution_type": 1
            })
        except Exception as e:
            print(f"⚠ Erreur étape: {str(e)}")
    return steps

def import_from_xml(xml_path):
    """Importe les test cases depuis un XML vers TestLink et la base de données"""
    try:
        # Connexion à TestLink
        tlc = TestlinkAPIClient(TESTLINK_URL, TESTLINK_DEVKEY)
        
        # Chargement du XML
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Extraction des infos de la test suite
        testsuite_id = int(root.attrib['id'])
        testsuite_name = root.attrib['name']
        print(f"Test Suite: {testsuite_name} (ID: {testsuite_id})")

        # Vérification de la test suite
        try:
            suite_info = tlc.getTestSuiteByID(testsuite_id)
            if suite_info['name'] != testsuite_name:
                print(f"⚠ Attention: Le nom de la suite ne correspond pas ({suite_info['name']} != {testsuite_name})")
            project_id = suite_info['testproject_id']
        except Exception as e:
            print(f"❌ La test suite spécifiée n'existe pas: {str(e)}")
            return False

        # Traitement des test cases
        success_count = 0
        db_success_count = 0
        for testcase in root.findall("testcase"):
            try:
                name = testcase.attrib.get("name", "Unnamed TestCase")
                summary = (testcase.find("summary").text or "").strip()
                preconditions = (testcase.find("preconditions").text or "").strip()
                steps = extract_steps(testcase)

                if not steps:
                    print(f"⚠ {name} ignoré (pas d'étapes valides)")
                    continue

                # Création du test case dans TestLink
                response = tlc.createTestCase(
                    testcasename=name,
                    testsuiteid=testsuite_id,
                    testprojectid=project_id,
                    authorlogin=AUTHOR_LOGIN,
                    summary=summary,
                    preconditions=preconditions,
                    steps=steps
                )

                # Récupération de l'ID créé
                testcase_id = None
                if isinstance(response, list) and response and 'id' in response[0]:
                    testcase_id = response[0]['id']
                    print(f"✓ {name} créé dans TestLink (ID: {testcase_id})")
                    success_count += 1
                else:
                    print(f"⚠ Réponse inattendue pour {name}: {response}")
                    continue

                # Ajout à la base de données
                if testcase_id:
                    db_result = add_to_database(
                        project_id=project_id,
                        project_name=tlc.getTestProjectByID(project_id)['name'],
                        suite_id=testsuite_id,
                        suite_name=testsuite_name,
                        testcase_id=testcase_id,
                        testcase_name=name
                    )
                    if db_result:
                        db_success_count += 1
                        print(f"✓ {name} ajouté à la base de données")
                    else:
                        print(f"⚠ {name} créé dans TestLink mais échec d'ajout en base")

            except Exception as e:
                print(f"❌ Erreur avec {name}: {str(e)}")
                continue

        print(f"\nTerminé: {success_count} test cases créés dans TestLink")
        print(f"{db_success_count} test cases ajoutés à la base de données")
        return True

    except Exception as e:
        print(f"❌ Erreur critique: {str(e)}")
        return False
def process_xml_import(xml_path):
    """Traite le fichier XML et effectue l'import dans TestLink"""
    try:
        # Initialisation TestLink
        tlc = TestlinkAPIClient(TESTLINK_URL, TESTLINK_DEVKEY)
        
        # Parse XML
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Récupération infos test suite
        testsuite_id = int(root.attrib['id'])
        testsuite_name = root.attrib['name']
        
        # Vérification de la suite
        suite_info = tlc.getTestSuiteByID(testsuite_id)
        project_id = suite_info['testproject_id']
        
        results = {
            'success_count': 0,
            'error_count': 0,
            'testcases': []
        }

        # Traitement des test cases
        for testcase in root.findall("testcase"):
            tc_result = {
                'name': testcase.attrib.get("name", "Unnamed"),
                'status': 'failed',
                'error': None
            }
            
            try:
                # Extraction des données
                name = testcase.attrib.get("name", "Unnamed TestCase")
                summary = (testcase.find("summary").text or "").strip()
                steps = extract_steps(testcase)  # Votre fonction existante

                # Création dans TestLink
                response = tlc.createTestCase(
                    testcasename=name,
                    testsuiteid=testsuite_id,
                    testprojectid=project_id,
                    authorlogin="admin",
                    summary=summary,
                    steps=steps
                )

                # Gestion de la réponse
                if isinstance(response, list) and response and 'id' in response[0]:
                    tc_result.update({
                        'status': 'success',
                        'testcase_id': response[0]['id']
                    })
                    results['success_count'] += 1
                    
                    # Ajout à la base de données
                    add_to_database(
                        project_id=project_id,
                        project_name=tlc.getTestProjectByID(project_id)['name'],
                        suite_id=testsuite_id,
                        suite_name=testsuite_name,
                        testcase_id=response[0]['id'],
                        testcase_name=name
                    )
                else:
                    tc_result['error'] = f"Réponse inattendue: {response}"
                    results['error_count'] += 1

            except Exception as e:
                tc_result['error'] = str(e)
                results['error_count'] += 1
            
            results['testcases'].append(tc_result)

        return {
            'success': results['success_count'] > 0,
            'message': f"Import terminé: {results['success_count']} succès, {results['error_count']} échecs",
            'details': results
        }

    except Exception as e:
        return {
            'success': False,
            'error': f"Erreur critique: {str(e)}"
        }    

# Initialisation de la connexion TestLink
testlink_server = xmlrpc.client.ServerProxy(TESTLINK_URL)

def get_projects():
    """Récupère tous les projets depuis PostgreSQL"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT project_id, project_name, suite_id, suite_name, testcase_id, testcase_name
        FROM testlinkdb
        ORDER BY project_id, suite_id, testcase_id
    """)
    rows = cursor.fetchall()

    projects_dict = {}
    for row in rows:
        project_id, project_name, suite_id, suite_name, testcase_id, testcase_name = row

        if project_id not in projects_dict:
            projects_dict[project_id] = {
                "id": project_id,
                "nom": project_name,
                "test_suites": {}
            }

        if suite_id not in projects_dict[project_id]["test_suites"]:
            projects_dict[project_id]["test_suites"][suite_id] = {
                "id": suite_id,
                "nom": suite_name,
                "test_cases": []
            }

        if testcase_id is not None:
            projects_dict[project_id]["test_suites"][suite_id]["test_cases"].append({
                "id": testcase_id,
                "nom": testcase_name
            })

    result = []
    for project in projects_dict.values():
        project["test_suites"] = list(project["test_suites"].values())
        result.append(project)

    cursor.close()
    conn.close()
    return result
def extract_steps(testcase_elem):
    steps = []
    for step_elem in testcase_elem.findall(".//step"):
        step_number = int(step_elem.find("step_number").text.strip())
        
        actions_elem = step_elem.find("actions")
        actions = actions_elem.text.strip() if actions_elem is not None and actions_elem.text else ""
        
        expected_elem = step_elem.find("expectedresults")
        expected = expected_elem.text.strip() if expected_elem is not None and expected_elem.text else ""
        
        steps.append({
            "step_number": step_number,
            "actions": actions,
            "expectedresults": expected,
            "execution_type": 1
        })
    return steps


def create_test_suite(project_id, suite_name, suite_description=""):
    """Crée une nouvelle suite de tests"""
    try:
        result = testlink_server.tl.createTestSuite({
            'devKey': TESTLINK_DEVKEY,
            'testprojectid': project_id,
            'testsuitename': suite_name,
            'details': suite_description
        })
        
        suite_id = result[0]['id'] if isinstance(result, list) else result['id']
        return {
            'success': True,
            'suite_id': suite_id,
            'message': f'Test Suite "{suite_name}" créée avec succès'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def create_test_case(project_id, suite_id, testcase_name, steps, summary="", author="admin"):
    """Crée un nouveau cas de test"""
    try:
        formatted_steps = [{
            'step_number': step.get('step_number', 1),
            'actions': step.get('actions', ''),
            'expected_results': step.get('expected_results', ''),
            'execution_type': step.get('execution_type', 1)
        } for step in steps]

        testlink_server.tl.createTestCase({
            'devKey': TESTLINK_DEVKEY,
            'testcasename': testcase_name,
            'testsuiteid': suite_id,
            'testprojectid': project_id,
            'authorlogin': author,
            'summary': summary,
            'steps': formatted_steps
        })

        # Récupération du test case créé
        testcases = get_test_cases_for_suite(suite_id)
        last_case = list(testcases.values())[-1] if isinstance(testcases, dict) else testcases[-1]
        
        return {
            'success': True,
            'testcase_id': last_case['id'],
            'testcase_name': last_case['name'],
            'message': f'Test Case "{testcase_name}" créé avec succès'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def get_test_cases_for_suite(suite_id):
    """Récupère les cas de test d'une suite"""
    return testlink_server.tl.getTestCasesForTestSuite({
        'devKey': TESTLINK_DEVKEY,
        'testsuiteid': suite_id,
        'deep': True,
        'details': 'simple'
    })

def add_to_database(project_id, project_name, suite_id, suite_name, testcase_id, testcase_name):
    """Ajoute une entrée dans la base de données"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO testlinkdb 
            (project_id, project_name, suite_id, suite_name, testcase_id, testcase_name)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (testcase_id) DO NOTHING
            """, 
            (project_id, project_name, suite_id, suite_name, testcase_id, testcase_name)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Erreur DB: {str(e)}")
        return False


def parse_feature_file(filepath):
    """Parse un fichier feature et extrait les informations"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    feature_name = ""
    scenarios = []
    current_scenario = None
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Détection Feature
        if line.startswith('Feature:'):
            feature_name = line.replace('Feature:', '').strip()
        
        # Détection Scenario
        elif line.startswith('Scenario:'):
            if current_scenario:
                scenarios.append(current_scenario)
            current_scenario = {
                'type': 'Scenario',
                'name': line.replace('Scenario:', '').strip(),
                'steps': []
            }
        
        # Détection Scenario Outline
        elif line.startswith('Scenario Outline:'):
            if current_scenario:
                scenarios.append(current_scenario)
            current_scenario = {
                'type': 'Scenario Outline',
                'name': line.replace('Scenario Outline:', '').strip(),
                'steps': [],
                'examples': []
            }
        
        # Détection Steps
        elif line.startswith(('Given ', 'When ', 'Then ', 'And ', 'But ')):
            if current_scenario:
                current_scenario['steps'].append(line)
        
        # Détection Examples
        elif line.startswith('Examples:'):
            if current_scenario and current_scenario['type'] == 'Scenario Outline':
                current_scenario['examples'].append(line)
        elif line.startswith('|') and current_scenario and current_scenario['type'] == 'Scenario Outline':
            current_scenario['examples'].append(line)
    
    if current_scenario:
        scenarios.append(current_scenario)
    
    return {
        'feature_name': feature_name,
        'scenarios': scenarios,
        'raw_content': content
    }


def extract_all_feature_data(folder_path):
    all_scenarios = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".feature"):
            file_path = os.path.join(folder_path, filename)
            try:
                feature_title, scenarios = parse_feature_file(file_path)
                for scenario in scenarios:
                    all_scenarios.append({
                        "file_name": filename,
                        "feature_name": feature_title,
                        "scenario_title": scenario["name"],
                        "type": scenario["type"],
                        "steps": scenario["steps"],
                        "examples": scenario.get("examples", [])
                    })
            except Exception as e:
                print(f"❌ Erreur dans {filename}: {e}")
    return all_scenarios
def synch(tlc):
  try:
    conn = psycopg2.connect(
        dbname="testlink_db",
        user="postgres",
        password="root",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS testlinkdb (
            project_id VARCHAR(50),
            project_name TEXT,
            suite_id VARCHAR(50),
            suite_name TEXT,
            testcase_id VARCHAR(50) PRIMARY KEY,
            testcase_name TEXT
        );
    """)

    conn.commit()
    print("Table créée avec succès.")
  except Exception as e:
    print("Erreur :", e)



  try:
    projects = tlc.getProjects()
    
  except Exception as e:
    print(f"❌ Erreur lors de la récupération des projets : {e}")
    conn.close()
    exit()

  total_cases = 0


  for project in projects:
    project_id = project['id']
    project_name = project['name']
    

    try:
        test_suites = tlc.getFirstLevelTestSuitesForTestProject(project_id)
    except Exception as e:
        print(f"❌ Erreur récupération des suites du projet {project_name} : {e}")
        continue
    if not test_suites:
        add_to_database(project_id, project_name, '00','**', '00' ,'**')
    else:    
     for suite in test_suites:
      suite_id = suite['id']
      suite_name = suite['name']

      test_cases = tlc.getTestCasesForTestSuite(testsuiteid=suite_id, deep=True)

      if not test_cases:
         add_to_database(project_id, project_name, suite_id, suite_name, f'no_tc_{suite_id}', '**')
        

      else:
        for tc in test_cases:
            case_id = tc["id"]
            case_name = tc["name"]

            try:
                add_to_database(project_id,project_name,suite_id,suite_name,case_id,case_name)
                total_cases += 1
            except Exception as insert_err:
                print(f"    ❌ Erreur insertion test case {case_id} : {insert_err}")
            


  conn.commit()
  conn.close()

  print(f"\n✅ Synchronisation terminée.") 

    