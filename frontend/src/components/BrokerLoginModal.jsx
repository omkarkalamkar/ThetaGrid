import React, { useState } from 'react';

const BrokerLoginModal = ({ isOpen, onClose }) => {
  const [broker, setBroker] = useState('angelone');
  const [apiKey, setApiKey] = useState('');
  const [clientId, setClientId] = useState('');
  const [password, setPassword] = useState('');
  const [totpSecret, setTotpSecret] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const apiUrl = import.meta.env.VITE_API_URL ? `${import.meta.env.VITE_API_URL}/api` : 'http://localhost:8000/api';
      const res = await fetch(`${apiUrl}/broker/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          broker,
          api_key: apiKey,
          client_id: clientId,
          password: password,
          totp_secret: totpSecret
        })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setSuccess(true);
        setTimeout(() => {
          onClose();
          window.location.reload(); // Reload to pick up new websocket connection
        }, 2000);
      } else {
        setError(data.detail || 'Login failed');
      }
    } catch (err) {
      setError('Failed to connect to backend.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.7)',
      display: 'flex', justifyContent: 'center', alignItems: 'center',
      zIndex: 9999, backdropFilter: 'blur(4px)'
    }}>
      <div style={{
        background: 'white', padding: '24px', borderRadius: '12px',
        width: '400px', boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        display: 'flex', flexDirection: 'column', gap: '16px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', paddingBottom: '12px' }}>
          <h2 style={{ margin: 0, fontSize: '18px', color: '#0f172a' }}>Broker Login</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '20px', color: '#64748b' }}>×</button>
        </div>

        {success ? (
          <div style={{ padding: '20px', textAlign: 'center', color: '#16a34a', fontWeight: 'bold' }}>
            Credentials Saved! Restarting backend...
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Select Broker</label>
              <select 
                value={broker} 
                onChange={(e) => setBroker(e.target.value)}
                style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1', background: '#f8fafc' }}
              >
                <option value="angelone">Angel One (SmartAPI)</option>
                <option value="zerodha" disabled>Zerodha (Coming Soon)</option>
                <option value="fyers" disabled>Fyers (Coming Soon)</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>API Key</label>
              <input type="password" required value={apiKey} onChange={(e) => setApiKey(e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>Client ID</label>
              <input type="text" required value={clientId} onChange={(e) => setClientId(e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>PIN / Password</label>
              <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: '#475569', marginBottom: '4px' }}>TOTP Secret</label>
              <input type="password" required value={totpSecret} onChange={(e) => setTotpSecret(e.target.value)} style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid #cbd5e1' }} />
            </div>

            {error && <div style={{ color: '#dc2626', fontSize: '12px', background: '#fee2e2', padding: '8px', borderRadius: '4px' }}>{error}</div>}

            <button type="submit" disabled={loading} style={{
              width: '100%', padding: '10px', marginTop: '8px',
              background: '#0f172a', color: 'white', fontWeight: 'bold',
              borderRadius: '6px', border: 'none', cursor: loading ? 'not-allowed' : 'pointer'
            }}>
              {loading ? 'Authenticating...' : 'Login & Connect'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default BrokerLoginModal;
