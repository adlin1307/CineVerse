import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getTrending, getPopularMovies, getPopularSeries } from '../../services/api'
import { isInWatchlist, addToWatchlist, removeFromWatchlist } from '../../services/watchlist'
import PosterRow from '../../components/PosterRow/PosterRow'
import CineImage from '../../components/CineImage/CineImage'
import './HomePage.css'

export default function HomePage() {
  const [trending, setTrending] = useState([])
  const [popularMovies, setPopularMovies] = useState([])
  const [popularSeries, setPopularSeries] = useState([])
  const [featured, setFeatured] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  useEffect(() => {
    loadHomeData()
  }, [])
  
  async function loadHomeData() {
    try {
      setLoading(true)
      setError(null)
      
      const [trendingData, moviesData, seriesData] = await Promise.all([
        getTrending('all', 'week'),
        getPopularMovies(1),
        getPopularSeries(1)
      ])
      
      setTrending(trendingData.results || [])
      setPopularMovies(moviesData.results || [])
      setPopularSeries(seriesData.results || [])
      
      // Set featured content from trending
      if (trendingData.results && trendingData.results.length > 0) {
        setFeatured(trendingData.results[0])
      }
    } catch (err) {
      console.error('Failed to load home data:', err)
      setError('Failed to load content. Please try again later.')
    } finally {
      setLoading(false)
    }
  }
  
  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p className="loading-text">Loading content...</p>
      </div>
    )
  }
  
  if (error) {
    return (
      <div className="container section">
        <div className="error-message">
          <svg 
            className="error-icon" 
            width="48" 
            height="48" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2"
            style={{ margin: '0 auto var(--spacing-md)' }}
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={loadHomeData}>
            Try Again
          </button>
        </div>
      </div>
    )
  }
  
  return (
    <div className="home-page">
      {featured && <HeroSection featured={featured} />}
      
      <div className="browse-sections">
        <div className="browse-container">
          <PosterRow
            title="Trending Now"
            items={trending.slice(0, 12)}
            mediaType="mixed"
          />
          
          <PosterRow
            title="Popular Movies"
            items={popularMovies.slice(0, 12)}
            viewAllLink="/movies"
            mediaType="movie"
          />
          
          <PosterRow
            title="Binge-Worthy Series"
            items={popularSeries.slice(0, 12)}
            viewAllLink="/series"
            mediaType="tv"
          />
        </div>
      </div>
    </div>
  )
}

function HeroSection({ featured }) {
  const title = featured.title || featured.name
  const releaseDate = featured.release_date || featured.first_air_date
  const year = releaseDate ? new Date(releaseDate).getFullYear() : null
  const rating = featured.vote_average ? featured.vote_average.toFixed(1) : null
  const backdropPath = featured.backdrop_path
  const mediaType = featured.media_type || 'movie'
  const detailPath = mediaType === 'movie' ? `/movie/${featured.id}` : `/series/${featured.id}`
  
  // Extract first 3 genres if available
  const genres = featured.genre_ids ? featured.genre_ids.slice(0, 3) : []
  const genreNames = {
    28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime",
    99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History",
    27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Sci-Fi",
    10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western"
  }

  const [inWatchlist, setInWatchlist] = useState(() => isInWatchlist(featured.id, mediaType))

  useEffect(() => {
    setInWatchlist(isInWatchlist(featured.id, mediaType))
    const handleUpdate = () => setInWatchlist(isInWatchlist(featured.id, mediaType))
    window.addEventListener('watchlistUpdated', handleUpdate)
    return () => window.removeEventListener('watchlistUpdated', handleUpdate)
  }, [featured.id, mediaType])

  const handleWatchlistToggle = () => {
    if (inWatchlist) {
      removeFromWatchlist(featured.id, mediaType)
      setInWatchlist(false)
    } else {
      addToWatchlist({
        ...featured,
        media_type: mediaType
      })
      setInWatchlist(true)
    }
    window.dispatchEvent(new Event('watchlistUpdated'))
  }
  
  return (
    <section className="hero-section">
      <div className="hero-backdrop">
        <CineImage
          src={backdropPath ? `https://image.tmdb.org/t/p/original${backdropPath}` : null}
          alt={title}
          title={title}
          year={year}
          variant="backdrop"
          showTitleInFallback={false}
        />
      </div>
      
      <div className="hero-content">
        <div className="hero-inner">
          <h1 className="hero-title">{title}</h1>
          
          <div className="hero-meta">
            {year && <span>{year}</span>}
            {rating && (
              <span className="hero-rating">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                </svg>
                {rating}
              </span>
            )}
          </div>
          
          {genres.length > 0 && (
            <div className="hero-genres">
              {genres.map(id => (
                <span key={id} className="genre-badge">
                  {genreNames[id] || 'Unknown'}
                </span>
              ))}
            </div>
          )}
          
          {featured.overview && (
            <p className="hero-overview">{featured.overview}</p>
          )}
          
          <div className="hero-actions">
            <Link to={detailPath} className="btn btn-primary">
              Explore Title
            </Link>
            <button 
              className={`btn ${inWatchlist ? 'btn-primary' : 'btn-secondary'}`}
              onClick={handleWatchlistToggle}
            >
              {inWatchlist ? '✓ In Watchlist' : '+ Add to Watchlist'}
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
