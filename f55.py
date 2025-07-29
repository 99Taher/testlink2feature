def extract_scenarios_from_feature(file_path):
    scenarios = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip().startswith("Scenario:"):
                scenario_name = line.strip().replace("Scenario:", "").strip()
                scenarios.append(scenario_name)
    return scenarios

if __name__ == "__main__":
    file_path = r"C:\Users\user\Downloads\01_smoke\01_smoke\01_validate_file_write_62.x_message.feature"
    scenarios = extract_scenarios_from_feature(file_path)
    
    print("feature name : \n------")
    
    print("Scénarios trouvés - "  )
    for s in scenarios:
        

      print("***",s,"***")