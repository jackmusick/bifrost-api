import * as React from "react"
import { X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"

export interface TagsInputProps {
  value: string[]
  onChange: (tags: string[]) => void
  placeholder?: string
  className?: string
  validate?: (tag: string) => boolean
  errorMessage?: string
}

/**
 * TagsInput component for creating tokenized input fields
 * Supports adding tags by pressing Space, Tab, Enter, or comma
 * Validates input based on optional validate function
 */
export function TagsInput({
  value,
  onChange,
  placeholder = "Type and press space...",
  className,
  validate,
  errorMessage = "Invalid input",
}: TagsInputProps) {
  const [inputValue, setInputValue] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const inputRef = React.useRef<HTMLInputElement>(null)

  const addTag = (tag: string) => {
    const trimmed = tag.trim()
    if (!trimmed) return

    // Validate if validator provided
    if (validate && !validate(trimmed)) {
      setError(errorMessage)
      return
    }

    // Check for duplicates
    if (value.includes(trimmed)) {
      setError("Already added")
      return
    }

    setError(null)
    onChange([...value, trimmed])
    setInputValue("")
  }

  const removeTag = (index: number) => {
    onChange(value.filter((_, i) => i !== index))
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Add tag on Space, Tab, Enter, or comma
    if (e.key === " " || e.key === "Tab" || e.key === "Enter" || e.key === ",") {
      e.preventDefault()
      addTag(inputValue)
    }
    // Remove last tag on Backspace if input is empty
    else if (e.key === "Backspace" && inputValue === "" && value.length > 0) {
      onChange(value.slice(0, -1))
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    setInputValue(newValue)
    // Clear error when user types
    if (error) setError(null)
  }

  const handleContainerClick = () => {
    inputRef.current?.focus()
  }

  return (
    <div className="space-y-2">
      <div
        className={cn(
          "flex min-h-10 w-full flex-wrap gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background cursor-text",
          "focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2",
          error && "border-destructive",
          className
        )}
        onClick={handleContainerClick}
      >
        {value.map((tag, index) => (
          <Badge
            key={index}
            variant="secondary"
            className="gap-1 pr-1 font-mono text-xs"
          >
            {tag}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation()
                removeTag(index)
              }}
              className="ml-1 rounded-sm hover:bg-secondary-foreground/20"
            >
              <X className="h-3 w-3" />
            </button>
          </Badge>
        ))}
        <Input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          placeholder={value.length === 0 ? placeholder : ""}
          className="flex-1 border-0 p-0 h-6 min-w-[120px] focus-visible:ring-0 focus-visible:ring-offset-0"
        />
      </div>
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  )
}
