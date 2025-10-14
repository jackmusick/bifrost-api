#!/bin/bash
# Script to fix integration tests to use async/await

set -e

echo "🔧 Fixing integration tests to use async/await..."

# Find all integration test files
for file in tests/integration/*.py; do
    if [ -f "$file" ] && [ "$file" != "tests/integration/__init__.py" ]; then
        echo "📝 Processing $file..."

        # Make all test methods async
        sed -i '' 's/^    def test_/    async def test_/g' "$file"

        # Add await to common endpoint patterns
        sed -i '' 's/= \([a-zA-Z_]*\)(req)/= await \1(req)/g' "$file"

        echo "✅ Fixed $file"
    fi
done

echo "✅ All integration tests fixed!"
echo "🧪 Run: pytest tests/integration/ -v"
