import { useState, useEffect } from 'react'
import { discoverSeries, getSeriesGenres } from '../../services/api'
import PosterCard from '../../components/PosterCard/PosterCard'
import '../MoviesPage/MoviesPage.css'

export default function SeriesPage() {
  const [series, setSeries] = useState([])
  const [genres, setGenres] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  
  // Filters
  const [selectedGenre, setSelectedGenre] = useState('')
  const [sortBy, setSortBy] = useState('popularity.desc')
  
  useEffect(() => {
    loadGenres()
  }, [])
  
  useEffect(() => {
    loadSeries()
  }, [page, selectedGenre, sortBy])
  
  async function loadGenres() {
    try {
      const data = await getSeriesGenres()
      setGenres(data.genres || [])
    } catch (err) {
      console.error('Failed to load genres:', err)
    }
  }
  
  async function loadSeries() {
    try {
      setLoading(true)
      setError(null)
      
      const params = {
        page,
        sort_by: sortBy,
      }
      
      if (selectedGenre) {
        params.with_genres = selectedGenre
      }
      
      const data = await discoverSeries(params)
      
      if (page === 1) {
        setSeries(data.results || [])
      } else {
        setSeries(prev => [...prev, ...(data.results || [])])
      }
      
      setHasMore(data.page < data.total_pages)
    } catch (err) {
      console.error('Failed to load series:', err)
      setError('Failed to load series. Please try again.')
    } finally {
      setLoading(false)
    }
  }
  
  const handleFilterChange = () => {
    setPage(1)
    setSeries([])
  }
  
  const handleGenreChange = (genreId) => {
    setSelectedGenre(genreId)
    handleFilterChange()
  }
  
  const handleSortChange = (sort) => {
    setSortBy(sort)
    handleFilterChange()
  }
  
  const loadMore = () => {
    if (!loading && hasMore) {
      setPage(prev => prev + 1)
    }
  }
  
  return (
    <div className="movies-page">
      <div className="container">
        <div className="page-header">
          <h1>Discover Series</h1>
          <p className="page-subtitle">
            Explore captivating television series from every corner of the world
          </p>
        </div>
        
        <div className="filters-section">
          <div className="filter-group">
            <label>Sort by:</label>
            <select value={sortBy} onChange={(e) => handleSortChange(e.target.value)} className="filter-select">
              <option value="popularity.desc">Most Popular</option>
              <option value="popularity.asc">Least Popular</option>
              <option value="vote_average.desc">Highest Rated</option>
              <option value="vote_average.asc">Lowest Rated</option>
              <option value="first_air_date.desc">Newest First</option>
              <option value="first_air_date.asc">Oldest First</option>
            </select>
          </div>
          
          {genres.length > 0 && (
            <div className="filter-group">
              <label>Genre:</label>
              <select value={selectedGenre} onChange={(e) => handleGenreChange(e.target.value)} className="filter-select">
                <option value="">All Genres</option>
                {genres.map(genre => (
                  <option key={genre.id} value={genre.id}>{genre.name}</option>
                ))}
              </select>
            </div>
          )}
        </div>
        
        {error && (
          <div className="error-message">{error}</div>
        )}
        
        {series.length > 0 && (
          <div className="posters-grid">
            {series.map(show => (
              <PosterCard key={show.id} item={show} mediaType="tv" />
            ))}
          </div>
        )}
        
        {loading && page === 1 && (
          <div className="loading">
            <div className="spinner"></div>
          </div>
        )}
        
        {!loading && series.length === 0 && (
          <div className="empty-state">
            <h3>No series found</h3>
            <p>Try adjusting your filters</p>
          </div>
        )}
        
        {hasMore && !loading && series.length > 0 && (
          <div className="load-more-container">
            <button className="btn btn-secondary" onClick={loadMore}>
              Load More
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
