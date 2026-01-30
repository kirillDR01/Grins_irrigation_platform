# Development Credentials

> ⚠️ **WARNING**: These are development/testing credentials only. Never use these in production!

## Default Admin User

The platform includes a default admin user for development and testing:

| Field | Value |
|-------|-------|
| **Username** | `admin` |
| **Email** | `admin@grins-irrigations.com` |
| **Password** | `admin123` |
| **Role** | Admin (superuser) |

## User Roles

The platform supports three user roles with different permission levels:

| Role | Permissions |
|------|-------------|
| **Admin** | Full access to all features including lien management |
| **Manager** | Access to scheduling, invoicing, and staff management |
| **Tech** | Access to assigned jobs and basic features |

## How Users Are Created

Users are stored in the `staff` table in the PostgreSQL database. The authentication system uses bcrypt for password hashing.

### Database Initialization

The default admin user is created via `scripts/init-db.sql` when the database is first initialized.

### Creating Additional Users

To create additional users for testing:

1. Use the staff management API endpoints
2. Or insert directly into the database with a bcrypt-hashed password

## Production Security Checklist

Before deploying to production:

- [ ] Change the default admin password
- [ ] Remove or disable the default admin account
- [ ] Use strong, unique passwords for all users
- [ ] Enable account lockout after failed login attempts
- [ ] Configure proper CORS origins
- [ ] Use HTTPS only
- [ ] Set secure JWT secret keys in environment variables

## Related Files

- `scripts/init-db.sql` - Database initialization with default user
- `src/grins_platform/services/auth_service.py` - Authentication service
- `src/grins_platform/api/v1/auth.py` - Authentication API endpoints
- `.env` - Environment variables (not committed to git)
