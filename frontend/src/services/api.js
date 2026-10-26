const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export function getAuthToken() {
  return localStorage.getItem('cineverse_token');
}

export function setAuthSession(token, user) {
  if (token) {
    localStorage.setItem('cineverse_token', token);
  } else {
    localStorage.removeItem('cineverse_token');
  }
  if (user) {
    localStorage.setItem('cineverse_user', JSON.stringify(user));
  } else {
    localStorage.removeItem('cineverse_user');
  }
  window.dispatchEvent(new Event('authChanged'));
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem('cineverse_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...options.headers,
  };
  
  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });
    
    if (response.status === 401 && token) {
      // Session expired or invalid
      setAuthSession(null, null);
    }
    
    if (!response.ok) {
      let errDetail = response.statusText;
      try {
        const errorJson = await response.json();
        if (errorJson.detail) errDetail = errorJson.detail;
      } catch {}
      const err = new Error(errDetail);
      err.status = response.status;
      throw err;
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

// Authentication
export async function signupUser(username, password) {
  const data = await fetchAPI('/api/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });
  if (data.token) {
    setAuthSession(data.token, data.user);
  }
  return data;
}

export async function loginUser(username, password) {
  const data = await fetchAPI('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });
  if (data.token) {
    setAuthSession(data.token, data.user);
  }
  return data;
}

export async function logoutUser() {
  try {
    await fetchAPI('/api/auth/logout', { method: 'POST' });
  } catch {}
  setAuthSession(null, null);
}

export async function checkAuthMe() {
  return fetchAPI('/api/auth/me');
}

// Watchlist API
export async function fetchWatchlistAPI() {
  return fetchAPI('/api/watchlist');
}

export async function addWatchlistAPI(item) {
  return fetchAPI('/api/watchlist', {
    method: 'POST',
    body: JSON.stringify({ item })
  });
}

export async function removeWatchlistAPI(mediaType, itemId) {
  return fetchAPI(`/api/watchlist/${mediaType}/${itemId}`, {
    method: 'DELETE'
  });
}

export async function clearWatchlistAPI() {
  return fetchAPI('/api/watchlist', {
    method: 'DELETE'
  });
}

export async function syncWatchlistAPI(items) {
  return fetchAPI('/api/watchlist/sync', {
    method: 'POST',
    body: JSON.stringify({ items })
  });
}

// Scout Conversations API
export async function fetchConversationsAPI() {
  return fetchAPI('/api/scout/conversations');
}

export async function fetchConversationAPI(convId) {
  return fetchAPI(`/api/scout/conversations/${convId}`);
}

export async function createConversationAPI(id, title) {
  return fetchAPI('/api/scout/conversations', {
    method: 'POST',
    body: JSON.stringify({ id, title })
  });
}

export async function deleteConversationAPI(convId) {
  return fetchAPI(`/api/scout/conversations/${convId}`, {
    method: 'DELETE'
  });
}

export async function sendScoutChatAPI(message, conversationHistory = [], conversationId = null, options = {}) {
  return fetchAPI('/api/scout/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      conversation_history: conversationHistory,
      conversation_id: conversationId
    }),
    ...options
  });
}

