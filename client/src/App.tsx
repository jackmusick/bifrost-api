import { useState, useEffect } from 'react'
import './App.css'

interface HealthStatus {
  status: string;
  service: string;
}

function App() {
  const [apiHealth, setApiHealth] = useState<string>('checking...')
  const [workflowHealth, setWorkflowHealth] = useState<string>('checking...')

  useEffect(() => {
    // Check API health
    fetch('http://localhost:7071/api/health')
      .then(res => res.json())
      .then((data: HealthStatus) => setApiHealth(data.status))
      .catch(() => setApiHealth('error'))

    // Check Workflow health
    fetch('http://localhost:7072/api/health')
      .then(res => res.json())
      .then((data: HealthStatus) => setWorkflowHealth(data.status))
      .catch(() => setWorkflowHealth('error'))
  }, [])

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'healthy': return 'green'
      case 'error': return 'red'
      default: return 'gray'
    }
  }

  return (
    <>
      <h1>MSP Automation Platform</h1>
      <div className="card">
        <h2>Service Status</h2>
        <p style={{ color: getStatusColor(apiHealth) }}>
          Management API: {apiHealth}
        </p>
        <p style={{ color: getStatusColor(workflowHealth) }}>
          Workflow Engine: {workflowHealth}
        </p>
      </div>
      <p className="read-the-docs">
        Open-source automation engine for MSPs.
      </p>
    </>
  )
}

export default App
