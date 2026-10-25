/**
 * Scout Configuration
 * 
 * Centralized configuration for the chatbot.
 * Change CHATBOT_NAME here to rename Scout throughout the application.
 */

export const CHATBOT_NAME = 'Scout';

// Scout mascot: Original cinema projectionist character
export const CHATBOT_ICON_SVG = () => (
  <svg 
    width="32" 
    height="32" 
    viewBox="0 0 32 32" 
    fill="none" 
    xmlns="http://www.w3.org/2000/svg"
    aria-label="Scout mascot - cinema projector character"
  >
    {/* Projector body - distinctive boxy shape */}
    <rect x="8" y="10" width="16" height="14" rx="2" fill="#1a1a1a" stroke="#D4AF37" strokeWidth="1.5"/>
    
    {/* Projector lens - large and prominent */}
    <circle cx="16" cy="17" r="5" fill="#2a2a2a" stroke="#D4AF37" strokeWidth="1.5"/>
    <circle cx="16" cy="17" r="3.5" fill="#D4AF37" opacity="0.3"/>
    <circle cx="16" cy="17" r="2" fill="#D4AF37"/>
    
    {/* Light beam coming from lens */}
    <path d="M 21 17 L 28 14 L 28 20 Z" fill="#D4AF37" opacity="0.2"/>
    
    {/* Film reels on top - iconic cinema detail */}
    <circle cx="11" cy="8" r="2.5" fill="none" stroke="#D4AF37" strokeWidth="1.5"/>
    <circle cx="11" cy="8" r="1" fill="#D4AF37"/>
    <circle cx="21" cy="8" r="2.5" fill="none" stroke="#D4AF37" strokeWidth="1.5"/>
    <circle cx="21" cy="8" r="1" fill="#D4AF37"/>
    
    {/* Expressive "eyes" - small dots on the body giving personality */}
    <circle cx="12" cy="14" r="1" fill="#D4AF37"/>
    <circle cx="20" cy="14" r="1" fill="#D4AF37"/>
    
    {/* Subtle smile curve */}
    <path d="M 12 20 Q 16 21 20 20" stroke="#D4AF37" strokeWidth="1.2" fill="none" strokeLinecap="round" opacity="0.8"/>
    
    {/* Control knobs - technical detail */}
    <rect x="9" y="22" width="1.5" height="1.5" rx="0.3" fill="#D4AF37"/>
    <rect x="14.5" y="22" width="1.5" height="1.5" rx="0.3" fill="#D4AF37"/>
    <rect x="20" y="22" width="1.5" height="1.5" rx="0.3" fill="#D4AF37"/>
  </svg>
);

export const CHATBOT_GREETING = `Heyyy, I'm ${CHATBOT_NAME}. Your next movie (or show) obsession might be one message away. Tell me what you're in the mood for!`;

export const CONVERSATION_STARTERS = [
  "Find something fun for tonight",
  "Recommend an underrated thriller",
  "Movie night with my friends",
  "I want something emotional",
  "Surprise me!"
];

export const QUICK_REFINEMENTS = [
  "Something shorter (< 2h)",
  "No horror",
  "Try again",
  "Surprise me",
  "Something lighter",
  "Top rated only"
];

