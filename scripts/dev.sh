#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[DEV]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Development workflow script
case "$1" in
    "setup")
        print_status "Running development setup..."
        ./scripts/setup.sh
        ;;
    
    "run")
        print_status "Starting application..."
        uv run python src/grins_platform/main.py
        ;;
    
    "test")
        print_status "Running tests..."
        uv run pytest tests/ -v --cov=src/grins_platform --cov-report=html
        print_success "Test results available in htmlcov/index.html"
        ;;
    
    "lint")
        print_status "Running code quality checks..."
        echo "🔍 Ruff check..."
        uv run ruff check src/ tests/
        echo "🎨 Ruff format check..."
        uv run ruff format --check src/ tests/
        echo "🔒 Bandit security check..."
        uv run bandit -r src/
        echo "🧹 MyPy type check..."
        uv run mypy src/
        print_success "All checks completed"
        ;;
    
    "fix")
        print_status "Auto-fixing code issues..."
        uv run ruff check src/ tests/ --fix
        uv run ruff format src/ tests/
        print_success "Code formatting applied"
        ;;
    
    "clean")
        print_status "Cleaning up development artifacts..."
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
        find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
        rm -rf htmlcov/ .coverage dist/ build/
        print_success "Cleanup completed"
        ;;
    
    "docker-build")
        print_status "Building Docker image..."
        docker build -t grins-platform:latest .
        print_success "Docker image built successfully"
        ;;
    
    "docker-run")
        print_status "Running application in Docker..."
        docker run --rm -p 8000:8000 grins-platform:latest
        ;;
    
    "docker-dev")
        print_status "Starting development environment with Docker Compose..."
        docker-compose up --build
        ;;
    
    "docker-dev-bg")
        print_status "Starting development environment in background..."
        docker-compose up -d --build
        print_success "Services started in background"
        print_warning "View logs with: docker-compose logs -f"
        print_warning "Stop services with: docker-compose down"
        ;;
    
    "docker-stop")
        print_status "Stopping Docker services..."
        docker-compose down
        print_success "Services stopped"
        ;;
    
    "install")
        print_status "Installing new package: $2"
        if [ -z "$2" ]; then
            print_warning "Usage: ./scripts/dev.sh install <package-name>"
            exit 1
        fi
        uv add "$2"
        print_success "Package $2 installed"
        ;;
    
    "install-dev")
        print_status "Installing development package: $2"
        if [ -z "$2" ]; then
            print_warning "Usage: ./scripts/dev.sh install-dev <package-name>"
            exit 1
        fi
        uv add --dev "$2"
        print_success "Development package $2 installed"
        ;;
    
    "update")
        print_status "Updating all dependencies..."
        uv sync --upgrade
        print_success "Dependencies updated"
        ;;
    
    "shell")
        print_status "Starting development shell..."
        uv run python
        ;;
    
    "docs")
        print_status "Building documentation..."
        if [ ! -d "docs" ]; then
            print_warning "Documentation not set up yet"
            exit 1
        fi
        uv run mkdocs serve
        ;;
    
    *)
        echo "Grins Irrigation Platform - Development Script"
        echo "=============================================="
        echo ""
        echo "Usage: ./scripts/dev.sh <command>"
        echo ""
        echo "Available commands:"
        echo "  setup          - Run initial project setup"
        echo "  run            - Start the application"
        echo "  test           - Run test suite with coverage"
        echo "  lint           - Run all code quality checks"
        echo "  fix            - Auto-fix code formatting issues"
        echo "  clean          - Clean up development artifacts"
        echo ""
        echo "Docker commands:"
        echo "  docker-build   - Build Docker image"
        echo "  docker-run     - Run application in Docker"
        echo "  docker-dev     - Start development environment"
        echo "  docker-dev-bg  - Start development environment in background"
        echo "  docker-stop    - Stop Docker services"
        echo ""
        echo "Package management:"
        echo "  install <pkg>     - Install a new package"
        echo "  install-dev <pkg> - Install a development package"
        echo "  update            - Update all dependencies"
        echo ""
        echo "Other:"
        echo "  shell          - Start Python shell"
        echo "  docs           - Build and serve documentation"
        echo ""
        ;;
esac