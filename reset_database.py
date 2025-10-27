#!/usr/bin/env python3
"""
Reset database script - drops all tables and recreates them with the new schema.
Use this if you want to start fresh with the updated models.
"""

import os
import sys
from werkzeug.security import generate_password_hash

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, User, Department, Branch, Semester, ClassModel, TeacherClass

def reset_database():
    """Drop all tables and recreate with new schema."""
    app = create_app()
    
    with app.app_context():
        print("🗑️  Dropping all existing tables...")
        db.drop_all()
        
        print("🏗️  Creating new tables with updated schema...")
        db.create_all()
        
        print("✅ Database reset completed!")
        print("Now run: python setup_database.py")

if __name__ == "__main__":
    reset_database()
