import { useState } from 'react'
import { loginUser, signupUser } from '../../services/api'
import './AuthModal.css'

export default function AuthModal({ isOpen, onClose, onSuccess }) {
  const [mode, setMode] = useState('login') // 'login' | 'signup'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (!isOpen) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    const cleanUsername = username.trim()
    if (!cleanUsername) {
      setError('Please enter a username.')
      return
    }
    if (cleanUsername.length < 3) {
      setError('Username must be at least 3 characters.')
      return
    }
    if (!password) {
      setError('Please enter a password.')
      return
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }

    setLoading(true)
    try {
      if (mode === 'signup') {
        await signupUser(cleanUsername, password)
      } else {
        await loginUser(cleanUsername, password)
      }
      setUsername('')
      setPassword('')
      setError('')
      if (onSuccess) onSuccess()
      onClose()
    } catch (err) {
      setError(err.message || 'Authentication failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const handleTabChange = (newMode) => {
    setMode(newMode)
    setError('')
  }

  return (
    <div className="auth-modal-overlay" onClick={onClose}>
      <div 
        className="auth-modal" 
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="auth-modal-title"
      >
        <button 
          className="auth-modal-close" 
          onClick={onClose} 
          aria-label="Close modal"
        >
          &times;
        </button>

        <div className="auth-modal-header">
          <div className="auth-brand-logo">CineVerse</div>
          <h2 id="auth-modal-title">
            {mode === 'login' ? 'Welcome Back' : 'Create Account'}
          </h2>
          <p className="auth-subtitle">
            {mode === 'login' 
              ? 'Sign in to access your personal watchlist and Scout history' 
              : 'Sign up to keep your personal watchlist and conversations safe'
            }
          </p>
        </div>

        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${mode === 'login' ? 'active' : ''}`}
            onClick={() => handleTabChange('login')}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`auth-tab ${mode === 'signup' ? 'active' : ''}`}
            onClick={() => handleTabChange('signup')}
          >
            Sign Up
          </button>
        </div>

        {error && (
          <div className="auth-error-message" role="alert">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-form-group">
            <label htmlFor="auth-username">Username</label>
            <input
              id="auth-username"
              type="text"
              className="auth-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. moviebuff24"
              autoComplete="username"
              disabled={loading}
              autoFocus
            />
          </div>

          <div className="auth-form-group">
            <label htmlFor="auth-password">Password</label>
            <input
              id="auth-password"
              type="password"
              className="auth-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 6 characters"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              disabled={loading}
            />
          </div>

          <button 
            type="submit" 
            className="btn btn-primary auth-submit-btn" 
            disabled={loading}
          >
            {loading ? (
              <span className="auth-loading-spinner">Processing...</span>
            ) : (
              mode === 'login' ? 'Sign In' : 'Create Account'
            )}
          </button>
        </form>

        <div className="auth-modal-footer">
          {mode === 'login' ? (
            <p>
              Don't have an account yet?{' '}
              <button 
                type="button" 
                className="auth-link-btn" 
                onClick={() => handleTabChange('signup')}
              >
                Sign Up
              </button>
            </p>
          ) : (
            <p>
              Already have an account?{' '}
              <button 
                type="button" 
                className="auth-link-btn" 
                onClick={() => handleTabChange('login')}
              >
                Sign In
              </button>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
