import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import SearchBar from '../SearchBar/SearchBar'
import Scout from '../Scout/Scout'
import AuthModal from '../AuthModal/AuthModal'
import { getStoredUser, logoutUser } from '../../services/api'
import { CHATBOT_NAME, CHATBOT_ICON_SVG } from '../Scout/scoutConfig'
import './Navigation.css'

export default function Navigation() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isScoutOpen, setIsScoutOpen] = useState(false)
  const [isAuthOpen, setIsAuthOpen] = useState(false)
  const [currentUser, setCurrentUser] = useState(() => getStoredUser())
  const location = useLocation()
  
  useEffect(() => {
    const handleAuthChange = () => {
      setCurrentUser(getStoredUser())
    }
    window.addEventListener('authChanged', handleAuthChange)
    return () => window.removeEventListener('authChanged', handleAuthChange)
  }, [])

  const isActive = (path) => location.pathname === path
  
  const handleScoutOpen = () => {
    setIsScoutOpen(true)
    setIsMenuOpen(false)
  }

  const handleLogout = async () => {
    await logoutUser()
    navigate('/', { replace: true })
  }
  
  return (
    <>
      <nav className="navigation">
        <div className="nav-container">
          <Link to="/" className="nav-logo">
            <span className="logo-main">CineVerse</span>
          </Link>
          
          <button 
            className="nav-toggle"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label="Toggle menu"
          >
            <span></span>
            <span></span>
            <span></span>
          </button>
          
          <div className={`nav-content ${isMenuOpen ? 'open' : ''}`}>
            <ul className="nav-links">
              <li>
                <Link 
                  to="/" 
                  className={isActive('/') ? 'active' : ''}
                  onClick={() => setIsMenuOpen(false)}
                >
                  Home
                </Link>
              </li>
              <li>
                <Link 
                  to="/movies" 
                  className={isActive('/movies') ? 'active' : ''}
                  onClick={() => setIsMenuOpen(false)}
                >
                  Movies
                </Link>
              </li>
              <li>
                <Link 
                  to="/series" 
                  className={isActive('/series') ? 'active' : ''}
                  onClick={() => setIsMenuOpen(false)}
                >
                  Series
                </Link>
              </li>
              <li>
                <Link 
                  to="/watchlist" 
                  className={isActive('/watchlist') ? 'active' : ''}
                  onClick={() => setIsMenuOpen(false)}
                >
                  My Watchlist
                </Link>
              </li>
            </ul>
            
            <div className="nav-actions">
              <button
                className="scout-trigger"
                onClick={handleScoutOpen}
                aria-label={`Ask ${CHATBOT_NAME}`}
              >
                <span className="scout-trigger-icon"><CHATBOT_ICON_SVG /></span>
                <span className="scout-trigger-text">Ask {CHATBOT_NAME}</span>
              </button>
              <SearchBar onSearch={() => setIsMenuOpen(false)} />

              {currentUser ? (
                <div className="nav-user-profile">
                  <span className="nav-username" title={currentUser.username}>
                    <svg className="nav-user-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                    {currentUser.username}
                  </span>
                  <button
                    type="button"
                    className="nav-auth-btn nav-logout-btn"
                    onClick={handleLogout}
                    title="Sign Out"
                  >
                    Sign Out
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  className="nav-auth-btn nav-signin-btn"
                  onClick={() => setIsAuthOpen(true)}
                >
                  Sign In
                </button>
              )}
            </div>
          </div>
        </div>
      </nav>
      
      <Scout isOpen={isScoutOpen} onClose={() => setIsScoutOpen(false)} />
      <AuthModal isOpen={isAuthOpen} onClose={() => setIsAuthOpen(false)} />
    </>
  )
}
