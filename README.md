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
- Provide `DATABASE_URL` (or the individual `POSTGRES_*` variables) in the backend environment. When using a
	managed connection string that already contains percent escapes such as `%21`, keep them as-is; Alembic now
	preserves those characters automatically.
- Set `CORS_ORIGINS` to include your public frontend host.
- Supply `VITE_API_BASE_URL` when building the frontend image so the SPA points at your hosted backend, e.g.
	`https://server-app.jollybeach-b45b73bd.swedencentral.azurecontainerapps.io`.

## On database schema changes
```PowerShell
# Generates the migration script
./scripts/setup/db.ps1 -Revision "<Message>"

# Applies the migration
./scripts/setup/db.ps1 -Upgrade
```
