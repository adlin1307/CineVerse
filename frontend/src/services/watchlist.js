// Watchlist storage using localStorage
// This will be replaced with backend API calls later

const WATCHLIST_KEY = 'cineverse_watchlist';

export function getWatchlist() {
  try {
    const data = localStorage.getItem(WATCHLIST_KEY);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    console.error('Failed to load watchlist:', error);
    return [];
  }
}

export function addToWatchlist(item) {
  try {
    const watchlist = getWatchlist();
    
    // Check if already exists
    const exists = watchlist.some(w => w.id === item.id && w.media_type === item.media_type);
    if (exists) {
      return watchlist;
    }
    
    // Add timestamp
    const newItem = {
      ...item,
      added_at: new Date().toISOString(),
    };
    
    const updated = [newItem, ...watchlist];
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify(updated));
    return updated;
  } catch (error) {
    console.error('Failed to add to watchlist:', error);
    throw error;
  }
}

export function removeFromWatchlist(id, mediaType) {
  try {
    const watchlist = getWatchlist();
    const updated = watchlist.filter(item => !(item.id === id && item.media_type === mediaType));
    localStorage.setItem(WATCHLIST_KEY, JSON.stringify(updated));
    return updated;
  } catch (error) {
    console.error('Failed to remove from watchlist:', error);
    throw error;
  }
}

export function isInWatchlist(id, mediaType) {
  const watchlist = getWatchlist();
  return watchlist.some(item => item.id === id && item.media_type === mediaType);
}

export function clearWatchlist() {
  try {
    localStorage.removeItem(WATCHLIST_KEY);
    return [];
  } catch (error) {
    console.error('Failed to clear watchlist:', error);
    throw error;
  }
}
