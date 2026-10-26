import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loginUser, signupUser } from '../../services/api'
import './LandingPage.css'

export default function LandingPage({ onAuthSuccess }) {
  const [mode, setMode] = useState('login') // 'login' | 'signup'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    const cleanUsername = username.trim()
    if (!cleanUsername) {
      setError('Please enter your username.')
      return
    }
    if (cleanUsername.length < 3) {
      setError('Username must be at least 3 characters.')
      return
    }
    if (!password) {
      setError('Please enter your password.')
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
      
      if (onAuthSuccess) {
        onAuthSuccess()
      }
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message || 'Authentication failed. Please verify your credentials.')
    } finally {
      setLoading(false)
    }
  }

  const handleTabChange = (newMode) => {
    setMode(newMode)
    setError('')
  }

  return (
    <div className="landing-page">
      <div className="landing-backdrop-glow"></div>

      <div className="landing-container">
        {/* Brand & Introduction */}
        <div className="landing-hero">
          <div className="landing-badge">
            <span className="badge-sparkle">✦</span>
            <span>Welcome to CineVerse</span>
          </div>

          <h1 className="landing-logo">
            <span className="logo-main">CineVerse</span>
          </h1>

          <p className="landing-tagline">
            Your personal universe of cinema, series, and intelligent discovery.
          </p>

          <div className="landing-features">
            <div className="landing-feature-item">
              <div className="feature-icon">🎬</div>
              <div className="feature-text">
                <strong>Vast Catalogue</strong>
                <span>Trending & top-rated movies & TV series powered by TMDB.</span>
              </div>
            </div>

            <div className="landing-feature-item">
              <div className="feature-icon">✨</div>
              <div className="feature-text">
                <strong>Ask Scout AI</strong>
                <span>Conversational discovery with natural language recommendations.</span>
              </div>
            </div>

            <div className="landing-feature-item">
              <div className="feature-icon">🔖</div>
              <div className="feature-text">
                <strong>Personal Watchlist</strong>
                <span>Persistent, account-isolated watchlists synced in real time.</span>
              </div>
            </div>
          </div>
        </div>

        {/* Authentication Card */}
        <div className="landing-auth-card">
          <div className="auth-card-header">
            <h2>{mode === 'login' ? 'Sign In' : 'Create an Account'}</h2>
            <p>
              {mode === 'login'
                ? 'Enter your credentials to access your personal CineVerse.'
                : 'Choose a username and password to start your journey.'}
            </p>
          </div>

          {/* Mode Tabs */}
          <div className="auth-card-tabs">
            <button
              type="button"
              className={`auth-card-tab ${mode === 'login' ? 'active' : ''}`}
              onClick={() => handleTabChange('login')}
            >
              Sign In
            </button>
            <button
              type="button"
              className={`auth-card-tab ${mode === 'signup' ? 'active' : ''}`}
              onClick={() => handleTabChange('signup')}
            >
              Sign Up
            </button>
          </div>

          {/* Error Message */}
          {error && (
            <div className="landing-error-alert" role="alert">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="landing-form">
            <div className="landing-form-group">
              <label htmlFor="landing-username">Username</label>
              <div className="input-with-icon">
                <svg className="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                  <circle cx="12" cy="7" r="4" />
                </svg>
                <input
                  id="landing-username"
                  type="text"
                  className="landing-input"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="e.g. cinema_lover"
                  autoComplete="username"
                  disabled={loading}
                  autoFocus
                />
              </div>
            </div>

            <div className="landing-form-group">
              <label htmlFor="landing-password">Password</label>
              <div className="input-with-icon">
                <svg className="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                <input
                  id="landing-password"
                  type="password"
                  className="landing-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 6 characters"
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  disabled={loading}
                />
              </div>
            </div>

            <button
              type="submit"
              className="landing-submit-btn"
              disabled={loading}
            >
              {loading ? (
                <span className="submit-loading-text">
                  <span className="spinner-small"></span> Authenticating...
                </span>
              ) : (
                mode === 'login' ? 'Sign In to CineVerse' : 'Create Free Account'
              )}
            </button>
          </form>

          <div className="landing-card-footer">
            {mode === 'login' ? (
              <p>
                Don't have an account yet?{' '}
                <button
                  type="button"
                  className="landing-switch-btn"
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
                  className="landing-switch-btn"
                  onClick={() => handleTabChange('login')}
                >
                  Sign In
                </button>
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
