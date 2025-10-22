#!/usr/bin/env bash

# Coverage Check Script
# Runs pytest with coverage and generates reports

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
MIN_COVERAGE=80
TEST_PATH="tests/"
SOURCE_PATH="."
REPORT_TYPE="term-missing"
OPEN_HTML=false
VERBOSE=false

# Help message
show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Run pytest with coverage analysis

OPTIONS:
    -h, --help              Show this help message
    -t, --tests PATH        Path to tests (default: tests/)
    -s, --source PATH       Source code path for coverage (default: .)
    -m, --min-coverage NUM  Minimum coverage percentage (default: 80)
    -r, --report TYPE       Report type: term, term-missing, html, json, xml (default: term-missing)
    -o, --open              Open HTML report in browser (implies --report html)
    -v, --verbose           Verbose output
    -u, --unit              Run unit tests only
    -i, --integration       Run integration tests only
    -c, --contract          Run contract tests only

EXAMPLES:
    # Basic coverage check
    $0

    # Check specific module with HTML report
    $0 --source shared/async_executor.py --report html --open

    # Unit tests only with 90% threshold
    $0 --unit --min-coverage 90

    # Integration tests with verbose output
    $0 --integration --verbose

    # Multiple report formats
    $0 --report html --report json --report term-missing
EOF
}

# Parse arguments
REPORT_TYPES=()
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -t|--tests)
            TEST_PATH="$2"
            shift 2
            ;;
        -s|--source)
            SOURCE_PATH="$2"
            shift 2
            ;;
        -m|--min-coverage)
            MIN_COVERAGE="$2"
            shift 2
            ;;
        -r|--report)
            REPORT_TYPES+=("$2")
            shift 2
            ;;
        -o|--open)
            OPEN_HTML=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -u|--unit)
            TEST_PATH="tests/unit/"
            shift
            ;;
        -i|--integration)
            TEST_PATH="tests/integration/"
            shift
            ;;
        -c|--contract)
            TEST_PATH="tests/contract/"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# If --open is specified, ensure HTML report is included
if [ "$OPEN_HTML" = true ]; then
    if [[ ! " ${REPORT_TYPES[@]} " =~ " html " ]]; then
        REPORT_TYPES+=("html")
    fi
fi

# If no report types specified, use default
if [ ${#REPORT_TYPES[@]} -eq 0 ]; then
    REPORT_TYPES=("term-missing")
fi

# Build pytest command
PYTEST_CMD="python -m pytest $TEST_PATH --cov=$SOURCE_PATH"

# Add report types
for report in "${REPORT_TYPES[@]}"; do
    PYTEST_CMD+=" --cov-report=$report"
done

# Add minimum coverage threshold
PYTEST_CMD+=" --cov-fail-under=$MIN_COVERAGE"

# Add verbose flag if requested
if [ "$VERBOSE" = true ]; then
    PYTEST_CMD+=" -v"
fi

# Print what we're doing
echo -e "${YELLOW}Running coverage check...${NC}"
echo -e "Tests: ${GREEN}$TEST_PATH${NC}"
echo -e "Source: ${GREEN}$SOURCE_PATH${NC}"
echo -e "Min coverage: ${GREEN}$MIN_COVERAGE%${NC}"
echo -e "Reports: ${GREEN}${REPORT_TYPES[*]}${NC}"
echo ""

# Run the tests
echo -e "${YELLOW}Command: $PYTEST_CMD${NC}"
echo ""

if eval "$PYTEST_CMD"; then
    echo ""
    echo -e "${GREEN}✓ Coverage check passed!${NC}"

    # Open HTML report if requested
    if [ "$OPEN_HTML" = true ]; then
        echo -e "${YELLOW}Opening HTML coverage report...${NC}"
        if [ -f "htmlcov/index.html" ]; then
            if command -v open &> /dev/null; then
                open htmlcov/index.html
            elif command -v xdg-open &> /dev/null; then
                xdg-open htmlcov/index.html
            else
                echo -e "${YELLOW}Could not open browser. Report available at: htmlcov/index.html${NC}"
            fi
        else
            echo -e "${RED}HTML report not found. Was it generated?${NC}"
        fi
    fi

    exit 0
else
    echo ""
    echo -e "${RED}✗ Coverage check failed!${NC}"
    echo -e "${YELLOW}Review the report above for uncovered code.${NC}"

    # Still open HTML if requested (helpful to see what's missing)
    if [ "$OPEN_HTML" = true ] && [ -f "htmlcov/index.html" ]; then
        echo -e "${YELLOW}Opening HTML coverage report to review gaps...${NC}"
        if command -v open &> /dev/null; then
            open htmlcov/index.html
        elif command -v xdg-open &> /dev/null; then
            xdg-open htmlcov/index.html
        fi
    fi

    exit 1
fi
