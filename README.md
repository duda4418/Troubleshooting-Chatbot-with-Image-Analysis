# Run command

## Initial Setup
```PowerShell
# Initializes the project setup, images, containers
./scripts/setup/run.ps1

# Creates the PostgreSQL database
./scripts/setup/db.ps1 -Init
```

## On code changes
```PowerShell
# Quick rebuild of the images and containers
docker-compose up --build frontend backend
```

## Deploying to Azure Container Apps
- Backend: provide `DATABASE_URL`, `SECRET_KEY`, `OPENAI_API_KEY`, and update `CORS_ORIGINS` with the public frontend URL.
- Frontend: build with the backend host baked in so no code edits are needed later.
	```
	docker build \
	  --build-arg VITE_API_BASE_URL="https://<backend-app>.azurecontainerapps.io" \
	  -t <registry>/frontend-app:latest frontend
	```
- Alternatively, skip the build arg above and set `VITE_API_BASE_URL` as an environment variable in Azure.
- Push both images and roll the Container Apps revisions as usual.

## On database schema changes
```PowerShell
# Generates the migration script
./scripts/setup/db.ps1 -Revision "<Message>"

# Applies the migration
./scripts/setup/db.ps1 -Upgrade
```
