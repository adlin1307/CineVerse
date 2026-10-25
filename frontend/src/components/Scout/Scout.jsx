import { useState, useEffect, useRef } from 'react'
import { CHATBOT_NAME, CHATBOT_ICON_SVG, CHATBOT_GREETING, CONVERSATION_STARTERS, QUICK_REFINEMENTS } from './scoutConfig.jsx'
import PosterCard from '../PosterCard/PosterCard'
import './Scout.css'

const createInitialMessage = () => ({
  id: `scout-welcome-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
  type: 'bot',
  content: CHATBOT_GREETING,
  timestamp: new Date()
})

export default function Scout({ isOpen, onClose }) {
  const [messages, setMessages] = useState(() => [createInitialMessage()])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expandedAnalysis, setExpandedAnalysis] = useState({})
  const [serviceHealth, setServiceHealth] = useState({ configured: true, model: 'gemini-2.5-flash', tmdb: true })
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)
  const requestIdRef = useRef(0)
  const abortControllerRef = useRef(null)
  const lastUserQueryRef = useRef('')

  const toggleAnalysis = (itemKey) => {
    setExpandedAnalysis(prev => ({
      ...prev,
      [itemKey]: !prev[itemKey]
    }))
  }

  // Fetch Scout engine health status when opened
  useEffect(() => {
    if (isOpen) {
      const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
      fetch(`${apiBase}/api/scout/health`)
        .then(res => (res.ok ? res.json() : null))
        .then(data => {
          if (data) {
            setServiceHealth({
              configured: !!data.configured,
              model: data.model || 'gemini-2.5-flash',
              tmdb: !!data.tmdb_configured
            })
          }
        })
        .catch(() => {
          // Default to deterministic fallback state
          setServiceHealth({ configured: false, model: '', tmdb: true })
        })
    }
  }, [isOpen])
  
  // Ensure we always have at least the greeting when opened
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([createInitialMessage()])
    }
  }, [isOpen, messages.length])
  
  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
  
  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [isOpen])
  
  const handleSend = async (messageText = inputValue.trim()) => {
    if (!messageText || isLoading) return
    
    lastUserQueryRef.current = messageText

    // Abort any existing in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    
    // Add user message
    const userMessage = {
      id: `user-msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      type: 'user',
      content: messageText,
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)
    setError(null)
    
    const currentRequestId = ++requestIdRef.current
    const controller = new AbortController()
    abortControllerRef.current = controller
    
    try {
      const timeoutId = setTimeout(() => controller.abort(), 30000) // 30 second timeout
      
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/scout/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: messageText,
          conversation_history: messages.map(m => ({
            role: m.type === 'user' ? 'user' : 'assistant',
            content: m.content,
            recommendations: m.recommendations || []
          }))
        }),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      
      if (!response.ok) {
        let errorDetail = ''
        try {
          const errData = await response.json()
          errorDetail = errData?.detail || ''
        } catch {
          // Response body was not JSON
        }
        const error = new Error(errorDetail || `Failed to get response: ${response.statusText}`)
        error.status = response.status
        error.detail = errorDetail
        throw error
      }
      
      const data = await response.json()
      
      // Guard against out-of-order async responses
      if (currentRequestId !== requestIdRef.current) return
      
      // Add Scout's response
      const botMessage = {
        id: `bot-msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        type: 'bot',
        content: data.message,
        recommendations: data.recommendations || [],
        timestamp: new Date()
      }
      
      setMessages(prev => [...prev, botMessage])
    } catch (err) {
      if (currentRequestId !== requestIdRef.current) return
      console.error('Scout chat error:', err)
      
      // Handle different error types
      let errorMessage = 'Oops! I had trouble connecting. Can you try again?'
      const status = err.status
      const detail = typeof err.detail === 'string' ? err.detail : ''
      
      if (err.name === 'AbortError' || status === 504 || /timeout|timed out|too long/i.test(detail)) {
        errorMessage = 'Scout took a bit too long to respond. The service might be busy—try again in a moment!'
      } else if (status === 429 || /rate limit|overwhelmed|too many requests/i.test(detail) || err.message?.includes('429')) {
        errorMessage = "I'm a bit overwhelmed right now (rate limit). Give me a minute and try again?"
      } else if (status === 503 || /not configured|gemini api key/i.test(detail)) {
        errorMessage = 'Scout is currently unavailable because the AI service is not configured. Please verify your GEMINI_API_KEY setup.'
      } else if (status >= 400 && status < 500 && detail && !detail.includes('Traceback') && !detail.includes('File "') && !detail.includes('http')) {
        errorMessage = detail
      }
      
      setError(errorMessage)
      
      // Add error message to chat with retry support
      setMessages(prev => [...prev, {
        id: `error-msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
        type: 'bot',
        content: errorMessage,
        isError: true,
        failedQuery: messageText,
        timestamp: new Date()
      }])
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setIsLoading(false)
        abortControllerRef.current = null
      }
    }
  }

  const handleRetry = (queryToRetry) => {
    const query = queryToRetry || lastUserQueryRef.current
    if (query) {
      handleSend(query)
    }
  }
  
  const handleStarterClick = (starter) => {
    handleSend(starter)
  }
  
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }
  
  const handleNewConversation = () => {
    // 1. Immediately abort any in-flight request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    
    // 2. Invalidate any pending async callbacks
    requestIdRef.current++
    
    // 3. Clear all temporary states
    setIsLoading(false)
    setError(null)
    setInputValue('')
    setExpandedAnalysis({})
    
    // 4. Reset to fresh initial conversation message
    setMessages([createInitialMessage()])
    
    // 5. Ensure input is focused and ready to type
    setTimeout(() => {
      inputRef.current?.focus()
    }, 50)
  }
  
  if (!isOpen) return null
  
  return (
    <div className="scout-overlay" onClick={onClose}>
      <div className="scout-drawer" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="scout-header">
          <div className="scout-identity">
            <div className="scout-icon"><CHATBOT_ICON_SVG /></div>
            <div>
              <div className="scout-title-row">
                <h2 className="scout-title">{CHATBOT_NAME}</h2>
                <span 
                  className={`scout-status-pill ${serviceHealth.configured ? 'ai' : 'fallback'}`}
                  title={serviceHealth.configured ? `AI Active (${serviceHealth.model})` : 'Offline / Deterministic Fallback Mode'}
                >
                  <span className="status-dot"></span>
                  {serviceHealth.configured ? 'AI Active' : 'Deterministic Mode'}
                </span>
              </div>
              <p className="scout-subtitle">Your movie & series discovery assistant</p>
            </div>
          </div>
          <div className="scout-actions">
            <button
              type="button"
              className="scout-btn scout-btn-ghost"
              onClick={handleNewConversation}
              title="New conversation"
              aria-label="Start new conversation"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 5v14M5 12h14" />
              </svg>
            </button>
            <button
              type="button"
              className="scout-btn scout-btn-ghost"
              onClick={onClose}
              aria-label="Close Scout"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        
        {/* Messages */}
        <div className="scout-messages">
          {messages.map((message) => (
            <div key={message.id} className={`scout-message ${message.type}`}>
              {message.type === 'bot' && (
                <div className="message-avatar"><CHATBOT_ICON_SVG /></div>
              )}
              <div className="message-content">
                <div className={`message-bubble ${message.isError ? 'error' : ''}`}>
                  {message.content}
                  {message.isError && (
                    <div className="message-retry-container">
                      <button
                        type="button"
                        className="scout-retry-btn"
                        onClick={() => handleRetry(message.failedQuery)}
                      >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                          <path d="M1 4v6h6M23 20v-6h-6" />
                          <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15" />
                        </svg>
                        <span>Retry</span>
                      </button>
                    </div>
                  )}
                </div>
                
                {/* Recommendations */}
                {message.recommendations && message.recommendations.length > 0 && (
                  <div className="message-recommendations">
                    {message.recommendations.map(item => {
                      const itemKey = `${item.media_type || 'movie'}-${item.id}`
                      const isExpanded = !!expandedAnalysis[itemKey]
                      return (
                        <div key={itemKey} className={`recommendation-card ${isExpanded ? 'is-expanded' : ''}`}>
                          <div className="recommendation-compact-view">
                            <PosterCard item={item} mediaType={item.media_type || 'movie'} />
                            {item.explanation && (
                              <p className="recommendation-reason">{item.explanation}</p>
                            )}
                            {item.analysis && (
                              <div className="recommendation-analysis-wrapper">
                                <button
                                  type="button"
                                  className="view-analysis-btn"
                                  onClick={() => toggleAnalysis(itemKey)}
                                  aria-expanded={isExpanded}
                                  id={`view-analysis-${itemKey}`}
                                >
                                  <span>{isExpanded ? 'Hide Analysis' : 'View Analysis'}</span>
                                  <svg
                                    className={`analysis-chevron ${isExpanded ? 'rotated' : ''}`}
                                    width="12"
                                    height="12"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                  >
                                    <path d="M6 9l6 6 6-6" />
                                  </svg>
                                </button>
                              </div>
                            )}
                          </div>

                          {item.analysis && isExpanded && (
                            <div className="recommendation-analysis-panel">
                              <div className="analysis-header">
                                <span className="analysis-section-title">Selection Analysis</span>
                                {item.analysis.media_type_label && (
                                  <span className="analysis-media-badge">{item.analysis.media_type_label}</span>
                                )}
                              </div>
                              
                              {item.analysis.mood_match && (
                                <div className="analysis-block">
                                  <span className="analysis-block-label">Why this fits</span>
                                  <p className="analysis-block-text">{item.analysis.mood_match}</p>
                                </div>
                              )}

                              {item.analysis.story_evidence && (
                                <div className="analysis-block">
                                  <span className="analysis-block-label">Story focus</span>
                                  <p className="analysis-block-text story-quote">“{item.analysis.story_evidence}”</p>
                                </div>
                              )}

                              <div className="analysis-signals-grid">
                                {item.analysis.ranking_signals && (
                                  <div className="analysis-signal-item">
                                    <span className="analysis-block-label">TMDB Consensus</span>
                                    <span className="analysis-signal-value">{item.analysis.ranking_signals}</span>
                                  </div>
                                )}
                                {item.analysis.genre_match && (
                                  <div className="analysis-signal-item">
                                    <span className="analysis-block-label">Genres</span>
                                    <span className="analysis-signal-value">{item.analysis.genre_match}</span>
                                  </div>
                                )}
                              </div>

                              {item.analysis.constraints_applied && item.analysis.constraints_applied.length > 0 && (
                                <div className="analysis-block">
                                  <span className="analysis-block-label">Active constraints</span>
                                  <div className="analysis-tags">
                                    {item.analysis.constraints_applied.map((c, i) => (
                                      <span key={i} className="analysis-tag">{c}</span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {item.analysis.provenance && (
                                <div className="analysis-provenance">
                                  {item.analysis.provenance}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {/* Loading indicator with skeleton cards */}
          {isLoading && (
            <div className="scout-message bot loading-block">
              <div className="message-avatar"><CHATBOT_ICON_SVG /></div>
              <div className="message-content">
                <div className="message-bubble loading">
                  <div className="typing-dots">
                    <span className="typing-dot"></span>
                    <span className="typing-dot"></span>
                    <span className="typing-dot"></span>
                  </div>
                  <span className="typing-label">Scouting TMDB catalog...</span>
                </div>
                <div className="scout-skeleton-grid">
                  <div className="scout-skeleton-card">
                    <div className="skeleton-poster shimmer"></div>
                    <div className="skeleton-line shimmer"></div>
                    <div className="skeleton-line shimmer short"></div>
                  </div>
                  <div className="scout-skeleton-card">
                    <div className="skeleton-poster shimmer"></div>
                    <div className="skeleton-line shimmer"></div>
                    <div className="skeleton-line shimmer short"></div>
                  </div>
                </div>
              </div>
            </div>
          )}
          
          {/* Conversation starters (only show at start) */}
          {messages.length <= 1 && !isLoading && (
            <div className="conversation-starters">
              {CONVERSATION_STARTERS.map((starter, index) => (
                <button
                  key={index}
                  type="button"
                  className="starter-button"
                  onClick={() => handleStarterClick(starter)}
                >
                  {starter}
                </button>
              ))}
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
        
        {/* Quick refinement pills (show when conversation has begun) */}
        {messages.length > 1 && !isLoading && (
          <div className="scout-quick-refinements">
            {QUICK_REFINEMENTS.map((refinement, index) => (
              <button
                key={index}
                type="button"
                className="refinement-pill"
                onClick={() => handleSend(refinement)}
              >
                {refinement}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="scout-input-container">
          <div className="scout-input-wrapper">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Ask ${CHATBOT_NAME} anything...`}
              className="scout-input"
              rows="1"
              disabled={isLoading}
            />
            <button
              className="scout-send-btn"
              onClick={() => handleSend()}
              disabled={!inputValue.trim() || isLoading}
              aria-label="Send message"
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            </button>
          </div>
          <p className="scout-hint">
            Press Enter to send, Shift+Enter for new line
          </p>
        </div>
      </div>
    </div>
  )
}
