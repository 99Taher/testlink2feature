#ce code est un code qui permet de créer et exucuter un chatbot qui permet de transformer le language naturel en un lanquage 
#sql et executer le langauge sql pour manupulier un tableau testlinkdb 
from flask import Flask, render_template, request, jsonify
import psycopg2
import requests

app = Flask(__name__)


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


#def generate_sql_local(user_input):
    schema = get_schema()
    prompt = f"""
Tu es un assistant SQL. Tu dois générer UNIQUEMENT une requête SQL valide, sans commentaire ni explication.
N'utilise que les colonnes suivantes : project_id, project_name, suite_id, suite_name, testcase_id, testcase_name.
Schéma :
{schema}
Question : {user_input}
Requête SQL :
"""
    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            }
        )
        sql = response.json().get("response", "").strip().rstrip(";")

        # ✅ Ajout automatique d’un LIMIT pour éviter les requêtes massives
        if sql.lower().startswith("select") and "limit" not in sql.lower():
            sql += " LIMIT 50"

        print("💡 SQL généré :", sql)
        return sql
    except Exception as e:
        print("❌ Erreur de génération LLM :", e)
        return None


def execute_query(query):
    try:
        conn = psycopg2.connect(
            dbname="testlink_db",
            user="postgres",
            password="root",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()
        print("Requête SQL exécutée :", query)
        cursor.execute(query)
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        conn.close()
        return columns, result
    except Exception as e:
        print("❌ Erreur SQL :", e)
        return [], [("Erreur SQL", str(e))]

# ✅ Route du chatbot
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"response": "❗Veuillez saisir une question."})

    query = generate_sql_local(user_message)
    if not query:
        return jsonify({"response": "❌ Erreur lors de la génération de la requête SQL."})

    columns, result = execute_query(query)
    if columns:
        formatted_result = "\n".join([", ".join(map(str, row)) for row in result])
        return jsonify({"response": f"✅ Résultats :\n{formatted_result}"})
    else:
        return jsonify({"response": f"⚠️ Aucune donnée trouvée ou erreur : {result[0][1]}"})


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)
