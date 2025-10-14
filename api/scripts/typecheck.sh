#!/bin/bash
# Run type checking on Python codebase
# Equivalent to TypeScript's 'tsc --noEmit'

set -e

echo "🔍 Running Python type checks with pyright..."
echo ""

# Run pyright via npx (no global install needed)
npx pyright

echo ""
echo "✅ Type checking complete!"
