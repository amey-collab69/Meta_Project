"""
SupportAI-Env — Server Entry Point for OpenEnv
This module provides the main() function required by OpenEnv validation.
"""

def main():
    """
    Main entry point for starting the SupportAI-Env server.
    This function is called by OpenEnv's multi-mode deployment system.
    """
    import uvicorn
    
    print("=" * 60)
    print("🚀 Starting SupportAI-Env Server (OpenEnv Mode)")
    print("=" * 60)
    print("📍 Server: http://0.0.0.0:7860")
    print("📍 API Docs: http://0.0.0.0:7860/docs")
    print("📍 Health Check: http://0.0.0.0:7860/health")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=7860,
        log_level="info"
    )

if __name__ == "__main__":
    main()
