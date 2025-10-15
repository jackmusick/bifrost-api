import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWorkflowEngineHealth } from '@/hooks/useWorkflowEngineHealth'

interface WorkflowEngineGuardProps {
  children: React.ReactNode
}

/**
 * Guard component that redirects to the workflow engine error page
 * if the engine is unhealthy. Use this to wrap workflow-dependent pages.
 */
export function WorkflowEngineGuard({ children }: WorkflowEngineGuardProps) {
  const navigate = useNavigate()
  const { data: serverHealth, isLoading } = useWorkflowEngineHealth()

  useEffect(() => {
    // Only redirect if we have data and it's unhealthy
    // Don't redirect while loading to avoid flash
    if (!isLoading && serverHealth?.status === 'unhealthy') {
      navigate('/workflow-engine-error', { replace: true })
    }
  }, [serverHealth, isLoading, navigate])

  // Show children while loading or if healthy
  // The redirect will happen in useEffect if unhealthy
  return <>{children}</>
}
