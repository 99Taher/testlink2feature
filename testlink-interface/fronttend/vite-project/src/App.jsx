import React, { useEffect, useState } from "react";
import axios from "axios";
import "./App.css";
import Chatbot from "./components/chatbot.jsx";
import Create from "./components/Create.jsx"; // Importez le composant Create

function App() {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showChatbot, setShowChatbot] = useState(false);
  const [showCreate, setShowCreate] = useState(false); // Nouvel état pour gérer l'affichage de Create

  useEffect(() => {
    axios.get("http://localhost:4000/api/projects")
      .then(response => {
        setProjects(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error("Erreur lors du chargement des projets:", error);
        setError(error.message);
        setLoading(false);
      });
  }, []);

  // Fonction pour rafraîchir la liste des projets après création
  const refreshProjects = () => {
    axios.get("http://localhost:4000/api/projects")
      .then(response => {
        setProjects(response.data);
      });
  };

  const renderTestCases = (testCases) => (
    <ul className="test-cases-list">
      {testCases.map(testCase => (
        <li key={testCase.id} className="test-case-item">
          <span className="test-case-icon">🧪</span>
          <div className="test-case-content">
            <h4>{testCase.nom}</h4>
            {testCase.summary && <p className="test-case-summary">{testCase.summary}</p>}
          </div>
        </li>
      ))}
    </ul>
  );

  const renderTestSuites = (suites, level = 0) => (
    <ul className="test-suites-list">
      {suites.map(suite => (
        <li key={suite.id} className="test-suite-item" style={{ marginLeft: `${level * 20}px` }}>
          <div className="test-suite-header">
            <span className="test-suite-icon">📁</span>
            <h3>{suite.nom}</h3>
          </div>
          {suite.description && <p className="test-suite-description">{suite.description}</p>}
          
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
            {projects.map(project => (
              <li 
                key={project.id} 
                className={`project-item ${selectedProject?.id === project.id ? 'active' : ''}`}
                onClick={() => {
                  setSelectedProject(project);
                  setShowCreate(false); // Retour à la vue principale lorsqu'on sélectionne un projet
                }}
              >
                <span className="project-icon">📌</span>
                <span className="project-name">{project.nom}</span>
              </li>
            ))}
          </ul>

          <div className="sidebar-buttons">
            <button 
              className="sidebar-button chat-button"
              onClick={() => {
                setShowChatbot(!showChatbot);
                setShowCreate(false); // Ferme Create si ouvert
              }}
            >
              <span className="button-icon">💬</span>
              <span>Chatbot</span>
            </button>
            <button 
              className="sidebar-button create-button"
              onClick={() => {
                setShowCreate(true);
                setShowChatbot(false); // Ferme Chatbot si ouvert
              }}
            >
              <span className="button-icon">➕</span>
              <span>Create</span>
            </button>
          </div>
        </aside>

        <main className="project-details">
          {showCreate ? (
            <Create 
              projects={projects} 
              onSuccess={() => {
                refreshProjects();
                setShowCreate(false);
              }}
              onCancel={() => setShowCreate(false)}
            />
          ) : selectedProject ? (
            <>
              <div className="project-header">
                <h2>{selectedProject.nom}</h2>
                {selectedProject.description && (
                  <p className="project-description">{selectedProject.description}</p>
                )}
              </div>

              <div className="test-suites-container">
                {selectedProject.test_suites && renderTestSuites(selectedProject.test_suites)}
              </div>
            </>
          ) : (
            <div className="empty-selection">
              <div className="empty-icon">👈</div>
              <h3>Sélectionnez un projet</h3>
              <p>Choisissez un projet dans la liste à gauche pour afficher ses détails</p>
            </div>
          )}
        </main>
      </div>

      {/* Chatbot rendu conditionnellement */}
      {showChatbot && <Chatbot onClose={() => setShowChatbot(false)} />}
    </div>
  );
}

export default App;