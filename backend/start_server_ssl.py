#!/usr/bin/env python3
"""
Production server startup script with SSL/TLS support.
"""
import uvicorn
import ssl
import os

if __name__ == "__main__":
    # SSL Configuration
    ssl_enabled = os.getenv("SSL_ENABLED", "false").lower() == "true"

    if ssl_enabled:
        # Paths to your SSL certificates
        ssl_certfile = os.getenv("SSL_CERTFILE", "certs/server.crt")
        ssl_keyfile = os.getenv("SSL_KEYFILE", "certs/server.key")

        # Verify certificate files exist
        if not os.path.exists(ssl_certfile):
            print(f"SSL certificate file not found: {ssl_certfile}")
            print("Falling back to HTTP...")
            ssl_enabled = False
        elif not os.path.exists(ssl_keyfile):
            print(f"SSL key file not found: {ssl_keyfile}")
            print("Falling back to HTTP...")
            ssl_enabled = False

    if ssl_enabled:
        print(f"Starting HTTPS server on port 8443 with SSL certificate: {ssl_certfile}")
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",  # Listen on all interfaces for production
            port=8443,       # Standard HTTPS port
            ssl_certfile=ssl_certfile,
            ssl_keyfile=ssl_keyfile,
            log_level="info",
            access_log=True
        )
    else:
        print("Starting HTTP server on port 8001 (SSL not enabled)")
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8001,
            reload=True,
            log_level="info"
        )