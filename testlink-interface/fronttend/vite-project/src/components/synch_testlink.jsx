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
        setMessage(`Synchronization successful: `);
      } else {
        setError(response.data.error || 'Error while synchronizing');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Server connection error');
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
        {loading ? 'Synchronization in progress...' : 'Synchronize with TestLink'}
      </button>
      
      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}

      {/* Popup de confirmation */}
      {showConfirmation && (
        <div className="confirmation-dialog">
          <div className="confirmation-content">
            <h3>Confirmation requise</h3>
            <p>The database will be modified. Are you sure you want to synchronize?</p>
            
            <div className="confirmation-buttons">
              <button onClick={handleSync} className="confirm-button">
              Yes, sync
              </button>
              <button onClick={cancelSync} className="cancel-button">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SyncTestLinkButton;
