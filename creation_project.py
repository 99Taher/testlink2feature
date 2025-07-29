from testlink import TestlinkAPIClient, TestLinkHelper

# Configuration
url = "http://localhost/testlink/testlink-1.9.20/lib/api/xmlrpc/v1/xmlrpc.php"  # adapte selon ton serveur
devKey = "66782e2ca0c3b440aca030c52c539bdb"


tlc = TestlinkAPIClient(url, devKey)

# Données du projet
project_name = "MonProjetTest"
project_prefix = "MPT"
notes = "Projet créé automatiquement via l'API"
enable_requirements = 1
enable_test_priority = 1
enable_automation = 1
enable_inventory = 0
is_active = 1
is_public = 1


response = tlc.createTestProject(
    testprojectname=project_name,
    testcaseprefix=project_prefix,
    notes=notes,
    enableRequirements=enable_requirements,
    enableTestPriority=enable_test_priority,
    enableAutomation=enable_automation,
    enableInventory=enable_inventory,
    active=is_active,
    public=is_public
)


print("Projet créé :", response)