# Unified Office Management System

A comprehensive, production-ready backend for managing office operations including floor planning, parking, desk booking, cafeteria, attendance, leave management, IT assets, and project management.

## Features

- **Authentication & Authorization**: JWT-based auth with RBAC
- **User Management**: Multi-role user system with hierarchy
- **Dynamic Floor Planning**: Visual grid-based floor plans with versioning
- **Parking Management**: Employee and visitor parking allocation
- **Desk Booking**: Time-based desk reservations
- **Cafeteria Management**: Table booking and food ordering
- **Attendance Tracking**: Check-in/out with approval workflow
- **Leave Management**: Multi-level leave approval system
- **IT Asset Management**: Hardware tracking and assignment
- **IT Support Requests**: Request lifecycle management
- **Project Management**: Team lead project requests
- **Semantic Search**: AI-powered search for food and IT assets

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with pgvector
- **ORM**: SQLAlchemy 2.0
- **Migrations**: Alembic
- **Authentication**: OAuth2 + JWT
- **Containerization**: Docker + Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Running with Docker

```bash
# Clone the repository
git clone <repository-url>
cd unified-office-management

# Start the application
docker compose up --build

# The API will be available at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Default Super Admin Credentials

- **Email**: super.admin@company.com
- **Password**: Admin@123

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

## API Documentation

Once running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Project Structure

```
/app
 ├── main.py              # Application entry point
 ├── core/                # Core configuration
 │    ├── config.py       # Settings management
 │    ├── database.py     # Database connection
 │    ├── security.py     # JWT and password utilities
 │    └── dependencies.py # FastAPI dependencies
 ├── api/v1/              # API endpoints
 │    ├── router.py       # Main router
 │    └── endpoints/      # Individual endpoint modules
 ├── models/              # SQLAlchemy models
 ├── schemas/             # Pydantic schemas
 ├── services/            # Business logic
 ├── middleware/          # Custom middleware
 ├── utils/               # Utility functions
 └── tests/               # Test suite
```

## Roles & Permissions

| Role | Permissions |
|------|-------------|
| Super Admin | Full system access, manage admins |
| Admin | Manage users, buildings, floor plans |
| Manager | Domain-specific management |
| Team Lead | Team attendance/leave approval, projects |
| Employee | Self-service operations |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | - |
| SECRET_KEY | JWT secret key | - |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token expiry | 1440 |
| COMPANY_DOMAIN | Email domain | company.com |
| EMBEDDING_MODEL | Sentence transformer model | all-MiniLM-L6-v2 |

## Testing

```bash
# Run tests with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test file
pytest app/tests/test_auth.py -v
```

## API Endpoints Overview

### Authentication
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh token
- `POST /api/v1/auth/change-password` - Change password
- `GET /api/v1/auth/me` - Current user info

### Users
- `GET /api/v1/users` - List users
- `POST /api/v1/users` - Create user
- `GET /api/v1/users/{id}` - Get user
- `PUT /api/v1/users/{id}` - Update user
- `DELETE /api/v1/users/{id}` - Delete user

### Buildings & Floor Plans
- `GET/POST /api/v1/buildings` - Building CRUD
- `GET/POST /api/v1/floor-plans` - Floor plan CRUD
- `POST /api/v1/floor-plans/{id}/versions` - Create version
- `POST /api/v1/floor-plans/{id}/clone` - Clone floor plan

### Parking
- `GET/POST /api/v1/parking/allocations` - Parking CRUD
- `POST /api/v1/parking/allocations/{id}/entry` - Record entry
- `POST /api/v1/parking/allocations/{id}/exit` - Record exit
- `GET /api/v1/parking/available/{floor_plan_id}` - Available slots

### Desk Booking
- `GET/POST /api/v1/desks/bookings` - Booking CRUD
- `GET /api/v1/desks/available/{floor_plan_id}` - Available desks

### Cafeteria
- `GET/POST /api/v1/cafeteria/bookings` - Table bookings
- `GET/POST /api/v1/food-orders/items` - Food items
- `GET/POST /api/v1/food-orders/orders` - Food orders

### Attendance
- `POST /api/v1/attendance/check-in` - Check in
- `POST /api/v1/attendance/check-out` - Check out
- `POST /api/v1/attendance/{id}/submit` - Submit for approval
- `POST /api/v1/attendance/{id}/approve` - Approve/reject

### Leave
- `GET/POST /api/v1/leave/requests` - Leave requests
- `POST /api/v1/leave/requests/{id}/approve-level1` - Team lead approval
- `POST /api/v1/leave/requests/{id}/approve-final` - Manager approval
- `GET /api/v1/leave/balance` - Leave balance

### IT Assets & Requests
- `GET/POST /api/v1/it-assets` - Asset CRUD
- `POST /api/v1/it-assets/{id}/assign` - Assign asset
- `GET/POST /api/v1/it-requests` - IT requests
- `POST /api/v1/it-requests/{id}/approve` - Approve request

### Projects
- `GET/POST /api/v1/projects` - Project CRUD
- `POST /api/v1/projects/{id}/submit` - Submit for approval
- `POST /api/v1/projects/{id}/approve` - Approve/reject

### Search
- `POST /api/v1/search` - Semantic search

## License

MIT License