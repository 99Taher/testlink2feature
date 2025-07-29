import psycopg2
import xmlrpc.client

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