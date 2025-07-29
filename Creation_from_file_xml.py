#ce code permet l'extraction des testcases et les ces etapes et les creér dans testlink 
import xml.etree.ElementTree as ET
from testlink import TestlinkAPIClient

# Configuration TestLink
url = "http://localhost/testlink/testlink-1.9.20/lib/api/xmlrpc/v1/xmlrpc.php"
devKey = "66782e2ca0c3b440aca030c52c539bdb"
PROJECT_NAME = "test2"
AUTHOR_LOGIN = "admin"
TARGET_TESTSUITE = "Imported TestCases"  # nom de la suite cible

# Connexion à TestLink
tlc = TestlinkAPIClient(url, devKey)
project = tlc.getTestProjectByName(PROJECT_NAME)
if not project:
    raise Exception(f"Le projet '{PROJECT_NAME}' n'existe pas dans TestLink.")
project_id = project['id']
print(f"ID du projet trouvé : {project_id}")

# Trouver ou créer la suite de test
def get_or_create_suite(project_id, suite_name):
    suites = tlc.getFirstLevelTestSuitesForTestProject(project_id)
    for suite in suites:
        if suite['name'] == suite_name:
            return int(suite['id'])
    # Sinon on la crée
    result = tlc.createTestSuite(project_id, suite_name, "Auto-created")
    return result[0]['id']

testsuite_id = get_or_create_suite(project_id, TARGET_TESTSUITE)

# Lire les étapes
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

# Charger le fichier XML
xml_file = r"C:\Users\user\OneDrive\Bureau\stagetest\hh.xml"
tree = ET.parse(xml_file)
root = tree.getroot()

# Traiter tous les test cases
for testcase in root.findall("testcase"):
    try:
        name = testcase.attrib.get("name", "Unnamed TestCase")
        summary = (testcase.find("summary").text or "").strip()
        preconditions = (testcase.find("preconditions").text or "").strip()
        steps = extract_steps(testcase)

        tc_args = {
            "testcasename": name,
            "testsuiteid": testsuite_id,
            "testprojectid": project_id,
            "authorlogin": "admin",
            "summary": summary,
            "preconditions": preconditions,
            "steps": steps
        }

        response = tlc.createTestCase(**tc_args)
        if isinstance(response, list) and len(response) > 0:
           print(f"✅ Test case '{name}' créé avec succès (ID: {response[0]['id']})")
        else:
           print(f"✅ Test case '{name}' créé (réponse inattendue : {response})")

    except Exception as e:
        print(f" Erreur avec le test case '{name}': {e}")
