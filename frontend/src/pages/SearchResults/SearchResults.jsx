import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { searchMulti } from '../../services/api'
import PosterCard from '../../components/PosterCard/PosterCard'
import '../MoviesPage/MoviesPage.css'
import './SearchResults.css'

export default function SearchResults() {
  const [searchParams] = useSearchParams()
  const query = searchParams.get('q') || ''
  
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  
  useEffect(() => {
    if (query) {
      setPage(1)
      loadSearchResults(1, true)
    }
  }, [query])
  
  useEffect(() => {
    if (page > 1) {
      loadSearchResults(page, false)
    }
  }, [page])
  
  async function loadSearchResults(currentPage, reset = false) {
    try {
      if (reset) {
        setLoading(true)
        setError(null)
      }
      
      const data = await searchMulti(query, currentPage)
      
      // Filter out people results, keep only movies and TV shows
      const filteredResults = (data.results || []).filter(
        item => item.media_type === 'movie' || item.media_type === 'tv'
      )
      
      if (reset) {
        setResults(filteredResults)
      } else {
        setResults(prev => [...prev, ...filteredResults])
      }
      
      setHasMore(data.page < data.total_pages)
    } catch (err) {
      console.error('Search failed:', err)
      setError('Search failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }
  
  const loadMore = () => {
    if (!loading && hasMore) {
      setPage(prev => prev + 1)
    }
  }
  
  if (!query) {
    return (
      <div className="movies-page search-results-page">
        <div className="container">
          <div className="page-header">
            <h1>Search</h1>
            <p className="page-subtitle">Enter a search query to find movies and series</p>
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="movies-page search-results-page">
      <div className="container">
        <div className="page-header">
          <h1>Search Results</h1>
          <p className="page-subtitle">
            {loading && page === 1 
              ? `Searching for "${query}"...`
              : `Results for "${query}"`
            }
          </p>
        </div>
        
        {error && (
          <div className="error-message">{error}</div>
        )}
        
        {!loading && results.length === 0 && !error && (
          <div className="empty-state">
            <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            <h3>No results found</h3>
            <p>We couldn't find any movies or series matching "{query}"</p>
            <p style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
              Try different keywords or check your spelling
            </p>
          </div>
        )}
        
        {results.length > 0 && (
          <>
            <div className="search-results-info">
              <p className="results-count">
                {results.length} {results.length === 1 ? 'result' : 'results'}
                {hasMore && ' (showing first results)'}
              </p>
            </div>
            
            <div className="posters-grid">
              {results.map((item) => (
                <PosterCard 
                  key={`${item.media_type}-${item.id}`} 
                  item={item} 
                  mediaType={item.media_type} 
                />
              ))}
            </div>
          </>
        )}
        
        {loading && page === 1 && (
          <div className="loading">
            <div className="spinner"></div>
          </div>
        )}
        
        {hasMore && !loading && results.length > 0 && (
          <div className="load-more-container">
            <button className="btn btn-secondary" onClick={loadMore}>
              Load More Results
            </button>
          </div>
        )}
        
        {loading && page > 1 && (
          <div className="loading-more">
            <div className="spinner" style={{ width: '30px', height: '30px' }}></div>
          </div>
        )}
      </div>
    </div>
  )
}
