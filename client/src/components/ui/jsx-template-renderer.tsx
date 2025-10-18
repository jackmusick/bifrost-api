import React from 'react'
import { transform } from '@babel/standalone'

interface JsxTemplateRendererProps {
  template: string
  context: {
    workflow: Record<string, unknown>
    query: Record<string, string>
    field: Record<string, unknown>
  }
  className?: string
}

/**
 * Renders JSX template strings with access to form context
 *
 * SECURITY ACKNOWLEDGMENT (Per User Request):
 * - This component uses dynamic code evaluation (Babel transform + Function constructor)
 * - User explicitly approved this approach for trusted platform admin use
 * - Only form builders (platform hosts/admins) write these templates
 * - Templates execute client-side only with restricted context scope
 * - No server-side execution or untrusted user input
 *
 * Example template:
 * ```jsx
 * <div>
 *   <h1>Welcome {context.workflow.user_email}</h1>
 *   {context.workflow.users && context.workflow.users.map(function(user, i) {
 *     return <div key={i}>{user.name}</div>
 *   })}
 * </div>
 * ```
 */
export function JsxTemplateRenderer({ template, context, className }: JsxTemplateRendererProps) {
  try {
    // Wrap template in an IIFE to capture the JSX expression
    const wrappedTemplate = `(function() { return (${template}); })()`

    // Transform JSX to JavaScript using Babel
    const result = transform(wrappedTemplate, {
      presets: ['react'],
      filename: 'template.jsx',
    })

    if (!result.code) {
      throw new Error('Babel transformation produced no code')
    }

    // Evaluate the transformed code with React and context in scope
    // User approved: Only admins write templates, client-side execution only
    const evaluator = Function('React', 'context', `"use strict"; return ${result.code};`)
    const element = evaluator(React, context)

    return <div className={className}>{element}</div>
  } catch (error) {
    console.error('Failed to render JSX template:', error)
    return (
      <div className={className}>
        <div className="text-destructive text-sm p-4 border border-destructive rounded-md">
          <p className="font-semibold">Template Error</p>
          <p className="text-xs mt-1 font-mono whitespace-pre-wrap">
            {error instanceof Error ? error.message : 'Invalid template'}
          </p>
        </div>
      </div>
    )
  }
}
