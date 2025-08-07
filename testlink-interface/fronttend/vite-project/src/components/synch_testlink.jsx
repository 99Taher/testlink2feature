import React, { useState } from 'react';
import axios from 'axios';

const SyncTestLinkButton = () => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const handleSync = async () => {
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await axios.post('http://localhost:4000/api/sync-testlink');
      
      if (response.data.success) {
        setMessage(`Synchronisation réussie: ${response.data.total_cases} cas de test insérés`);
      } else {
        setError(response.data.error || 'Erreur lors de la synchronisation');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Erreur de connexion au serveur');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="sync-container">
      <button 
        onClick={handleSync}
        disabled={loading}
        className="sync-button"
      >
        {loading ? 'Synchronisation en cours...' : 'Synchroniser avec TestLink'}
      </button>
      
      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}
    </div>
  );
};

export default SyncTestLinkButton;