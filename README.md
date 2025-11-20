# Troubleshooting Chatbot with Image Analysis

A conversational AI system that helps users troubleshoot dishwasher problems using text and image analysis. The assistant identifies issues, suggests solutions from a knowledge base, and can escalate to human support when needed.

## Application Flow

1. User describes a problem or uploads an image
2. AI classifies the issue into a problem category (e.g., spots, residue, cloudy glass)
3. System asks clarifying questions if needed to confirm the problem
4. AI suggests solutions from the knowledge base catalog
5. User tries solutions and provides feedback
6. If unresolved after trying all solutions, user can escalate to support
7. Session closes when problem is resolved or escalated

## Architecture

### Backend
- FastAPI application with PostgreSQL database
- Unified classifier determines user intent and next actions
- Response generator creates user-friendly messages
- Knowledge base stores problem categories, causes, and solutions
- Image analysis using OpenAI Vision models
- Session management and conversation history tracking

### Frontend
- React with TypeScript and Tailwind CSS
- Conversation interface with message history
- Form-based interactions for feedback and escalation
- Dashboard showing past conversations
- Catalogue management page for editing knowledge base

### Database Schema
- Conversation sessions and messages
- Problem categories, causes, and solutions (hierarchical)
- Session problem state tracking
- Suggested solutions and user feedback
- Usage metrics for AI model calls

## Setup

### Initial Setup
```powershell
# Initialize project, images, and containers
./scripts/setup/run.ps1

# Create PostgreSQL database
./scripts/setup/db.ps1 -Init
```

### Load Knowledge Base
Once services are running, import the troubleshooting catalog:
```powershell
# POST to /troubleshooting/import with backend/app/data/troubleshooting_catalog.json
```

### Development
```powershell
# Rebuild on code changes
docker-compose up --build frontend backend
```

### Database Migrations
```powershell
# Generate migration
./scripts/setup/db.ps1 -Revision "Migration message"

# Apply migration
./scripts/setup/db.ps1 -Upgrade
```

## Azure Deployment

### Backend Configuration
Set environment variables in Azure Container App:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Application secret key
- `OPENAI_API_KEY` - OpenAI API key
- `CORS_ORIGINS` - Frontend URL (e.g., https://frontend-app.azurecontainerapps.io)
- CORS add allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

### Frontend Build
```powershell
# Build with backend URL
docker build --build-arg VITE_API_BASE_URL="https://backend-app.azurecontainerapps.io" -t registry/frontend-app:latest frontend

# Push to registry
docker push registry/frontend-app:latest
```

### Backend Build
```powershell
# Build backend
docker build -t registry/backend-app:latest backend

# Push to registry
docker push registry/backend-app:latest
```

Deploy container revisions in Azure Portal or via Azure CLI.
