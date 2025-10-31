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

## On database schema changes
```PowerShell
# Generates the migration script
./scripts/setup/db.ps1 -Revision "<Message>"

# Applies the migration
./scripts/setup/db.ps1 -Upgrade
```
