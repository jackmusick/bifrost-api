import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from '@/components/layout/Layout'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { Config } from '@/pages/Config'
import { Roles } from '@/pages/Roles'
import { Users } from '@/pages/Users'
import { Organizations } from '@/pages/Organizations'
import { Forms } from '@/pages/Forms'
import { FormBuilder } from '@/pages/FormBuilder'
import { RunForm } from '@/pages/RunForm'
import { Workflows } from '@/pages/Workflows'
import { ExecuteWorkflow } from '@/pages/ExecuteWorkflow'
import { ExecutionHistory } from '@/pages/ExecutionHistory'
import { ExecutionDetails } from '@/pages/ExecutionDetails'
import { useAuth } from '@/hooks/useAuth'
import { OrgScopeProvider } from '@/contexts/OrgScopeContext'

// Placeholder page components
function Dashboard() {
  const { isPlatformAdmin, isOrgUser } = useAuth()

  // Redirect OrgUsers to /forms (their only accessible page)
  if (isOrgUser && !isPlatformAdmin) {
    return <Navigate to="/forms" replace />
  }

  // PlatformAdmin sees dashboard
  return (
    <div>
      <h1 className="scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl">
        Dashboard
      </h1>
      <p className="leading-7 mt-6">Welcome to the MSP Automation Platform</p>
    </div>
  )
}

function Settings() {
  return (
    <div>
      <h1 className="scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl">
        Settings
      </h1>
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <OrgScopeProvider>
          <Routes>
          <Route path="/" element={<Layout />}>
          {/* Dashboard - PlatformAdmin only (OrgUsers redirected to /forms) */}
          <Route index element={<Dashboard />} />

          {/* Workflows - PlatformAdmin only */}
          <Route
            path="workflows"
            element={
              <ProtectedRoute requirePlatformAdmin>
                <Workflows />
              </ProtectedRoute>
            }
          />
          <Route
            path="workflows/:workflowName/execute"
            element={
              <ProtectedRoute requirePlatformAdmin>
                <ExecuteWorkflow />
              </ProtectedRoute>
            }
          />

          {/* Forms - PlatformAdmin or OrgUser */}
          <Route
            path="forms"
            element={
              <ProtectedRoute requireOrgUser>
                <Forms />
              </ProtectedRoute>
            }
          />
          <Route
            path="execute/:formId"
            element={
              <ProtectedRoute requireOrgUser>
                <RunForm />
              </ProtectedRoute>
            }
          />

          {/* Form Builder - PlatformAdmin only */}
          <Route
            path="forms/new"
            element={
              <ProtectedRoute requirePlatformAdmin>
                <FormBuilder />
              </ProtectedRoute>
            }
          />
          <Route
            path="forms/:formId/edit"
            element={
              <ProtectedRoute requirePlatformAdmin>
                <FormBuilder />
              </ProtectedRoute>
            }
          />

          {/* History - PlatformAdmin only */}
          <Route
            path="history"
            element={
              <ProtectedRoute requirePlatformAdmin>
                <ExecutionHistory />
              </ProtectedRoute>
            }
          />
          <Route
            path="history/:executionId"
            element={
              <ProtectedRoute requirePlatformAdmin>
                <ExecutionDetails />
              </ProtectedRoute>
            }
          />

          {/* Organizations - PlatformAdmin only */}
          <Route
            path="organizations"
            element={
              <ProtectedRoute requirePlatformAdmin>
                <Organizations />
              </ProtectedRoute>
            }
          />

          {/* Users - PlatformAdmin only */}
          <Route
            path="users"
            element={
              <ProtectedRoute requirePlatformAdmin>
                <Users />
              </ProtectedRoute>
            }
          />

          {/* Roles - PlatformAdmin only */}
          <Route
            path="roles"
            element={
              <ProtectedRoute requirePlatformAdmin>
                <Roles />
              </ProtectedRoute>
            }
          />

          {/* Config - PlatformAdmin only */}
          <Route
            path="config"
            element={
              <ProtectedRoute requirePlatformAdmin>
                <Config />
              </ProtectedRoute>
            }
          />

          {/* Settings - PlatformAdmin only */}
          <Route
            path="settings"
            element={
              <ProtectedRoute requirePlatformAdmin>
                <Settings />
              </ProtectedRoute>
            }
          />
          </Route>
        </Routes>
        </OrgScopeProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
