# Expose the local Vite dev server via ngrok (default port 3000).
# Prerequisite: backend on :8000 and `npm run dev` in frontend/
param(
    [string]$Domain = "hungrily-throttle-nintendo.ngrok-free.dev",
    [int]$Port = 3000
)

Write-Host "Public URL:  https://$Domain"
Write-Host "Forwarding:  https://$Domain -> http://127.0.0.1:$Port"
Write-Host ""
Write-Host "Before starting, ensure:"
Write-Host "  1. Backend:  cd backend && python manage.py runserver"
Write-Host "  2. Frontend: cd frontend && npm run dev"
Write-Host ""
ngrok http $Port --domain=$Domain