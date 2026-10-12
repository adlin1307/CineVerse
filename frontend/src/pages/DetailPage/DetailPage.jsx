import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { getMovieDetails, getSeriesDetails } from '../../services/api'
import { isInWatchlist, addToWatchlist, removeFromWatchlist } from '../../services/watchlist'
import PosterRow from '../../components/PosterRow/PosterRow'
import './DetailPage.css'

export default function DetailPage({ mediaType }) {
  const { id } = useParams()
  const [details, setDetails] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [inWatchlist, setInWatchlist] = useState(false)
  
  useEffect(() => {
    loadDetails()
    checkWatchlist()
  }, [id, mediaType])
  
  async function loadDetails() {
    try {
      setLoading(true)
      setError(null)
      
      const data = mediaType === 'movie' 
        ? await getMovieDetails(id)
        : await getSeriesDetails(id)
      
      setDetails(data)
    } catch (err) {
      console.error('Failed to load details:', err)
      setError('Failed to load details. Please try again.')
    } finally {
      setLoading(false)
    }
  }
  
  function checkWatchlist() {
    setInWatchlist(isInWatchlist(parseInt(id), mediaType))
  }
  
  const handleWatchlistToggle = () => {
    if (!details) return
    
    if (inWatchlist) {
      removeFromWatchlist(details.id, mediaType)
    } else {
      addToWatchlist({
        ...details,
        media_type: mediaType,
        title: details.title || details.name,
      })
    }
    
    checkWatchlist()
    window.dispatchEvent(new Event('watchlistUpdated'))
  }
  
  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    )
  }
  
  if (error || !details) {
    return (
      <div className="container section">
        <div className="error-message">
          <p>{error || 'Content not found'}</p>
        </div>
      </div>
    )
  }
  
  const title = details.title || details.name
  const originalTitle = details.original_title || details.original_name
  const releaseDate = details.release_date || details.first_air_date
  const year = releaseDate ? new Date(releaseDate).getFullYear() : null
  const rating = details.vote_average ? details.vote_average.toFixed(1) : null
  const voteCount = details.vote_count
  
  const cast = details.credits?.cast?.slice(0, 12) || []
  const director = details.credits?.crew?.find(person => person.job === 'Director')
  const creators = details.created_by || []
  
  const recommendations = details.recommendations?.results?.slice(0, 12) || []
  
  return (
    <div className="detail-page">
      {/* Hero Section */}
      <div className="detail-hero">
        <div className="detail-backdrop">
          {details.backdrop_path ? (
            <img
              src={`https://image.tmdb.org/t/p/original${details.backdrop_path}`}
              alt={title}
            />
          ) : (
            <div style={{ background: 'var(--color-bg-secondary)', width: '100%', height: '100%' }} />
          )}
        </div>
        
        <div className="detail-hero-content">
          <div className="detail-poster">
            {details.poster_path ? (
              <img
                src={`https://image.tmdb.org/t/p/w500${details.poster_path}`}
                alt={title}
              />
            ) : (
              <div className="detail-poster-placeholder">
                <span>No poster available</span>
              </div>
            )}
          </div>
          
          <div className="detail-info">
            <h1 className="detail-title">{title}</h1>
            {originalTitle && originalTitle !== title && (
              <p className="detail-original-title">{originalTitle}</p>
            )}
            
            <div className="detail-meta">
              {year && <span>{year}</span>}
              {rating && (
                <span className="detail-rating">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
                  </svg>
                  {rating}
                  {voteCount && <span style={{ fontWeight: 400, color: 'var(--color-text-muted)' }}>({voteCount.toLocaleString()} votes)</span>}
                </span>
              )}
              {details.runtime && <span>{details.runtime} min</span>}
              {details.number_of_seasons && (
                <span>{details.number_of_seasons} Season{details.number_of_seasons > 1 ? 's' : ''}</span>
              )}
            </div>
            
            {details.genres && details.genres.length > 0 && (
              <div className="detail-genres">
                {details.genres.map(genre => (
                  <span key={genre.id} className="genre-badge">
                    {genre.name}
                  </span>
                ))}
              </div>
            )}
            
            <div className="detail-actions">
              <button 
                className={`btn ${inWatchlist ? 'btn-secondary' : 'btn-primary'}`}
                onClick={handleWatchlistToggle}
              >
                {inWatchlist ? '✓ In Watchlist' : '+ Add to Watchlist'}
              </button>
            </div>
          </div>
        </div>
      </div>
      
      {/* Content Section */}
      <div className="detail-content">
        <div className="detail-grid">
          <div>
            {details.overview && (
              <div className="detail-section">
                <h2>Overview</h2>
                <p className="detail-overview">{details.overview}</p>
              </div>
            )}
            
            {cast.length > 0 && (
              <div className="detail-section">
                <h2>Cast</h2>
                <div className="cast-grid">
                  {cast.map(person => (
                    <div key={person.id} className="cast-card">
                      <div className="cast-photo">
                        {person.profile_path ? (
                          <img
                            src={`https://image.tmdb.org/t/p/w185${person.profile_path}`}
                            alt={person.name}
                          />
                        ) : (
                          <div className="cast-photo-placeholder">
                            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                              <circle cx="12" cy="7" r="4" />
                            </svg>
                          </div>
                        )}
                      </div>
                      <div className="cast-name">{person.name}</div>
                      {person.character && (
                        <div className="cast-character">{person.character}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          
          <div className="detail-sidebar">
            {details.original_language && (
              <div className="detail-fact">
                <div className="detail-fact-label">Original Language</div>
                <div className="detail-fact-value">{details.original_language.toUpperCase()}</div>
              </div>
            )}
            
            {director && (
              <div className="detail-fact">
                <div className="detail-fact-label">Director</div>
                <div className="detail-fact-value">{director.name}</div>
              </div>
            )}
            
            {creators.length > 0 && (
              <div className="detail-fact">
                <div className="detail-fact-label">Created By</div>
                <div className="detail-fact-value">
                  {creators.map(c => c.name).join(', ')}
                </div>
              </div>
            )}
            
            {details.status && (
              <div className="detail-fact">
                <div className="detail-fact-label">Status</div>
                <div className="detail-fact-value">{details.status}</div>
              </div>
            )}
            
            {details.production_companies && details.production_companies.length > 0 && (
              <div className="detail-fact">
                <div className="detail-fact-label">Production</div>
                <div className="detail-fact-value">
                  {details.production_companies.slice(0, 3).map(c => c.name).join(', ')}
                </div>
              </div>
            )}
          </div>
        </div>
        
        {recommendations.length > 0 && (
          <PosterRow
            title="More Like This"
            items={recommendations}
            mediaType={mediaType}
          />
        )}
      </div>
    </div>
  )
}
