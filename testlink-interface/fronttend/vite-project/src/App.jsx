import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import "./App.css";
import Chatbot from "./components/chatbot.jsx";
import Create from "./components/Create.jsx";
import ImportFeatureFile from "./components/Import_feature_file.jsx";

function App() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showChatbot, setShowChatbot] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [showImportFeature, setShowImportFeature] = useState(false);
  const [selectedTestCase, setSelectedTestCase] = useState(null);
  const [featureMapping, setFeatureMapping] = useState([]);
  const [mappingLoading, setMappingLoading] = useState(false);
  const [showDetailsPanel, setShowDetailsPanel] = useState(true);
  const [currentView, setCurrentView] = useState('projects');
  const [syncStatus, setSyncStatus] = useState(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const detailsPanelRef = useRef(null);
  const testSuitesContainerRef = useRef(null);

  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const response = await axios.get("http://localhost:4000/api/projects");
        setProjects(response.data);
        setLoading(false);
      } catch (error) {
        console.error("Erreur lors du chargement des projets:", error);
        setError(error.message);
        setLoading(false);
      }
    };

    fetchProjects();
  }, []);

  const refreshProjects = async () => {
    try {
      const response = await axios.get("http://localhost:4000/api/projects");
      setProjects(response.data);
    } catch (error) {
      console.error("Erreur lors du rafraîchissement des projets:", error);
    }
  };

  const handleSyncTestLink = async () => {
    setIsSyncing(true);
    setSyncStatus(null);
    
    try {
      const response = await axios.post('http://localhost:4000/api/sync-testlink');
      
      if (response.data.success) {
        setSyncStatus({
          type: 'success',
          message: `Synchronisation réussie`
        });
        refreshProjects();
      } else {
        setSyncStatus({
          type: 'error',
          message: response.data.error || 'Erreur lors de la synchronisation'
        });
      }
    } catch (error) {
      setSyncStatus({
        type: 'error',
        message: error.response?.data?.error || error.message || 'Erreur de connexion'
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleTestCaseClick = async (testCase) => {
    setSelectedTestCase(testCase);
    setMappingLoading(true);
    
    try {
      const response = await axios.get('http://localhost:4000/api/feature-mappings', {
        params: { testlink_case_id: testCase.id },
        headers: { 'Accept': 'application/json' }
      });
      
      setFeatureMapping(response.data);
    } catch (error) {
      console.error("ERREUR COMPLÈTE:", error);
      setFeatureMapping([]);
    } finally {
      setMappingLoading(false);
    }
  };

  const renderTestCases = (testCases) => (
    <ul className="test-cases-list">
      {testCases.map((testCase) => (
        <li
          key={testCase.id}
          className={`test-case-item ${
            selectedTestCase?.id === testCase.id ? "selected" : ""
          }`}
          onClick={() => handleTestCaseClick(testCase)}
        >
          <span className="test-case-icon">🧪</span>
          <div className="test-case-content">
            <h4>{testCase.nom}</h4>
            {testCase.summary && (
              <p className="test-case-summary">{testCase.summary}</p>
            )}
          </div>
        </li>
      ))}
    </ul>
  );

  const renderTestSuites = (suites, level = 0) => (
    <ul className="test-suites-list">
      {suites.map((suite) => (
        <li
          key={suite.id}
          className="test-suite-item"
          style={{ marginLeft: `${level * 20}px` }}
        >
          <div className="test-suite-header">
            <span className="test-suite-icon">📁</span>
            <h3>{suite.nom}</h3>
          </div>
          {suite.description && (
            <p className="test-suite-description">{suite.description}</p>
          )}
          {suite.test_cases && renderTestCases(suite.test_cases)}
          {suite.sub_suites && suite.sub_suites.length > 0 && (
            renderTestSuites(suite.sub_suites, level + 1)
          )}
        </li>
      ))}
    </ul>
  );

  if (loading) return <div className="loading-screen">Chargement des projets...</div>;
  if (error) return <div className="error-screen">Erreur: {error}</div>;

  return (
    <div className="app-container">
      <header className="app-header">
        <h1 className="app-title">TestLink Dashboard</h1>
      </header>

      <div className="app-content">
        <aside className="projects-sidebar">
          <h2 className="sidebar-title">Projets</h2>
          <ul className="projects-list">
            {projects.map((project) => (
              <li
                key={project.id}
                className={`project-item ${
                  selectedProject?.id === project.id ? "active" : ""
                }`}
                onClick={() => {
                  setSelectedProject(project);
                  setSelectedTestCase(null);
                  setFeatureMapping([]);
                  setShowCreate(false);
                  setShowImportFeature(false);
                  setCurrentView('projects');
                }}
              >
                <span className="project-icon">📌</span>
                <span className="project-name">{project.name || project.nom}</span>
              </li>
            ))}
          </ul>

          <div className="sidebar-buttons">
            <button
              className="sidebar-button chat-button"
              onClick={() => {
                setShowChatbot(!showChatbot);
                setCurrentView(
                  showCreate ? 'create' : 
                  showImportFeature ? 'import' : 'projects'
                );
              }}
            >
              <span className="button-icon">💬</span>
              <span>Chatbot</span>
            </button>
            <button
              className="sidebar-button create-button"
              onClick={() => {
                setShowCreate(true);
                setShowImportFeature(false);
                setCurrentView('create');
              }}
            >
              <span className="button-icon">➕</span>
              <span>Create</span>
            </button>
            <button
              className="sidebar-button import-button"
              onClick={() => {
                setShowImportFeature(true);
                setShowCreate(false);
                setCurrentView('import');
              }}
            >
              <span className="button-icon">📁</span>
              <span>Import Feature</span>
            </button>
            <button
              className="sidebar-button sync-button"
              onClick={() => {
                setCurrentView('sync');
                setShowCreate(false);
                setShowImportFeature(false);
              }}
            >
              <span className="button-icon">🔄</span>
              <span>Synchroniser TestLink</span>
            </button>
          </div>
        </aside>

        <main className="project-details">
          {currentView === 'sync' ? (
            <div className="sync-container">
              <h2>Synchronisation avec TestLink</h2>
              <p>Cette action va mettre à jour la base de données avec les dernières données de TestLink.</p>
              
              <button
                onClick={handleSyncTestLink}
                disabled={isSyncing}
                className="sync-action-button"
              >
                {isSyncing ? 'Synchronisation en cours...' : 'Lancer la synchronisation'}
              </button>
              
              {syncStatus && (
                <div className={`sync-status sync-${syncStatus.type}`}>
                  {syncStatus.message}
                </div>
              )}
            </div>
          ) : showCreate ? (
            <Create
              projects={projects}
              onSuccess={() => {
                refreshProjects();
                setShowCreate(false);
                setCurrentView('projects');
              }}
              onCancel={() => {
                setShowCreate(false);
                setCurrentView('projects');
              }}
            />
          ) : showImportFeature ? (
            <ImportFeatureFile 
              onSuccess={() => {
                refreshProjects();
                setShowImportFeature(false);
                setCurrentView('projects');
              }}
              onCancel={() => {
                setShowImportFeature(false);
                setCurrentView('projects');
              }}
            />
          ) : selectedProject ? (
            <div className="project-details-container">
              <div className="test-suites-container" ref={testSuitesContainerRef}>
                <div className="project-header">
                  <h2>{selectedProject.nom}</h2>
                  {selectedProject.description && (
                    <p className="project-description">
                      {selectedProject.description}
                    </p>
                  )}
                </div>
                {selectedProject.test_suites && renderTestSuites(selectedProject.test_suites)}
              </div>

              <div 
                className={`feature-details-panel ${showDetailsPanel ? 'active' : ''}`}
                ref={detailsPanelRef}
                style={{
                  position: 'sticky',
                  top: '20px',
                  maxHeight: 'calc(100vh - 100px)',
                  overflowY: 'auto',
                  padding: '15px',
                  backgroundColor: '#f8f9fa',
                  borderRadius: '8px',
                  boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
                }}
              >
                {selectedTestCase ? (
                  <>
                    <div className="details-header">
                      <h3 style={{ marginTop: 0 }}>Détails du Test Case</h3>
                      <button 
                        className="close-details-btn"
                        onClick={() => setShowDetailsPanel(false)}
                      >
                        ×
                      </button>
                    </div>
                    <p><strong>Nom:</strong> {selectedTestCase.nom}</p>
                    <p><strong>ID:</strong> {selectedTestCase.id}</p>

                    {mappingLoading ? (
                      <div className="loading-message">Chargement des détails...</div>
                    ) : featureMapping.length > 0 ? (
                      <>
                        <h4>Feature Files Associés ({featureMapping.length})</h4>
                        <div className="mappings-container">
                          {featureMapping.map((mapping, index) => (
                            <div key={mapping.id || index} className="mapping-item">
                              <div className="mapping-header">
                                <span className="mapping-index">#{index + 1}</span>
                                <span className="mapping-file">{mapping.file_name}</span>
                              </div>
                              <p><strong>Feature:</strong> {mapping.feature_name}</p>
                              <p><strong>Scénario:</strong> {mapping.scenario_title}</p>
                              <div className="similarity-score">
                                <strong>Score:</strong>
                                <div className="score-bar-container">
                                  <div 
                                    className="score-bar"
                                    style={{
                                      width: `${mapping.similarity_score}%`,
                                      backgroundColor: mapping.similarity_score > 70 
                                        ? '#4CAF50' 
                                        : mapping.similarity_score > 40 
                                          ? '#FFC107' 
                                          : '#F44336'
                                    }}
                                  />
                                </div>
                                <span>{mapping.similarity_score}%</span>
                              </div>
                              {index < featureMapping.length - 1 && <hr className="mapping-divider" />}
                            </div>
                          ))}
                        </div>
                      </>
                    ) : (
                      <div className="no-feature-warning">
                        ⚠️ Ce test case n'a pas de feature file associé
                      </div>
                    )}
                  </>
                ) : (
                  <div className="no-selection">
                    👈 Sélectionnez un test case pour voir les détails
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="empty-selection">
              <div className="empty-icon">👈</div>
              <h3>Sélectionnez un projet</h3>
              <p>
                Choisissez un projet dans la liste à gauche pour afficher ses
                détails
              </p>
            </div>
          )}
        </main>
      </div>

      {showChatbot && (
        <div className="chatbot-overlay">
          <Chatbot 
            onClose={() => setShowChatbot(false)}
            currentContext={{
              project: selectedProject,
              testCase: selectedTestCase,
              featureMappings: featureMapping
            }}
          />
        </div>
      )}

      <button 
        className={`mobile-toggle-details ${!showDetailsPanel ? 'visible' : ''}`}
        onClick={() => setShowDetailsPanel(!showDetailsPanel)}
      >
        {showDetailsPanel ? 'Masquer détails' : 'Afficher détails'}
      </button>
    </div>
  );
}

export default App;