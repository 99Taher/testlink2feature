import React, { useState } from 'react';

const TestCaseDetails = () => {
  const [selectedTestCase, setSelectedTestCase] = useState(null);
  const [featureDetails, setFeatureDetails] = useState(null);
  
  // Données simulées - à remplacer par votre vrai appel API
  const testCases = [
    { id: 1, name: "Test Login", testlink_case_id: "TC-001" },
    { id: 2, name: "Test Logout", testlink_case_id: "TC-002" }
  ];

  // Simulez les données de mapping
  const featureMappings = [
    {
      testlink_case_id: "TC-001",
      feature_name: "Authentication",
      scenario_title: "User login",
      file_name: "authentication.feature",
      similarity_score: 95
    }
  ];

  const handleTestCaseClick = (testCase) => {
    setSelectedTestCase(testCase);
    
    // Trouver les détails du feature file
    const mapping = featureMappings.find(
      m => m.testlink_case_id === testCase.testlink_case_id
    );
    
    setFeatureDetails(mapping || null);
  };

  return (
    <div className="test-case-container">
      <div className="test-case-list">
        <h3>Test Cases</h3>
        <ul>
          {testCases.map(testCase => (
            <li 
              key={testCase.id}
              onClick={() => handleTestCaseClick(testCase)}
              className={selectedTestCase?.id === testCase.id ? 'selected' : ''}
            >
              {testCase.name} ({testCase.testlink_case_id})
            </li>
          ))}
        </ul>
      </div>

      <div className="feature-details-panel">
        {selectedTestCase && (
          <>
            <h3>Détails du Test Case</h3>
            <p><strong>Nom:</strong> {selectedTestCase.name}</p>
            <p><strong>ID:</strong> {selectedTestCase.testlink_case_id}</p>
            
            {featureDetails ? (
              <>
                <h4>Feature File Associé</h4>
                <p><strong>Fichier:</strong> {featureDetails.file_name}</p>
                <p><strong>Feature:</strong> {featureDetails.feature_name}</p>
                <p><strong>Scénario:</strong> {featureDetails.scenario_title}</p>
                <p><strong>Score de similarité:</strong> {featureDetails.similarity_score}%</p>
              </>
            ) : (
              <div className="no-feature-warning">
                ⚠️ Ce test case n'a pas de feature file associé
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default TestCaseDetails;