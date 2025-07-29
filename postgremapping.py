import psycopg2

# Connexion à la base PostgreSQL
conn = psycopg2.connect(
    dbname="testlink_db",
    user="postgres",         # ⚠️ adapte selon ton user
    password="root", # ⚠️ adapte ton mot de passe
    host="localhost",
    port="5432",
    sslmode="disable"
)

cursor = conn.cursor()

# Création de la table
create_table_query = """
CREATE TABLE IF NOT EXISTS feature_testlink_mapping (
    id SERIAL PRIMARY KEY,
    feature_name TEXT NOT NULL,
    scenario_title TEXT NOT NULL,
    testlink_case_id TEXT NOT NULL
);
"""

cursor.execute(create_table_query)
conn.commit()

print("✅ Table créée avec succès.")

# Fermeture
cursor.close()
conn.close()