"""
Pytest configuration for backend tests.
Sets up Python path so Lambda function imports work correctly.
"""
import sys
import os

# Get the path to the backend/src/functions directory
# This allows imports like "from auth import ..." to work
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
functions_dir = os.path.join(backend_dir, 'src', 'functions')
src_dir = os.path.join(backend_dir, 'src')

# Add to Python path - functions dir first so "from auth import" works
sys.path.insert(0, functions_dir)
sys.path.insert(0, src_dir)
sys.path.insert(0, backend_dir)