import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Analyze from './pages/Analyze'
import History from './pages/History'
import './index.css'

export default function App() {
  const [page, setPage] = useState('analyze')
  const [history, setHistory] = useState([])

  const addToHistory = (report) =>
    setHistory(prev => [report, ...prev])

  return (
    <div className="layout">
      <Sidebar page={page} setPage={setPage} />
      <main className="main">
        {page === 'analyze'
          ? <Analyze onResult={addToHistory} />
          : <History records={history} />
        }
      </main>
    </div>
  )
}
