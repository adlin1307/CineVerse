import { Link } from 'react-router-dom'
import PosterCard from '../PosterCard/PosterCard'
import './PosterRow.css'

export default function PosterRow({ title, items, viewAllLink, mediaType }) {
  if (!items || items.length === 0) {
    return null
  }
  
  return (
    <div className="poster-row">
      <div className="poster-row-header">
        <h2 className="poster-row-title">{title}</h2>
        {viewAllLink && (
          <Link to={viewAllLink} className="view-all-link">
            View All →
          </Link>
        )}
      </div>
      
      <div className="poster-row-container">
        <div className="poster-row-content">
          {items.map((item) => (
            <div key={item.id} className="poster-row-item">
              <PosterCard item={item} mediaType={mediaType} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
