import { useState, useEffect } from 'react'
import { getWatchlist, clearWatchlist } from '../../services/watchlist'
import PosterCard from '../../components/PosterCard/PosterCard'
import '../MoviesPage/MoviesPage.css'
import './WatchlistPage.css'

export default function WatchlistPage() {
  const [watchlist, setWatchlist] = useState([])
  
  useEffect(() => {
    loadWatchlist()
    
    // Listen for watchlist updates
    const handleUpdate = () => {
      loadWatchlist()
    }
    
    window.addEventListener('watchlistUpdated', handleUpdate)
    return () => window.removeEventListener('watchlistUpdated', handleUpdate)
  }, [])
  
  function loadWatchlist() {
    const items = getWatchlist()
    setWatchlist(items)
  }
  
  const handleClear = () => {
    if (window.confirm('Are you sure you want to clear your entire watchlist?')) {
      clearWatchlist()
      loadWatchlist()
    }
  }
  
  return (
    <div className="movies-page watchlist-page">
      <div className="container">
        <div className="page-header">
          <h1>My Watchlist</h1>
          <p className="page-subtitle">
            {watchlist.length > 0 
              ? `${watchlist.length} title${watchlist.length !== 1 ? 's' : ''} saved for later`
              : 'Save movies and series to watch later'
            }
          </p>
        </div>
        
        {watchlist.length > 0 && (
          <div className="watchlist-actions">
            <button className="btn btn-ghost" onClick={handleClear}>
              Clear Watchlist
            </button>
          </div>
        )}
        
        {watchlist.length > 0 ? (
          <div className="posters-grid">
            {watchlist.map(item => (
              <PosterCard 
                key={`${item.media_type}-${item.id}`} 
                item={item} 
                mediaType={item.media_type} 
              />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
            </svg>
            <h3>Your watchlist is empty</h3>
            <p>Start adding movies and series you want to watch later</p>
          </div>
        )}
      </div>
    </div>
  )
}
