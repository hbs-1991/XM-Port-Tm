#!/usr/bin/env python3
"""
Development server startup script with all security fixes
"""
import os
import sys

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    import uvicorn
    
    # Log startup info
    print("🚀 Starting XM-Port API server with security fixes...")
    print("📁 Working directory:", os.getcwd())
    print("🐍 Python path includes:", os.path.join(os.path.dirname(__file__), 'src'))
    print("🔒 Security headers middleware enabled")
    print("🌐 CORS configuration enabled")
    print("=" * 50)
    
    # Start the server
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        reload_dirs=["src"],
        log_level="info"
    )