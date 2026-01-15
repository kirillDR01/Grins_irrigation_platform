# Grins Irrigation Platform

A comprehensive business optimization platform for Grins Irrigations, featuring AI-powered development tools, automated workflows, and modern Python development practices.

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** (3.11+ recommended)
- **Docker & Docker Compose** (for containerized development)
- **Git** (for version control)

### Option 1: Local Development with uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/kirillDR01/Grins_irrigation_platform.git
cd Grins_irrigation_platform

# Run the setup script
./scripts/setup.sh

# Start the application
uv run python src/grins_platform/main.py
```

### Option 2: Docker Development

```bash
# Clone the repository
git clone https://github.com/kirillDR01/Grins_irrigation_platform.git
cd Grins_irrigation_platform

# Start the development environment
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

## 🏗️ Project Structure

```
grins-irrigation-platform/
├── src/grins_platform/          # Main application code
│   ├── __init__.py
│   └── main.py                   # Application entry point
├── tests/                        # Test suite
├── scripts/                      # Development and deployment scripts
│   ├── setup.sh                  # Project setup script
│   ├── dev.sh                    # Development workflow script
│   └── init-db.sql              # Database initialization
├── docs/                         # Documentation
├── .kiro/                        # Kiro AI development tools
│   ├── agents/                   # AI agents for development
│   ├── prompts/                  # Custom prompts
│   └── steering/                 # Development guidelines
├── pyproject.toml               # Project configuration and dependencies
├── Dockerfile                   # Container definition
├── docker-compose.yml           # Development environment
├── uv.lock                      # Locked dependencies (auto-generated)
└── README.md                    # This file
```

## 🛠️ Development Workflow

### Using the Development Script

The `./scripts/dev.sh` script provides convenient commands for common development tasks:

```bash
# Setup project
./scripts/dev.sh setup

# Run application
./scripts/dev.sh run

# Run tests with coverage
./scripts/dev.sh test

# Code quality checks
./scripts/dev.sh lint

# Auto-fix code issues
./scripts/dev.sh fix

# Clean up artifacts
./scripts/dev.sh clean

# Docker commands
./scripts/dev.sh docker-dev        # Start development environment
./scripts/dev.sh docker-dev-bg     # Start in background
./scripts/dev.sh docker-stop       # Stop services

# Package management
./scripts/dev.sh install <package>     # Install package
./scripts/dev.sh install-dev <package> # Install dev package
./scripts/dev.sh update                # Update all dependencies
```

### Manual Commands

```bash
# Install dependencies
uv sync

# Run the application
uv run python src/grins_platform/main.py

# Run tests
uv run pytest

# Code formatting and linting
uv run ruff check src/ --fix
uv run ruff format src/

# Type checking
uv run mypy src/

# Security scanning
uv run bandit -r src/
```

## 🐳 Docker Development

This project uses an **optimized Docker setup** following uv best practices for maximum performance:

- ✅ Official uv images (pre-optimized by Astral)
- ✅ Cache mounts (3-10x faster rebuilds)
- ✅ Bytecode compilation (5-15% faster startup)
- ✅ Multi-stage builds (smaller images)
- ✅ Non-root user (security)
- ✅ Database-ready (PostgreSQL/Redis configs included)

### Quick Start

```bash
# Build and run
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

### Development Mode

```bash
# Run with hot reload and debug logging
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Adding Databases

PostgreSQL and Redis configurations are included but commented out. To enable:

1. Open `docker-compose.yml`
2. Uncomment the `postgres` and/or `redis` service blocks
3. Uncomment the corresponding volume definitions
4. Run `docker-compose up`

**For detailed Docker documentation, see [DOCKER.md](DOCKER.md)**

## 📦 Dependencies

### Core Dependencies
- **FastAPI**: Modern web framework for APIs
- **Pydantic**: Data validation and settings management
- **SQLAlchemy**: SQL toolkit and ORM
- **Uvicorn**: ASGI server
- **Ruff**: Fast Python linter and formatter

### Development Dependencies
- **pytest**: Testing framework
- **mypy**: Static type checker
- **pre-commit**: Git hooks for code quality
- **bandit**: Security linter

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/grins_platform --cov-report=html

# Run specific test file
uv run pytest tests/test_main.py

# Run with verbose output
uv run pytest -v
```

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=true

# Database
DATABASE_URL=postgresql://grins_user:grins_password@localhost:5432/grins_platform

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production

# API
API_HOST=0.0.0.0
API_PORT=8000
```

### Database Setup

The database is automatically initialized with:
- User management tables
- Customer management
- Service definitions
- Job/appointment scheduling
- Sample data for development

## 🤖 AI Development Tools

This project includes Kiro AI development tools:

### Available Prompts
- `@devlog-entry`: Create comprehensive development log entries
- `@devlog-summary`: Generate session summaries
- `@devlog-quick`: Quick progress updates
- `@find-prompts`: Search for available prompts
- `@list-prompts`: Browse all prompts
- `@prompt-help`: Get help for specific prompts

### Development Agents
- **devlog-agent**: Specialized for maintaining development logs
- **prompt-manager-agent**: Manages and discovers prompts

### Usage
```bash
# List available prompts
@list-prompts

# Create a development log entry
@devlog-entry "Implemented user authentication system"

# Generate session summary
@devlog-summary
```

## 🚀 Deployment

### Production Docker Build

```bash
# Build production image
docker build -t grins-platform:latest .

# Run production container
docker run -p 8000:8000 grins-platform:latest
```

### Environment-Specific Deployment

1. **Development**: Use `docker-compose.yml`
2. **Staging**: Use `docker-compose.staging.yml` (create as needed)
3. **Production**: Use orchestration tools like Kubernetes or Docker Swarm

## 📊 Code Quality

This project maintains high code quality standards:

- **Ruff**: Fast linting and formatting (800+ rules)
- **MyPy**: Static type checking
- **Bandit**: Security vulnerability scanning
- **Pytest**: Comprehensive test coverage
- **Pre-commit**: Automated quality checks

### Quality Metrics
- Code coverage target: >90%
- Type coverage target: >95%
- Security scan: No high/medium vulnerabilities
- Linting: Zero violations in production code

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run quality checks: `./scripts/dev.sh lint`
5. Run tests: `./scripts/dev.sh test`
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

## 📝 Development Log

See [DEVLOG.md](DEVLOG.md) for detailed development progress and decisions.

## 🔗 Links

- **Repository**: https://github.com/kirillDR01/Grins_irrigation_platform
- **Issues**: https://github.com/kirillDR01/Grins_irrigation_platform/issues
- **Documentation**: [docs/](docs/)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

If you encounter any issues:

1. Check the [troubleshooting guide](docs/troubleshooting.md)
2. Search existing [issues](https://github.com/kirillDR01/Grins_irrigation_platform/issues)
3. Create a new issue with detailed information

## 🎯 Roadmap

- [ ] Web-based dashboard
- [ ] Mobile application
- [ ] Advanced scheduling algorithms
- [ ] Customer portal
- [ ] Integration with accounting software
- [ ] Weather-based irrigation recommendations
- [ ] IoT sensor integration

---

**Built with ❤️ for Grins Irrigations**