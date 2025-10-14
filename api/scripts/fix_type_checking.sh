#!/bin/bash
# Script to fix common Pylance type checking issues in Azure Functions

set -e

if [ -z "$1" ]; then
    echo "Usage: ./scripts/fix_type_checking.sh <path-to-file.py>"
    echo "Example: ./scripts/fix_type_checking.sh functions/organizations.py"
    exit 1
fi

FILE="$1"

if [ ! -f "$FILE" ]; then
    echo "Error: File not found: $FILE"
    exit 1
fi

echo "🔧 Fixing type checking issues in $FILE"

# Check if file uses @with_request_context
if ! grep -q "@with_request_context" "$FILE"; then
    echo "⚠️  File does not use @with_request_context decorator"
    echo "   This script is for files using @with_request_context"
    exit 1
fi

# Backup original file
cp "$FILE" "$FILE.backup"
echo "📦 Created backup: $FILE.backup"

# Add imports if not present
if ! grep -q "from shared.types import" "$FILE"; then
    echo "➕ Adding type helper imports"
    # Find the line with "from shared.decorators import" and add our import before it
    sed -i '' '/from shared.decorators import/i\
from shared.types import get_context, get_route_param
' "$FILE"
fi

# Replace context = req.context with context = get_context(req)
echo "🔄 Replacing context assignments"
sed -i '' 's/context = req\.context/context = get_context(req)/g' "$FILE"

# Replace common route param patterns
echo "🔄 Replacing route parameter extractions"
sed -i '' 's/\([a-zA-Z_]*\) = req\.route_params\.get("\([a-zA-Z_]*\)")/\1 = get_route_param(req, "\2")/g' "$FILE"

# Verify Python syntax
echo "✅ Verifying Python syntax"
if python3 -m py_compile "$FILE"; then
    echo "✅ Type checking fixes applied successfully!"
    echo "📝 Review changes and test the endpoint"
    echo "🗑️  If everything works, delete backup: rm $FILE.backup"
else
    echo "❌ Syntax error detected! Restoring backup..."
    mv "$FILE.backup" "$FILE"
    echo "🔙 Original file restored"
    exit 1
fi
