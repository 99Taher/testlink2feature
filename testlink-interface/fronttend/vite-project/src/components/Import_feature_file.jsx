import React, { useState, useCallback } from 'react';
import axios from 'axios';
import './Import_feature_file.css';

const ImportFeatureFile = ({ onSuccess, onCancel }) => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [expandedFile, setExpandedFile] = useState(null);
  const [fileContents, setFileContents] = useState([]);
  const [directoryHandle, setDirectoryHandle] = useState(null);
  const [matchingDone, setMatchingDone] = useState(false);
  const [matchedResults, setMatchedResults] = useState({ matched: [], unmatched: [] });
  const [projectName, setProjectName] = useState('');
  const [warning, setWarning] = useState(null);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    const droppedItems = e.dataTransfer.items;
    const fileList = [];
    
    for (let i = 0; i < droppedItems.length; i++) {
      const item = droppedItems[i];
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file.name.endsWith('.feature')) {
          fileList.push(file);
        }
      }
    }
    
    if (fileList.length > 0) {
      setFiles(fileList);
      setError(null);
      await parseFeatureFiles(fileList);
    } else {
      setError('Seuls les fichiers .feature sont acceptés');
    }
  }, []);

  const handleFileSelect = async (e) => {
    const selectedFiles = Array.from(e.target.files)
      .filter(file => file.name.endsWith('.feature'));
    
    if (selectedFiles.length > 0) {
      setFiles(selectedFiles);
      setError(null);
      await parseFeatureFiles(selectedFiles);
    } else {
      setError('Seuls les fichiers .feature sont acceptés');
    }
  };

  const handleDirectorySelect = async () => {
    try {
      const directoryHandle = await window.showDirectoryPicker();
      setDirectoryHandle(directoryHandle);
      
      const featureFiles = await getFeatureFilesFromDirectory(directoryHandle);
      
      if (featureFiles.length > 0) {
        setFiles(featureFiles);
        setError(null);
        await parseFeatureFiles(featureFiles);
      } else {
        setError('Aucun fichier .feature trouvé dans le dossier sélectionné');
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError('Erreur lors de la sélection du dossier');
      }
    }
  };

  const getFeatureFilesFromDirectory = async (dirHandle) => {
    const files = [];
    
    for await (const entry of dirHandle.values()) {
      if (entry.kind === 'file' && entry.name.endsWith('.feature')) {
        const file = await entry.getFile();
        files.push(file);
      } else if (entry.kind === 'directory') {
        const subDirFiles = await getFeatureFilesFromDirectory(entry);
        files.push(...subDirFiles);
      }
    }
    
    return files;
  };

  const parseFeatureFiles = async (files) => {
    const contents = [];
    
    for (const file of files) {
      try {
        const text = await file.text();
        const featureName = extractFeatureName(text);
        const scenarios = extractScenarios(text);
        
        contents.push({
          fileName: file.name,
          featureName,
          scenarios,
          content: text
        });
      } catch (err) {
        console.error(`Erreur lors de la lecture du fichier ${file.name}:`, err);
        contents.push({
          fileName: file.name,
          error: "Impossible de lire le fichier"
        });
      }
    }
    
    setFileContents(contents);
  };

  const extractFeatureName = (text) => {
    const featureLine = text.split('\n').find(line => line.trim().startsWith('Feature:'));
    return featureLine ? featureLine.replace('Feature:', '').trim() : 'Sans nom';
  };

  const extractScenarios = (text) => {
    const scenarios = [];
    const lines = text.split('\n');
    let currentScenario = null;
    
    for (const line of lines) {
      const trimmedLine = line.trim();
      
      if (trimmedLine.startsWith('Scenario:')) {
        if (currentScenario) scenarios.push(currentScenario);
        currentScenario = {
          type: 'Scenario',
          title: trimmedLine.replace('Scenario:', '').trim(),
          steps: []
        };
      } else if (trimmedLine.startsWith('Scenario Outline:')) {
        if (currentScenario) scenarios.push(currentScenario);
        currentScenario = {
          type: 'Scenario Outline',
          title: trimmedLine.replace('Scenario Outline:', '').trim(),
          steps: [],
          examples: []
        };
      } else if (trimmedLine.startsWith('Examples:')) {
        if (currentScenario && currentScenario.type === 'Scenario Outline') {
          currentScenario.examples.push(trimmedLine);
        }
      } else if (trimmedLine.startsWith('|') && currentScenario?.type === 'Scenario Outline') {
        currentScenario.examples.push(trimmedLine);
      } else if (trimmedLine && currentScenario && 
                 (trimmedLine.startsWith('Given') || 
                  trimmedLine.startsWith('When') || 
                  trimmedLine.startsWith('Then') || 
                  trimmedLine.startsWith('And') || 
                  trimmedLine.startsWith('But'))) {
        currentScenario.steps.push(trimmedLine);
      }
    }
    
    if (currentScenario) scenarios.push(currentScenario);
    return scenarios;
  };

  const handleMatching = async () => {
  // Validation des données
  if (fileContents.length === 0) {
    setError('Veuillez d\'abord analyser les fichiers feature');
    return;
  }

  if (!projectName) {
    setError('Veuillez entrer un nom de projet');
    return;
  }

  setLoading(true);
  setError(null);
  setSuccess(null);

  try {
    // Structure de données cohérente avec le backend
    const payload = {
      features: fileContents.map(file => ({
        file_name: file.fileName,       // snake_case
        feature_name: file.featureName, // snake_case
        scenarios: file.scenarios.map(scenario => ({
          name: scenario.title,
          type: scenario.type,
          steps: scenario.steps
        }))
      })),
      projectName: projectName // snake_case au lieu de projectName
    };

    console.log("Payload envoyé:", payload); // Pour débogage

    const response = await axios.post('http://localhost:4000/api/matching/match', 
      payload,
      {
        headers: {
          'Content-Type': 'application/json'
        }
      }
    );
    

    if (!response.data) {
      throw new Error('Réponse vide du serveur');
    }

    setMatchedResults({
      matched: response.data.matched || [],
      unmatched: response.data.unmatched || []
    });
    
    setMatchingDone(true);
    setSuccess(`Matching terminé: ${response.data.matched?.length || 0} correspondances trouvées`);
    
  } catch (err) {
    let errorMessage = "Erreur lors du matching";
    
    if (err.response) {
      // Erreur du serveur
      errorMessage = err.response.data?.error || 
                    err.response.data?.message || 
                    `Erreur ${err.response.status}: ${err.response.statusText}`;
      
      console.error('Détails erreur:', err.response.data);
    } else if (err.request) {
      // Pas de réponse du serveur
      errorMessage = "Pas de réponse du serveur";
      console.error('Requête:', err.request);
    } else {
      // Erreur de configuration
      errorMessage = err.message;
      console.error('Erreur:', err.message);
    }
    
    setError(errorMessage);
  } finally {
    setLoading(false);
  }
};

  const saveMatchingResults = async () => {
  setLoading(true);
  setError(null);
  setWarning(null); // Réinitialise les warnings

  try {
    const payload = {
  matched: matchedResults.matched.map(item => ({
    file_name: item.file_name || "", // Fallback explicite
    feature_name: item.feature_name || "",
    scenario_title: item.scenario?.name || item.scenario_title || "Sans titre",
    testcase_id: item.testlink_case_id || item.testcase_id || "", // Fallback pour éviter undefined
    similarity_score: item.similarity_score || 0 // Fallback pour éviter undefined
  }))
};

    const response = await axios.post('http://localhost:4000/api/matching/save', payload, {
      headers: {
        'Content-Type': 'application/json'
      }
    });

    if (response.data.errors?.length > 0) {
      // Utilisation de setWarning si disponible, sinon utilisez setError
      if (typeof setWarning === 'function') {
        setWarning(`Enregistrement partiel : ${response.data.saved} réussis, ${response.data.errors.length} erreurs`);
      } else {
        setError(`Enregistrement partiel : ${response.data.saved} réussis, certaines erreurs sont survenues`);
      }
      console.error("Erreurs d'enregistrement:", response.data.errors);
    } else {
      setSuccess(`${response.data.saved} enregistrements réussis`);
    }
  } catch (error) {
    let errorMessage = "Échec de l'enregistrement";
    
    if (error.response) {
      errorMessage += ` : ${error.response.data?.error || error.response.statusText}`;
      console.error("Détails erreur:", error.response.data);
    } else {
      errorMessage += ` : ${error.message}`;
    }
    
    setError(errorMessage);
  } finally {
    setLoading(false);
  }
};

  const toggleFile = (index) => {
    setExpandedFile(expandedFile === index ? null : index);
  };
  const renderScenarioDetails = (scenario) => {
  if (!scenario) return 'N/A';
  
  return (
    <>
      <div><strong>Nom:</strong> {scenario.name || 'N/A'}</div>
      <div><strong>Type:</strong> {scenario.type || 'N/A'}</div>
      <div>
        <strong>Steps:</strong>
        <ul>
          {scenario.steps?.map((step, i) => (
            <li key={i}>{step}</li>
          )) || <li>Aucun step</li>}
        </ul>
      </div>
    </>
  );
};

  return (
    <div className="import-feature-container">
      <h2>Importer des Feature Files</h2>
      
      <div 
        className={`drop-zone ${files.length > 0 ? 'has-files' : ''}`}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {files.length === 0 ? (
          <>
            <p>Glissez-déposez vos fichiers .feature ici</p>
            <p>ou</p>
            <div className="file-select-options">
              <label className="browse-button">
                Sélectionner des fichiers
                <input 
                  type="file" 
                  multiple 
                  accept=".feature" 
                  onChange={handleFileSelect}
                  style={{ display: 'none' }}
                />
              </label>
              <span className="option-separator">ou</span>
              <button 
                className="directory-button"
                onClick={handleDirectorySelect}
              >
                Sélectionner un dossier
              </button>
            </div>
          </>
        ) : (
          <div className="file-list">
            <h4>Fichiers sélectionnés ({files.length}) :</h4>
            <ul>
              {files.slice(0, 3).map((file, index) => (
                <li key={index}>{file.name}</li>
              ))}
              {files.length > 3 && <li>... et {files.length - 3} autres</li>}
            </ul>
            {directoryHandle && <p>Dossier sélectionné: {directoryHandle.name}</p>}
          </div>
        )}
      </div>

      {fileContents.length > 0 && !matchingDone && (
        <>
          <div className="project-name-input">
            <label htmlFor="projectName">Nom du projet TestLink:</label>
            <input
              id="projectName"
              type="text"
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="Entrez le nom du projet"
            />
          </div>

          <div className="file-contents-section">
            <h3>Contenu des fichiers</h3>
            
            <div className="files-list">
              {fileContents.map((file, index) => (
                <div key={index} className="file-card">
                  <div 
                    className="file-header"
                    onClick={() => toggleFile(index)}
                  >
                    <span className="file-name">{file.fileName}</span>
                    {file.featureName && (
                      <span className="feature-name">Feature: {file.featureName}</span>
                    )}
                    <span className="scenarios-count">
                      {file.scenarios ? `${file.scenarios.length} scénario(s)` : ''}
                    </span>
                    <span className="toggle-icon">
                      {expandedFile === index ? '▼' : '►'}
                    </span>
                  </div>

                  {expandedFile === index && (
                    <div className="file-details">
                      {file.error ? (
                        <div className="error-message">{file.error}</div>
                      ) : (
                        <>
                          <div className="feature-section">
                            <h4>Feature: {file.featureName}</h4>
                          </div>
                          
                          <div className="scenarios-section">
                            {file.scenarios.map((scenario, sIndex) => (
                              <div key={sIndex} className="scenario-item">
                                <h5>{scenario.type}: {scenario.title}</h5>
                                <ul className="steps-list">
                                  {scenario.steps.map((step, stepIndex) => (
                                    <li key={stepIndex}>{step}</li>
                                  ))}
                                </ul>
                                {scenario.examples && scenario.examples.length > 0 && (
                                  <div className="examples-section">
                                    <h6>Examples:</h6>
                                    <pre>{scenario.examples.join('\n')}</pre>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {matchingDone && (
  <div className="matching-results">
    <h3>Résultats du Matching</h3>
    <div className="matched-section">
      <h4>Correspondances trouvées ({matchedResults.matched.length})</h4>
      <div className="table-container">
        <table>
          <thead>
            <tr>
              <th>Fichier</th>
              <th>Feature</th>
              <th>Scénarios</th>
              <th>ID Test Case</th>
              <th>Nom du Test Case</th>
              <th>Score moyen</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(
              matchedResults.matched.reduce((acc, match) => {
                const key = match.feature_name;
                if (!acc[key]) {
                  acc[key] = {
                    feature_name: key,
                    file_name: match.file_name,
                    testcases: [],
                    scenarios: []
                  };
                }
                if (!acc[key].testcases.some(tc => tc.id === match.testcase_id)) {
                  acc[key].testcases.push({
                    id: match.testcase_id,
                    name: match.testcase_name || match.name || 'N/A',
                    score: match.similarity_score
                  });
                }
                acc[key].scenarios.push(match.scenario_title);
                return acc;
              }, {})
            ).map(([featureName, data], index) => (
              <tr key={index}>
                <td>{data.file_name}</td>
                <td>{featureName}</td>
                <td>
                  <details>
                    <summary>{data.scenarios.length} scénario(s)</summary>
                    <ul>
                      {data.scenarios.map((scenario, i) => (
                        <li key={i}>{scenario}</li>
                      ))}
                    </ul>
                  </details>
                </td>
                <td>
                  {data.testcases.map((tc, i) => (
                    <div key={i}>{tc.id}</div>
                  ))}
                </td>
                <td>
                  {data.testcases.map((tc, i) => (
                    <div key={i}>{tc.name}</div>
                  ))}
                </td>
                <td>
                  {Math.round(
                    data.testcases.reduce((sum, tc) => sum + (tc.score || 0), 0) / 
                    data.testcases.length
                  )}%
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  </div>
)}

      <div className="button-group">
        {!matchingDone ? (
          <>
            {fileContents.length > 0 && (
              <button 
                onClick={handleMatching} 
                disabled={loading || files.length === 0 || !projectName}
                className="matching-button"
              >
                {loading ? 'Matching en cours...' : 'Faire le matching'}
              </button>
            )}
            <button 
              onClick={onCancel} 
              disabled={loading}
              className="cancel-button"
            >
              Annuler
            </button>
          </>
        ) : (
          <>
            <button 
              onClick={saveMatchingResults} 
              disabled={loading}
              className="save-button"
            >
              Enregistrer les résultats
            </button>
            <button 
              onClick={() => setMatchingDone(false)}
              className="back-button"
            >
              Retour aux features
            </button>
          </>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}
    </div>
  );
};

export default ImportFeatureFile;