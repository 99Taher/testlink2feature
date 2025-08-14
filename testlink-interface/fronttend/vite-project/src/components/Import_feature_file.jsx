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
  const [matchedResults, setMatchedResults] = useState({ matched: [], unmatched: [], stats: { matched_count: 0, unmatched_count: 0 } });
  const [projectName, setProjectName] = useState('');
  const [warning, setWarning] = useState(null);
  const [selectedMatches, setSelectedMatches] = useState([]);

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
      await uploadFiles(fileList);
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
      await uploadFiles(selectedFiles);
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
        await uploadFiles(featureFiles);
      } else {
        setError('Aucun fichier .feature trouvé dans le dossier sélectionné');
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError('Erreur lors de la sélection du dossier');
      }
    }
  };

  const uploadFiles = async (files) => {
    const formData = new FormData();
    for (let file of files) {
      formData.append('files', file);
    }

    try {
      setLoading(true);
      const response = await axios.post('http://localhost:4000/api/import-features', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      console.log('File upload successful:', response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to upload files');
      console.error('Upload error:', err.response?.data || err);
    } finally {
      setLoading(false);
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
        const featureName = extractFeatureName(text) || 'Unknown Feature';
        const scenarios = extractScenarios(text);
        
        contents.push({
          fileName: file.name || 'Unknown File',
          featureName,
          scenarios,
          content: text
        });
      } catch (err) {
        console.error(`Erreur lors de la lecture du fichier ${file.name}:`, err);
        contents.push({
          fileName: file.name || 'Unknown File',
          error: "Impossible de lire le fichier"
        });
      }
    }
    
    setFileContents(contents);
  };

  const extractFeatureName = (text) => {
    const featureLine = text.split('\n').find(line => line.trim().startsWith('Feature:'));
    return featureLine ? featureLine.replace('Feature:', '').trim() : null;
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
          title: trimmedLine.replace('Scenario:', '').trim() || 'Unnamed Scenario',
          steps: []
        };
      } else if (trimmedLine.startsWith('Scenario Outline:')) {
        if (currentScenario) scenarios.push(currentScenario);
        currentScenario = {
          type: 'Scenario Outline',
          title: trimmedLine.replace('Scenario Outline:', '').trim() || 'Unnamed Scenario Outline',
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
      const payload = {
        project_name: projectName,
        features: fileContents.map(file => ({
          file_name: file.fileName || 'Unknown File',
          feature_name: file.featureName || 'Unknown Feature',
          scenarios: file.scenarios.map(scenario => ({
            name: scenario.title || 'Unknown Scenario',
            type: scenario.type || 'Scenario',
            steps: scenario.steps || []
          }))
        }))
      };

      console.log("Payload envoyé:", payload);
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
        unmatched: response.data.unmatched || [],
        stats: response.data.stats || { matched_count: 0, unmatched_count: 0 }
      });
      
      setMatchingDone(true);
      setSuccess(`Matching terminé: ${response.data.stats?.matched_count || 0} correspondances trouvées`);
      
    } catch (err) {
      let errorMessage = "Erreur lors du matching";
      
      if (err.response) {
        errorMessage = err.response.data?.error || 
                      err.response.data?.message || 
                      `Erreur ${err.response.status}: ${err.response.statusText}`;
        console.error('Détails erreur:', err.response.data);
      } else if (err.request) {
        errorMessage = "Pas de réponse du serveur";
        console.error('Requête:', err.request);
      } else {
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
    setWarning(null);

    try {
      const selectedItems = matchedResults.matched.filter(match => 
        selectedMatches.includes(`${match.file_name}-${match.feature_name}-${match.testcase_id}`)
      );

      if (selectedItems.length === 0) {
        setError('Veuillez sélectionner au moins un élément');
        return;
      }

      const payload = {
        matched: selectedItems.map(item => ({
          file_name: item.file_name || "",
          feature_name: item.feature_name || "",
          scenario_title: item.scenario?.name || item.scenario_title || "Sans titre",
          testcase_id: item.testlink_case_id || item.testcase_id || "",
          similarity_score: item.similarity_score || 0
        }))
      };

      const response = await axios.post('http://localhost:4000/api/matching/save', payload, {
        headers: {
          'Content-Type': 'application/json'
        }
      });

      setSuccess('Résultats enregistrés avec succès');
      onSuccess();
    } catch (error) {
      setError('Erreur lors de l\'enregistrement des résultats');
      console.error('Erreur:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadUnmatchedReport = async () => {
    try {
      setLoading(true);
      setError(null);

      if (matchedResults.unmatched.length === 0) {
        setWarning("Toutes les features sont matchées - aucun rapport à générer");
        return;
      }

      if (!projectName) {
        throw new Error("Veuillez spécifier un nom de projet");
      }

      const payload = {
        project_name: projectName,
        features: fileContents.map(file => ({
          file_name: file.fileName,
          feature_name: file.featureName,
          scenarios: file.scenarios || []
        }))
      };

      const response = await axios.post(
        'http://localhost:4000/api/matching/report/unmatched',
        payload,
        { 
          responseType: 'blob',
          timeout: 30000
        }
      );

      if (response.headers['content-type']?.includes('application/json')) {
        const errorData = JSON.parse(await response.data.text());
        throw new Error(errorData.message || "Erreur lors de la génération du rapport");
      }

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `unmatched_report_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();

    } catch (err) {
      console.error("Erreur lors du téléchargement:", err);
      setError(err.message || "Échec du téléchargement du rapport");
    } finally {
      setLoading(false);
    }
  };

  const toggleMatchSelection = (matchId) => {
    setSelectedMatches(prev => 
      prev.includes(matchId) 
        ? prev.filter(id => id !== matchId) 
        : [...prev, matchId]
    );
  };

  const selectAllMatches = () => {
    if (selectedMatches.length === matchedResults.matched.length) {
      setSelectedMatches([]);
    } else {
      setSelectedMatches(matchedResults.matched.map(match => 
        `${match.file_name}-${match.feature_name}-${match.testcase_id}`
      ));
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
          <div className="file-title-section">
            <span className="file-name">{file.fileName}</span>
            {file.featureName && (
              <div className="feature-name">Feature: {file.featureName}</div>
            )}
          </div>
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
          <div className="stats">
            <p>Matchés: {matchedResults.stats.matched_count}</p>
            <p>Non matchés: {matchedResults.stats.unmatched_count}</p>
          </div>
          
          {matchedResults.matched.length > 0 && (
            <div className="matched-section">
              <h4>Features matchées</h4>
              <div className="selection-controls">
                <label>
                  <input
                    type="checkbox"
                    checked={selectedMatches.length === matchedResults.matched.length}
                    onChange={selectAllMatches}
                  />
                  Tout sélectionner ({matchedResults.matched.length} éléments)
                </label>
                <span className="selection-count">
                  {selectedMatches.length} sélectionné(s)
                </span>
              </div>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Sélection</th>
                      <th>Fichier</th>
                      <th>Feature</th>
                      <th>Scénario</th>
                      <th>ID Test Case</th>
                      <th>Nom Test Case</th>
                      <th>Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {matchedResults.matched.map((match, index) => {
                      const matchId = `${match.file_name}-${match.feature_name}-${match.testcase_id}`;
                      const isSelected = selectedMatches.includes(matchId);
                      
                      return (
                        <tr 
                          key={index} 
                          className={isSelected ? 'selected-row' : ''}
                          onClick={() => toggleMatchSelection(matchId)}
                        >
                          <td>
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleMatchSelection(matchId)}
                              onClick={e => e.stopPropagation()}
                            />
                          </td>
                          <td className="file-cell">
                            <div className="truncate-text" title={match.file_name}>
                              {match.file_name}
                            </div>
                          </td>
                          <td className="feature-cell">
                            <div className="truncate-text" title={match.feature_name}>
                              {match.feature_name}
                            </div>
                          </td>
                          <td className="scenario-cell">
                            <details>
                              <summary className="truncate-text" title={match.scenario_title}>
                                {match.scenario_title}
                              </summary>
                              <div className="scenario-details">
                                {renderScenarioDetails(match.scenario)}
                              </div>
                            </details>
                          </td>
                          <td className="id-cell">{match.testcase_id}</td>
                          <td className="name-cell">
                            <div className="truncate-text" title={match.testcase_name || 'N/A'}>
                              {match.testcase_name || 'N/A'}
                            </div>
                          </td>
                          <td className="score-cell">
                            <div className={`score-badge ${
                              match.similarity_score > 80 ? 'high-score' : 
                              match.similarity_score > 50 ? 'medium-score' : 'low-score'
                            }`}>
                              {Math.round(match.similarity_score)}%
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {matchedResults.unmatched.length > 0 && (
            <div className="unmatched-section">
              <h4>Features non matchées</h4>
              <table className="results-table">
                <thead>
                  <tr>
                    <th>Fichier</th>
                    <th>Feature</th>
                  </tr>
                </thead>
                <tbody>
                  {matchedResults.unmatched.map((unmatched, index) => (
                    <tr key={index}>
                      <td>{unmatched.file_name}</td>
                      <td>{unmatched.feature_name}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
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
              onClick={handleDownloadUnmatchedReport} 
              disabled={loading || matchedResults.unmatched.length === 0}
              className="download-unmatched-button"
            >
              {loading ? 'Génération...' : `Télécharger les non-matchés (${matchedResults.unmatched.length})`}
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
      {warning && <div className="warning-message">{warning}</div>}
    </div>
  );
};

export default ImportFeatureFile;
