import React from 'react'

export default function Card({ title, children, onClick }) {
  return (
    <div className="card" onClick={onClick}>
      {title && <h3 className="card-title">{title}</h3>}
      <div className="card-content">
        {children}
      </div>
    </div>
  )
}
