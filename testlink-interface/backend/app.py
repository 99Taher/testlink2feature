from flask import Flask, jsonify, request,send_file
from werkzeug.utils import secure_filename
from flask_cors import CORS
import os
import xml.etree.ElementTree as ET
from rapidfuzz import process, fuzz
import csv
from io import StringIO
from typing import List, Dict, Any
from pathlib import Path
import logging
from datetime import datetime

from io import StringIO
import csv
from testlin import (  # Importez vos fonctions depuis creation.py
    get_projects,
    create_test_suite,
    
    add_to_database,
    parse_feature_file,
    synch
)  # Ton wrapper personnalisé
from testlink import TestlinkAPIClient  # Lib officielle
import psycopg2
import requests




app = Flask(__name__)
CORS(app)

# Configuration TestLink
TL_URL = "http://localhost/testlink/testlink-1.9.20/lib/api/xmlrpc/v1/xmlrpc.php" 
TL_DEVKEY = "66782e2ca0c3b440aca030c52c539bdb"

DB_CONFIG = {
    'dbname': "testlink_db",
    'user': "postgres",
    'password': "root",
    'host': "localhost",
    'port': "5432"
}

try:
    from testlink import TestlinkAPIClient as OfficialTestlinkClient
    tlc = OfficialTestlinkClient(TL_URL, TL_DEVKEY)
    print("✓ TestLink client initialisé")
except Exception as e:
    print(f"✗ Erreur initialisation client TestLink: {e}")
    from testlin import TestlinkAPIClient  # fallback custom client
    tlc = TestlinkAPIClient(TL_URL, TL_DEVKEY)

# Configuration base de données


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




