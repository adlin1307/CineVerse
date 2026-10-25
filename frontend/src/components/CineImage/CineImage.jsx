import { useState } from 'react'
import './CineImage.css'

/**
 * CineImage - Production-ready, resilient cinematic image component.
 *
 * Features:
 * - Lazy loading by default
 * - Graceful error handling (onError switches to styled placeholder)
 * - Cinematic fallback with gold branding, film reel iconography, title & year
 * - Supports variants: 'poster', 'backdrop', 'profile'
 */
export default function CineImage({
  src,
  alt = '',
  title = '',
  year = null,
  variant = 'poster', // 'poster' | 'backdrop' | 'profile'
  className = '',
  loading = 'lazy',
  aspectRatio = null,
  showTitleInFallback = true
}) {
  const [hasError, setHasError] = useState(false)
  const [isLoaded, setIsLoaded] = useState(false)

  const handleImageError = () => {
    setHasError(true)
  }

  const handleImageLoad = () => {
    setIsLoaded(true)
  }

  const effectiveSrc = src && !hasError ? src : null

  return (
    <div
      className={`cine-image-container ${variant} ${className} ${isLoaded ? 'loaded' : 'loading'}`}
      style={aspectRatio ? { aspectRatio } : undefined}
    >
      {effectiveSrc ? (
        <img
          src={effectiveSrc}
          alt={alt || title}
          className={`cine-img ${isLoaded ? 'visible' : 'hidden'}`}
          loading={loading}
          onLoad={handleImageLoad}
          onError={handleImageError}
        />
      ) : null}

      {/* Fallback / Missing state */}
      {(!effectiveSrc || !isLoaded) && (
        <div className={`cine-fallback ${variant} ${effectiveSrc ? 'underlay' : 'active'}`}>
          <div className="cine-fallback-mesh"></div>
          
          <div className="cine-fallback-content">
            {variant === 'profile' ? (
              <svg className="cine-fallback-icon" width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            ) : variant === 'backdrop' ? (
              <div className="cine-backdrop-branding">
                <div className="cine-badge">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18 4l2 4h-3l-2-4h-2l2 4h-3l-2-4H8l2 4H7L5 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4h-4z" />
                  </svg>
                  <span>CINEVERSE SELECTION</span>
                </div>
                {showTitleInFallback && title && <h2 className="cine-fallback-title">{title}</h2>}
              </div>
            ) : (
              <>
                <div className="cine-reel-icon">
                  <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
                    <rect x="2" y="2" width="20" height="20" rx="3" />
                    <line x1="7" y1="2" x2="7" y2="22" strokeDasharray="2 2" />
                    <line x1="17" y1="2" x2="17" y2="22" strokeDasharray="2 2" />
                    <line x1="2" y1="12" x2="22" y2="12" />
                    <circle cx="12" cy="7" r="1.5" fill="currentColor" />
                    <circle cx="12" cy="17" r="1.5" fill="currentColor" />
                  </svg>
                </div>
                {showTitleInFallback && (
                  <div className="cine-fallback-text">
                    <span className="cine-brand-tag">CINEVERSE</span>
                    <span className="cine-title-tag">{title || 'Cinema Preview'}</span>
                    {year && <span className="cine-year-tag">{year}</span>}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
