#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "🚀 Setting up Grins Irrigation Platform"
echo "=============================================="

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_error "pyproject.toml not found. Please run this script from the project root directory."
    exit 1
fi

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    print_error "Python $required_version or higher is required. Found: $python_version"
    exit 1
fi

print_success "Python version check passed: $python_version"

# Install uv if not present
if ! command -v uv &> /dev/null; then
    print_status "Installing uv package manager..."
    
    # Detect OS and install accordingly
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install uv
        else
            curl -LsSf https://astral.sh/uv/install.sh | sh
            source $HOME/.cargo/env
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source $HOME/.cargo/env
    else
        print_warning "Unsupported OS. Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
    
    print_success "uv installed successfully"
else
    print_success "uv is already installed"
fi

# Verify uv installation
if ! command -v uv &> /dev/null; then
    print_error "uv installation failed or not in PATH"
    print_status "Please restart your terminal or run: source ~/.bashrc (or ~/.zshrc)"
    exit 1
fi

# Create virtual environment and install dependencies
print_status "Creating virtual environment and installing dependencies..."
uv sync --all-extras

print_success "Dependencies installed successfully"

# Install pre-commit hooks if available
if [ -f ".pre-commit-config.yaml" ]; then
    print_status "Setting up pre-commit hooks..."
    uv run pre-commit install
    print_success "Pre-commit hooks installed"
fi

# Create necessary directories
print_status "Creating project directories..."
mkdir -p logs
mkdir -p output
mkdir -p data
mkdir -p config

# Set up environment file if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating .env file from template..."
    cat > .env << EOF
# Environment Configuration
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=true

# Database Configuration
DATABASE_URL=postgresql://grins_user:grins_password@localhost:5432/grins_platform

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# External Services
# Add your external service configurations here
EOF
    print_success ".env file created"
else
    print_warning ".env file already exists, skipping creation"
fi

# Run initial tests to verify setup
print_status "Running initial tests to verify setup..."
if uv run python -c "import sys; print(f'Python {sys.version}'); import grins_platform; print('✅ Package import successful')"; then
    print_success "Package import test passed"
else
    print_error "Package import test failed"
    exit 1
fi

# Run Ruff check
print_status "Running code quality checks..."
if uv run ruff check src/ --quiet; then
    print_success "Code quality checks passed"
else
    print_warning "Code quality issues found. Run 'uv run ruff check src/ --fix' to auto-fix"
fi

print_success "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "  1. Review and update the .env file with your configuration"
echo "  2. Run the application: uv run python src/grins_platform/main.py"
echo "  3. Run tests: uv run pytest"
echo "  4. Start development server: uv run uvicorn grins_platform.main:app --reload"
echo ""
echo "For Docker development:"
echo "  1. Build and start services: docker-compose up --build"
echo "  2. Run in background: docker-compose up -d"
echo "  3. View logs: docker-compose logs -f app"
echo ""
echo "Happy coding! 🚀"