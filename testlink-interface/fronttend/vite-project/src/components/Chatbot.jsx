import React, { useState, useEffect, useRef, useMemo } from 'react';
import axios from 'axios';
import './Chatbot.css';

const initialMessages = [{
  text: "Hello! I'm the TestLink Assistant. Ask me any questions you have about projects, suites, or test cases.",
  sender: 'bot'
}];

const formatResponse = (data) => {
  if (!data) return "Réponse inconnue";

  if (data.type === 'project_list') {
    return (
      <div className="structured-response">
        <h4>Liste des projets :</h4>
        <ul>
          {data.response.split('\n').filter(line => line.trim()).map((line, i) => (
            <li key={i}>{line.replace(/^- /, '')}</li>
          ))}
        </ul>
      </div>
    );
  }
  
  if (data.type === 'test_cases') {
    const lines = data.response.split('\n').filter(line => line.trim());
    
    return (
      <div className="structured-response">
        <h4>Test cases found ({lines.length}) :</h4>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Nom</th>
                <th>Suite</th>
                <th>Statut</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line, i) => {
                const [id, name, suite, status] = line.split('|').map(item => item.trim());
                return (
                  <tr key={i} className={`status-${status?.toLowerCase() || 'unknown'}`}>
                    <td>{id}</td>
                    <td>{name}</td>
                    <td>{suite}</td>
                    <td>{status || 'N/A'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  return data.response || "I didn't understand the answer";
};

const Chatbot = ({ onClose }) => {
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem('chatHistory');
    return saved ? JSON.parse(saved) : initialMessages;
  });
  const [inputMessage, setInputMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Sauvegarde l'historique et scroll vers le bas
  useEffect(() => {
    localStorage.setItem('chatHistory', JSON.stringify(messages));
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSendMessage = async (e) => {
    e?.preventDefault();
    const message = inputMessage.trim();
    if (!message || loading) return;

    // Ajout du message utilisateur
    const userMessage = {
      text: message,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setLoading(true);
    setError(null);

    try {
      const response = await axios.post('http://localhost:4000/chat', {
        message: message
      }, {
        timeout: 15000
      });

      const botMessage = {
        text: formatResponse(response.data),
        sender: 'bot',
        rawData: response.data,
        
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      console.error("Erreur API:", error);
      
      const errorMessage = {
        text: error.response?.data?.error || 
             error.message || 
             "Sorry, I'm experiencing technical difficulties. Please try again later.",
        sender: 'bot',
        isError: true,
         
      };

      setMessages(prev => [...prev, errorMessage]);
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages(initialMessages);
    localStorage.removeItem('chatHistory');
  };

  const formattedMessages = useMemo(() => messages.map((msg, index) => (
    <Message 
      key={index} 
      msg={msg} 
      isLast={index === messages.length - 1}
    />
  )), [messages]);

  return (
    <div className="chatbot-container">
      <div className="chatbot-header">
        <h3>TestLink Assistant</h3>
        <div className="header-actions">
          <button onClick={clearChat} className="icon-button" title="Effacer l'historique">
            🗑️
          </button>
          <button onClick={onClose} className="icon-button" aria-label="Fermer le chatbot">
            X
          </button>
        </div>
      </div>
      
      <div className="chatbot-messages">
        {formattedMessages}
        {loading && (
          <div className="message bot">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <form onSubmit={handleSendMessage} className="chatbot-input">
        <input
          ref={inputRef}
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          placeholder="Ask your question..."
          disabled={loading}
          aria-label="Message input"
          autoFocus
        />
        <button 
          type="submit"
          disabled={loading || !inputMessage.trim()}
          aria-busy={loading}
        >
          {loading ? (
            <span className="loading-text">...</span>
          ) : (
            'Envoyer'
          )}
        </button>
      </form>
      
      {error && (
        <div className="chatbot-error">
          <small>Erreur : {error}</small>
        </div>
      )}
    </div>
  );
};

// Composant Message mémoïsé
const Message = React.memo(({ msg, isLast }) => (
  <div 
    className={`message ${msg.sender} ${msg.isError ? 'error' : ''} ${isLast ? 'last' : ''}`}
    aria-live={isLast ? "polite" : "off"}
  >
    <div className="message-content">
      {typeof msg.text === 'string' ? msg.text : msg.text}
    </div>
    <div className="message-timestamp">
      {msg.timestamp}
    </div>
  </div>
));

export default Chatbot;
