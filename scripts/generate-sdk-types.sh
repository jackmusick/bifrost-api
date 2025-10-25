#!/bin/bash
# Generate .pyi stub files for bifrost SDK
# This provides type hints for developers who only have /home mounted

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUTPUT_DIR="$PROJECT_ROOT/home/repo/.bifrost-types"

echo "🔧 Generating bifrost SDK type stubs..."

# Remove old stubs
rm -rf "$OUTPUT_DIR"
mkdir -p "$OUTPUT_DIR"

# Generate stubs from bifrost package
stubgen -p bifrost -o "$OUTPUT_DIR" --include-docstrings

echo "✅ Type stubs generated at: $OUTPUT_DIR/bifrost/"
echo ""
echo "Developers can now import bifrost with full type hints:"
echo "  from bifrost import organizations, workflows, files"