UPLOAD_FOLDER = 'uploads'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
AUTHOR_LOGIN = "admin"
ALLOWED_EXTENSIONS = {'xml', 'XML'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xml'}  # Case-insensitive check

@app.route('/api/import/xml', methods=['POST'])
def handle_xml_import():
    # Debug avancé
    print("\n=== Nouvelle requête reçue ===")
    print("Headers:", request.headers)
    print("Form data:", request.form)
    
    # Vérification améliorée du fichier
    if 'xmlFile' not in request.files:
        print("Erreur: Aucun fichier dans FormData")
        return jsonify({"success": False, "error": "Aucun fichier fourni"}), 400
    
    file = request.files['xmlFile']
    print(f"Fichier reçu - Nom: {file.filename}, Type: {file.content_type}, Taille: {file.content_length} bytes")

    # Vérification du contenu (plus robuste)
    try:
        file_content = file.stream.read().decode('utf-8')
        file.stream.seek(0)  # Réinitialise le pointeur du fichier
        
        # Validation XML
        try:
            ET.fromstring(file_content)  # Test le parsing XML
            print("Validation XML réussie")
        except ET.ParseError:
            print("Erreur: Le contenu n'est pas du XML valide")
            return jsonify({
                "success": False,
                "error": "Le fichier n'est pas un XML valide",
                "content_sample": file_content[:100] + "..." if file_content else "Vide"
            }), 400

    except UnicodeDecodeError:
        print("Erreur: Fichier non texte")
        return jsonify({
            "success": False,
            "error": "Le fichier doit être un texte (XML)",
            "content_type": file.content_type
        }), 400

    # Traitement normal si tout est valide
    try:
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)
        print(f"File saved temporarily at: {temp_path}")

        # Parse XML
        tree = ET.parse(temp_path)
        root = tree.getroot()
        xml_suite_id = int(root.attrib.get('id', 0))  # Default to 0 if missing
        xml_suite_name = root.attrib.get('name', 'Default Suite')

        # Debug: Print XML structure
        print("XML Structure:")
        print(ET.tostring(root, encoding='utf8').decode('utf8'))
        project_id = request.form.get('projectId')

        # Get or create test suite
        suites = tlc.getFirstLevelTestSuitesForTestProject(int(project_id))
        suite = next((s for s in suites if s['name'] == xml_suite_name), None)
        
        if not suite:
            suite_response = tlc.createTestSuite(int(project_id), xml_suite_name, "Imported from XML")
            if not suite_response or 'id' not in suite_response[0]:
                raise Exception("Failed to create test suite")
            testsuite_id = int(suite_response[0]['id'])
        else:
            testsuite_id = int(suite['id'])

        # Process test cases
        success_count = 0
        error_count = 0
        testcases = []

        for testcase in root.findall("testcase"):
            name = testcase.attrib.get("name", "Unnamed TestCase")
            try:
                summary = (testcase.find("summary").text or "").strip() if testcase.find("summary") is not None else ""
                preconditions = (testcase.find("preconditions").text or "").strip() if testcase.find("preconditions") is not None else ""
                
                # Extract steps
                steps = []
                step_elems = testcase.findall(".//step")
                for step_idx, step_elem in enumerate(step_elems, start=1):
                    step_number = int(step_elem.find("step_number").text.strip()) if step_elem.find("step_number") is not None else step_idx
                    actions = (step_elem.find("actions").text or "").strip() if step_elem.find("actions") is not None else ""
                    expected = (step_elem.find("expectedresults").text or "").strip() if step_elem.find("expectedresults") is not None else ""
                    steps.append({
                        "step_number": step_number,
                        "actions": actions,
                        "expected_results": expected,  # Match TestLink API key
                        "execution_type": 1
                    })

                # Create test case in TestLink
                response = tlc.createTestCase(
                    testcasename=name,
                    testsuiteid=testsuite_id,
                    testprojectid=int(project_id),
                    authorlogin=AUTHOR_LOGIN,
                    summary=summary,
                    preconditions=preconditions,
                    steps=steps
                )

                if isinstance(response, list) and response and 'id' in response[0]:
                    testcase_id = response[0]['id']
                    testcases.append({
                        "name": name,
                        "id": testcase_id,
                        "status": "success"
                    })
                    success_count += 1

                    # Add to database (assuming add_to_database is defined elsewhere; implement as needed)
                    db_success = add_to_database(
                        project_id=project_id,
                        project_name=request.form.get('project_name', ''),
                        suite_id=testsuite_id,
                        suite_name=xml_suite_name,
                        testcase_id=testcase_id,
                        testcase_name=name
                    )
                    if not db_success:
                        testcases[-1]['status'] = 'db_failed'
                        testcases[-1]['error'] = 'Erreur enregistrement base de données'
                        error_count += 1
                else:
                    raise Exception("Unexpected response from TestLink")

            except Exception as e:
                testcases.append({
                    "name": name,
                    "status": "failed",
                    "error": str(e)
                })
                error_count += 1

        return jsonify({
            "success": True,
            "message": f"Import terminé: {success_count} succès, {error_count} échecs",
            "test_suite": {
                "id": testsuite_id,
                "name": xml_suite_name
            },
            "testcases": testcases,
            "successCount": success_count,
            "errorCount": error_count
        })

    except ET.ParseError as parse_err:
        print(f"XML Parse Error: {parse_err}")
        return jsonify({"success": False, "error": "Fichier XML malformé"}), 400
    except Exception as e:
        print(f"General Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
            print(f"Temporary file removed: {temp_path}")

    


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
import time
@app.route('/api/create/testcase', methods=['POST'])




def create_testcase():
    data = request.get_json()
    required_fields = ['testprojectid', 'testsuiteid', 'testcasename', 'steps']
    
    if not all(field in data for field in required_fields):
        return jsonify({"success": False, "error": "Champs manquants"}), 400

    try:
        # Validation et formatage des étapes
        steps = [{
            'step_number': step['step_number'],
            'actions': step['actions'],
            'expected_results': step['expected_results'],
            'execution_type': step.get('execution_type', 1)
        } for step in data['steps']]

        # Création du test case dans TestLink
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

        # Traitement de la réponse
        testcase_id = None
        testcase_name = data['testcasename']
        
        if isinstance(result, list) and result and 'id' in result[0]:
            testcase_id = result[0]['id']
            testcase_name = result[0].get('name', testcase_name)
        elif isinstance(result, dict):
            if 'id' in result:
                testcase_id = result['id']
                testcase_name = result.get('name', testcase_name)
            elif 'testcase_id' in result:
                testcase_id = result['testcase_id']
                testcase_name = result.get('testcase_name', testcase_name)
        
        if not testcase_id:
            logging.error(f"TestLink response missing testcase_id: {result}")
            return jsonify({
                "success": False,
                "error": "La réponse de TestLink ne contient pas d'ID de test case",
                "response": result
            }), 500

        # Récupération du nom de la suite
        suite_name = ''
        try:
            suite_info = tlc.getTestSuiteByID(data['testsuiteid'])
            suite_name = suite_info.get('name', 'Unnamed Suite')
            logging.debug(f"Suite name: {suite_name}")
        except Exception as e:
            logging.warning(f"Impossible de récupérer le nom de la suite: {e}")

        # Récupération robuste du nom du projet
        project_name = 'Unnamed Project'
        try:
            project_info = tlc.getTestProjectByID(data['testprojectid'])
            if project_info and 'name' in project_info:
                project_name = project_info['name']
                logging.debug(f"Project name retrieved: {project_name}")
            else:
                logging.warning(f"Project info malformé: {project_info}")
        except Exception as e:
            logging.error(f"Erreur récupération projet: {e}")
            try:
                # Fallback - essai alternatif
                projects = tlc.getProjects()
                for p in projects:
                    if str(p['id']) == str(data['testprojectid']):
                        project_name = p.get('name', 'Unnamed Project')
                        break
            except Exception as fallback_e:
                logging.error(f"Fallback failed: {fallback_e}")

        # Enregistrement en base de données
        db_success = add_to_database(
            project_id=data['testprojectid'],
            project_name=project_name,
            suite_id=data['testsuiteid'],
            suite_name=suite_name,
            testcase_id=testcase_id,
            testcase_name=testcase_name
        )
        
        if not db_success:
            logging.error("Échec de l'enregistrement en base de données")
            return jsonify({
                'success': False,
                'error': 'La suite a été créée mais pas enregistrée en base'
            }), 500

        return jsonify({
            "success": True,
            "testcase_id": testcase_id,
            "testcase_name": testcase_name,
            "project_name": project_name  # Retourne aussi le nom pour vérification
        })

    except Exception as e:
        logging.error(f"Erreur dans create_testcase: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Erreur serveur: {str(e)}",
            "received_data": data
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
@app.route('/api/feature-mappings', methods=['GET'])
def get_feature_mappings():
    testlink_case_id = request.args.get('testlink_case_id')
    
    if not testlink_case_id:
        return jsonify({"error": "Le paramètre testlink_case_id est requis"}), 400

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Modifiez la requête pour récupérer tous les scénarios
        query = """
        SELECT id, file_name, feature_name, scenario_title, similarity_score 
        FROM Mapping
        WHERE testcase_id = %s
        ORDER BY similarity_score DESC
        """
        
        cursor.execute(query, (testlink_case_id,))
        results = cursor.fetchall()
        
        mappings = []
        for result in results:
            mappings.append({
                "id": result[0],
                "file_name": result[1],
                "feature_name": result[2],
                "scenario_title": result[3],
                "similarity_score": result[4]
            })
            
        return jsonify(mappings)  # Retourne tous les mappings
            
    except Exception as e:
        print(f"Erreur lors de la récupération des mappings: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()



app.config['UPLOAD_FOLDER'] = os.path.abspath('uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  

ALLOWED_EXTENSIONS = {'feature'}


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def allowed_file(filename):
    
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_feature_file(filepath):
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    file_stats = os.stat(filepath)
    metadata = {
        'lastModified': datetime.fromtimestamp(file_stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        'size': f"{file_stats.st_size} bytes"
    }
    
    return {
        'content': content,
        'metadata': metadata
    }

@app.route('/api/import-features', methods=['POST'])
def import_features():
    """Endpoint to import .feature files."""
    if 'files' not in request.files:
        logger.error("No files part in request")
        return jsonify({'error': 'No files part'}), 400
    
    files = request.files.getlist('files')
    results = []
    
    for file in files:
        if file.filename == '':
            continue
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            base, ext = os.path.splitext(filename)
            counter = 1
            unique_filename = filename
            while os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)):
                unique_filename = f"{base}_{counter}{ext}"
                counter += 1
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            logger.info(f"Saving file: {filepath}")
            
            file.save(filepath)
            parsed_content = parse_feature_file(filepath)
            parsed_content['filename'] = unique_filename
            results.append(parsed_content)
    
    if not results:
        logger.error("No valid feature files uploaded")
        return jsonify({'error': 'No valid feature files uploaded'}), 400
    
    logger.info(f"Successfully imported {len(results)} files")
    return jsonify({
        'success': True,
        'count': len(results),
        'files': results
    })

@app.route('/api/feature-content', methods=['GET'])
def get_feature_content():
    """Endpoint to retrieve content of a .feature file."""
    try:
        file_name = request.args.get('file_name')
        if not file_name:
            logger.error("Missing file_name parameter")
            return jsonify({"error": "Paramètre file_name requis"}), 400
        
        UPLOAD_DIR = Path(app.config['UPLOAD_FOLDER'])
        file_path = (UPLOAD_DIR / file_name).resolve()
        
        if not str(file_path).startswith(str(UPLOAD_DIR.resolve())):
            logger.error(f"Path traversal attempt: {file_name}")
            return jsonify({"error": "Accès non autorisé"}), 403
        
        if not file_path.exists():
            available_files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.feature')]
            logger.error(f"File not found: {file_path}. Available files: {available_files}")
            return jsonify({
                "error": "Fichier non trouvé",
                "available_files": available_files
            }), 404
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        logger.info(f"Successfully loaded file: {file_name}")
        return jsonify({
            "content": content,
            "file_name": file_name,
            "status": "success",
            "lastModified": parse_feature_file(file_path)['metadata']['lastModified'],
            "size": parse_feature_file(file_path)['metadata']['size']
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        return jsonify({"error": str(e), "type": type(e).__name__}), 500

@app.route('/api/list-features', methods=['GET'])
def list_features():
    """Endpoint to list all available .feature files (for debugging)."""
    try:
        UPLOAD_DIR = Path(app.config['UPLOAD_FOLDER'])
        feature_files = [f for f in os.listdir(UPLOAD_DIR) if f.endswith('.feature')]
        logger.info(f"Listing feature files: {feature_files}")
        return jsonify({
            "success": True,
            "files": feature_files
        })
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}", exc_info=True)
        return jsonify({"error": str(e), "type": type(e).__name__}), 500    


@app.route('/api/matching/match', methods=['POST'])
def match_features():
    

    try:
        data = request.get_json()
        
       
        project_name = data.get('project_name') or data.get('projectName')
        if not project_name:
            return jsonify({"error": "Le paramètre 'project_name' est requis"}), 400

        features = data.get('features', [])
        if not features:
            return jsonify({"error": "Aucune feature fournie"}), 400

        
        testcases = get_testcases(project_name)
        if not testcases:
            return jsonify({"error": f"Aucun test case trouvé pour le projet {project_name}"}), 404
            
        testcase_names = [tc["name"] for tc in testcases]
        testcase_id_map = {tc["name"]: tc["id"] for tc in testcases}

        matched = []
        unmatched = []

        
        for feature in features:
            feature_name = feature.get('feature_name') or feature.get('featureName')
            if not feature_name:
                continue

            best_match = process.extractOne(
                feature_name, 
                testcase_names, 
                scorer=fuzz.token_sort_ratio,
                score_cutoff=60  
            )

            if best_match and best_match[1] >= 50:
                for scenario in feature.get('scenarios', []):
                  matched.append({
                    "file_name": feature.get('file_name'),
                    "feature_name": feature_name,
                    "scenario_title": scenario.get('title', scenario.get('name', '')),  # Garantit un champ scenario_title
                    "scenario": scenario,  
                    "testcase_name": best_match[0],
                    "testcase_id": testcase_id_map[best_match[0]],
                    "similarity_score": best_match[1]
                })
            else:
                unmatched.append({
                    "file_name": feature.get('file_name') or feature.get('fileName'),
                    "feature_name": feature_name,
                    "match_found": False
                })

        return jsonify({
            "success": True,
            "matched": matched,
            "unmatched": unmatched,
            "stats": {
                "matched_count": len(matched),
                "unmatched_count": len(unmatched)
            }
        })

    except Exception as e:
        app.logger.error(f"Erreur lors du matching: {str(e)}")
        return jsonify({
            "error": "Erreur interne du serveur",
            "details": str(e)
        }), 500
def get_db_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
            
        return conn
    except Exception as e:
        app.logger.error(f"Échec de connexion à la base de données: {str(e)}")
        raise   
def get_testcases(project_name: str) -> List[Dict[str, Any]]:
    
    conn = get_db_connection()
    cursor = conn.cursor()
    

    tlc = TestlinkAPIClient(TL_URL, TL_DEVKEY)

    # Récupération du projet
    
    project = tlc.getTestProjectByName(project_name)
    project_id = project['id']
    
    try:
        cursor.execute("""
            SELECT testcase_id,
            testcase_name 
            FROM testlinkdb
            WHERE project_id  = %s
        """, (project_id,))
        
        return [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
    finally:
        cursor.close()
        conn.close() 


@app.route('/api/matching/save', methods=['POST'])
def save_matching():
    try:
        
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400

        data = request.get_json()
        
        
        if 'matched' not in data or not isinstance(data['matched'], list):
            return jsonify({"error": "Le champ 'matched' est requis et doit être une liste"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Mapping (
                id SERIAL PRIMARY KEY,
                file_name TEXT NOT NULL,
                feature_name TEXT NOT NULL,
                scenario_title TEXT NOT NULL,
                testcase_id TEXT NOT NULL,
                similarity_score INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT unique_mapping UNIQUE (feature_name, scenario_title)
            )
        """)
        conn.commit()

        
        success_count = 0
        errors = []

        for item in data['matched']:
            try:
               
                required_fields = {
                    'file_name': str,
                    'feature_name': str,
                    'scenario_title': str,
                    'testcase_id': (str, int),
                    'similarity_score': (int, float)
                }
                
                for field, field_type in required_fields.items():
                    if field not in item:
                        raise ValueError(f"Champ manquant: {field}")
                    if not isinstance(item[field], field_type):
                        raise ValueError(f"Type invalide pour {field}")

                cursor.execute("""
                    INSERT INTO Mapping (
                        file_name, feature_name, scenario_title,
                        testcase_id, similarity_score
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (feature_name, scenario_title) DO UPDATE SET
                        testcase_id = EXCLUDED.testcase_id,
                        similarity_score = EXCLUDED.similarity_score
                """, (
                    item['file_name'],
                    item['feature_name'],
                    item['scenario_title'],
                    str(item['testcase_id']),
                    int(item['similarity_score'])
                ))
                success_count += 1
            except Exception as e:
                errors.append(str(e))
                continue

        conn.commit()
        return jsonify({
            "success": True,
            "saved": success_count,
            "errors": errors,
            "message": f"{success_count} enregistrements sauvegardés, {len(errors)} erreurs"
        })

    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
        app.logger.error(f"Erreur serveur: {str(e)}")
        return jsonify({
            "error": "Erreur interne du serveur",
            "details": str(e)
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()
 

def handle_save_matching():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    data = request.get_json()
    return save_matching(data.get('matched'))          




logging.basicConfig(level=logging.DEBUG, filename='app.log', format='%(asctime)s - %(levelname)s - %(message)s')

from flask import jsonify, send_file, request
from io import StringIO
import csv
import logging
from datetime import datetime
from rapidfuzz import process, fuzz

from flask import jsonify, send_file, request
from io import StringIO
import csv
import logging
from datetime import datetime
from rapidfuzz import process, fuzz


from io import BytesIO  # Modification importante ici

from io import BytesIO
import csv
from datetime import datetime
import logging

@app.route('/api/matching/report/unmatched', methods=['POST'])
def generate_unmatched_report():
    try:
        if not request.is_json:
            return jsonify({
                "status": "error",
                "message": "Content-Type must be application/json"
            }), 415

        data = request.get_json()
        if not data:
            return jsonify({
                "status": "error", 
                "message": "Request body cannot be empty"
            }), 400

        # Extraction et validation des paramètres
        project_name = data.get('project_name') or data.get('projectName', '').strip()
        features = data.get('features', [])

        if not project_name:
            return jsonify({
                "status": "error",
                "message": "Project name is required"
            }), 400

        if not features or not isinstance(features, list):
            return jsonify({
                "status": "error",
                "message": "Features must be a non-empty array"
            }), 400

        # Récupération des test cases
        testcases = get_testcases(project_name)
        if not testcases:
            return jsonify({
                "status": "error",
                "message": "No test cases found for this project"
            }), 404

        # Processus de matching
        testcase_names = [tc["name"] for tc in testcases]
        unmatched = []

        for feature in features:
            feature_name = (feature.get('feature_name') or feature.get('featureName', '')).strip()
            if not feature_name:
                continue

            best_match = process.extractOne(
                feature_name,
                testcase_names,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=60
            )

            if not best_match:
                unmatched.append({
                    "file_name": feature.get('file_name') or feature.get('fileName', 'Unknown'),
                    "feature_name": feature_name
                })

        if not unmatched:
            return jsonify({
                "status": "success",
                "message": "All features matched successfully",
                "data": []
            }), 200

        
        text_buffer = StringIO()
        writer = csv.writer(text_buffer, delimiter=',')
        
       
        writer.writerow(['File', 'Feature', 'Status'])
        for item in unmatched:
            writer.writerow([item['file_name'], item['feature_name'], 'NOT_MATCHED'])
        
        csv_content = text_buffer.getvalue()
        output = BytesIO()
        output.write(csv_content.encode('utf-8-sig'))  
        output.seek(0)

        # Envoi du fichier
        return send_file(
            output,
            mimetype='text/csv; charset=utf-8-sig',
            as_attachment=True,
            download_name=f"unmatched_report_{datetime.now().strftime('%Y%m%d')}.csv"
        )

    except Exception as e:
        logging.exception("Error generating unmatched report")
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

@app.route("/")
def home():
    return "✅ Serveur Flask opérationnel"
@app.route('/api/sync-testlink', methods=['POST'])
def sync_testlink():
    try:
        
        tlc = OfficialTestlinkClient(TL_URL, TL_DEVKEY)
        synch(tlc)

        return jsonify({
            "success": True,
            "message": "Synchronisation terminée avec succès",
            
        }), 200

    except Exception as e:
        print(f"❌ Erreur globale de synchronisation : {e}")
        
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Échec de la synchronisation"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=4000, debug=True)
