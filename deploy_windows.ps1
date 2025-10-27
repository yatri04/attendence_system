# WiFi Attendance Management System - Windows Deployment Script
# This script will help you deploy your app to Heroku

Write-Host "🚀 WiFi Attendance Management System - Deployment Script" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""

# Check if git is installed
Write-Host "📋 Checking prerequisites..." -ForegroundColor Yellow
if (!(Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Git is not installed. Please install Git from https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Git found" -ForegroundColor Green

# Check if Heroku CLI is installed
if (!(Get-Command heroku -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️  Heroku CLI not found. Installing..." -ForegroundColor Yellow
    Write-Host "Please download and install from: https://devcenter.heroku.com/articles/heroku-cli" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "After installing Heroku CLI, restart PowerShell and run this script again." -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Heroku CLI found" -ForegroundColor Green

Write-Host ""
Write-Host "📦 Step 1: Checking Git status..." -ForegroundColor Cyan
Write-Host ""

# Check if git is initialized
if (!(Test-Path ".git")) {
    Write-Host "Initializing Git repository..." -ForegroundColor Yellow
    git init
    git add .
    git commit -m "Initial commit: WiFi Attendance Management System"
} else {
    Write-Host "✅ Git repository initialized" -ForegroundColor Green
}

# Check for uncommitted changes
$status = git status --porcelain
if ($status) {
    Write-Host "📝 Uncommitted changes detected." -ForegroundColor Yellow
    Write-Host "Committing changes..." -ForegroundColor Yellow
    git add .
    git commit -m "Update: Preparing for deployment"
} else {
    Write-Host "✅ No uncommitted changes" -ForegroundColor Green
}

Write-Host ""
Write-Host "🌐 Step 2: Choose your deployment platform" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Heroku (Recommended - Easy to use)" -ForegroundColor White
Write-Host "2. Railway (Modern UI)" -ForegroundColor White
Write-Host "3. Render (Best free tier)" -ForegroundColor White
Write-Host "4. Manual GitHub setup only" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Enter your choice (1-4)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "🚀 Deploying to Heroku..." -ForegroundColor Cyan
        Write-Host ""
        
        # Check if logged in to Heroku
        Write-Host "Checking Heroku login..." -ForegroundColor Yellow
        $herokuLogin = heroku auth:whoami 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "📝 Please login to Heroku..." -ForegroundColor Yellow
            heroku login
        }
        
        Write-Host ""
        $appName = Read-Host "Enter your Heroku app name (must be unique, e.g., wifi-attendance-yourname)"
        
        Write-Host ""
        Write-Host "Creating Heroku app..." -ForegroundColor Yellow
        heroku create $appName
        
        Write-Host ""
        Write-Host "Adding PostgreSQL database..." -ForegroundColor Yellow
        heroku addons:create heroku-postgresql:mini --app $appName
        
        Write-Host ""
        Write-Host "Setting environment variables..." -ForegroundColor Yellow
        $secretKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
        heroku config:set SECRET_KEY=$secretKey --app $appName
        heroku config:set FLASK_ENV=production --app $appName
        
        Write-Host ""
        Write-Host "Pushing code to Heroku (this may take a few minutes)..." -ForegroundColor Yellow
        git push heroku main
        
        Write-Host ""
        Write-Host "Running database migrations..." -ForegroundColor Yellow
        heroku run python migrate_database.py --app $appName
        heroku run python migrate_proxy_lecture.py --app $appName
        
        Write-Host ""
        Write-Host "Creating admin account..." -ForegroundColor Yellow
        heroku run python -c "from app import app, db; from models import User; from werkzeug.security import generate_password_hash; app.app_context().push(); admin = User(name='Administrator', email='admin@attendance.com', password_hash=generate_password_hash('admin123'), role='admin'); db.session.add(admin); db.session.commit(); print('✅ Admin created!')" --app $appName
        
        Write-Host ""
        Write-Host "🎉 Deployment complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Your app is live at: https://$appName.herokuapp.com" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Admin credentials:" -ForegroundColor Yellow
        Write-Host "Email: admin@attendance.com" -ForegroundColor White
        Write-Host "Password: admin123" -ForegroundColor White
        Write-Host ""
        Write-Host "⚠️  IMPORTANT: Change the admin password after first login!" -ForegroundColor Red
        
        # Open the app
        Start-Sleep -Seconds 2
        heroku open --app $appName
        
    }
    "2" {
        Write-Host ""
        Write-Host "🚂 Deploying to Railway..." -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Manual steps:" -ForegroundColor Yellow
        Write-Host "1. Go to https://railway.app" -ForegroundColor White
        Write-Host "2. Sign up with GitHub" -ForegroundColor White
        Write-Host "3. Create new project" -ForegroundColor White
        Write-Host "4. Deploy from GitHub repo" -ForegroundColor White
        Write-Host "5. Select this repository" -ForegroundColor White
        Write-Host "6. Add PostgreSQL service" -ForegroundColor White
        Write-Host "7. Set environment variables:" -ForegroundColor White
        Write-Host "   - SECRET_KEY: your-secret-key" -ForegroundColor White
        Write-Host "   - FLASK_ENV: production" -ForegroundColor White
        Write-Host ""
        Write-Host "For detailed instructions, see: COMPLETE_DEPLOYMENT_STEPS.md" -ForegroundColor Cyan
    }
    "3" {
        Write-Host ""
        Write-Host "🎨 Deploying to Render..." -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Manual steps:" -ForegroundColor Yellow
        Write-Host "1. Go to https://render.com" -ForegroundColor White
        Write-Host "2. Sign up with GitHub" -ForegroundColor White
        Write-Host "3. Create web service" -ForegroundColor White
        Write-Host "4. Connect GitHub repo" -ForegroundColor White
        Write-Host "5. Add PostgreSQL database" -ForegroundColor White
        Write-Host "6. Set environment variables:" -ForegroundColor White
        Write-Host "   - SECRET_KEY: your-secret-key" -ForegroundColor White
        Write-Host "   - FLASK_ENV: production" -ForegroundColor White
        Write-Host ""
        Write-Host "For detailed instructions, see: COMPLETE_DEPLOYMENT_STEPS.md" -ForegroundColor Cyan
    }
    "4" {
        Write-Host ""
        Write-Host "📁 GitHub setup only..." -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Your code is ready to push to GitHub." -ForegroundColor Green
        Write-Host ""
        Write-Host "Run these commands to push to GitHub:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git" -ForegroundColor White
        Write-Host "git push -u origin main" -ForegroundColor White
        Write-Host ""
        Write-Host "Then follow the deployment guide in COMPLETE_DEPLOYMENT_STEPS.md" -ForegroundColor Cyan
    }
    default {
        Write-Host "❌ Invalid choice!" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "📖 For more details, read:" -ForegroundColor Cyan
Write-Host "   - COMPLETE_DEPLOYMENT_STEPS.md (Detailed step-by-step guide)" -ForegroundColor White
Write-Host "   - DEPLOYMENT_GUIDE.md (Platform comparison)" -ForegroundColor White
Write-Host "   - README.md (Project documentation)" -ForegroundColor White
Write-Host ""

