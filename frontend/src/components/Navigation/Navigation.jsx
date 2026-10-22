import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import SearchBar from '../SearchBar/SearchBar'
import Scout from '../Scout/Scout'
import { CHATBOT_NAME, CHATBOT_ICON_SVG } from '../Scout/scoutConfig'
import './Navigation.css'

export default function Navigation() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [isScoutOpen, setIsScoutOpen] = useState(false)
  const location = useLocation()
  
  const isActive = (path) => location.pathname === path
  
  const handleScoutOpen = () => {
    setIsScoutOpen(true)
    setIsMenuOpen(false)
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
            </div>
          </div>
        </div>
      </nav>
      
      <Scout isOpen={isScoutOpen} onClose={() => setIsScoutOpen(false)} />
    </>
  )
}
