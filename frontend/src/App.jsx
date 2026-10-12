import { Routes, Route } from 'react-router-dom'
import Navigation from './components/Navigation/Navigation'
import HomePage from './pages/HomePage/HomePage'
import MoviesPage from './pages/MoviesPage/MoviesPage'
import SeriesPage from './pages/SeriesPage/SeriesPage'
import DetailPage from './pages/DetailPage/DetailPage'
import WatchlistPage from './pages/WatchlistPage/WatchlistPage'
import SearchResults from './pages/SearchResults/SearchResults'
import './App.css'

function App() {
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
          <Route path="/watchlist" element={<WatchlistPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
