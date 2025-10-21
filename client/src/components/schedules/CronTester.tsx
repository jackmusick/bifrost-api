import { useState, useEffect } from 'react'
import { AlertCircle, CheckCircle2, Copy, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { formatDistanceToNow } from 'date-fns'

interface ValidationResult {
  valid: boolean
  humanReadable: string
  nextRuns?: string[]
  intervalSeconds?: number
  warning?: string
  error?: string
}

const EXAMPLE_EXPRESSIONS = [
  { label: 'Every 5 min', expression: '*/5 * * * *' },
  { label: 'Hourly', expression: '0 * * * *' },
  { label: 'Daily 9 AM', expression: '0 9 * * *' },
  { label: 'Weekly Mon', expression: '0 0 * * 1' },
]

export function CronTester() {
  const [expression, setExpression] = useState('')
  const [result, setResult] = useState<ValidationResult | null>(null)
  const [copied, setCopied] = useState(false)

  // Debounced validation
  useEffect(() => {
    if (!expression) {
      setResult(null)
      return
    }

    const timer = setTimeout(() => {
      validateExpression(expression)
    }, 500)

    return () => clearTimeout(timer)
  }, [expression])

  const validateExpression = async (expr: string) => {
    if (!expr.trim()) return

    try {
      const response = await fetch('/api/schedules/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expression: expr }),
      })
      const data = await response.json()
      setResult(data)
    } catch (error) {
      console.error('Failed to validate CRON expression:', error)
      setResult({
        valid: false,
        humanReadable: 'Failed to validate',
        error: 'Unable to connect to validation service'
      })
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(expression)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          placeholder="0 9 * * *"
          value={expression}
          onChange={(e) => setExpression(e.target.value)}
          className="font-mono"
        />
        {expression && (
          <Button
            variant="outline"
            size="icon"
            onClick={handleCopy}
            title="Copy expression"
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
        )}
      </div>

      {result && (
        <div className="space-y-3">
          {result.valid ? (
            <Alert className="bg-green-50 border-green-200 dark:bg-green-950 dark:border-green-800">
              <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
              <AlertDescription className="text-green-800 dark:text-green-200">
                {result.humanReadable}
              </AlertDescription>
            </Alert>
          ) : (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {result.error || result.humanReadable}
              </AlertDescription>
            </Alert>
          )}

          {result.warning && (
            <Alert className="bg-yellow-50 border-yellow-200 dark:bg-yellow-950 dark:border-yellow-800">
              <AlertCircle className="h-4 w-4 text-yellow-600 dark:text-yellow-400" />
              <AlertDescription className="text-yellow-800 dark:text-yellow-200">
                {result.warning}
              </AlertDescription>
            </Alert>
          )}

          {result.nextRuns && result.nextRuns.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold mb-2">Next 5 runs:</h4>
              <div className="space-y-1">
                {result.nextRuns.map((run, i) => {
                  const date = new Date(run)
                  return (
                    <div key={i} className="text-sm flex items-center gap-2">
                      <span className="text-gray-500 dark:text-gray-400">•</span>
                      <span>{date.toLocaleString()}</span>
                      <span className="text-xs text-gray-500">
                        ({formatDistanceToNow(date, { addSuffix: true })})
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      <div>
        <h4 className="text-sm font-semibold mb-2">Quick examples:</h4>
        <div className="flex flex-wrap gap-2">
          {EXAMPLE_EXPRESSIONS.map((ex) => (
            <Button
              key={ex.expression}
              variant="outline"
              size="sm"
              onClick={() => setExpression(ex.expression)}
              className="text-xs"
            >
              {ex.label}
            </Button>
          ))}
        </div>
      </div>
    </div>
  )
}
