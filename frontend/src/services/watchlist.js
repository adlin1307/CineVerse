import {
  getAuthToken,
  getStoredUser,
  fetchWatchlistAPI,
  addWatchlistAPI,
  removeWatchlistAPI,
  clearWatchlistAPI,
  syncWatchlistAPI
} from './api';

const GUEST_KEY = 'cineverse_watchlist_guest';

function getStorageKey() {
  const user = getStoredUser();
  if (user && user.id) {
    return `cineverse_watchlist_u_${user.id}`;
  }
  return GUEST_KEY;
}

export function getWatchlist() {
  try {
    const key = getStorageKey();
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    console.error('Failed to load watchlist from local cache:', error);
    return [];
  }
}

function saveWatchlistLocal(items) {
  try {
    const key = getStorageKey();
    localStorage.setItem(key, JSON.stringify(items));
  } catch (error) {
    console.error('Failed to save watchlist locally:', error);
  }
}

export async function refreshWatchlistFromServer() {
  if (!getAuthToken()) return getWatchlist();
  try {
    const remoteItems = await fetchWatchlistAPI();
    saveWatchlistLocal(remoteItems);
    window.dispatchEvent(new Event('watchlistUpdated'));
    return remoteItems;
  } catch (err) {
    console.warn('Could not sync watchlist from server, using local cache:', err);
    return getWatchlist();
  }
}

export function addToWatchlist(item) {
  const current = getWatchlist();
  const mediaType = item.media_type || (item.first_air_date || item.name ? 'tv' : 'movie');
  const exists = current.some(w => w.id === item.id && w.media_type === mediaType);
  
  if (exists) {
    return current;
  }
  
  const newItem = {
    ...item,
    media_type: mediaType,
    added_at: new Date().toISOString(),
  };
  
  const updated = [newItem, ...current];
  saveWatchlistLocal(updated);
  
  if (getAuthToken()) {
    addWatchlistAPI(newItem).then(serverItems => {
      saveWatchlistLocal(serverItems);
      window.dispatchEvent(new Event('watchlistUpdated'));
    }).catch(err => {
      console.error('Failed to sync added item to server:', err);
    });
  }
  
  return updated;
}

export function removeFromWatchlist(id, mediaType) {
  const current = getWatchlist();
  const updated = current.filter(item => !(item.id === id && item.media_type === mediaType));
  saveWatchlistLocal(updated);
  
  if (getAuthToken()) {
    removeWatchlistAPI(mediaType, id).then(serverItems => {
      saveWatchlistLocal(serverItems);
      window.dispatchEvent(new Event('watchlistUpdated'));
    }).catch(err => {
      console.error('Failed to sync remove item to server:', err);
    });
  }
  
  return updated;
}

export function isInWatchlist(id, mediaType) {
  const current = getWatchlist();
  return current.some(item => item.id === id && item.media_type === mediaType);
}

export function clearWatchlist() {
  saveWatchlistLocal([]);
  if (getAuthToken()) {
    clearWatchlistAPI().catch(err => {
      console.error('Failed to clear watchlist on server:', err);
    });
  }
  return [];
}

// Initial sync on startup and listen for auth changes
if (typeof window !== 'undefined') {
  if (getAuthToken()) {
    refreshWatchlistFromServer();
  }
  
  window.addEventListener('authChanged', async () => {
    const user = getStoredUser();
    if (user && getAuthToken()) {
      // Check if there are guest items to safely migrate
      try {
        const guestData = localStorage.getItem(GUEST_KEY);
        const guestItems = guestData ? JSON.parse(guestData) : [];
        if (guestItems.length > 0) {
          const merged = await syncWatchlistAPI(guestItems);
          saveWatchlistLocal(merged);
          localStorage.removeItem(GUEST_KEY);
        } else {
          await refreshWatchlistFromServer();
        }
      } catch (e) {
        await refreshWatchlistFromServer();
      }
    }
    window.dispatchEvent(new Event('watchlistUpdated'));
  });
}
