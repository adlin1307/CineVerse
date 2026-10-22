import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { getPersonDetails } from '../../services/api'
import PosterCard from '../../components/PosterCard/PosterCard'
import './PersonDetailPage.css'

export default function PersonDetailPage() {
  const { personId } = useParams()
  const [person, setPerson] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [creditFilter, setCreditFilter] = useState('all') // 'all', 'movie', 'tv'
  const [visibleCount, setVisibleCount] = useState(20) // Number of items to display
  
  useEffect(() => {
    loadPersonDetails()
  }, [personId])
  
  // Reset visible count when filter changes
  useEffect(() => {
    setVisibleCount(20)
  }, [creditFilter])
  
  async function loadPersonDetails() {
    try {
      setLoading(true)
      setError(null)
      
      const data = await getPersonDetails(personId)
      setPerson(data)
    } catch (err) {
      console.error('Failed to load person details:', err)
      setError('Failed to load person details. Please try again.')
    } finally {
      setLoading(false)
    }
  }
  
  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
        <p className="loading-text">Loading profile...</p>
      </div>
    )
  }
  
  if (error || !person) {
    return (
      <div className="container section">
        <div className="error-message">
          <svg 
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
          <p>{error || 'Person not found'}</p>
        </div>
      </div>
    )
  }
  
  // Get credits from API
  const movieCredits = person.movie_credits?.cast || []
  const tvCredits = person.tv_credits?.cast || []
  
  // GLOBAL DEDUPLICATION: Deduplicate by ID and media type
  const deduplicateCredits = (credits, mediaType) => {
    const uniqueMap = new Map()
    
    credits.forEach(credit => {
      const id = credit.id
      if (!id) return // Skip credits without ID
      
      const key = `${mediaType}-${id}`
      
      if (!uniqueMap.has(key)) {
        // First occurrence - add with media_type
        uniqueMap.set(key, { ...credit, media_type: mediaType })
      } else {
        // Duplicate found - merge character/role info if useful
        const existing = uniqueMap.get(key)
        
        // Keep the entry with more episodes (for TV) or higher popularity
        if (mediaType === 'tv') {
          const existingEpisodes = existing.episode_count || 0
          const newEpisodes = credit.episode_count || 0
          if (newEpisodes > existingEpisodes) {
            uniqueMap.set(key, { ...credit, media_type: mediaType })
          }
        } else if ((credit.popularity || 0) > (existing.popularity || 0)) {
          uniqueMap.set(key, { ...credit, media_type: mediaType })
        }
      }
    })
    
    return Array.from(uniqueMap.values())
  }
  
  // Deduplicate movie and TV credits separately
  const uniqueMovieCredits = deduplicateCredits(movieCredits, 'movie')
  const uniqueTvCredits = deduplicateCredits(tvCredits, 'tv')
  
  // Calculate CORRECT counts from full deduplicated datasets
  const totalMovieCount = uniqueMovieCredits.length
  const totalTvCount = uniqueTvCredits.length
  const totalAllCount = totalMovieCount + totalTvCount
  
  // Sort ALL credits by popularity (no slicing yet)
  const allSortedMovieCredits = [...uniqueMovieCredits]
    .sort((a, b) => (b.popularity || 0) - (a.popularity || 0))
  
  const allSortedTvCredits = [...uniqueTvCredits]
    .sort((a, b) => (b.popularity || 0) - (a.popularity || 0))
  
  // Combine and sort for "All" filter
  const allSortedCombinedCredits = [
    ...allSortedMovieCredits.map(c => ({ ...c, media_type: 'movie' })),
    ...allSortedTvCredits.map(c => ({ ...c, media_type: 'tv' }))
  ].sort((a, b) => (b.popularity || 0) - (a.popularity || 0))
  
  // Determine which credits to display based on filter
  let allCredits = allSortedCombinedCredits
  let totalCount = totalAllCount
  
  if (creditFilter === 'movie') {
    allCredits = allSortedMovieCredits
    totalCount = totalMovieCount
  } else if (creditFilter === 'tv') {
    allCredits = allSortedTvCredits
    totalCount = totalTvCount
  }
  
  // Apply visible count limit for display
  const displayCredits = allCredits.slice(0, visibleCount)
  const hasMoreCredits = displayCredits.length < totalCount
  
  // Load more handler
  const handleLoadMore = () => {
    setVisibleCount(prev => prev + 20)
  }
  
  const knownFor = person.known_for_department || 'Acting'
  const birthday = person.birthday ? new Date(person.birthday).toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  }) : null
  
  const age = person.birthday && !person.deathday
    ? new Date().getFullYear() - new Date(person.birthday).getFullYear()
    : null
  
  return (
    <div className="person-detail-page">
      <div className="person-header">
        <div className="container">
          <div className="person-header-content">
            <div className="person-photo-container">
              {person.profile_path ? (
                <img
                  src={`https://image.tmdb.org/t/p/h632${person.profile_path}`}
                  alt={person.name}
                  className="person-photo"
                />
              ) : (
                <div className="person-photo-placeholder">
                  <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
              )}
            </div>
            
            <div className="person-info">
              <h1 className="person-name">{person.name}</h1>
              
              <div className="person-meta">
                <span className="person-department">{knownFor}</span>
                {birthday && (
                  <span>
                    Born {birthday}
                    {age && ` (${age} years old)`}
                  </span>
                )}
                {person.place_of_birth && (
                  <span>{person.place_of_birth}</span>
                )}
              </div>
              
              {person.biography && (
                <div className="person-biography">
                  <h2>Biography</h2>
                  <p>{person.biography}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      
      <div className="person-content">
        <div className="container">
          <div className="filmography-section">
            <div className="filmography-header">
              <h2>Known For</h2>
              <div className="credit-filters">
                <button
                  className={`filter-btn ${creditFilter === 'all' ? 'active' : ''}`}
                  onClick={() => setCreditFilter('all')}
                >
                  All ({totalAllCount})
                </button>
                <button
                  className={`filter-btn ${creditFilter === 'movie' ? 'active' : ''}`}
                  onClick={() => setCreditFilter('movie')}
                >
                  Movies ({totalMovieCount})
                </button>
                <button
                  className={`filter-btn ${creditFilter === 'tv' ? 'active' : ''}`}
                  onClick={() => setCreditFilter('tv')}
                >
                  TV ({totalTvCount})
                </button>
              </div>
            </div>
            
            {displayCredits.length > 0 && (
              <div className="filmography-status">
                Showing {displayCredits.length} of {totalCount} {
                  creditFilter === 'all' ? 'titles' : 
                  creditFilter === 'movie' ? 'movies' : 
                  'series'
                }
              </div>
            )}
            
            {displayCredits.length > 0 ? (
              <>
                <div className="filmography-grid">
                  {displayCredits.map(credit => {
                    const mediaType = credit.media_type || (creditFilter === 'tv' ? 'tv' : 'movie')
                    return (
                      <PosterCard
                        key={`${mediaType}-${credit.id}`}
                        item={{ ...credit, media_type: mediaType }}
                        mediaType={mediaType}
                      />
                    )
                  })}
                </div>
                
                {hasMoreCredits && (
                  <div className="load-more-container">
                    <button className="btn btn-secondary load-more-btn" onClick={handleLoadMore}>
                      Load More {creditFilter === 'all' ? 'Titles' : creditFilter === 'movie' ? 'Movies' : 'Series'}
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="empty-state">
                <p>No credits found</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
