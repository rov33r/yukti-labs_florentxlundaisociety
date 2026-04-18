import React, { useState } from 'react'
import Header from './components/Header'
import Dashboard from './components/Dashboard'
import SchemaReview from './components/SchemaReview'
import './index.css'

export default function App() {
  const [tab, setTab] = useState('dashboard')

  return (
    <div className="app">
      <Header />
      <nav className="tab-nav">
        <button
          className={`tab-btn ${tab === 'dashboard' ? 'active' : ''}`}
          onClick={() => setTab('dashboard')}
        >
          Dashboard
        </button>
        <button
          className={`tab-btn ${tab === 'schema' ? 'active' : ''}`}
          onClick={() => setTab('schema')}
        >
          Schema Contract
        </button>
      </nav>
      {tab === 'dashboard' ? <Dashboard /> : <SchemaReview />}
    </div>
  )
}
