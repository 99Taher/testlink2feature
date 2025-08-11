import React, { useEffect, useState, useRef } from "react";
import axios from "axios";
import "./App.css";
import Chatbot from "./components/chatbot.jsx";
import Create from "./components/Create.jsx";
import ImportFeatureFile from "./components/Import_feature_file.jsx";
import SyncTestLinkButton from "./components/synch_testlink.jsx"

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
  const [leftWidth, setLeftWidth] = useState(60);
  const containerRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [startX, setStartX] = useState(0);
  const [startWidth, setStartWidth] = useState(0);
  const [expandedTestCase, setExpandedTestCase] = useState(null);
  const [selectedFeatureContent, setSelectedFeatureContent] = useState(null);

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

  const startDrag = (e) => {
    if (!containerRef.current) return;
    setIsDragging(true);
    setStartX(e.clientX);
    setStartWidth(leftWidth);
    e.preventDefault();
  };

  const handleDrag = (e) => {
    if (!isDragging || !containerRef.current) return;

    const containerRect = containerRef.current.getBoundingClientRect();
    const containerWidth = containerRect.width;
    const dx = e.clientX - startX;
    let newLeftWidth = startWidth + (dx / containerWidth) * 100;

    newLeftWidth = Math.max(10, Math.min(90, newLeftWidth));
    setLeftWidth(newLeftWidth);
  };

  const stopDrag = () => {
    setIsDragging(false);
  };

  useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleDrag);
      document.addEventListener('mouseup', stopDrag);
    }

    return () => {
      document.removeEventListener('mousemove', handleDrag);
      document.removeEventListener('mouseup', stopDrag);
    };
  }, [isDragging]);

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
    if (expandedTestCase?.id === testCase.id) {
      setExpandedTestCase(null);
      setSelectedFeatureContent(null);
    } else {
      setSelectedTestCase(testCase);
      setMappingLoading(true);
      setSelectedFeatureContent(null);
      
      try {
        const response = await axios.get('http://localhost:4000/api/feature-mappings', {
          params: { testlink_case_id: testCase.id }
        });
        
        setFeatureMapping(response.data);
        setExpandedTestCase(testCase);
        
        if (response.data.length === 1) {
          handleSelectFeature(response.data[0].file_name);
        }
      } catch (error) {
        console.error("Error loading feature mappings:", error);
        setFeatureMapping([]);
      } finally {
        setMappingLoading(false);
      }
    }
  };

  const handleSelectFeature = async (file_name) => {
    try {
      const response = await axios.get('http://localhost:4000/api/feature-content', {
        params: { file_name }
      });
      setSelectedFeatureContent({
        file_name,
        content: response.data.content
      });
    } catch (error) {
      console.error("Error loading feature content:", error);
      setSelectedFeatureContent(null);
    }
  };

  const renderTestCases = (testCases) => (
    <ul className="test-cases-list">
      {testCases.map((testCase) => (
        <React.Fragment key={testCase.id}>
          <li
            className={`test-case-item ${
              expandedTestCase?.id === testCase.id ? "selected" : ""
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
            <span className="expand-icon">
              {expandedTestCase?.id === testCase.id ? '▼' : '►'}
            </span>
          </li>
          
          {expandedTestCase?.id === testCase.id && (
            <div className="feature-mapping-panel">
              {mappingLoading ? (
                <div className="loading-message">Chargement...</div>
              ) : featureMapping.length > 0 ? (
                <div className="feature-mappings">
                  {featureMapping.map((mapping, index) => (
                    <div key={index} className="feature-mapping">
                      <div className="feature-header">
                        <span className="feature-icon">📄</span>
                        <span className="feature-name">{mapping.feature_name}</span>
                        <span className="similarity-score">
                          {mapping.similarity_score}% de correspondance
                        </span>
                      </div>
                      
                      <div className="scenario-details">
                        <div className="scenario-title">
                          <span>Scénario:</span> {mapping.scenario_title}
                        </div>
                        
                        {mapping.steps && (
                          <div className="scenario-steps">
                            {mapping.steps.map((step, i) => (
                              <div key={i} className="step">{step}</div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="no-mappings">
                  Aucun feature file associé à ce test case
                </div>
              )}
            </div>
          )}
        </React.Fragment>
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
  <div className="full-screen-view">
    <div className="sync-container">
      <h2>Synchronisation avec TestLink</h2>
      <p>Cette action va mettre à jour la base de données avec les dernières données de TestLink. Elle peut prendre quelques instants.</p>
      
      <SyncTestLinkButton onSyncComplete={refreshProjects} />
    </div>
  </div>
) : showCreate ?  (
            <div className="full-screen-view">
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
            </div>
          ) : showImportFeature ? (
            <div className="full-screen-view">
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
            </div>
          ) : selectedProject ? (
            <div 
              className="project-details-container" 
              ref={containerRef}
              style={{ cursor: isDragging ? 'col-resize' : 'auto' }}
            >
              <div 
                className="test-suites-container" 
                style={{ width: `${leftWidth}%` }}
              >
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
                className="splitter" 
                onMouseDown={startDrag}
                style={{ backgroundColor: isDragging ? '#1976d2' : '#f0f0f0' }}
              />

              <div 
                className="feature-details-panel"
                style={{ width: `calc(100% - ${leftWidth}% - 10px)` }}
              >
                {selectedTestCase && (
                  <div className="test-case-details">
                    <div className="feature-file-header">
                      <span className="file-icon">📄</span>
                      <h3 className="feature-file-title">
                        {selectedFeatureContent?.file_name || selectedTestCase.nom}
                      </h3>
                    </div>
                    
                    <div className="feature-code-fullwidth">
                      {selectedFeatureContent ? (
                        <pre>{selectedFeatureContent.content}</pre>
                      ) : featureMapping.length > 0 ? (
                        <div className="feature-mapping-list">
                          <h4>Features associées:</h4>
                          <ul>
                            {featureMapping.map((mapping, index) => (
                              <li 
                                key={index}
                                onClick={() => handleSelectFeature(mapping.file_name)}
                                className={selectedFeatureContent?.file_name === mapping.file_name ? "active" : ""}
                              >
                                <span>{mapping.feature_name}</span>
                                <span className="score">{mapping.similarity_score}%</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      ) : (
                        <div className="no-feature-message">
                          Aucun feature file associé à ce test case
                        </div>
                      )}
                    </div>
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
        {showDetailsPanel ? '◄ Masquer détails' : 'Afficher détails ►'}
      </button>
    </div>
  );
}

export default App;
