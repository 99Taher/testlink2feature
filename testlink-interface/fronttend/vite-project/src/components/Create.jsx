import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Create.css';


const Create = ({ projects, onSuccess, onCancel }) => {
  const [state, setState] = useState({
    activeTab: 'manual',
    step: 1,
    projectId: '',
    projectName: '',
    actionType: '',
    suiteName: '',
    suiteDescription: '',
    existingSuites: [],
    selectedSuiteId: '',
    testCases: [{
      name: '',
      summary: '',
      steps: [{
        stepNumber: 1,
        actions: '',
        expectedResults: '',
        executionType: 1
      }]
    }],
    xmlFile: null,
    loading: false,
    error: null,
    formErrors: {},
    importResults: null
  });

  const {
    activeTab, step, projectId, projectName, actionType,
    suiteName, suiteDescription, existingSuites,
    selectedSuiteId, testCases, xmlFile, loading,
    error, formErrors, importResults
  } = state;

  useEffect(() => {
    if (projectId && actionType === 'testcase') {
      fetchTestSuites();
    }
  }, [projectId, actionType]);

  const fetchTestSuites = async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      const response = await axios.get(`http://localhost:4000/api/suites?project_id=${projectId}`);
      setState(prev => ({ 
        ...prev, 
        existingSuites: response.data,
        loading: false 
      }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: `Error loading suites: ${err.response?.data?.message || err.message}`,
        loading: false
      }));
    }
  };

  const validateForm = () => {
    const errors = {};

    if (!projectId) {
      errors.project = 'A project must be selected';
    }

    if (actionType === 'suite') {
      if (!suiteName.trim()) {
        errors.suiteName = 'Le nom de la suite est requis';
      }
    } else if (actionType === 'testcase') {
      if (!selectedSuiteId) {
        errors.suite = 'A suite must be selected';
      }

      testCases.forEach((tc, index) => {
        if (!tc.name.trim()) {
          errors[`testCaseName_${index}`] = 'Name of the required test case';
        }
        if (!tc.steps[0].actions.trim()) {
          errors[`actions_${index}`] = 'Actions requises';
        }
        if (!tc.steps[0].expectedResults.trim()) {
          errors[`expectedResults_${index}`] = 'Résultats attendus requis';
        }
      });
    }

    setState(prev => ({ ...prev, formErrors: errors }));
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      if (actionType === 'suite') {
        await createTestSuite();
      } else {
        await createTestCases();
      }
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: err.response?.data?.error || err.message || 'Erreur création'
      }));
    } finally {
      setState(prev => ({ ...prev, loading: false }));
    }
  };

  const createTestSuite = async () => {
    const response = await axios.post('http://localhost:4000/api/create/suite', {
      project_id: parseInt(projectId),
      suite_name: suiteName,
      suite_description: suiteDescription
    });

    if (!response.data.success) {
      throw new Error(response.data.error || "Error creating suite");
    }

    onSuccess(`Suite "${suiteName}"successfully created`);
  };

  const createTestCases = async () => {
  const results = [];
  for (const tc of testCases) {
    try {
      const response = await axios.post('http://localhost:4000/api/create/testcase', {
        testprojectid: parseInt(projectId),
        testsuiteid: parseInt(selectedSuiteId),
        testcasename: tc.name,
        summary: tc.summary,
        project_name: projectName, // Add project_name (ensure this is defined in your component)
        steps: tc.steps.map(step => ({
          step_number: step.stepNumber,
          actions: step.actions,
          expected_results: step.expectedResults,
          execution_type: step.executionType
        }))
      });
      results.push(response);
    } catch (error) {
      results.push({
        data: {
          success: false,
          error: error.response?.data?.error || error.message
        }
      });
    }
  }

  const failed = results.filter(r => !r.data.success);
  if (failed.length > 0) {
    throw new Error(`${failed.length} test case(s) failed: ${failed.map(r => r.data.error).join(', ')}`);
  }

  onSuccess(`${testCases.length} test case(s) successfully created`);
};

  const handleXmlImport = async (e) => {
  e.preventDefault();
  if (!xmlFile) {
    setState(prev => ({
      ...prev,
      error: 'Veuillez sélectionner un fichier XML',
      loading: false
    }));
    return;
  }
  setState(prev => ({ ...prev, loading: true, error: null }));

  try {
    const formData = new FormData();
    formData.append('xmlFile', xmlFile);
    formData.append('projectId', projectId);

    // Log FormData content
    for (let [key, value] of formData.entries()) {
      console.log(`${key}: ${value.name || value}`);
    }

    const response = await axios.post(
      'http://localhost:4000/api/import/xml',
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' }
      }
    );

    setState(prev => ({
      ...prev,
      importResults: response.data,
      loading: false
    }));
  } catch (err) {
    setState(prev => ({
      ...prev,
      error: `Erreur: ${err.response?.data?.error || err.message}`,
      loading: false
    }));
  }
};

  const handleChange = (e) => {
  const { name, value, files } = e.target;
  if (name === 'xmlFile' && files[0]) {
    console.log('Selected file:', files[0].name, 'Type:', files[0].type);
  }
  setState(prev => ({
    ...prev,
    [name]: files ? files[0] : value,
    formErrors: {}
  }));
};
  const updateTestCase = (index, field, value) => {
    setState(prev => {
      const updated = [...prev.testCases];
      updated[index][field] = value;
      return { ...prev, testCases: updated, formErrors: {} };
    });
  };

  const updateStep = (caseIndex, stepIndex, field, value) => {
    setState(prev => {
      const updated = [...prev.testCases];
      updated[caseIndex].steps[stepIndex][field] = value;
      return { ...prev, testCases: updated, formErrors: {} };
    });
  };

  const addStep = (testCaseIdx) => {
    setState(prev => {
      const updatedTestCases = [...prev.testCases];
      updatedTestCases[testCaseIdx] = {
        ...updatedTestCases[testCaseIdx],
        steps: [
          ...updatedTestCases[testCaseIdx].steps,
          {
            stepNumber: updatedTestCases[testCaseIdx].steps.length + 1,
            actions: '',
            expectedResults: '',
            executionType: 1
          }
        ]
      };
      return {
        ...prev,
        testCases: updatedTestCases,
        formErrors: {}
      };
    });
  };

  const addTestCase = () => {
    setState(prev => ({
      ...prev,
      testCases: [
        ...prev.testCases,
        {
          name: '',
          summary: '',
          steps: [{
            stepNumber: 1,
            actions: '',
            expectedResults: '',
            executionType: 1
          }]
        }
      ],
      formErrors: {}
    }));
  };

  return (
    <div className="create-container">
      <h2>Creation in TestLink</h2>
      
      {error && <div className="error-message">{error}</div>}

      <div className="tabs">
        <button
          className={activeTab === 'manual' ? 'active' : ''}
          onClick={() => setState(prev => ({ ...prev, activeTab: 'manual' }))}
        >
          Manual Creation
        </button>
        <button
          className={activeTab === 'import' ? 'active' : ''}
          onClick={() => setState(prev => ({ ...prev, activeTab: 'import' }))}
        >
          Import XML
        </button>
      </div>

      {activeTab === 'manual' ? (
        <>
          {step === 1 && (
            <div className="create-step">
              <div className="form-group">
                <label>Project:</label>
                <select 
                  name="projectId"
                  value={projectId} 
                  onChange={handleChange}
                  disabled={loading}
                  className={formErrors.project ? 'error' : ''}
                >
                  <option value="">-- Select a project --</option>
                  {projects.map(project => (
                    <option key={project.id} value={project.id}>
                      {project.name || project.nom}
                    </option>
                  ))}
                </select>
                {formErrors.project && <span className="error-text">{formErrors.project}</span>}
              </div>

              <div className="form-group">
                <label>Type of creation:</label>
                <div className="action-buttons">
                  <button
                    type="button"
                    onClick={() => setState(prev => ({ ...prev, actionType: 'suite' }))}
                    disabled={!projectId || loading}
                    className={actionType === 'suite' ? 'active' : ''}
                  >
                    New Suite
                  </button>
                  <button
                    type="button"
                    onClick={() => setState(prev => ({ ...prev, actionType: 'testcase' }))}
                    disabled={!projectId || loading}
                    className={actionType === 'testcase' ? 'active' : ''}
                  >
                    New Test Cases
                  </button>
                </div>
              </div>

              {actionType && (
                <div className="form-actions">
                  <button
                    type="button"
                    onClick={onCancel}
                    disabled={loading}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={() => setState(prev => ({ ...prev, step: 2 }))}
                    disabled={loading || !actionType}
                  >
                    Continue
                  </button>
                </div>
              )}
            </div>
          )}

          {step === 2 && actionType === 'suite' && (
            <form onSubmit={handleSubmit} className="create-step">
              <h3>New Test Suite</h3>
              
              <div className="form-group">
                <label>Suite name:</label>
                <input
                  type="text"
                  name="suiteName"
                  value={suiteName}
                  onChange={handleChange}
                  disabled={loading}
                  className={formErrors.suiteName ? 'error' : ''}
                />
                {formErrors.suiteName && <span className="error-text">{formErrors.suiteName}</span>}
              </div>

              <div className="form-group">
                <label>Description:</label>
                <textarea
                  name="suiteDescription"
                  value={suiteDescription}
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>

              <div className="form-actions">
                <button 
                  type="button" 
                  onClick={() => setState(prev => ({ ...prev, step: 1 }))} 
                  disabled={loading}
                >
                  Back
                </button>
                <button 
                  type="submit" 
                  disabled={loading || !suiteName.trim()}
                >
                  {loading ? 'Envoi en cours...' : 'Créer'}
                </button>
              </div>
            </form>
          )}

          {step === 2 && actionType === 'testcase' && (
            <form onSubmit={handleSubmit} className="create-step">
              <h3>New Test Cases</h3>
              
              <div className="form-group">
                <label>Test Suite:</label>
                <select
                  name="selectedSuiteId"
                  value={selectedSuiteId}
                  onChange={handleChange}
                  disabled={loading || existingSuites.length === 0}
                  className={formErrors.suite ? 'error' : ''}
                >
                  <option value="">-- Select a suite --</option>
                  {existingSuites.map(suite => (
                    <option key={suite.id} value={suite.id}>
                      {suite.name || suite.nom} (ID: {suite.id})
                    </option>
                  ))}
                </select>
                {formErrors.suite && <span className="error-text">{formErrors.suite}</span>}
              </div>

              {testCases.map((testCase, idx) => (
                <div key={idx} className="testcase-group">
                  <h4>Test Case #{idx + 1}</h4>

                  <div className="form-group">
                    <label>Name:</label>
                    <input
                      type="text"
                      value={testCase.name}
                      onChange={(e) => updateTestCase(idx, 'name', e.target.value)}
                      disabled={loading}
                      className={formErrors[`testCaseName_${idx}`] ? 'error' : ''}
                    />
                    {formErrors[`testCaseName_${idx}`] && (
                      <span className="error-text">{formErrors[`testCaseName_${idx}`]}</span>
                    )}
                  </div>

                  <div className="form-group">
                    <label>Summary:</label>
                    <textarea
                      value={testCase.summary}
                      onChange={(e) => updateTestCase(idx, 'summary', e.target.value)}
                      disabled={loading}
                    />
                  </div>

                  {testCase.steps.map((step, stepIdx) => (
                    <div key={stepIdx} className="step-group">
                      <h5>Step {stepIdx + 1}</h5>

                      <div className="form-group">
                        <label>Actions:</label>
                        <textarea
                          value={step.actions}
                          onChange={(e) => updateStep(idx, stepIdx, 'actions', e.target.value)}
                          disabled={loading}
                          className={formErrors[`actions_${idx}`] ? 'error' : ''}
                        />
                        {formErrors[`actions_${idx}`] && (
                          <span className="error-text">{formErrors[`actions_${idx}`]}</span>
                        )}
                      </div>

                      <div className="form-group">
                        <label>Expected results:</label>
                        <textarea
                          value={step.expectedResults}
                          onChange={(e) => updateStep(idx, stepIdx, 'expectedResults', e.target.value)}
                          disabled={loading}
                          className={formErrors[`expectedResults_${idx}`] ? 'error' : ''}
                        />
                        {formErrors[`expectedResults_${idx}`] && (
                          <span className="error-text">{formErrors[`expectedResults_${idx}`]}</span>
                        )}
                      </div>
                    </div>
                  ))}

                  <button
                    type="button"
                    className="add-step-button"
                    onClick={() => addStep(idx)}
                    disabled={loading}
                  >
                    + Add a step
                  </button>
                </div>
              ))}

              <button 
                type="button" 
                onClick={addTestCase}
                className="add-button"
                disabled={loading}
              >
                + Add a Test Case
              </button>

              <div className="form-actions">
                <button 
                  type="button" 
                  onClick={() => setState(prev => ({ ...prev, step: 1 }))} 
                  disabled={loading}
                >
                  Back
                </button>
                <button 
                  type="submit" 
                  disabled={loading || !selectedSuiteId || testCases.some(tc => 
                    !tc.name.trim() || 
                    !tc.steps[0].actions.trim() || 
                    !tc.steps[0].expectedResults.trim()
                  )}
                >
                  {loading ? 'Envoi...' : 'Créer'}
                </button>
              </div>
            </form>
          )}
        </>
      ) : (
        <form onSubmit={handleXmlImport} className="create-step">
          <h3>Import from XML</h3>
          
          <div className="form-group">
            <label>Project:</label>
            <select 
              name="projectId"
              value={projectId} 
              onChange={handleChange}
              disabled={loading}
              className={formErrors.project ? 'error' : ''}
            >
              <option value="">-- Select a project --</option>
              {projects.map(project => (
                <option key={project.id} value={project.id}>
                  {project.name || project.nom}
                </option>
              ))}
            </select>
            {formErrors.project && <span className="error-text">{formErrors.project}</span>}
          </div>

          <div className="form-group">
            <label>XML file:</label>
            <input
              type="file"
              name="xmlFile"
              accept=".xml"
              onChange={handleChange}
              disabled={loading}
            />
          </div>

          {importResults && (
            <div className="import-results">
              <p>Import completed :</p>
              <ul>
                <li>Succès: {importResults.successCount}</li>
                <li>Échecs: {importResults.errorCount}</li>
              </ul>
            </div>
          )}

          <div className="form-actions">
            <button 
              type="submit" 
              disabled={loading || !projectId || !xmlFile}
            >
              {loading ? 'Import in progress...' : 'Import'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default Create;
