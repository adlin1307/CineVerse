const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API request failed:', error);
    throw error;
  }
}

// Search & Discovery
export async function searchMulti(query, page = 1) {
  return fetchAPI(`/api/search/multi?query=${encodeURIComponent(query)}&page=${page}`);
}

export async function getTrending(mediaType = 'all', timeWindow = 'week') {
  return fetchAPI(`/api/search/trending?media_type=${mediaType}&time_window=${timeWindow}`);
}

// Movies
export async function getPopularMovies(page = 1) {
  return fetchAPI(`/api/movies/popular?page=${page}`);
}

export async function discoverMovies(params = {}) {
  const queryString = new URLSearchParams(params).toString();
  return fetchAPI(`/api/movies/discover?${queryString}`);
}

export async function getMovieDetails(movieId) {
  return fetchAPI(`/api/movies/${movieId}`);
}

export async function getMovieGenres() {
  return fetchAPI('/api/movies/genres/list');
}

// Series
export async function getPopularSeries(page = 1) {
  return fetchAPI(`/api/series/popular?page=${page}`);
}

export async function discoverSeries(params = {}) {
  const queryString = new URLSearchParams(params).toString();
  return fetchAPI(`/api/series/discover?${queryString}`);
}

export async function getSeriesDetails(seriesId) {
  return fetchAPI(`/api/series/${seriesId}`);
}

export async function getSeriesGenres() {
  return fetchAPI('/api/series/genres/list');
}

// Health Check
export async function checkHealth() {
  return fetchAPI('/health');
}

// People
export async function getPersonDetails(personId) {
  return fetchAPI(`/api/people/${personId}`);
}

// Videos
export async function getMovieVideos(movieId) {
  return fetchAPI(`/api/movies/${movieId}/videos`);
}

export async function getSeriesVideos(seriesId) {
  return fetchAPI(`/api/series/${seriesId}/videos`);
}

// Recommendations
export async function getSituationAwareRecommendations(params) {
  return fetchAPI('/api/recommendations/situation-aware', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function getRecommendationOptions() {
  return fetchAPI('/api/recommendations/options');
}

export async function getRecommendationGenres() {
  return fetchAPI('/api/recommendations/genres');
}
