from flask import Flask, jsonify, request,send_file
from werkzeug.utils import secure_filename
from flask_cors import CORS
import os
import xml.etree.ElementTree as ET
from rapidfuzz import process, fuzz
import csv
from io import StringIO
from typing import List, Dict, Any

from testlin import (  # Importez vos fonctions depuis creation.py
    get_projects,
    create_test_suite,
    create_test_case,
    add_to_database,
    get_test_cases_for_suite,
    extract_steps,
    import_from_xml,
    process_xml_import,
    extract_all_feature_data,
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




UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xml'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
AUTHOR_LOGIN = "admin"




def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/import/xml', methods=['POST'])
def handle_xml_import():
    # Vérification du fichier
    if 'xmlFile' not in request.files:
        return jsonify({"success": False, "error": "Aucun fichier fourni"}), 400
    
    file = request.files['xmlFile']
    if file.filename == '':
        return jsonify({"success": False, "error": "Nom de fichier vide"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({"success": False, "error": "Seuls les fichiers XML sont acceptés"}), 400

    # Vérification du projet
    project_id = request.form.get('projectId')
    if not project_id:
        return jsonify({"success": False, "error": "Project ID manquant"}), 400

    try:
        # Sauvegarde temporaire
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(temp_path)

        # Parse XML
        tree = ET.parse(temp_path)
        root = tree.getroot()
        xml_suite_id = int(root.attrib['id'])
        xml_suite_name = root.attrib['name']

        # Nom de la suite (peut être personnalisé)
        
        suites = tlc.getFirstLevelTestSuitesForTestProject(int(project_id))
        suite = next((s for s in suites if s['name'] == xml_suite_name), None)
        
        if not suite:
            suite = tlc.createTestSuite(project_id, xml_suite_name, "Importé depuis XML")[0]
            testsuite_id = int(suite['id'])
        else:
            testsuite_id = int(suite['id'])

        # Traitement des test cases
        success_count = 0
        error_count = 0
        testcases = []

        for testcase in root.findall("testcase"):
            name = testcase.attrib.get("name", "Unnamed TestCase")
            try:
                summary = (testcase.find("summary").text or "").strip()
                preconditions = (testcase.find("preconditions").text or "").strip()
                
                # Extraction des étapes
                steps = []
                for step_elem in testcase.findall(".//step"):
                    step_number = int(step_elem.find("step_number").text.strip())
                    actions = (step_elem.find("actions").text or "").strip()
                    expected = (step_elem.find("expectedresults").text or "").strip()
                    steps.append({
                        "step_number": step_number,
                        "actions": actions,
                        "expectedresults": expected,
                        "execution_type": 1
                    })

                # Création dans TestLink
                response = tlc.createTestCase(
                    testcasename=name,
                    testsuiteid=testsuite_id,
                    testprojectid=project_id,
                    authorlogin=AUTHOR_LOGIN,
                    summary=summary,
                    preconditions=preconditions,
                    steps=steps
                )

                if isinstance(response, list) and response:
                    testcases.append({
                        "name": name,
                        "id": response[0]['id'],
                        "status": "success"
                    })
                    success_count += 1
                else:
                    raise Exception("Réponse inattendue de TestLink")
                db_success = add_to_database(
                project_id=project_id,
                project_name=request.form.get('project_name', ''),
                suite_id=testsuite_id,
                suite_name=xml_suite_name,
                testcase_id=response[0]['id'],
                testcase_name=name
                )
            
                if not db_success:
                  testcases[-1]['status'] = 'db_failed'
                  testcases[-1]['error'] = 'Erreur enregistrement base de données'
                  error_count += 1
                continue

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
            

    except ET.ParseError:
        return jsonify({"success": False, "error": "Fichier XML malformé"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)


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
    project_name=data.get('project_name'),
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
@app.route('/api/import/features', methods=['POST'])
def import_features():
    """Endpoint pour importer des fichiers feature"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files part'}), 400
    
    files = request.files.getlist('files')
    results = []
    
    for file in files:
        if file.filename == '':
            continue
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Créer le dossier s'il n'existe pas
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            file.save(filepath)
            parsed_content = parse_feature_file(filepath)
            
            # Ajouter le nom du fichier aux résultats
            parsed_content['filename'] = filename
            results.append(parsed_content)
            
            # Supprimer le fichier après traitement (optionnel)
            os.remove(filepath)
    
    if not results:
        return jsonify({'error': 'No valid feature files uploaded'}), 400
    
    return jsonify({
        'success': True,
        'count': len(results),
        'files': results
    })     


@app.route('/api/matching/match', methods=['POST'])
def match_features():
    

    try:
        data = request.get_json()
        
        # Validation des données
        project_name = data.get('project_name') or data.get('projectName')
        if not project_name:
            return jsonify({"error": "Le paramètre 'project_name' est requis"}), 400

        features = data.get('features', [])
        if not features:
            return jsonify({"error": "Aucune feature fournie"}), 400

        # Récupérer les testsuites (au lieu des testcases)
        testcases = get_testcases(project_name)
        if not testcases:
            return jsonify({"error": f"Aucun test case trouvé pour le projet {project_name}"}), 404
            
        testcase_names = [tc["name"] for tc in testcases]
        testcase_id_map = {tc["name"]: tc["id"] for tc in testcases}

        matched = []
        unmatched = []

        # Faire le matching entre feature_name et testsuite_name
        for feature in features:
            feature_name = feature.get('feature_name') or feature.get('featureName')
            if not feature_name:
                continue

            best_match = process.extractOne(
                feature_name, 
                testcase_names, 
                scorer=fuzz.token_sort_ratio,
                score_cutoff=60  # Seuil de similarité à 70%
            )

            if best_match and best_match[1] >= 50:
                for scenario in feature.get('scenarios', []):
                  matched.append({
                    "file_name": feature.get('file_name'),
                    "feature_name": feature_name,
                    "scenario_title": scenario.get('title', scenario.get('name', '')),  # Garantit un champ scenario_title
                    "scenario": scenario,  # Conserve l'objet complet pour référence
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
        conn = psycopg2.connect(
            dbname="testlink_db",
            user="postgres",
            password="root",
            host="localhost",
            port="5432"
        )
        return conn
    except Exception as e:
        app.logger.error(f"Échec de connexion à la base de données: {str(e)}")
        raise   
def get_testcases(project_name: str) -> List[Dict[str, Any]]:
    """Récupère les test cases depuis la base TestLink"""
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
        # Vérification du Content-Type
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400

        data = request.get_json()
        
        # Validation des données
        if 'matched' not in data or not isinstance(data['matched'], list):
            return jsonify({"error": "Le champ 'matched' est requis et doit être une liste"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Création de table sécurisée
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

        # Insertion des données
        success_count = 0
        errors = []

        for item in data['matched']:
            try:
                # Validation des champs requis
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
def _build_cors_preflight_response():
    response = jsonify()
    response.headers.add("Access-Control-Allow-Origin", "http://localhost:5173")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add("Access-Control-Allow-Methods", "POST")
    return response  

def handle_save_matching():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    data = request.get_json()
    return save_matching(data.get('matched'))          

from flask import send_file
from io import StringIO
import csv

import logging
from datetime import datetime

import logging
from io import StringIO
import csv
from flask import jsonify, send_file

import logging
from datetime import datetime

@app.route('/api/matching/report/unmatched', methods=['POST'])
def generate_unmatched_report():
    """Génère un rapport CSV des scénarios non matchés"""
    try:
        logging.info(f"Requête reçue pour générer le rapport - {datetime.now()}")
        
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Requête sécurisée avec gestion des NULL
            query = """
                SELECT 
                    COALESCE(f.file_name, 'N/A') as file_name,
                    COALESCE(f.feature_name, 'N/A') as feature_name,
                    COALESCE(s.title, 'N/A') as scenario_title
                FROM features f
                JOIN scenarios s ON f.id = s.feature_id
                LEFT JOIN matched_scenarios m ON s.id = m.scenario_id
                WHERE m.scenario_id IS NULL
                ORDER BY f.file_name
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            if not results:
                logging.warning("Aucun scénario non matché trouvé")
                return jsonify({
                    "status": "success",
                    "message": "Aucun scénario non matché trouvé",
                    "timestamp": datetime.now().isoformat()
                }), 200

            # Génération CSV
            output = StringIO()
            writer = csv.writer(output, delimiter=';')
            writer.writerow(['Fichier', 'Feature', 'Scénario'])
            writer.writerows(results)
            output.seek(0)
            
            logging.info(f"Rapport généré avec {len(results)} entrées")
            return send_file(
                output,
                mimetype='text/csv; charset=utf-8',
                as_attachment=True,
                download_name=f"unmatched_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
            )

    except Exception as e:
        logging.error(f"Erreur critique: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": "Erreur serveur",
            "details": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

    finally:
        if 'conn' in locals():
            conn.close()

@app.route("/")
def home():
    return "✅ Serveur Flask opérationnel"
@app.route('/api/sync-testlink', methods=['POST'])
def sync_testlink():
    try:
        # Initialisation de l'API TestLink
        tlc = OfficialTestlinkClient(TL_URL, TL_DEVKEY)
        
        # Connexion à la base de données
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