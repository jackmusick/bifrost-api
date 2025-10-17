import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useHealthStore } from '@/stores/healthStore'

interface WorkflowEngineGuardProps {
  children: React.ReactNode
}

/**
 * Guard component that redirects to the workflow engine error page
 * if the engine is unhealthy. Use this to wrap workflow-dependent pages.
 */
export function WorkflowEngineGuard({ children }: WorkflowEngineGuardProps) {
  const navigate = useNavigate()
  const healthStatus = useHealthStore((state) => state.status)

  useEffect(() => {
    // Only redirect if the server is marked as unhealthy
    // This happens when we actually get a 500+ error response
    if (healthStatus === 'unhealthy') {
      navigate('/workflow-engine-error', { replace: true })
    }
  }, [healthStatus, navigate])

  // Show children unless unhealthy
  // The redirect will happen in useEffect if unhealthy
  return <>{children}</>
}
