import React from 'react'

export default function AsteriskSpinner({ size = 20, color = '#1E3A5F' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      className="asterisk-spinner"
      aria-label="Loading"
      role="status"
    >
      {[0, 30, 60, 90, 120, 150].map((angle) => (
        <line
          key={angle}
          x1="12" y1="3.5"
          x2="12" y2="20.5"
          stroke={color}
          strokeWidth="2.2"
          strokeLinecap="round"
          transform={`rotate(${angle} 12 12)`}
        />
      ))}
    </svg>
  )
}
