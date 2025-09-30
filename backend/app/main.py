"""
Main FastAPI application for the OSINT data collection and analysis platform.
Implements REST API endpoints for social media data collection, threat detection, and analysis.
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
import uuid

from app.core.config import get_settings, setup_logging
from app.core.mongodb import connect_to_mongo, close_mongo_connection, ping_database
from app.core.security import SecurityHeaders, generate_correlation_id, log_security_event
from app.api.v1.api import api_router

# Initialize settings and logging
settings = get_settings()
setup_logging(settings)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.version}")
    
    try:
        # Initialize MongoDB connection
        logger.info("Attempting MongoDB connection...")
        connected = await connect_to_mongo()
        if connected:
            logger.info("✅ MongoDB connected successfully")
        else:
            logger.warning("⚠️  MongoDB connection failed, starting in limited mode")
            # Allow server to start without MongoDB for debugging
        
        # Additional services can be initialized here if needed
        logger.info("All core services initialized successfully")
        
        logger.info("✅ Application startup completed")
        
    except Exception as e:
        logger.error(f"❌ Application startup error: {e}")
        logger.warning("⚠️  Starting server in limited mode for debugging...")
        # Don't raise the exception - allow server to start for debugging
    
    yield
    
    # Shutdown
    logger.info("Application shutdown initiated")
    await close_mongo_connection()
    logger.info("Application shutdown completed")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="OSINT Data Collection and Analysis Platform API",
    version=settings.version,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    lifespan=lifespan,
    openapi_url=f"{settings.api_prefix}/openapi.json"
)

# Security middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])  # Configure for production

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "https://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses"""
    response = await call_next(request)
    
    # Add security headers
    for header, value in SecurityHeaders.get_headers().items():
        response.headers[header] = value
    
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """Log HTTP requests and responses"""
    correlation_id = generate_correlation_id()
    request.state.correlation_id = correlation_id
    
    start_time = time.time()
    client_ip = request.client.host
    
    logger.info(
        f"Request started - {request.method} {request.url.path} "
        f"- IP: {client_ip} - Correlation: {correlation_id}"
    )
    
    try:
        response = await call_next(request)
        
        process_time = time.time() - start_time
        logger.info(
            f"Request completed - {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Time: {process_time:.3f}s "
            f"- Correlation: {correlation_id}"
        )
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed - {request.method} {request.url.path} "
            f"- Error: {str(e)} - Time: {process_time:.3f}s "
            f"- Correlation: {correlation_id}"
        )
        
        # Log security event for errors
        log_security_event(
            event_type="request_error",
            ip_address=client_ip,
            details={
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "correlation_id": correlation_id
            }
        )
        
        raise


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.version
    }


@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check():
    """Detailed health check with dependencies"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.version,
        "checks": {}
    }
    
    # Database health check
    try:
        db_healthy = await ping_database()
        health_status["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "details": "MongoDB connection successful" if db_healthy else "MongoDB connection failed"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "details": f"Database error: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    # Additional service health checks can be added here
    # Currently using MongoDB as primary data store
    
    return health_status


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "docs_url": settings.docs_url,
        "api_prefix": settings.api_prefix,
        "timestamp": time.time()
    }


# Include API routes
app.include_router(api_router, prefix=settings.api_prefix)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )