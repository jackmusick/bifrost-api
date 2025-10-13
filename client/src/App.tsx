import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "@/components/layout/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { WorkflowEngineGuard } from "@/components/WorkflowEngineGuard";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Config } from "@/pages/Config";
import { Roles } from "@/pages/Roles";
import { Users } from "@/pages/Users";
import { Organizations } from "@/pages/Organizations";
import { Forms } from "@/pages/Forms";
import { FormBuilder } from "@/pages/FormBuilder";
import { RunForm } from "@/pages/RunForm";
import { Workflows } from "@/pages/Workflows";
import { ExecuteWorkflow } from "@/pages/ExecuteWorkflow";
import { ExecutionHistory } from "@/pages/ExecutionHistory";
import { ExecutionDetails } from "@/pages/ExecutionDetails";
import { WorkflowEngineError } from "@/pages/WorkflowEngineError";
import { Secrets } from "@/pages/Secrets";
import { OAuthConnections } from "@/pages/OAuthConnections";
import { OAuthCallback } from "@/pages/OAuthCallback";
import { Docs } from "@/pages/Docs";
import { Dashboard } from "@/pages/Dashboard";
import { useAuth } from "@/hooks/useAuth";
import { OrgScopeProvider } from "@/contexts/OrgScopeContext";

function Settings() {
    return (
        <div>
            <h1 className="scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl">
                Settings
            </h1>
        </div>
    );
}

function App() {
    return (
        <ErrorBoundary>
            <BrowserRouter>
                <OrgScopeProvider>
                    <Routes>
                        {/* OAuth Callback - Public (no auth, no layout) */}
                        <Route
                            path="oauth/callback/:connectionName"
                            element={<OAuthCallback />}
                        />

                        <Route path="/" element={<Layout />}>
                            {/* Dashboard - PlatformAdmin only (OrgUsers redirected to /forms) */}
                            <Route index element={<Dashboard />} />

                            {/* Workflow Engine Error Page */}
                            <Route
                                path="workflow-engine-error"
                                element={<WorkflowEngineError />}
                            />

                            {/* Workflows - PlatformAdmin only */}
                            <Route
                                path="workflows"
                                element={
                                    <ProtectedRoute requirePlatformAdmin>
                                        <WorkflowEngineGuard>
                                            <Workflows />
                                        </WorkflowEngineGuard>
                                    </ProtectedRoute>
                                }
                            />
                            <Route
                                path="workflows/:workflowName/execute"
                                element={
                                    <ProtectedRoute requirePlatformAdmin>
                                        <WorkflowEngineGuard>
                                            <ExecuteWorkflow />
                                        </WorkflowEngineGuard>
                                    </ProtectedRoute>
                                }
                            />

                            {/* Forms - PlatformAdmin or OrgUser */}
                            <Route
                                path="forms"
                                element={
                                    <ProtectedRoute requireOrgUser>
                                        <WorkflowEngineGuard>
                                            <Forms />
                                        </WorkflowEngineGuard>
                                    </ProtectedRoute>
                                }
                            />
                            <Route
                                path="execute/:formId"
                                element={
                                    <ProtectedRoute requireOrgUser>
                                        <WorkflowEngineGuard>
                                            <RunForm />
                                        </WorkflowEngineGuard>
                                    </ProtectedRoute>
                                }
                            />

                            {/* Form Builder - PlatformAdmin only */}
                            <Route
                                path="forms/new"
                                element={
                                    <ProtectedRoute requirePlatformAdmin>
                                        <WorkflowEngineGuard>
                                            <FormBuilder />
                                        </WorkflowEngineGuard>
                                    </ProtectedRoute>
                                }
                            />
                            <Route
                                path="forms/:formId/edit"
                                element={
                                    <ProtectedRoute requirePlatformAdmin>
                                        <WorkflowEngineGuard>
                                            <FormBuilder />
                                        </WorkflowEngineGuard>
                                    </ProtectedRoute>
                                }
                            />

                            {/* History - PlatformAdmin only */}
                            <Route
                                path="history"
                                element={
                                    <ProtectedRoute requirePlatformAdmin>
                                        <WorkflowEngineGuard>
                                            <ExecutionHistory />
                                        </WorkflowEngineGuard>
                                    </ProtectedRoute>
                                }
                            />
                            <Route
                                path="history/:executionId"
                                element={
                                    <ProtectedRoute requirePlatformAdmin>
                                        <WorkflowEngineGuard>
                                            <ExecutionDetails />
                                        </WorkflowEngineGuard>
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

                            {/* Secrets - PlatformAdmin only */}
                            <Route
                                path="secrets"
                                element={
                                    <ProtectedRoute requirePlatformAdmin>
                                        <Secrets />
                                    </ProtectedRoute>
                                }
                            />

                            {/* OAuth Connections - PlatformAdmin only */}
                            <Route
                                path="oauth"
                                element={
                                    <ProtectedRoute requirePlatformAdmin>
                                        <OAuthConnections />
                                    </ProtectedRoute>
                                }
                            />

                            {/* Docs - PlatformAdmin only */}
                            <Route
                                path="docs/*"
                                element={
                                    <ProtectedRoute requirePlatformAdmin>
                                        <Docs />
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
    );
}

export default App;
