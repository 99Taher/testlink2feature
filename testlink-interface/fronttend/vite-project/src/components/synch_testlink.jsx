import React, { useState } from 'react';
import axios from 'axios';
import './synch_testlink.css';

const SyncTestLinkButton = () => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [showConfirmation, setShowConfirmation] = useState(false);

  const handleSync = async () => {
    setShowConfirmation(false);
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await axios.post('http://localhost:4000/api/sync-testlink');
      
      if (response.data.success) {
        setMessage(`Synchronisation réussie: `);
      } else {
        setError(response.data.error || 'Erreur lors de la synchronisation');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Erreur de connexion au serveur');
    } finally {
      setLoading(false);
    }
  };

  const openConfirmationDialog = () => {
    setShowConfirmation(true);
  };

  const cancelSync = () => {
    setShowConfirmation(false);
  };

  return (
    <div className="sync-container">
      <button 
        onClick={openConfirmationDialog}
        disabled={loading}
        className="sync-button"
      >
        {loading ? 'Synchronisation en cours...' : 'Synchroniser avec TestLink'}
      </button>
      
      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}

      {/* Popup de confirmation */}
      {showConfirmation && (
        <div className="confirmation-dialog">
          <div className="confirmation-content">
            <h3>Confirmation requise</h3>
            <p>La base de données sera modifiée. Êtes-vous sûr de vouloir effectuer la synchronisation ?</p>
            
            <div className="confirmation-buttons">
              <button onClick={handleSync} className="confirm-button">
                Oui, synchroniser
              </button>
              <button onClick={cancelSync} className="cancel-button">
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SyncTestLinkButton;
