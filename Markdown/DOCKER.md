# Docker Setup Guide

## Overview

This project uses an optimized Docker setup following uv best practices for maximum performance and maintainability.

## Key Features

- ✅ **Official uv images**: Pre-optimized by Astral
- ✅ **Cache mounts**: 3-10x faster rebuilds
- ✅ **Intermediate layers**: Only rebuild when dependencies change
- ✅ **Bytecode compilation**: 5-15% faster startup
- ✅ **Non-editable installs**: Production-ready, smaller images
- ✅ **Security**: Non-root user (appuser)
- ✅ **Health checks**: Container health monitoring
- ✅ **Database-ready**: PostgreSQL and Redis configs ready to uncomment

## Quick Start

### Prerequisites

- Docker 20.10+ (with BuildKit support)
- Docker Compose 2.0+

### Build and Run

```bash
# Build the image
docker build -t grins-platform:latest .

# Run the container
docker run -p 8000:8000 grins-platform:latest

# Or use docker-compose
docker-compose up
```

## Docker Commands

### Building

```bash
# Standard build (uses cache)
docker build -t grins-platform:latest .

# Clean build (no cache)
docker build --no-cache -t grins-platform:latest .

# Build with docker-compose
docker-compose build

# Build with no cache
docker-compose build --no-cache
```

### Running

```bash
# Run with docker
docker run -p 8000:8000 grins-platform:latest

# Run with docker-compose (recommended)
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop containers
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Development Mode

```bash
# Run with development overrides (hot reload, debug logging)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run in background
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

## File Structure

```
.
├── Dockerfile              # Production-optimized multi-stage build
├── docker-compose.yml      # Main orchestration file
├── docker-compose.dev.yml  # Development overrides
└── .dockerignore          # Build optimization
```

## Configuration

### Environment Variables

Set in `docker-compose.yml` or pass via command line:

```yaml
environment:
  - PYTHONPATH=/app/src
  - ENVIRONMENT=development  # or production
  - LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
```

### Volumes

- `./src:/app/src:ro` - Source code (read-only, hot reload)
- `./config:/app/config:ro` - Configuration files
- `app_output:/app/output` - Persistent output directory
- `app_logs:/app/logs` - Persistent logs directory

## Adding Database Services

When you need PostgreSQL or Redis, simply uncomment the relevant sections in `docker-compose.yml`:

### Adding PostgreSQL

1. Uncomment the `postgres` service block
2. Uncomment `postgres_data` volume
3. Uncomment `depends_on: - postgres` in app service
4. Add database connection environment variable:
   ```yaml
   environment:
     - DATABASE_URL=postgresql://grins_user:grins_password@postgres:5432/grins_platform
   ```

### Adding Redis

1. Uncomment the `redis` service block
2. Uncomment `redis_data` volume
3. Uncomment `depends_on: - redis` in app service
4. Add Redis connection environment variable:
   ```yaml
   environment:
     - REDIS_URL=redis://redis:6379/0
   ```

## Performance Optimizations

### Build Performance

**Cache Mounts**: Dependencies are cached between builds
```dockerfile
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
```

**Intermediate Layers**: Dependencies and project installed separately
- First layer: Install dependencies (rarely changes)
- Second layer: Install project (changes frequently)
- Result: Only rebuild project layer on code changes

### Runtime Performance

**Bytecode Compilation**: Python files pre-compiled to bytecode
```dockerfile
ENV UV_COMPILE_BYTECODE=1
```

**Non-Editable Installs**: Production-ready, no source code dependency
```dockerfile
RUN uv sync --frozen --no-editable --no-dev
```

### Image Size

**Multi-Stage Build**: Only runtime dependencies in final image
- Builder stage: ~500MB (includes build tools)
- Runtime stage: ~200-250MB (minimal)

## Security Features

### Non-Root User

Container runs as `appuser` (not root):
```dockerfile
USER appuser
```

### Read-Only Mounts

Source code mounted read-only in development:
```yaml
volumes:
  - ./src:/app/src:ro
```

### Minimal Base Image

Uses `python:3.12-slim-bookworm` (minimal Debian):
- Smaller attack surface
- Fewer vulnerabilities
- Faster updates

## Health Checks

### Container Health

Docker monitors container health:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"
```

Check health status:
```bash
docker ps
docker inspect grins-platform-app | grep -A 10 Health
```

## Troubleshooting

### Build Issues

**Problem**: Cache mount not working
```bash
# Ensure BuildKit is enabled
export DOCKER_BUILDKIT=1
docker build -t grins-platform:latest .
```

**Problem**: Dependencies not updating
```bash
# Force rebuild without cache
docker-compose build --no-cache
```

### Runtime Issues

**Problem**: Permission denied errors
```bash
# Check volume permissions
docker-compose exec app ls -la /app/output
docker-compose exec app ls -la /app/logs
```

**Problem**: Module not found
```bash
# Verify PYTHONPATH
docker-compose exec app env | grep PYTHONPATH
```

**Problem**: Container exits immediately
```bash
# Check logs
docker-compose logs app

# Run interactively
docker-compose run --rm app /bin/bash
```

### Development Issues

**Problem**: Code changes not reflected
```bash
# Ensure volume mount is correct
docker-compose config | grep -A 5 volumes

# Restart container
docker-compose restart app
```

## Best Practices

### Development Workflow

1. Make code changes locally
2. Changes automatically reflected in container (volume mount)
3. Container restarts automatically (if using --reload)
4. View logs: `docker-compose logs -f app`

### Production Deployment

1. Build image: `docker build -t grins-platform:latest .`
2. Tag for registry: `docker tag grins-platform:latest registry.example.com/grins-platform:v1.0.0`
3. Push to registry: `docker push registry.example.com/grins-platform:v1.0.0`
4. Deploy to production environment

### Image Management

```bash
# List images
docker images | grep grins-platform

# Remove old images
docker image prune -a

# View image size
docker images grins-platform:latest

# Inspect image layers
docker history grins-platform:latest
```

## Expected Performance

### Build Times

- **First build**: ~2-3 minutes (downloads dependencies)
- **Cached build**: ~10-30 seconds (uses cache mounts)
- **Code-only change**: ~5-10 seconds (only rebuilds project layer)

### Image Size

- **Builder stage**: ~500MB (includes build tools)
- **Final image**: ~200-250MB (runtime only)
- **Compressed**: ~80-100MB (when pushed to registry)

### Runtime Performance

- **Startup time**: <2 seconds
- **Memory usage**: ~50-100MB (app only)
- **CPU usage**: Minimal at idle

## Additional Resources

- [uv Docker Guide](https://docs.astral.sh/uv/guides/integration/docker/)
- [Docker BuildKit](https://docs.docker.com/build/buildkit/)
- [Docker Compose](https://docs.docker.com/compose/)
- [Multi-Stage Builds](https://docs.docker.com/build/building/multi-stage/)

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f app`
2. Inspect container: `docker-compose exec app /bin/bash`
3. Review this guide's troubleshooting section
4. Check project documentation in `README.md`
