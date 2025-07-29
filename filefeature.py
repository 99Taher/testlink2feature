# ce code permet la recuperation d'un dossier de feature file et extraire les features names et les sceanarios  
import os

def parse_feature_file(path):
    feature_title = None
    scenarios = []
    current_scenario = None
    in_examples = False
    examples = []

    with open(path, 'r', encoding='utf-8') as file:
        for line in file:
            stripped = line.strip()

            if stripped.startswith("Feature:"):
                feature_title = stripped[len("Feature:"):].strip()

            elif stripped.startswith("Scenario:") or stripped.startswith("Scenario Outline:"):
                if current_scenario:
                    if examples:
                        current_scenario["examples"] = examples
                        examples = []
                current_scenario = {
                    "type": "Scenario Outline" if "Outline" in stripped else "Scenario",
                    "name": stripped.split(":", 1)[1].strip(),
                    "steps": [],
                }
                scenarios.append(current_scenario)
                in_examples = False

            elif any(stripped.startswith(k) for k in ("Given", "When", "Then", "And", "But")):
                if current_scenario:
                    current_scenario["steps"].append(stripped)

            elif stripped.startswith("Examples:"):
                in_examples = True
                examples = []

            elif in_examples and stripped.startswith("|"):
                row = [cell.strip() for cell in stripped.strip('|').split('|')]
                examples.append(row)

    if current_scenario and examples:
        current_scenario["examples"] = examples

    return feature_title, scenarios


def extract_all_feature_data(folder_path):
    all_scenarios = []
    for filename in os.listdir(folder_path):
        if filename.endswith(".feature"):
            file_path = os.path.join(folder_path, filename)
            try:
                feature_title, scenarios = parse_feature_file(file_path)
                for scenario in scenarios:
                    all_scenarios.append({
                        "file_name": filename,
                        "feature_name": feature_title,
                        "scenario_title": scenario["name"],
                        "type": scenario["type"],
                        "steps": scenario["steps"],
                        "examples": scenario.get("examples", [])
                    })
            except Exception as e:
                print(f"❌ Erreur dans {filename}: {e}")
    return all_scenarios


# 📂 Dossier contenant les fichiers .feature
folder_path = r"C:\Users\user\Downloads\01_smoke\01_smoke"

# 📥 Extraction
scenarios = extract_all_feature_data(folder_path)

# 📤 Affichage
for s in scenarios:
    print(f"\n📄 Fichier: {s['file_name']}")
    print(f"✅ Feature: {s['feature_name']}")
    print(f"🔹 {s['type']}: {s['scenario_title']}")
    for step in s['steps']:
        print(f"    {step}")
    if s['type'] == "Scenario Outline" and s['examples']:
        print("    📊 Examples:")
        for row in s['examples']:
            print(f"      {row}")