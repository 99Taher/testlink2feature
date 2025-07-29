#cette fonction permet de mise a jour du tableau testlinkdb lorsque on faire la creation d'une testsuite ou une testcase 
def add_db(projectid, projectname, suiteid, suitename, caseid, casename):
    import psycopg2
    conn = psycopg2.connect(
        dbname="testlink_db",
        user="postgres",
        password="root",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO testlinkdb (
            project_id, project_name, suite_id, suite_name, testcase_id, testcase_name
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (testcase_id) DO NOTHING;
    """, (projectid, projectname, suiteid, suitename, caseid, casename))
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Ajout en DB : {suiteid} | {caseid} - {casename}")