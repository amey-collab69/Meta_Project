"""
Quick server starter for SupportAI-Env
Run this file to start the server: python start_server.py
"""
import uvicorn

if __name__ == "__main__":
    print("🚀 Starting SupportAI-Env Server...")
    print("📍 Server will be available at: http://localhost:7860")
    print("📍 API docs at: http://localhost:7860/docs")
    print("⏹️  Press Ctrl+C to stop the server\n")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=7860,
        reload=True,
        log_level="info"
    )
