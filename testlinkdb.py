# ce code permet la recupération de données du testlinket et  l'enregistrement dans le tableau testlinkdb 
import psycopg2
from testlink import TestlinkAPIClient
from adddb import add_db

url = "http://localhost/testlink/testlink-1.9.20/lib/api/xmlrpc/v1/xmlrpc.php"
devKey = "66782e2ca0c3b440aca030c52c539bdb"
tlc = TestlinkAPIClient(url, devKey)

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
        project_id TEXT,
        project_name TEXT,
        suite_id TEXT,
        suite_name TEXT,
        testcase_id TEXT PRIMARY KEY,
        testcase_name TEXT
    );
""")


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

    for suite in test_suites:
     suite_id = suite['id']
     suite_name = suite['name']

     test_cases = tlc.getTestCasesForTestSuite(testsuiteid=suite_id, deep=True)

     if not test_cases:
         add_db(project_id, project_name, suite_id, suite_name, f'no_tc_{suite_id}', '**')
        

     else:
        for tc in test_cases:
            case_id = tc["id"]
            case_name = tc["name"]

            try:
                add_db(project_id,project_name,suite_id,suite_name,case_id,case_name)
                total_cases += 1
            except Exception as insert_err:
                print(f"    ❌ Erreur insertion test case {case_id} : {insert_err}")
            


conn.commit()
conn.close()

print(f"\n✅ Synchronisation terminée. Total cas de test insérés : {total_cases}")