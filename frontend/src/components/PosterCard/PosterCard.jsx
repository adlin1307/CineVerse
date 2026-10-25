import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { isInWatchlist, addToWatchlist, removeFromWatchlist } from '../../services/watchlist'
import './PosterCard.css'

export default function PosterCard({ item, mediaType }) {
  const type = mediaType || item.media_type || 'movie'
  const title = item.title || item.name
  const releaseDate = item.release_date || item.first_air_date
  const posterPath = item.poster_path
  const year = releaseDate ? new Date(releaseDate).getFullYear() : null
  const rating = item.vote_average ? item.vote_average.toFixed(1) : null
  
  const [inWatchlist, setInWatchlist] = useState(() => isInWatchlist(item.id, type))

  useEffect(() => {
    setInWatchlist(isInWatchlist(item.id, type))
    
    const handleUpdate = () => {
      setInWatchlist(isInWatchlist(item.id, type))
    }
    
    window.addEventListener('watchlistUpdated', handleUpdate)
    return () => window.removeEventListener('watchlistUpdated', handleUpdate)
  }, [item.id, type])
  
  const handleWatchlistToggle = (e) => {
    e.preventDefault()
    e.stopPropagation()
    
    if (inWatchlist) {
      removeFromWatchlist(item.id, type)
      setInWatchlist(false)
    } else {
      addToWatchlist({
        ...item,
        media_type: type,
      })
      setInWatchlist(true)
    }
    
    window.dispatchEvent(new Event('watchlistUpdated'))
  }
  
  const linkPath = type === 'movie' ? `/movie/${item.id}` : `/series/${item.id}`
  
  return (
    <Link to={linkPath} className="poster-card">
      <div className="poster-image-container">
        {posterPath ? (
          <img
            src={`https://image.tmdb.org/t/p/w500${posterPath}`}
            alt={title}
            className="poster-image"
            loading="lazy"
          />
        ) : (
          <div className="poster-placeholder">
            <svg width="60" height="60" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="2" y="3" width="20" height="18" rx="2" />
              <circle cx="8.5" cy="8.5" r="2.5" />
              <path d="M14.5 21 7 13.5" />
            </svg>
            <span>{title}</span>
          </div>
        )}
        
        <button
          className={`watchlist-button ${inWatchlist ? 'active' : ''}`}
          onClick={handleWatchlistToggle}
          aria-label={inWatchlist ? 'Remove from watchlist' : 'Add to watchlist'}
        >
          {inWatchlist ? (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
          )}
        </button>
        
        <div className="poster-overlay">
          <p className="poster-overview">{item.overview}</p>
        </div>
      </div>
      
      <div className="poster-info">
        <h3 className="poster-title">{title}</h3>
        <div className="poster-meta">
          {year && <span className="poster-year">{year}</span>}
          {rating && (
            <span className="poster-rating">
              ★ {rating}
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}
