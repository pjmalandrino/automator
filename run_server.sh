#!/bin/bash
# run_server.sh - Start MCP BDD Automation Server with different configurations

# Default configuration
start_default() {
    echo "Starting MCP BDD Automation Server (default configuration)..."
    python -m src.server
}

# Development mode - visible browser
start_dev() {
    echo "Starting in development mode (visible browser)..."
    export HEADLESS=false
    export LOG_LEVEL=DEBUG
    python -m src.server
}

# Production mode - optimized settings
start_prod() {
    echo "Starting in production mode..."
    export HEADLESS=true
    export LOG_LEVEL=INFO
    export BROWSER_TIMEOUT=60000
    python -m src.server
}

# Test mode - with test data
start_test() {
    echo "Starting in test mode..."
    export HEADLESS=true
    export LOG_LEVEL=DEBUG
    export TEST_MODE=true
    python -m src.server
}

# Custom Ollama host
start_custom_ollama() {
    echo "Starting with custom Ollama host..."
    export OLLAMA_HOST="${1:-http://localhost:11434}"
    echo "Using Ollama at: $OLLAMA_HOST"
    python -m src.server
}

# Show usage
usage() {
    echo "Usage: ./run_server.sh [mode]"
    echo ""
    echo "Modes:"
    echo "  default    - Run with default settings"
    echo "  dev        - Development mode (visible browser)"
    echo "  prod       - Production mode (optimized)"
    echo "  test       - Test mode with debug logging"
    echo "  ollama URL - Use custom Ollama endpoint"
    echo ""
    echo "Examples:"
    echo "  ./run_server.sh"
    echo "  ./run_server.sh dev"
    echo "  ./run_server.sh ollama http://192.168.1.100:11434"
}

# Main script logic
case "${1:-default}" in
    default)
        start_default
        ;;
    dev|development)
        start_dev
        ;;
    prod|production)
        start_prod
        ;;
    test)
        start_test
        ;;
    ollama)
        start_custom_ollama "$2"
        ;;
    help|--help|-h)
        usage
        ;;
    *)
        echo "Unknown mode: $1"
        usage
        exit 1
        ;;
esac