# Coffee Shop API - User Management

## Overview

This is a production-ready FastAPI-based API for managing users in a Coffee Shop application. It implements full user lifecycle: registration, authentication (JWT with access/refresh tokens), email verification, role-based access control (User/Admin), and admin-only user management endpoints. The architecture is asynchronous, scalable, and uses SQLAlchemy ORM with PostgreSQL (or SQLite for dev).

Key features align with the project requirements:
- User registration with unique email check and optional full name.
- JWT-based auth: signup, login, refresh.
- Email verification (code-based, console-printed in dev).
- Roles: User (default) and Admin (extended access).
- Endpoints: `/me`, admin-only `/users` list/detail/update/delete.
- Automatic cleanup: Planned logic for unverified users (described below).
- OpenAPI docs via Swagger UI.

## Architecture

The project follows a modular, layered architecture for extensibility:

- **app/core/**: Shared utilities (config from .env, async database engine/session, JWT security with Argon2 hashing).
- **app/models/**: SQLAlchemy async models (User with roles, verification fields, timestamps).
- **app/schemas/**: Pydantic models for requests/responses (UserCreate, UserOut, Token, etc.).
- **app/crud/**: Data access layer (CRUDUser class for async operations: create, get, authenticate, verify).
- **app/api/v1/endpoints/**: FastAPI routers (auth.py for signup/login/verify/refresh; users.py for profile and admin ops).
- **app/api/deps.py**: Dependency injectors (current_user, admin check, update permissions).
- **app/main.py**: App entrypoint with CORS, lifespan (auto DB tables), and router includes.

Async flow: Request → Depends(get_db) → CRUD async ops → Commit/Refresh → Response.
- Database: PostgreSQL (asyncpg driver) for production; SQLite fallback for dev.
- Security: JWT (HS256), password hashing (Argon2/Bcrypt), role guards.
- Deployment: Dockerized with healthchecks for reliability.

For scalability: Easy to add Celery for background tasks (e.g., cleanup), Redis for token blacklist.

## Quick Start (Local Development)

1. **Clone the repo**:
   ```
   git clone <your-repo-url>
   cd coffee-shop-api
   ```

2. **Setup environment**:
   - Copy example env: `cp .env.example .env`
   - Edit `.env`:
     ```
     DATABASE_URL=sqlite+aiosqlite:///app.db  # Or postgresql+asyncpg://user:pass@localhost/db for Postgres
     SECRET_KEY=your-secret-key  # Generate: openssl rand -hex 32
     ALGORITHM=HS256
     ACCESS_TOKEN_EXPIRE_MINUTES=30
     REFRESH_TOKEN_EXPIRE_DAYS=7
     ```
   - Install dependencies: `pip install -r requirements.txt`

3. **Run the app**:
   ```
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   - Access Swagger docs: http://localhost:8000/docs
   - Health check: http://localhost:8000/health (added for Docker).

## Docker Setup

For containerized deployment (recommended for production):

1. **Build and run**:
   ```
   docker-compose up --build
   ```
   - API: http://localhost:8000/docs
   - DB: PostgreSQL on port 5432 (creds: postgres/1234, db: coffee_shop).

2. **Production notes**:
   - Remove `--reload` in CMD for perf.
   - Use external volumes for DB persistence.
   - Scale with `docker-compose up -d --scale api=3`.

3. **Stop**: `docker-compose down -v` (removes volumes).

## Usage Examples

Use tools like Postman or curl. All endpoints under `/api/v1` (but prefixed in routers).

### 1. Registration
```
POST /auth/signup
Content-Type: application/json
{
  "email": "user@example.com",
  "password": "strongpass123",
  "full_name": "John Doe"  // Optional
}
```
- Response: `{"message": "User registered... Check console for verification code."}`
- Console prints: `🔑 Verification code for user@example.com: 123456`

### 2. Verification
```
POST /auth/verify
Content-Type: application/x-www-form-urlencoded  // Or JSON with model
email=user@example.com&code=123456
```
- Response: `{"message": "User verified successfully"}`

### 3. Login
```
POST /auth/login
{
  "email": "user@example.com",
  "password": "strongpass123"
}
```
- Response: `{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}`
- Note: Only verified users can login (added check in authenticate).

### 4. Refresh Token
```
POST /auth/refresh
Content-Type: application/x-www-form-urlencoded
refresh_token=your_refresh_token
```
- Response: `{"access_token": "...", "token_type": "bearer"}`

### 5. Profile (Authenticated)
```
GET /me
Authorization: Bearer your_access_token
```
- Response: User details (id, email, role, is_verified).

### 6. Admin Endpoints (Admin Token Required)
- `GET /users?skip=0&limit=10`: List users.
- `GET /users/1`: Get user by ID.
- `PATCH /users/1`: Update (self: full_name only; admin: full_name + role).
  ```
  {
    "full_name": "Updated Name",
    "role": "admin"  // Admin only for others
  }
  ```
- `DELETE /users/1`: Delete user.

## Automatic Cleanup Logic

Unverified users are auto-deleted after 2 days (based on `created_at` timestamp).

**Planned Implementation** (described per requirements; not yet coded for simplicity):
- Use Celery + Beat (scheduled tasks) or APScheduler in a background service.
- Daily cron job (e.g., at 00:00 UTC):
  ```sql
  DELETE FROM users
  WHERE is_verified = False AND created_at < NOW() - INTERVAL '2 days';
  ```
- In code: Add `app/core/tasks.py` with Celery task:
  ```python
  from celery import Celery
  from app.crud.user import user_crud
  from datetime import datetime, timedelta

  celery = Celery('tasks', broker='redis://localhost:6379/0')

  @celery.task
  def cleanup_unverified_users(db_url):
      # Connect to DB, execute query, commit
      cutoff = datetime.utcnow() - timedelta(days=2)
      # Use SQLAlchemy to delete where is_verified=False and created_at < cutoff
  ```
- Schedule: Celery Beat config: `{'cleanup': {'task': 'tasks.cleanup_unverified_users', 'schedule': crontab(hour=0, minute=0)}}`.
- Docker: Add Redis service to compose.yml; run Celery worker/beat as separate services.
- TODO: Implement in production; monitor via logs/metrics.

## Simplifications and TODOs

- **Verification**: Code printed to console (dev-only). TODO: Integrate SendGrid/Twilio for real email/SMS (use `aiosmtplib` in requirements; add task in signup).
- **Tests**: Not included. TODO: Add `tests/` with pytest-asyncio (e.g., TestClient for endpoints).
- **Migrations**: Tables auto-created on startup. TODO: Use Alembic for schema changes.
- **Rate Limiting**: None. TODO: Add slowapi for auth endpoints.
- **Logging**: Basic (SQL echo). TODO: Structured logging with structlog.
- Comments: All in English (per requirements).

If more time: Full CI/CD (GitHub Actions), unit/integration tests, email service, token revocation (Redis blacklist).

## Contributing

- Fork, branch, PR.
- Run tests: `pytest` (after adding).
- Lint: `black .` and `ruff check .`.

## License

MIT License - feel free to use/modify.

---

**Repository**: [https://github.com/Bekjan145/coffee_shop_api.git]  
**Author**: [Bekjan]  
**Version**: 1.0.0 (October 2025)

---