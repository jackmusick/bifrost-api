import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
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
  const location = useLocation()
  const healthStatus = useHealthStore((state) => state.status)

  useEffect(() => {
    // Only redirect if the server is marked as unhealthy
    // This happens when we actually get a 500+ error response
    if (healthStatus === 'unhealthy') {
      // Store the current path so we can return to it when the server recovers
      navigate('/workflow-engine-error', {
        replace: true,
        state: { from: location.pathname }
      })
    }
  }, [healthStatus, navigate, location.pathname])

  // Show children unless unhealthy
  // The redirect will happen in useEffect if unhealthy
  return <>{children}</>
}
