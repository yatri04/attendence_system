#!/bin/bash
# Deployment script for WiFi Attendance Management System

echo "🚀 WiFi Attendance Management System - Deployment Script"
echo "========================================================"

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📁 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit: WiFi Attendance Management System"
else
    echo "✅ Git repository already initialized"
fi

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "❌ requirements.txt not found!"
    exit 1
fi

# Check if Procfile exists
if [ ! -f "Procfile" ]; then
    echo "❌ Procfile not found!"
    exit 1
fi

echo "✅ All deployment files ready!"

echo ""
echo "🌐 Choose your deployment platform:"
echo "1. Heroku (Recommended for students)"
echo "2. Railway"
echo "3. Render"
echo "4. PythonAnywhere"
echo ""
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo "🚀 Deploying to Heroku..."
        echo "1. Install Heroku CLI: https://devcenter.heroku.com/articles/heroku-cli"
        echo "2. Login: heroku login"
        echo "3. Create app: heroku create your-attendance-app"
        echo "4. Set environment variables:"
        echo "   heroku config:set FLASK_ENV=production"
        echo "   heroku config:set SECRET_KEY=your-secret-key-here"
        echo "5. Add database: heroku addons:create heroku-postgresql:hobby-dev"
        echo "6. Deploy: git push heroku main"
        echo "7. Run migrations: heroku run python migrate_database.py"
        ;;
    2)
        echo "🚀 Deploying to Railway..."
        echo "1. Go to https://railway.app"
        echo "2. Connect your GitHub repository"
        echo "3. Set environment variables in Railway dashboard"
        echo "4. Add PostgreSQL service"
        echo "5. Deploy automatically!"
        ;;
    3)
        echo "🚀 Deploying to Render..."
        echo "1. Go to https://render.com"
        echo "2. Connect your GitHub repository"
        echo "3. Create Web Service"
        echo "4. Set environment variables"
        echo "5. Add PostgreSQL database"
        echo "6. Deploy!"
        ;;
    4)
        echo "🚀 Deploying to PythonAnywhere..."
        echo "1. Go to https://pythonanywhere.com"
        echo "2. Create student account with college email"
        echo "3. Create new web app (Flask)"
        echo "4. Upload your code via git"
        echo "5. Configure WSGI file"
        echo "6. Set up database"
        ;;
    *)
        echo "❌ Invalid choice!"
        exit 1
        ;;
esac

echo ""
echo "📋 Post-deployment checklist:"
echo "✅ Application loads successfully"
echo "✅ Database connection works"
echo "✅ All routes accessible"
echo "✅ QR code generation works"
echo "✅ File uploads functional"
echo "✅ Test all user roles (Admin, Teacher, Student, HOD, Principal)"

echo ""
echo "🎉 Your WiFi Attendance Management System is ready for deployment!"
echo "📖 Read DEPLOYMENT_GUIDE.md for detailed instructions"
