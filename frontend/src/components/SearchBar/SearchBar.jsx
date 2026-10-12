import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './SearchBar.css'

export default function SearchBar({ onSearch }) {
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
  
  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`)
      if (onSearch) onSearch()
    }
  }
  
  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Search movies, series..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="search-input"
      />
      <button type="submit" className="search-button">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
      </button>
    </form>
  )
}
