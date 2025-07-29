# ce code permet d'assurer le mapping entre les testcases et les features files par le creation de 2 liste matched et unmatched
#ensuite l'enregistrement de liste matched dans la base de données mapping
from filefeature import extract_all_feature_data
from test import get_testcases_from_testlink
import psycopg2
from rapidfuzz import process, fuzz


folder_path = r"C:\Users\user\Downloads\01_smoke\01_smoke"
feature_scenarios = extract_all_feature_data(folder_path)
project_name = input("Nom du projet TestLink : ")
testcases = get_testcases_from_testlink(project_name)
repport=[]

testcase_names = [tc["testcase_name"] for tc in testcases]
testcase_id_map = {tc["testcase_name"]: tc["testcase_id"] for tc in testcases}


from rapidfuzz import process, fuzz

matched = []
unmatched = []

for fs in feature_scenarios:
    scenario = fs["scenario_title"]
    best_match = process.extractOne(scenario, testcase_names, scorer=fuzz.partial_ratio)

    if best_match and best_match[1] >= 50:
        matched.append({
            "file_name": fs["file_name"],
            "feature_name": fs["feature_name"],
            "scenario_title": scenario,
            "testlink_case_id": testcase_id_map[best_match[0]],
            "similarity_score": best_match[1]
        })
    else:
        unmatched.append({
            "file_name": fs["file_name"],
            "feature_name": fs["feature_name"],
            "scenario_title": scenario,
            "match_found": False
        })   
import csv

with open("unmatched_features_report.csv", "w", newline='', encoding="utf-8") as csvfile:
    fieldnames = ["file_name", "feature_name", "scenario_title", "match_found"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    writer.writeheader()
    for row in unmatched:
        writer.writerow(row)

print(f"📝 Rapport généré : {len(unmatched)} features sans test case ont été enregistrées dans 'unmatched_features_report.csv'")

# 📦 Connexion PostgreSQL
conn = psycopg2.connect(
    dbname="testlink_db",
    user="postgres",       # adapte selon ton utilisateur
    password="root",       # adapte selon ton mot de passe
    host="localhost",
    port="5432",
    sslmode="disable"
)
cursor = conn.cursor()


# 📋 Créer la table si elle n'existe pas (ajout colonne similarity_score)
cursor.execute("""
CREATE TABLE IF NOT EXISTS Mapping (
    id SERIAL PRIMARY KEY,
    feature_name TEXT NOT NULL,
    scenario_title TEXT NOT NULL ,
    file_name TEXT NOT NULL,
    testlink_case_id TEXT NOT NULL,
    similarity_score INTEGER NOT NULL,
    CONSTRAINT unique_feature_scenario UNIQUE (feature_name, scenario_title)
    
)
""")


conn.commit()

# 💾 Insertion des correspondances
for row in matched:
    cursor.execute("""
        INSERT INTO Mapping (feature_name, scenario_title, file_name, testlink_case_id, similarity_score)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (scenario_title, feature_name) DO NOTHING
        
    """, (
        row["feature_name"],
        row["scenario_title"],
        row["file_name"],
        row["testlink_case_id"],
        row["similarity_score"]
    ))

conn.commit()
cursor.close()
conn.close()

print(f"✅ {len(matched)} correspondances insérées avec succès dans PostgreSQL.")