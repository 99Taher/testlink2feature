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
        error: `Erreur chargement suites: ${err.response?.data?.message || err.message}`,
        loading: false
      }));
    }
  };

  const validateForm = () => {
    const errors = {};

    if (!projectId) {
      errors.project = 'Un projet doit être sélectionné';
    }

    if (actionType === 'suite') {
      if (!suiteName.trim()) {
        errors.suiteName = 'Le nom de la suite est requis';
      }
    } else if (actionType === 'testcase') {
      if (!selectedSuiteId) {
        errors.suite = 'Une suite doit être sélectionnée';
      }

      testCases.forEach((tc, index) => {
        if (!tc.name.trim()) {
          errors[`testCaseName_${index}`] = 'Nom du test case requis';
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
      throw new Error(response.data.error || "Erreur lors de la création de la suite");
    }

    onSuccess(`Suite "${suiteName}" créée avec succès`);
  };

  const createTestCases = async () => {
    const results = await Promise.all(
      testCases.map(tc => 
        axios.post('http://localhost:4000/api/create/testcase', {
          testprojectid: parseInt(projectId),
          testsuiteid: parseInt(selectedSuiteId),
          testcasename: tc.name,
          summary: tc.summary,
          steps: tc.steps.map(step => ({
            step_number: step.stepNumber,
            actions: step.actions,
            expected_results: step.expectedResults,
            execution_type: step.executionType
          }))
        })
      )
    );

    const failed = results.filter(r => !r.data.success);
    if (failed.length > 0) {
      throw new Error(`${failed.length} test case(s) ont échoué`);
    }

    onSuccess(`${testCases.length} test case(s) créé(s) avec succès`);
  };

  const handleXmlImport = async (e) => {
    e.preventDefault();
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const formData = new FormData();
      formData.append('xmlFile', xmlFile);
      formData.append('projectId', projectId);

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
      <h2>Création dans TestLink</h2>
      
      {error && <div className="error-message">{error}</div>}

      <div className="tabs">
        <button
          className={activeTab === 'manual' ? 'active' : ''}
          onClick={() => setState(prev => ({ ...prev, activeTab: 'manual' }))}
        >
          Création Manuelle
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
                <label>Projet:</label>
                <select 
                  name="projectId"
                  value={projectId} 
                  onChange={handleChange}
                  disabled={loading}
                  className={formErrors.project ? 'error' : ''}
                >
                  <option value="">-- Sélectionnez un projet --</option>
                  {projects.map(project => (
                    <option key={project.id} value={project.id}>
                      {project.name || project.nom}
                    </option>
                  ))}
                </select>
                {formErrors.project && <span className="error-text">{formErrors.project}</span>}
              </div>

              <div className="form-group">
                <label>Type de création:</label>
                <div className="action-buttons">
                  <button
                    type="button"
                    onClick={() => setState(prev => ({ ...prev, actionType: 'suite' }))}
                    disabled={!projectId || loading}
                    className={actionType === 'suite' ? 'active' : ''}
                  >
                    Nouvelle Suite
                  </button>
                  <button
                    type="button"
                    onClick={() => setState(prev => ({ ...prev, actionType: 'testcase' }))}
                    disabled={!projectId || loading}
                    className={actionType === 'testcase' ? 'active' : ''}
                  >
                    Nouveaux Test Cases
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
                    Annuler
                  </button>
                  <button
                    type="button"
                    onClick={() => setState(prev => ({ ...prev, step: 2 }))}
                    disabled={loading || !actionType}
                  >
                    Continuer
                  </button>
                </div>
              )}
            </div>
          )}

          {step === 2 && actionType === 'suite' && (
            <form onSubmit={handleSubmit} className="create-step">
              <h3>Nouvelle Test Suite</h3>
              
              <div className="form-group">
                <label>Nom de la suite:</label>
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
                  Retour
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
              <h3>Nouveaux Test Cases</h3>
              
              <div className="form-group">
                <label>Test Suite:</label>
                <select
                  name="selectedSuiteId"
                  value={selectedSuiteId}
                  onChange={handleChange}
                  disabled={loading || existingSuites.length === 0}
                  className={formErrors.suite ? 'error' : ''}
                >
                  <option value="">-- Sélectionnez une suite --</option>
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
                    <label>Nom:</label>
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
                    <label>Résumé:</label>
                    <textarea
                      value={testCase.summary}
                      onChange={(e) => updateTestCase(idx, 'summary', e.target.value)}
                      disabled={loading}
                    />
                  </div>

                  {testCase.steps.map((step, stepIdx) => (
                    <div key={stepIdx} className="step-group">
                      <h5>Étape {stepIdx + 1}</h5>

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
                        <label>Résultats attendus:</label>
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
                    + Ajouter une étape
                  </button>
                </div>
              ))}

              <button 
                type="button" 
                onClick={addTestCase}
                className="add-button"
                disabled={loading}
              >
                + Ajouter un Test Case
              </button>

              <div className="form-actions">
                <button 
                  type="button" 
                  onClick={() => setState(prev => ({ ...prev, step: 1 }))} 
                  disabled={loading}
                >
                  Retour
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
          <h3>Import depuis XML</h3>
          
          <div className="form-group">
            <label>Projet:</label>
            <select 
              name="projectId"
              value={projectId} 
              onChange={handleChange}
              disabled={loading}
              className={formErrors.project ? 'error' : ''}
            >
              <option value="">-- Sélectionnez un projet --</option>
              {projects.map(project => (
                <option key={project.id} value={project.id}>
                  {project.name || project.nom}
                </option>
              ))}
            </select>
            {formErrors.project && <span className="error-text">{formErrors.project}</span>}
          </div>

          <div className="form-group">
            <label>Fichier XML:</label>
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
              <p>Import terminé :</p>
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
              {loading ? 'Import en cours...' : 'Importer'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default Create;