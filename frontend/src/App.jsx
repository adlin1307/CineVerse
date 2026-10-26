import { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { getStoredUser, getAuthToken } from './services/api'
import Navigation from './components/Navigation/Navigation'
import LandingPage from './pages/LandingPage/LandingPage'
import HomePage from './pages/HomePage/HomePage'
import MoviesPage from './pages/MoviesPage/MoviesPage'
import SeriesPage from './pages/SeriesPage/SeriesPage'
import DetailPage from './pages/DetailPage/DetailPage'
import WatchlistPage from './pages/WatchlistPage/WatchlistPage'
import SearchResults from './pages/SearchResults/SearchResults'
import PersonDetailPage from './pages/PersonDetailPage/PersonDetailPage'
import './App.css'

function App() {
  const [currentUser, setCurrentUser] = useState(() => {
    const token = getAuthToken()
    const user = getStoredUser()
    return token && user ? user : null
  })

  useEffect(() => {
    const handleAuthChange = () => {
      const token = getAuthToken()
      const user = getStoredUser()
      setCurrentUser(token && user ? user : null)
    }
    window.addEventListener('authChanged', handleAuthChange)
    return () => window.removeEventListener('authChanged', handleAuthChange)
  }, [])

  if (!currentUser) {
    return (
      <div className="app">
        <LandingPage onAuthSuccess={() => setCurrentUser(getStoredUser())} />
      </div>
    )
  }

  return (
    <div className="app">
      <Navigation />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/movies" element={<MoviesPage />} />
          <Route path="/series" element={<SeriesPage />} />
          <Route path="/search" element={<SearchResults />} />
          <Route path="/movie/:id" element={<DetailPage mediaType="movie" />} />
          <Route path="/series/:id" element={<DetailPage mediaType="tv" />} />
          <Route path="/person/:personId" element={<PersonDetailPage />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
