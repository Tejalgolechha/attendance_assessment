import React, { useState } from 'react';
import { X, ShieldCheck, User } from 'lucide-react';
import { loginUser } from '../api';

export default function LoginModal({ onClose, onLoginSuccess }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setLoading(true);

    try {
      const res = await loginUser(username, password);
      onLoginSuccess(res.data.user);
      onClose();
    } catch (err) {
      setErrorMsg(err.response?.data?.error || 'Invalid admin credentials. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="glass-panel modal-content">
        <div className="section-header">
          <div className="section-title">
            <ShieldCheck size={22} className="text-indigo-400" />
            <span>Admin Authentication</span>
          </div>
          <button className="nav-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        {errorMsg && <div className="alert alert-danger">{errorMsg}</div>}

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="form-group">
            <label className="form-label">Admin Username</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. admin"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-control"
              placeholder="••••••••"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="btn btn-success btn-lg" disabled={loading} style={{ marginTop: '0.5rem' }}>
            <User size={18} />
            <span>{loading ? 'Authenticating...' : 'Sign In as Admin'}</span>
          </button>
        </form>

        <div style={{ marginTop: '1.25rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)', fontSize: '0.8rem', color: 'var(--text-muted)', textAlign: 'center' }}>
          Default Admin Login: <strong style={{ color: 'var(--text-main)' }}>admin</strong> / <strong style={{ color: 'var(--text-main)' }}>admin123</strong>
        </div>
      </div>
    </div>
  );
}
