from flask import Flask, jsonify, request
from flask_cors import CORS
from testlin import (  # Importez vos fonctions depuis creation.py
    get_projects,
    create_test_suite,
    create_test_case,
    add_to_database,
    get_test_cases_for_suite
)  # Ton wrapper personnalisé
from testlink import TestlinkAPIClient  # Lib officielle
import psycopg2
import requests

app = Flask(__name__)
CORS(app)

# Configuration TestLink
TL_URL = "http://localhost/testlink/testlink-1.9.20/lib/api/xmlrpc/v1/xmlrpc.php"
TL_DEVKEY = "66782e2ca0c3b440aca030c52c539bdb"

try:
    from testlink import TestlinkAPIClient as OfficialTestlinkClient
    tlc = OfficialTestlinkClient(TL_URL, TL_DEVKEY)
    print("✓ TestLink client initialisé")
except Exception as e:
    print(f"✗ Erreur initialisation client TestLink: {e}")
    from testlin import TestlinkAPIClient  # fallback custom client
    tlc = TestlinkAPIClient(TL_URL, TL_DEVKEY)

# Configuration base de données
DB_CONFIG = {
    'dbname': "testlink_db",
    'user': "postgres",
    'password': "root",
    'host': "localhost",
    'port': "5432"
}

def get_schema():
    return """
Table: testlinkdb
Colonnes :
- project_id (integer)
- project_name (text)
- suite_id (integer)
- suite_name (text)
- testcase_id (integer)
- testcase_name (text)
"""

def generate_sql_local(user_input):
    prompt = f"""
Tu es un expert SQL. Génère UNIQUEMENT une requête SELECT valide.
Schéma :
{get_schema()}
Question : {user_input}
Requête SQL (sans commentaires) :
"""
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1}
            },
            timeout=10  # Timeout après 10 secondes
        )
        response.raise_for_status()  # Lève une exception pour les codes 4xx/5xx
        
        sql = response.json().get("response", "").strip().rstrip(";")
        
        if not sql.lower().startswith("select"):
            raise ValueError("Seules les requêtes SELECT sont autorisées")
            
        if "limit" not in sql.lower():
            sql += " LIMIT 50"
            
        print(f"SQL générée: {sql}")
        return sql
        
    except requests.exceptions.RequestException as e:
        print(f"Erreur de connexion à Ollama: {str(e)}")
        return None
    except Exception as e:
        print(f"Erreur de traitement: {str(e)}")
        return None

def execute_query(query):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        cursor.close()
        conn.close()
        return columns, result
    except Exception as e:
        print("Erreur SQL:", e)
        return [], [("Erreur SQL", str(e))]

# --- Routes API ---

@app.route("/api/projects", methods=["GET"])
def api_projects():
    try:
        data = get_projects()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"response": "Veuillez saisir une question."}), 400

    query = generate_sql_local(user_message)
    print("🔍 SQL générée :", query)

    if not query or not query.lower().startswith("select"):
        return jsonify({"response": "Erreur : requête invalide."}), 400

    columns, result = execute_query(query)

    if not columns or "Erreur SQL" in columns:
        return jsonify({"response": f"Aucune donnée ou erreur: {result[0][1]}"}), 400

    formatted = "\n".join([", ".join(map(str, row)) for row in result])
    return jsonify({"response": f"Résultats:\n{formatted}"})

@app.route('/api/projects', methods=['GET'])
def api_get_projects():
    try:
        projects = get_projects()
        return jsonify({'success': True, 'data': projects})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/create/suite', methods=['POST'])
def api_create_suite():
    data = request.get_json()
    required_fields = ['project_id', 'suite_name']
    
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'error': 'Champs manquants'}), 400

    try:
        # Création de la suite
        result = create_test_suite(
            project_id=data['project_id'],
            suite_name=data['suite_name'],
            suite_description=data.get('suite_description', '')
        )

        if not result['success']:
            return jsonify(result), 400

        # Ajout à la base de données
        db_success = add_to_database(
            project_id=data['project_id'],
            project_name=data.get('project_name', ''),
            suite_id=result['suite_id'],
            suite_name=data['suite_name'],
            testcase_id=f'no_tc_{result["suite_id"]}',
            testcase_name='**'
        )

        if not db_success:
            return jsonify({
                'success': False,
                'error': 'La suite a été créée mais pas enregistrée en base'
            }), 500

        return jsonify(result)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/create/testcase', methods=['POST'])

def create_testcase():
    data = request.get_json()
    required_fields = ['testprojectid', 'testsuiteid', 'testcasename', 'steps']
    
    if not all(field in data for field in required_fields):
        return jsonify({"success": False, "error": "Champs manquants"}), 400

    try:
        # Formatage des étapes pour TestLink
        steps = [{
            'step_number': step['step_number'],
            'actions': step['actions'],
            'expected_results': step['expected_results'],
            'execution_type': step.get('execution_type', 1)
        } for step in data['steps']]

        # Appel à l'API TestLink
        result = tlc.createTestCase(
            testcasename=data['testcasename'],
            testsuiteid=data['testsuiteid'],
            testprojectid=data['testprojectid'],
            authorlogin=data.get('authorlogin', 'admin'),
            summary=data.get('summary', ''),
            steps=steps,
            executiontype=data.get('executiontype', 1),
            importance=data.get('importance', 2)
        )

        # Gestion de la réponse - plus robuste
        testcase_id = None
        testcase_name = data['testcasename']  # Fallback to the name we sent
        
        # Handle different response formats
        if isinstance(result, list):
            if result and 'id' in result[0]:
                testcase_id = result[0]['id']
                testcase_name = result[0].get('name', testcase_name)
        elif isinstance(result, dict):
            if 'id' in result:
                testcase_id = result['id']
                testcase_name = result.get('name', testcase_name)
            # Some TestLink versions might use different field names
            elif 'testcase_id' in result:
                testcase_id = result['testcase_id']
                testcase_name = result.get('testcase_name', testcase_name)
        suite_name=''
        try:
           suite_info = tlc.getTestSuiteByID(data['testsuiteid'])
           suite_name = suite_info.get('name', '')
        except Exception as e:
            print("⚠️ Impossible de récupérer le nom de la suite :", e)
            suite_name = ''

        db_success = add_to_database(
    project_id=data['testprojectid'],
    project_name=data.get('project_name', ''),
    suite_id=data['testsuiteid'],
    suite_name=suite_name,
    testcase_id=testcase_id,
    testcase_name=testcase_name
)
            
        if not db_success:
            return jsonify({
                'success': False,
                'error': 'La suite a été créée mais pas enregistrée en base'
            }), 500
        if not testcase_id:
            return jsonify({
                "success": False,
                "error": "La réponse de TestLink ne contient pas d'ID de test case",
                "response": result
            }), 500

        return jsonify({
            "success": True,
            "testcase_id": testcase_id,
            "testcase_name": testcase_name
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "received_data": data  # Pour le débogage
        }), 500
@app.route("/api/suites", methods=["GET"])
def get_suites():
    project_id = request.args.get('project_id')
    if not project_id:
        return jsonify({"error": "project_id parameter is required"}), 400
    
    try:
        # Utilisez votre client TestLink
        suites = tlc.getFirstLevelTestSuitesForTestProject(int(project_id))
        return jsonify([{
            "id": suite['id'],
            "name": suite['name']
        } for suite in suites])
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

@app.route("/")
def home():
    return "✅ Serveur Flask opérationnel"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000, debug=True)