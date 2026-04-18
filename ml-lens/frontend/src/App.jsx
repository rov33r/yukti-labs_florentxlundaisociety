import React, { useState } from 'react'
import Header from './components/Header'
import Dashboard from './components/Dashboard'
import Ingestion from './components/Ingestion'
import Sandbox from './components/Sandbox'
import './index.css'

export default function App() {
  const [currentPage, setCurrentPage] = useState('sandbox')

  return (
    <div className="app">
      <Header currentPage={currentPage} onNavigate={setCurrentPage} />
      {currentPage === 'dashboard' && <Dashboard />}
      {currentPage === 'ingestion' && <Ingestion />}
      {currentPage === 'sandbox' && <Sandbox />}
    </div>
  )
}
