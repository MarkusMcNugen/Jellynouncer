#!/usr/bin/env python3
"""
Jellynouncer Web Interface API Server

This module provides a comprehensive web interface for managing and monitoring
the Jellynouncer service. It runs on a separate port (1985) from the main webhook
service and provides REST API endpoints for the React frontend.

Architecture:
    - FastAPI backend with async support
    - JWT-based authentication with refresh tokens
    - Separate SQLite database for web-specific data
    - Real-time statistics from the main Jellynouncer database
    - Template management with file system operations
    - Log streaming and filtering capabilities

Security Features:
    - Bcrypt password hashing
    - JWT tokens with expiration
    - CORS configuration for production
    - Rate limiting on authentication endpoints
    - Secure session management

Author: Mark Newton
Project: Jellynouncer Web Interface
Version: 1.0.0
License: MIT
"""

import os
import sys
import json
import secrets
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

# Third-party imports
from fastapi import FastAPI, HTTPException, Depends, Security, status, Request, File, Form, UploadFile, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel, Field, field_validator, ValidationError
import aiosqlite
import jwt
from passlib.context import CryptContext

# Add early debug logging before any imports
print(f"[WEB_API MODULE] Starting web_api.py import (Python {sys.version})", flush=True)

# Import Jellynouncer modules
print("[WEB_API MODULE] Importing config_models...", flush=True)
try:
    from jellynouncer.config_models import ConfigurationValidator
    print("[WEB_API MODULE] config_models imported successfully", flush=True)
except Exception as e:
    print(f"[WEB_API MODULE] ERROR importing config_models: {e}", flush=True)
    import traceback
    traceback.print_exc()
    raise

print("[WEB_API MODULE] Importing utils...", flush=True)
try:
    from jellynouncer.utils import get_web_logger, setup_web_logging
    print("[WEB_API MODULE] utils imported successfully", flush=True)
except Exception as e:
    print(f"[WEB_API MODULE] ERROR importing utils: {e}", flush=True)
    import traceback
    traceback.print_exc()
    raise

print("[WEB_API MODULE] Importing backup_manager...", flush=True)
try:
    from jellynouncer.backup_manager import BackupManager
    print("[WEB_API MODULE] backup_manager imported successfully", flush=True)
except Exception as e:
    print(f"[WEB_API MODULE] ERROR importing backup_manager: {e}", flush=True)
    import traceback
    traceback.print_exc()
    raise

# Log early to catch import issues
print("[WEB_API MODULE] Setting up early logger...", flush=True)
try:
    early_logger = get_web_logger("jellynouncer.web_api.imports")
    early_logger.debug("Starting Jellynouncer module imports...")
    print("[WEB_API MODULE] Early logger setup complete", flush=True)
except Exception as e:
    print(f"[WEB_API MODULE] ERROR setting up early logger: {e}", flush=True)
    import traceback
    traceback.print_exc()
    # Continue anyway
    early_logger = None

try:
    print("[WEB_API MODULE] Attempting to import WebhookService...", flush=True)
    from jellynouncer.webhook_service import WebhookService
    if early_logger:
        early_logger.debug("WebhookService imported successfully")
    print("[WEB_API MODULE] WebhookService imported successfully", flush=True)
except ImportError as e:
    if early_logger:
        early_logger.error(f"Failed to import WebhookService: {e}")
    print(f"[WEB_API MODULE] Failed to import WebhookService (non-fatal): {e}", flush=True)
    WebhookService = None

try:
    print("[WEB_API MODULE] Attempting to import JellyfinAPI...", flush=True)
    from jellynouncer.jellyfin_api import JellyfinAPI
    if early_logger:
        early_logger.debug("JellyfinAPI imported successfully")
    print("[WEB_API MODULE] JellyfinAPI imported successfully", flush=True)
except ImportError as e:
    if early_logger:
        early_logger.error(f"Failed to import JellyfinAPI: {e}")
    print(f"[WEB_API MODULE] Failed to import JellyfinAPI (non-fatal): {e}", flush=True)
    JellyfinAPI = None

try:
    print("[WEB_API MODULE] Attempting to import DatabaseManager...", flush=True)
    from jellynouncer.database_manager import DatabaseManager
    if early_logger:
        early_logger.debug("DatabaseManager imported successfully")
    print("[WEB_API MODULE] DatabaseManager imported successfully", flush=True)
except ImportError as e:
    if early_logger:
        early_logger.error(f"Failed to import DatabaseManager: {e}")
    print(f"[WEB_API MODULE] Failed to import DatabaseManager (non-fatal): {e}", flush=True)
    DatabaseManager = None

print("[WEB_API MODULE] Importing ssl_manager...", flush=True)
try:
    from jellynouncer.ssl_manager import SSLManager, setup_ssl_routes
    print("[WEB_API MODULE] ssl_manager imported successfully", flush=True)
except Exception as e:
    print(f"[WEB_API MODULE] ERROR importing ssl_manager: {e}", flush=True)
    import traceback
    traceback.print_exc()
    raise

print("[WEB_API MODULE] Importing security_middleware...", flush=True)
try:
    from jellynouncer.security_middleware import setup_security_middleware
    print("[WEB_API MODULE] security_middleware imported successfully", flush=True)
except Exception as e:
    print(f"[WEB_API MODULE] ERROR importing security_middleware: {e}", flush=True)
    import traceback
    traceback.print_exc()
    raise

print("[WEB_API MODULE] Importing web_database...", flush=True)
try:
    from jellynouncer.web_database import WebDatabaseManager
    print("[WEB_API MODULE] web_database imported successfully", flush=True)
except Exception as e:
    print(f"[WEB_API MODULE] ERROR importing web_database: {e}", flush=True)
    import traceback
    traceback.print_exc()
    raise

if early_logger:
    early_logger.debug("All imports completed")
print("[WEB_API MODULE] All module imports completed successfully", flush=True)

# Constants
WEB_DB_PATH = "data/web_interface.db"
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# Determine log directory - use relative path for flexibility
# Works both in Docker (/app/logs) and outside (./logs)
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
if not os.path.exists(LOG_DIR):
    # Fallback to current directory logs if parent doesn't exist
    LOG_DIR = "logs"

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token handler - auto_error=False to allow optional authentication
security = HTTPBearer(auto_error=False)

# Logger setup with extensive debug logging - uses separate web log file
logger = get_web_logger("jellynouncer.web_api")


# ==================== Pydantic Models ====================

class UserCreate(BaseModel):
    """Model for user creation request"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    email: Optional[str] = None
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must be alphanumeric with optional _ or -')
        return v


class UserLogin(BaseModel):
    """Model for user login request"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Model for JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class QueueStats(BaseModel):
    """Model for queue statistics"""
    pending: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    processing_rate: float = 0


class SystemHealth(BaseModel):
    """Model for system health information"""
    webhook_service: str = "stopped"
    database: str = "disconnected"
    last_sync: Optional[str] = None
    database_size_mb: float = 0
    uptime_hours: float = 0
    uptime_percentage: float = 100
    cpu_usage: float = 0
    memory_usage: float = 0
    disk_usage: float = 0


class DiscordWebhookStatus(BaseModel):
    """Model for Discord webhook status"""
    configured: bool = False
    last_used: Optional[str] = None
    messages_sent: int = 0


class RecentNotification(BaseModel):
    """Model for recent notification entry"""
    id: Optional[str] = None
    name: str = "Unknown"
    type: Optional[str] = None
    event: Optional[str] = None
    timestamp: Optional[str] = None


class SyncedItems(BaseModel):
    """Model for synced items information"""
    total: int = 0
    by_type: Dict[str, int] = {}
    database_size_mb: float = 0
    last_sync_time: Optional[str] = None
    sync_type: Optional[str] = None
    recent_additions: int = 0
    # Sync progress fields
    is_syncing: bool = False
    sync_progress: float = 0  # 0-100 percentage
    items_processed: int = 0
    items_total: int = 0
    items_per_second: float = 0
    eta_seconds: Optional[int] = None
    sync_started_at: Optional[str] = None


class HistoricalStats(BaseModel):
    """Model for historical statistics"""
    hourly: List[Dict[str, Any]] = []
    totals: Dict[str, Any] = {}
    period_hours: int = 24


class OverviewStats(BaseModel):
    """Model for overview statistics response"""
    total_items: int = 0
    items_today: int = 0
    items_week: int = 0
    discord_webhooks: Dict[str, DiscordWebhookStatus] = {}
    recent_notifications: List[RecentNotification] = []
    queue_stats: QueueStats = QueueStats()
    system_health: SystemHealth = SystemHealth()
    jellyfin_stats: Optional[Dict[str, Any]] = None
    historical_stats: Optional[HistoricalStats] = None
    synced_items: Optional[SyncedItems] = None  # Added missing field for database sync stats


class ConfigUpdate(BaseModel):
    """Model for configuration updates"""
    section: str
    key: str
    value: Any
    
    
class TemplateUpdate(BaseModel):
    """Model for template updates"""
    name: str
    content: str
    

class LogQuery(BaseModel):
    """Model for log query parameters"""
    file: str = "jellynouncer.log"
    lines: int = Field(100, le=1000)
    level: Optional[str] = None
    component: Optional[str] = None
    search: Optional[str] = None


class ClientLogEntry(BaseModel):
    """Model for individual client log entry"""
    timestamp: str
    level: str
    sessionId: str
    url: str
    message: str
    metadata: Optional[Dict[str, Any]] = {}
    userAgent: Optional[str] = None


class ClientLogBatch(BaseModel):
    """Model for batch of client logs"""
    logs: List[ClientLogEntry]
    sessionId: str
    timestamp: str


# ==================== Authentication ====================
# The database manager is now imported from web_database.py
# This provides a shared module for both web_api and webhook_api

# NOTE: The LocalWebDatabaseManager class has been removed.
# All functionality is now in the shared WebDatabaseManager from web_database.py

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    logger.debug(f"Creating access token for data: {data}")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    logger.debug(f"Access token will expire at: {expire.isoformat()}")
    to_encode.update({"exp": expire.timestamp(), "type": "access"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    logger.debug(f"Access token created, length: {len(encoded_jwt)} chars")
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """Create a JWT refresh token"""
    logger.debug(f"Creating refresh token for data: {data}")
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    logger.debug(f"Refresh token will expire at: {expire.isoformat()}")
    to_encode.update({"exp": expire.timestamp(), "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    logger.debug(f"Refresh token created, length: {len(encoded_jwt)} chars")
    return encoded_jwt


async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> Optional[Dict[str, Any]]:
    """Validate JWT token if provided, return user or None"""
    if not credentials:
        logger.debug("No credentials provided in request")
        return None
        
    token = credentials.credentials
    logger.debug(f"Validating JWT token (length: {len(token)} chars)")
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        token_type = payload.get("type")
        if token_type != "access":
            logger.debug(f"Invalid token type: {token_type}, expected 'access'")
            return None
        
        user_id = payload.get("user_id")
        username = payload.get("username")
        logger.debug(f"Token validated successfully for user {username} (ID: {user_id})")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating JWT: {str(e)}", exc_info=True)
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, Any]:
    """Validate JWT token and return user, raises exception if not authenticated"""
    if not credentials:
        logger.debug("No credentials provided, authentication required")
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    token = credentials.credentials
    logger.debug(f"Validating required JWT token (length: {len(token)} chars)")
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        
        token_type = payload.get("type")
        if token_type != "access":
            logger.debug(f"Invalid token type: {token_type}, expected 'access'")
            raise HTTPException(
                status_code=401,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = payload.get("user_id")
        username = payload.get("username")
        logger.debug(f"Token validated successfully for user {username} (ID: {user_id})")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token has expired")
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Unexpected error validating JWT: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Authentication error",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def check_auth_required(user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)) -> Optional[Dict[str, Any]]:
    """Check if authentication is required and validate user"""
    logger.info(f"[AUTH_CHECK] Starting auth check - user provided: {user is not None}")
    
    try:
        # Check if web_service is initialized
        if not web_service:
            logger.error("[AUTH_CHECK] web_service is None!")
            return None
            
        if not web_service.web_db:
            logger.error("[AUTH_CHECK] web_service.web_db is None!")
            return None
        
        logger.debug("[AUTH_CHECK] Getting security settings from database...")
        settings = await web_service.web_db.get_security_settings()
        
        logger.info(f"[AUTH_CHECK] Security settings retrieved: {settings}")
        
        auth_enabled = settings.get("auth_enabled", False)
        logger.info(f"[AUTH_CHECK] Auth enabled: {auth_enabled}, User present: {user is not None}")
        
        if auth_enabled:
            if not user:
                logger.warning("[AUTH_CHECK] Authentication required but no valid user token provided")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            logger.info(f"[AUTH_CHECK] Auth required and user authenticated: {user.get('username', 'unknown')}")
            return user
        
        # Auth not required, return None or user if provided
        logger.info(f"[AUTH_CHECK] Auth not required, allowing access. User: {user is not None}")
        return user
    except HTTPException as he:
        logger.error(f"[AUTH_CHECK] HTTPException raised: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        logger.error(f"[AUTH_CHECK] Unexpected error in auth check: {type(e).__name__}: {e}", exc_info=True)
        # On error, default to no auth required - return None to allow access
        logger.warning("[AUTH_CHECK] Auth check failed with error, defaulting to no auth required")
        return None


async def check_webhook_key_auth(user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)) -> Optional[Dict[str, Any]]:
    """
    Special auth check for webhook API key management.
    Allows access if:
    1. User is authenticated (normal flow)
    2. No admin users exist yet (setup flow)
    3. Auth is disabled (no auth required)
    """
    logger.info(f"[WEBHOOK_KEY_AUTH] Starting webhook key auth check - user provided: {user is not None}")
    
    try:
        # Check if web_service is initialized
        if not web_service or not web_service.web_db:
            logger.error("[WEBHOOK_KEY_AUTH] web_service or web_db is None!")
            return None
        
        # Get security settings
        settings = await web_service.web_db.get_security_settings()
        auth_enabled = settings.get("auth_enabled", False)
        
        # If auth is disabled, allow access
        if not auth_enabled:
            logger.info("[WEBHOOK_KEY_AUTH] Auth disabled, allowing access")
            return user  # Return user if provided, None otherwise
        
        # Check if any admin accounts exist
        has_admin = False
        try:
            async with aiosqlite.connect(WEB_DB_PATH) as db:
                cursor = await db.execute("SELECT COUNT(*) FROM users WHERE id = 1")
                count = await cursor.fetchone()
                has_admin = count and count[0] > 0
        except Exception as e:
            logger.error(f"[WEBHOOK_KEY_AUTH] Error checking for admin user: {e}")
            has_admin = False
        
        # If no admin exists, allow access for initial setup
        if not has_admin:
            logger.info("[WEBHOOK_KEY_AUTH] No admin user exists, allowing access for setup")
            return None  # Return None to indicate anonymous/setup access
        
        # Admin exists and auth is enabled, require authentication
        if not user:
            logger.warning("[WEBHOOK_KEY_AUTH] Authentication required but no valid user token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info(f"[WEBHOOK_KEY_AUTH] User authenticated: {user.get('username', 'unknown')}")
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[WEBHOOK_KEY_AUTH] Unexpected error: {type(e).__name__}: {e}", exc_info=True)
        # On error, deny access for security (fail closed, not open)
        # Only exception: if no database exists at all, allow initial setup
        import os
        if not os.path.exists(WEB_DB_PATH):
            logger.warning("[WEBHOOK_KEY_AUTH] No database exists, allowing initial setup access")
            return None
        
        # Database exists but error occurred - deny access for security
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service temporarily unavailable"
        )


# ==================== Service Manager ====================

class WebInterfaceService:
    """Main service class for web interface operations"""
    
    def __init__(self, webhook_service: Optional[WebhookService] = None):
        self.webhook_service = webhook_service
        self.config = None
        self.jellyfin = None  # Own Jellyfin client for web interface
        self.db = None  # Own database connection for web interface
        self.web_db = WebDatabaseManager()
        self.ssl_manager = SSLManager(WEB_DB_PATH)
        self.backup_manager = None  # Will be initialized after config is loaded
        self.logger = get_web_logger("jellynouncer.web_interface")
        self.logger.debug("Initializing WebInterfaceService")
        
        if webhook_service:
            self.logger.debug("WebhookService provided - will have access to main database")
        else:
            self.logger.debug("No WebhookService - running in standalone mode")
        
    async def initialize(self):
        """Initialize the web interface service"""
        self.logger.debug("Starting web interface service initialization")
        
        # Initialize database
        self.logger.debug("Initializing web database...")
        await self.web_db.initialize()
        self.logger.debug("Web database initialized successfully")
        
        # Initialize SSL manager
        self.logger.debug("Initializing SSL manager...")
        await self.ssl_manager.initialize()
        self.logger.debug("SSL manager initialized successfully")
        
        # Load configuration
        self.logger.debug("Loading configuration...")
        try:
            config_validator = ConfigurationValidator()
            self.config = config_validator.load_and_validate_config()
            self.logger.debug(f"Configuration loaded successfully from {config_validator.config_path if hasattr(config_validator, 'config_path') else 'default path'}")
            
            # Initialize SSL manager with config
            self.logger.debug("Initializing SSL manager with config...")
            ssl_config_obj = self.config.ssl if hasattr(self.config, 'ssl') else None
            self.ssl_manager = SSLManager(ssl_config=ssl_config_obj, db_path=WEB_DB_PATH)
            await self.ssl_manager.initialize()
            self.logger.debug("SSL manager initialized successfully")
            
            # Initialize backup manager with config
            self.logger.debug("Initializing backup manager...")
            backup_config = self.config.backup.model_dump() if hasattr(self.config, 'backup') else {}
            self.backup_manager = BackupManager(backup_config)
            # BackupManager is initialized in __init__, start scheduler instead
            await self.backup_manager.start_scheduler()
            self.logger.debug("Backup manager initialized and scheduler started")
            
            # Initialize Jellyfin API client
            self.logger.debug("Initializing Jellyfin API client...")
            try:
                # Log the config we're using
                self.logger.debug(f"Jellyfin config - Server URL: {self.config.jellyfin.server_url if self.config.jellyfin else 'None'}")
                self.logger.debug(f"Jellyfin config - Has API Key: {bool(self.config.jellyfin.api_key) if self.config.jellyfin else False}")
                self.logger.debug(f"Jellyfin config - User ID: {self.config.jellyfin.user_id if self.config.jellyfin else 'None'}")
                
                self.jellyfin = JellyfinAPI(self.config.jellyfin)
                if await self.jellyfin.connect():
                    self.logger.info("Connected to Jellyfin API successfully")
                    # Try to get initial stats
                    try:
                        stats = await self.jellyfin.get_server_stats()
                        self.logger.info(f"Initial Jellyfin stats retrieved: {stats.get('server_name', 'Unknown')} v{stats.get('server_version', 'Unknown')}")
                    except Exception as stats_e:
                        self.logger.warning(f"Could not retrieve initial stats: {stats_e}")
                else:
                    self.logger.warning("Failed to connect to Jellyfin API - stats will be limited")
                    self.jellyfin = None
            except Exception as e:
                self.logger.error(f"Jellyfin API initialization failed: {e}", exc_info=True)
                self.jellyfin = None
            
            # Initialize main database connection
            self.logger.debug("Initializing main database connection...")
            if self.config and self.config.database:
                import os
                db_path = self.config.database.path
                self.logger.debug(f"Database config: path={db_path}")
                self.logger.debug(f"Database file exists: {os.path.exists(db_path)}")
                self.logger.debug(f"Database file absolute path: {os.path.abspath(db_path)}")
                self.logger.debug(f"Current working directory: {os.getcwd()}")
            else:
                self.logger.debug(f"Database config: None")
            try:
                if not self.config.database:
                    self.logger.warning("No database configuration found - running without database")
                    self.db = None
                else:
                    self.logger.debug(f"Creating DatabaseManager with path: {self.config.database.path}")
                    if DatabaseManager is None:
                        self.logger.error("DatabaseManager class is None - import failed")
                        self.db = None
                    else:
                        self.db = DatabaseManager(self.config.database)
                        self.logger.debug("DatabaseManager created, calling initialize()...")
                        await self.db.initialize()
                        self.logger.info(f"Connected to main database successfully at {self.config.database.path}")
                        
                        # Test the connection
                        test_stats = await self.db.get_stats()
                        self.logger.debug(f"Database test query successful - total items: {test_stats.get('total_items', 0)}")
            except ImportError as e:
                self.logger.error(f"Failed to import DatabaseManager: {e}")
                self.db = None
            except FileNotFoundError as e:
                self.logger.error(f"Database file not found: {e}")
                self.db = None
            except Exception as e:
                self.logger.error(f"Main database initialization failed: {e}", exc_info=True)
                self.logger.debug(f"Exception type: {type(e).__name__}")
                self.logger.debug(f"Exception args: {e.args}")
                self.db = None
                
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}", exc_info=True)
            raise
        
        # Start periodic stats refresh task
        asyncio.create_task(self._periodic_stats_refresh())
        self.logger.info("Started periodic Jellyfin stats refresh task")
    
    async def _periodic_stats_refresh(self):
        """Periodically refresh Jellyfin stats"""
        # Do initial refresh immediately on startup
        try:
            self.logger.info("Performing initial Jellyfin stats collection...")
            await self.refresh_jellyfin_stats()
            self.logger.info("Initial Jellyfin stats collection complete")
        except Exception as e:
            self.logger.error(f"Initial stats refresh failed: {e}")
        
        # Then refresh periodically
        while True:
            try:
                # Wait 30 minutes between refreshes
                await asyncio.sleep(1800)
                
                # Refresh stats
                self.logger.debug("Refreshing Jellyfin stats...")
                await self.refresh_jellyfin_stats()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in periodic stats refresh: {e}")
                # Wait 5 minutes before retry on error
                await asyncio.sleep(300)
    
    async def refresh_jellyfin_stats(self) -> Dict[str, Any]:
        """
        Refresh Jellyfin server statistics and store in database.
        
        Returns:
            Latest statistics dictionary
        """
        try:
            # Use web interface's own Jellyfin client first
            if self.jellyfin:
                self.logger.debug("Fetching stats from Jellyfin server using web interface client...")
                stats = await self.jellyfin.get_server_stats()
                self.logger.debug(f"Retrieved Jellyfin stats: {len(stats)} fields")
                
                # Save to database
                if self.db:
                    self.logger.debug("Saving stats to database...")
                    await self.db.save_jellyfin_stats(stats)
                    self.logger.info(f"Jellyfin stats saved to database successfully")
                elif self.webhook_service and self.webhook_service.db:
                    self.logger.debug("Saving stats to webhook service database...")
                    await self.webhook_service.db.save_jellyfin_stats(stats)
                else:
                    self.logger.warning("Database not available to save Jellyfin stats")
                
                return stats
            # Fall back to webhook service if available
            elif self.webhook_service and self.webhook_service.jellyfin:
                self.logger.debug("Fetching stats from Jellyfin server via webhook service...")
                stats = await self.webhook_service.jellyfin.get_server_stats()
                self.logger.debug(f"Retrieved Jellyfin stats: {len(stats)} fields")
                
                # Save to database
                if self.webhook_service.db:
                    self.logger.debug("Saving stats to database...")
                    await self.webhook_service.db.save_jellyfin_stats(stats)
                    self.logger.info(f"Jellyfin stats saved to database successfully")
                
                return stats
            else:
                self.logger.warning(f"Cannot fetch Jellyfin stats - jellyfin: {self.jellyfin is not None}, webhook_service: {self.webhook_service is not None}")
                # Try to get from database
                if self.db:
                    self.logger.debug("Fetching cached stats from database...")
                    return await self.db.get_latest_jellyfin_stats()
                elif self.webhook_service and self.webhook_service.db:
                    self.logger.debug("Fetching cached stats from webhook service database...")
                    return await self.webhook_service.db.get_latest_jellyfin_stats()
                
            return {}
        except Exception as e:
            self.logger.error(f"Failed to refresh Jellyfin stats: {e}", exc_info=True)
            return {}
    
    async def get_overview_stats(self) -> OverviewStats:
        """Get statistics for the overview page"""
        import psutil
        from datetime import datetime, timezone
        
        self.logger.debug("Starting get_overview_stats...")
        
        stats = {
            "total_items": 0,
            "items_today": 0,
            "items_week": 0,
            "discord_webhooks": {},
            "recent_notifications": [],
            "queue_stats": {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0,
                "processing_rate": 0
            },
            "system_health": {
                "webhook_service": "running" if self.webhook_service else "stopped",
                "jellyfin_connection": "connected" if self.jellyfin else "disconnected",
                "database": "connected",
                "last_sync": None,
                "database_size_mb": 0,
                "uptime_hours": 0,
                "uptime_percentage": 100,
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0
            },
            "jellyfin_stats": None,  # Will be populated from database
            "synced_items": SyncedItems(),  # Initialize with default SyncedItems model
            "webhook_stats": {
                "received": 0,
                "processed": 0,
                "failed": 0,
                "processing_rate": 0.0
            },
            "notification_stats": {
                "sent": 0,
                "failed": 0,
                "queued": 0,
                "success_rate": 0.0
            },
            "filtering_stats": {
                "renames_filtered": 0,
                "deletes_filtered": 0,
                "mass_renames_caught": 0,
                "metadata_only": 0
            },
            "channel_routing": {
                "default": 0,
                "movies": 0,
                "tv": 0,
                "music": 0
            },
            "historical_stats": {
                "hourly": [],
                "totals": {},
                "period_hours": 24
            }
        }
        
        # System metrics
        try:
            # CPU and Memory
            stats["system_health"]["cpu_usage"] = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            stats["system_health"]["memory_usage"] = memory.percent
            
            # Disk usage for data directory
            data_dir = Path("data")
            if data_dir.exists():
                disk = psutil.disk_usage(str(data_dir))
                stats["system_health"]["disk_usage"] = disk.percent
                
                # Database size
                db_path = data_dir / "jellynouncer.db"
                if db_path.exists():
                    stats["system_health"]["database_size_mb"] = round(db_path.stat().st_size / (1024 * 1024), 2)
            
            # Uptime (simplified - would need proper tracking)
            stats["system_health"]["uptime_hours"] = 24  # Placeholder
            stats["system_health"]["uptime_percentage"] = 99.9  # Placeholder
            
        except Exception as e:
            self.logger.warning(f"Could not get system metrics: {e}")
        
        # Get Jellyfin stats from database
        try:
            self.logger.debug(f"Attempting to get Jellyfin stats - db: {self.db is not None}, webhook_service.db: {self.webhook_service.db if self.webhook_service else None}")
            jellyfin_stats = None
            if self.db:
                self.logger.debug("Getting stats from main database...")
                jellyfin_stats = await self.db.get_latest_jellyfin_stats()
            elif self.webhook_service and self.webhook_service.db:
                self.logger.debug("Getting stats from webhook service database...")
                jellyfin_stats = await self.webhook_service.db.get_latest_jellyfin_stats()
            
            self.logger.debug(f"Retrieved jellyfin_stats: {bool(jellyfin_stats)}")
            
            if jellyfin_stats:
                # Check if stats are stale (older than 1 hour)
                if 'last_check' in jellyfin_stats:
                    last_check = datetime.fromisoformat(jellyfin_stats['last_check'])
                    if (datetime.now(timezone.utc) - last_check).total_seconds() > 3600:
                        self.logger.debug("Stats are stale, triggering refresh...")
                        # Refresh stats in background
                        asyncio.create_task(self.refresh_jellyfin_stats())
                
                stats["jellyfin_stats"] = jellyfin_stats
            else:
                self.logger.debug("No stats in database, triggering refresh and providing defaults...")
                # No stats in database, trigger refresh and provide defaults
                asyncio.create_task(self.refresh_jellyfin_stats())
                # Provide default structure for Jellyfin stats
                stats["jellyfin_stats"] = {
                    "server_name": "Unknown",
                    "server_version": "Unknown",
                    "server_id": None,
                    "server_status": "unknown",
                    "total_users": 0,
                    "active_users": 0,
                    "total_items": 0,
                    "movie_count": 0,
                    "series_count": 0,
                    "episode_count": 0,
                    "music_count": 0,
                    "music_album_count": 0,
                    "photo_count": 0,
                    "book_count": 0,
                    "total_size_gb": 0,
                    "total_play_count": 0,
                    "total_watch_time_minutes": 0,
                    "library_stats": {},
                    "plugin_stats": {},
                    "system_info": {},
                    "last_check": None,
                    "last_error": None
                }
        except Exception as e:
            self.logger.warning(f"Could not get Jellyfin stats: {e}")
            # Provide default Jellyfin stats structure on error
            if not stats.get("jellyfin_stats"):
                stats["jellyfin_stats"] = {
                    "server_name": "Error",
                    "server_version": "Unknown",
                    "server_id": None,
                    "server_status": "error",
                    "total_users": 0,
                    "active_users": 0,
                    "total_items": 0,
                    "movie_count": 0,
                    "series_count": 0,
                    "episode_count": 0,
                    "music_count": 0,
                    "music_album_count": 0,
                    "photo_count": 0,
                    "book_count": 0,
                    "total_size_gb": 0,
                    "total_play_count": 0,
                    "total_watch_time_minutes": 0,
                    "library_stats": {},
                    "plugin_stats": {},
                    "system_info": {},
                    "last_check": None,
                    "last_error": str(e)
                }
        
        # Get historical statistics from web database
        self.logger.debug("Fetching historical notification stats...")
        try:
            historical_stats = await self.web_db.get_notification_stats(hours=24)
            self.logger.debug(f"Historical stats retrieved: {len(historical_stats.get('hourly', []))} hourly records")
            stats["historical_stats"] = historical_stats
            
            # Update totals with historical data if available
            if historical_stats.get("totals"):
                totals = historical_stats["totals"]
                
                # Webhook and notification statistics
                stats["webhook_stats"] = {
                    "received": totals.get("total_webhooks_received", 0),
                    "processed": totals.get("total_webhooks_processed", 0),
                    "failed": totals.get("total_webhooks_failed", 0),
                    "processing_rate": round((totals.get("total_webhooks_processed", 0) / max(totals.get("total_webhooks_received", 1), 1)) * 100, 1)
                }
                
                stats["notification_stats"] = {
                    "sent": totals.get("total_sent", 0),
                    "failed": totals.get("total_failed", 0),
                    "queued": totals.get("total_queued", 0),
                    "success_rate": round((totals.get("total_sent", 0) / max(totals.get("total_sent", 0) + totals.get("total_failed", 0), 1)) * 100, 1)
                }
                
                stats["filtering_stats"] = {
                    "renames_filtered": totals.get("total_renames_filtered", 0),
                    "deletes_filtered": totals.get("total_deletes_filtered", 0),
                    "mass_renames_caught": totals.get("total_mass_renames", 0),
                    "metadata_only": totals.get("total_metadata_only", 0)
                }
                
                stats["channel_routing"] = {
                    "default": totals.get("total_sent_default", 0),
                    "movies": totals.get("total_sent_movies", 0),
                    "tv": totals.get("total_sent_tv", 0),
                    "music": totals.get("total_sent_music", 0)
                }
                
                # Legacy fields for compatibility
                stats["total_items"] = totals.get("total_sent", 0)
                new_items = totals.get("total_new") or 0
                upgraded_items = totals.get("total_upgraded") or 0
                stats["items_today"] = new_items + upgraded_items
                self.logger.debug(f"Stats from historical data: total_items={stats['total_items']}, items_today={stats['items_today']}")
            else:
                self.logger.debug("No historical totals available, using defaults")
                # Defaults are already set in the initial stats dictionary
        except Exception as e:
            self.logger.error(f"Error getting historical stats: {e}", exc_info=True)
            # Keep defaults that were already set
        
        # Get statistics from main database if webhook service is available
        self.logger.debug(f"Checking database availability: self.db={self.db is not None}, webhook_service.db={hasattr(self.webhook_service, 'db') if self.webhook_service else False}")
        
        if self.db or (self.webhook_service and hasattr(self.webhook_service, 'db') and self.webhook_service.db):
            try:
                # Get comprehensive database stats
                if self.db:
                    self.logger.debug("Using web interface's own database connection")
                    db_stats = await self.db.get_stats()
                    self.logger.debug(f"Database stats retrieved: {db_stats.keys() if db_stats else 'None'}")
                else:
                    self.logger.debug("Using webhook service's database connection")
                    db_stats = await self.webhook_service.db.get_stats()
                    self.logger.debug(f"Database stats retrieved via webhook service: {db_stats.keys() if db_stats else 'None'}")
                
                # Store synced items information
                stats["synced_items"] = SyncedItems(
                    total=db_stats.get("total_items", 0),
                    by_type=db_stats.get("item_counts", {}),
                    database_size_mb=db_stats.get("db_size_mb", 0),
                    last_sync_time=db_stats.get("last_sync_time"),
                    sync_type=db_stats.get("sync_type"),
                    recent_additions=db_stats.get("recent_additions", 0)
                )
                
                # Also update legacy fields for compatibility
                stats["total_items"] = db_stats.get("total_items", 0)
                
                # Get recent notifications from notification history (last 4 hours, max 10 items)
                try:
                    if self.web_db:
                        # Use the actual notification history with delivery status
                        recent_notifications = await self.web_db.get_recent_notifications(limit=10, hours=4)
                        stats["recent_notifications"] = recent_notifications
                    else:
                        # Fallback to old method if web_db not available
                        if self.db:
                            recent = await self.db.get_recent_changes(limit=10)
                        else:
                            recent = await self.webhook_service.db.get_recent_changes(limit=10)
                        stats["recent_notifications"] = [
                            {
                                "id": item.get("id"),
                                "name": item.get("name", "Unknown"),
                                "type": item.get("media_type"),
                                "event": item.get("last_event"),
                                "status": "pending",  # Old method doesn't track status
                                "timestamp": item.get("last_updated")
                            }
                            for item in recent
                        ]
                except Exception as e:
                    self.logger.warning(f"Failed to get recent notifications: {e}")
                    stats["recent_notifications"] = []
                
                # Discord webhook status
                if hasattr(self.webhook_service, 'discord') and self.webhook_service.discord:
                    for webhook_name, webhook_url in self.webhook_service.discord.webhooks.items():
                        stats["discord_webhooks"][webhook_name] = {
                            "configured": bool(webhook_url),
                            "last_used": None,  # Would need to track this
                            "messages_sent": 0   # Would need to track this
                        }
                
            except Exception as e:
                self.logger.error(f"Failed to get database statistics: {e}", exc_info=True)
                self.logger.debug(f"Database error type: {type(e).__name__}")
                self.logger.debug(f"Database error details: {e.args}")
                stats["system_health"]["database"] = f"error: {str(e)[:50]}"  # Include error snippet
                # Keep default values for synced_items that were already set
        else:
            # Running in standalone mode without webhook service
            self.logger.warning("No database connection available")
            self.logger.debug(f"Standalone mode details: self.db={self.db}, webhook_service={self.webhook_service is not None}")
            if self.webhook_service:
                self.logger.debug(f"Webhook service exists but has no db: {hasattr(self.webhook_service, 'db')}")
            stats["system_health"]["webhook_service"] = "not available (standalone mode)"
            stats["system_health"]["database"] = "not connected"
            # Keep all default values that were already set
        
        self.logger.debug(f"Returning overview stats: total_items={stats.get('total_items', 0)}, items_today={stats.get('items_today', 0)}, has_historical={bool(stats.get('historical_stats'))}")
        return OverviewStats(**stats)
    
    async def get_config(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Get current configuration"""
        if not self.config:
            validator = ConfigurationValidator()
            self.config = validator.load_and_validate_config()
        
        config_dict = self.config.model_dump()
        
        # Remove sensitive information unless requested
        if not include_sensitive:
            # Remove API keys and webhook URLs
            if "jellyfin" in config_dict:
                config_dict["jellyfin"]["api_key"] = "***HIDDEN***"
                
            if "discord" in config_dict:
                for key in config_dict["discord"]:
                    if "webhook_url" in key:
                        config_dict["discord"][key] = "***HIDDEN***" if config_dict["discord"][key] else None
            
            if "metadata_services" in config_dict:
                for service in ["omdb", "tmdb", "tvdb"]:
                    if service in config_dict["metadata_services"]:
                        if "api_key" in config_dict["metadata_services"][service]:
                            config_dict["metadata_services"][service]["api_key"] = "***HIDDEN***"
        
        return config_dict
    
    async def update_config(self, section: str, key: str, value: Any) -> bool:
        """Update configuration value"""
        config_path = Path("config/config.json")
        
        try:
            # Load current config
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            # Update the value
            if section not in config_data:
                config_data[section] = {}
            
            # Check if this value is from environment variable
            env_var_map = {
                ('jellyfin', 'api_key'): 'JELLYFIN_API_KEY',
                ('jellyfin', 'server_url'): 'JELLYFIN_SERVER_URL',
                ('jellyfin', 'user_id'): 'JELLYFIN_USER_ID',
                ('metadata_services.omdb', 'api_key'): 'OMDB_API_KEY',
                ('metadata_services.tmdb', 'api_key'): 'TMDB_API_KEY',
                ('metadata_services.tvdb', 'api_key'): 'TVDB_API_KEY',
                ('web_interface', 'jwt_secret'): 'JWT_SECRET_KEY',
                ('discord.webhooks.default', 'url'): 'DISCORD_WEBHOOK_URL',
            }
            
            env_var = env_var_map.get((section, key))
            is_from_env = env_var and os.environ.get(env_var) is not None
            
            if value == "**HIDDEN**":
                if is_from_env:
                    # It's OK to save **HIDDEN** because env var takes precedence
                    self.logger.debug(f"Saving hidden placeholder for {section}.{key} (env var overrides)")
                    config_data[section][key] = value
                else:
                    # Preserve the existing value from config
                    self.logger.debug(f"Preserving existing value for {section}.{key} (not from env var)")
                    # Don't update the value, keep what's there
            else:
                # Update with the new value
                config_data[section][key] = value
            
            # Validate the new configuration using Pydantic model
            from jellynouncer.config_models import AppConfig
            validated_config = AppConfig(**config_data)
            
            # Save the updated config
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Update in-memory config
            self.config = validated_config
            
            self.logger.info(f"Updated config: {section}.{key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update config: {e}")
            raise ValueError(f"Configuration update failed: {str(e)}")
    
    @staticmethod
    async def get_templates() -> List[Dict[str, Any]]:
        """Get list of available templates"""
        templates_dir = Path("templates")
        templates = []
        
        for template_file in templates_dir.glob("*.j2"):
            # Read template metadata from first line comment if available
            with open(template_file, 'r') as f:
                _ = f.read()  # Read to check file is accessible but content not needed here
                
            templates.append({
                "name": template_file.stem,
                "filename": template_file.name,
                "size": template_file.stat().st_size,
                "modified": template_file.stat().st_mtime,
                "is_default": not template_file.stem.startswith("custom_")
            })
        
        return sorted(templates, key=lambda x: x["name"])
    
    @staticmethod
    async def get_template_content(name: str) -> str:
        """Get template content"""
        template_path = Path(f"templates/{name}.j2")
        
        if not template_path.exists():
            raise ValueError(f"Template {name} not found")
        
        with open(template_path, 'r') as f:
            return f.read()
    
    async def save_template(self, name: str, content: str) -> bool:
        """Save template content"""
        # Ensure custom templates are prefixed
        if not name.startswith("custom_") and not Path(f"templates/{name}.j2").exists():
            name = f"custom_{name}"
        
        template_path = Path(f"templates/{name}.j2")
        
        try:
            # Validate Jinja2 syntax
            from jinja2 import Environment, TemplateSyntaxError
            env = Environment()
            try:
                env.parse(content)
            except TemplateSyntaxError as e:
                raise ValueError(f"Invalid Jinja2 syntax: {str(e)}")
            
            # Save the template
            with open(template_path, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Saved template: {name}")
            return True
            
        except ValueError:
            raise  # Re-raise validation errors
        except Exception as e:
            self.logger.error(f"Failed to save template: {e}")
            raise
    
    async def restore_default_template(self, name: str) -> bool:
        """Restore a template to its default content"""
        # This would need the original templates stored somewhere
        # For now, we'll just indicate this needs implementation
        raise NotImplementedError("Default template restoration not yet implemented")
    
    async def get_logs(self, query: LogQuery) -> List[Dict[str, Any]]:
        """Get log entries based on query parameters"""
        # Use the configured log directory
        log_path = Path(LOG_DIR) / query.file
        self.logger.debug(f"Attempting to read log file: {log_path}")
        
        if not log_path.exists():
            self.logger.warning(f"Log file not found: {log_path}")
            # Try alternative paths
            alt_paths = [
                Path("logs") / query.file,
                Path("/app/logs") / query.file,
                Path("../logs") / query.file
            ]
            for alt_path in alt_paths:
                self.logger.debug(f"Trying alternative path: {alt_path}")
                if alt_path.exists():
                    log_path = alt_path
                    self.logger.debug(f"Found log file at: {log_path}")
                    break
            else:
                raise ValueError(f"Log file {query.file} not found in any standard location")
        
        logs = []
        current_log = None
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read last N lines (but we need more to handle multi-line entries)
                # Read extra lines to account for multi-line messages
                lines = f.readlines()[-(query.lines * 3):]
                
                import re
                log_pattern = re.compile(r'^\[([^\]]+)\]\[([^\]]+)\]\[([^\]]+)\]\s*(.*)')
                
                for line in lines:
                    # Check if this line starts a new log entry
                    match = log_pattern.match(line)
                    
                    if match:
                        # Save previous log entry if it exists and passes filters
                        if current_log:
                            # Apply filters
                            if (not query.level or current_log["level"] == query.level) and \
                               (not query.component or query.component in current_log["component"]) and \
                               (not query.search or query.search.lower() in (current_log["message"] + current_log["component"]).lower()):
                                logs.append(current_log)
                        
                        # Start new log entry
                        current_log = {
                            "timestamp": match.group(1),
                            "level": match.group(2),
                            "component": match.group(3),
                            "message": match.group(4)
                        }
                    elif current_log:
                        # This is a continuation line - append to current log's message
                        # Preserve the newline for multi-line messages
                        current_log["message"] += "\n" + line.rstrip()
                    # If no current_log and line doesn't match pattern, skip it
                
                # Don't forget the last log entry
                if current_log:
                    if (not query.level or current_log["level"] == query.level) and \
                       (not query.component or query.component in current_log["component"]) and \
                       (not query.search or query.search.lower() in (current_log["message"] + current_log["component"]).lower()):
                        logs.append(current_log)
                
                # Limit to requested number of entries (take from the end)
                logs = logs[-query.lines:]
                
        except Exception as e:
            self.logger.error(f"Failed to read logs: {e}")
            raise
        
        return logs


# ==================== FastAPI Application ====================

# Global service instance
web_service = WebInterfaceService()

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """Manage application lifecycle"""
    # Initialize logging first (with colors)
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    log_dir = os.environ.get("LOG_DIR", "/app/logs")
    if not os.path.exists('/.dockerenv'):
        log_dir = "logs"
    
    setup_web_logging(log_level, log_dir)
    
    # Re-get the logger to ensure it has the colored formatter for web
    global logger
    logger = get_web_logger("jellynouncer.web_api")
    
    # Startup
    logger.info("=" * 60)
    logger.info("Starting Jellynouncer Web Interface...")
    logger.info("=" * 60)
    
    logger.debug(f"Environment variables:")
    logger.debug(f"  LOG_LEVEL: {log_level}")
    logger.debug(f"  LOG_DIR: {log_dir}")
    logger.debug(f"  WEB_PORT: {os.environ.get('WEB_PORT', '1985')}")
    logger.debug(f"  JELLYNOUNCER_RUN_MODE: {os.environ.get('JELLYNOUNCER_RUN_MODE', 'all')}")
    logger.debug(f"  JWT_SECRET_KEY: {'SET' if JWT_SECRET_KEY else 'NOT SET'} (length: {len(JWT_SECRET_KEY)} chars)")
    logger.debug(f"  Working directory: {os.getcwd()}")
    logger.debug(f"  Python version: {sys.version}")
    
    logger.info(f"Web logs will be written to {log_dir}/jellynouncer-web.log")
    
    try:
        logger.debug("Initializing web service...")
        await web_service.initialize()
        logger.debug("Web service initialization complete")
    except Exception as e:
        logger.error(f"Failed to initialize web service: {str(e)}", exc_info=True)
        raise
    
    # Setup SSL routes
    try:
        logger.debug("Setting up SSL routes...")
        await setup_ssl_routes(app_instance, web_service.ssl_manager)
        logger.debug("SSL routes configured")
    except Exception as e:
        logger.error(f"Failed to setup SSL routes: {str(e)}", exc_info=True)
        # Non-critical, continue
    
    # Check SSL configuration
    try:
        ssl_settings = await web_service.ssl_manager.get_ssl_settings()
        if ssl_settings.get("ssl_enabled"):
            logger.info(f"SSL enabled on port {ssl_settings.get('port', 9000)}")
        else:
            logger.info("Web interface ready on port 1985 (HTTP)")
    except Exception as e:
        logger.warning(f"Could not check SSL settings: {str(e)}")
        logger.info("Web interface ready (SSL status unknown)")
    
    # Start background task for cleaning up old notification history
    cleanup_task = None
    async def cleanup_old_notifications():
        """Background task to clean up notification history older than 7 days"""
        logger.info("Starting notification history cleanup task")
        while True:
            try:
                await asyncio.sleep(86400)  # Run once per day (24 hours)
                if web_service.web_db:
                    await web_service.web_db.cleanup_old_notifications(days=7)
                    logger.info("Cleaned up notification history older than 7 days")
            except Exception as e:
                logger.error(f"Failed to cleanup old notifications: {e}")
                await asyncio.sleep(3600)  # On error, wait 1 hour before retry
    
    cleanup_task = asyncio.create_task(cleanup_old_notifications())
    
    logger.info("Web interface startup complete")
    logger.debug(f"Total registered routes: {len(app_instance.routes)}")
    
    yield
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("Shutting down web interface...")
    logger.info("=" * 60)
    
    # Cancel background cleanup task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    
    try:
        # Cleanup tasks if needed
        logger.debug("Performing cleanup tasks...")
        # Add any cleanup code here
        logger.debug("Cleanup complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)


# Create FastAPI app
app = FastAPI(
    title="Jellynouncer Web Interface",
    description="Web management interface for Jellynouncer",
    version="1.0.0",
    lifespan=lifespan
)

# Setup security middleware - must be done immediately after app creation
# Custom CSP policy to allow connections to webhook service
csp_policy = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
    "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
    "img-src 'self' data: https: blob:; "
    "connect-src 'self' ws: wss: https: http://localhost:1984 http://localhost:1985 http://*:1984 http://*:1985; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

security_config = {
    "rate_limit": 300,  # 300 requests per minute (5 per second) - much more reasonable for interactive use
    "rate_window": 60,
    "max_auth_attempts": 5,
    "ban_duration": 30,
    "exempt_paths": ["/webhook", "/health", "/api/health", "/api/auth/status", "/api/overview", "/api/config"],
    "enable_hsts": True,
    "enable_csp": True,
    "csp_policy": csp_policy
}
setup_security_middleware(app, security_config)

# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses with extensive debug information"""
    import time
    start_time = time.time()
    
    # Generate request ID for tracking
    request_id = secrets.token_hex(8)
    
    # Log incoming request with detailed information
    logger.debug(f"[{request_id}] Incoming request: {request.method} {request.url.path}")
    
    # Extra logging for static file requests to debug serving issues
    if not request.url.path.startswith("/api"):
        logger.debug(f"[{request_id}] Static file request detected")
        if "/assets/" in request.url.path:
            logger.debug(f"[{request_id}] Asset request: {request.url.path}")
        elif request.url.path in ["/", "/config", "/templates", "/logs", "/overview"]:
            logger.debug(f"[{request_id}] SPA route request: {request.url.path} - should serve index.html")
    logger.debug(f"[{request_id}] Client: {request.client.host if request.client else 'unknown'}")
    logger.debug(f"[{request_id}] Headers: {dict(request.headers)}")
    logger.debug(f"[{request_id}] Query params: {dict(request.query_params)}")
    
    # Log request body for POST/PUT/PATCH (be careful with sensitive data)
    if request.method in ["POST", "PUT", "PATCH"]:
        # Don't log auth endpoints bodies (contains passwords)
        if "/auth/" not in request.url.path:
            try:
                body = await request.body()
                if body:
                    logger.debug(f"[{request_id}] Request body size: {len(body)} bytes")
                    # Only log small bodies to avoid cluttering logs
                    if len(body) < 1000:
                        try:
                            body_json = json.loads(body)
                            # Mask sensitive fields
                            if "password" in body_json:
                                body_json["password"] = "***MASKED***"
                            if "api_key" in body_json:
                                body_json["api_key"] = "***MASKED***"
                            logger.debug(f"[{request_id}] Request body: {json.dumps(body_json, indent=2)}")
                        except json.JSONDecodeError:
                            logger.debug(f"[{request_id}] Request body (non-JSON): {body[:200]}...")
                # Need to recreate the request body stream
                from starlette.datastructures import Headers
                from starlette.requests import Request as StarletteRequest
                request = StarletteRequest(request.scope, request.receive)
                request._body = body
            except Exception as e:
                logger.debug(f"[{request_id}] Could not read request body: {e}")
    
    # Process the request
    try:
        response = await call_next(request)
    except Exception as e:
        # Log any unhandled exceptions
        logger.error(f"[{request_id}] Unhandled exception: {e}", exc_info=True)
        raise
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response
    logger.debug(f"[{request_id}] Response status: {response.status_code}")
    logger.debug(f"[{request_id}] Processing time: {process_time:.3f}s")
    
    # Add custom headers for debugging
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log response details based on status code
    if response.status_code >= 400:
        logger.warning(f"[{request_id}] Error response: {response.status_code} for {request.method} {request.url.path}")
        # Extra detail for 404s on static files
        if response.status_code == 404 and not request.url.path.startswith("/api"):
            logger.warning(f"[{request_id}] Static file not found - this may indicate the SPA routes aren't working correctly")
            logger.warning(f"[{request_id}] Path requested: {request.url.path}")
            logger.warning(f"[{request_id}] Should have served index.html for SPA route")
    elif response.status_code >= 300:
        logger.debug(f"[{request_id}] Redirect response: {response.status_code}")
    else:
        logger.debug(f"[{request_id}] Success response: {response.status_code}")
    
    return response

# Configure CORS - Disabled by default for security
# Can be enabled via environment variable if needed
cors_enabled = os.environ.get("JELLYNOUNCER_ENABLE_CORS", "false").lower() == "true"

if cors_enabled:
    # Get allowed origins from environment variable
    custom_origins = os.environ.get("JELLYNOUNCER_ALLOWED_ORIGINS", "")
    if custom_origins:
        if custom_origins == "*":
            allowed_origins = ["*"]
        else:
            allowed_origins = [origin.strip() for origin in custom_origins.split(",")]
    else:
        # Default to common development origins if CORS is enabled without specific origins
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    
    logger.info(f"CORS enabled with origins: {allowed_origins}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    logger.debug("CORS disabled (default for security). Set JELLYNOUNCER_ENABLE_CORS=true to enable.")

# Add trusted host middleware for security
if os.environ.get("JELLYNOUNCER_PRODUCTION"):
    allowed_hosts = os.environ.get("JELLYNOUNCER_ALLOWED_HOSTS", "").split(",")
    if allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
        logger.info(f"Trusted host middleware enabled with hosts: {allowed_hosts}")
else:
    logger.debug("Running in development mode - trusted host middleware disabled")


# ==================== API Endpoints ====================

@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user_login: UserLogin, request: Request):
    """Authenticate user and return JWT tokens"""
    client_ip = request.client.host if request.client else "unknown"
    logger.debug(f"Login attempt from {client_ip} for user: {user_login.username}")
    
    user = await web_service.web_db.verify_user(user_login.username, user_login.password)
    
    if not user:
        logger.warning(f"Failed login attempt for username: {user_login.username} from {client_ip}")
        # Log failed attempt
        await web_service.web_db.log_audit(
            None, "login_failed", f"Username: {user_login.username}", 
            request.client.host
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    logger.debug(f"User {user_login.username} authenticated successfully, creating tokens")
    
    # Create tokens
    access_token = create_access_token({"user_id": user["id"], "username": user["username"]})
    user_refresh_token = create_refresh_token({"user_id": user["id"]})
    
    logger.debug(f"Tokens created for user {user['id']}, saving refresh token")
    
    # Save refresh token
    expires_at = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    await web_service.web_db.save_refresh_token(user["id"], user_refresh_token, expires_at)
    
    # Log successful login
    await web_service.web_db.log_audit(
        user["id"], "login_success", None, request.client.host
    )
    
    logger.info(f"User {user_login.username} logged in successfully from {client_ip}")
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=user_refresh_token,
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.post("/api/auth/refresh", response_model=TokenResponse)
async def refresh_token(token_string: str):
    """Refresh access token using refresh token"""
    user_id = await web_service.web_db.verify_refresh_token(token_string)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    # Get user details
    async with aiosqlite.connect(WEB_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Create new access token
    access_token = create_access_token({"user_id": user_id, "username": user["username"]})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=token_string,  # Return same refresh token
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@app.get("/api/auth/status")
async def get_auth_status():
    """Get authentication status (no auth required)"""
    logger.debug("Auth status check requested")
    settings = await web_service.web_db.get_security_settings()
    
    # Check if any admin accounts exist
    has_admin = False
    try:
        async with aiosqlite.connect(WEB_DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE id = 1")
            row = await cursor.fetchone()
            has_admin = row[0] > 0 if row else False
    except Exception as e:
        logger.error(f"Error checking for admin account: {e}")
        has_admin = False
    
    logger.debug(f"Returning auth status: auth_enabled={settings.get('auth_enabled', False)}, has_admin={has_admin}")
    return {
        **settings,
        "has_admin": has_admin
    }


@app.post("/api/auth/setup")
async def setup_authentication(user_create: UserCreate):
    """Initial authentication setup - only works when no users exist"""
    # Check if any users exist
    async with aiosqlite.connect(WEB_DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        user_count = (await cursor.fetchone())[0]
    
    if user_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication already configured. Use login endpoint."
        )
    
    try:
        # Create the first admin user
        user_id = await web_service.web_db.create_user(
            user_create.username,
            user_create.password,
            user_create.email,
            is_admin=True
        )
        
        # Enable authentication
        await web_service.web_db.update_security_settings(auth_enabled=True, require_webhook_auth=False)
        
        # Create tokens for immediate login
        access_token = create_access_token({"user_id": user_id, "username": user_create.username})
        new_refresh_token = create_refresh_token({"user_id": user_id})
        
        # Save refresh token
        expires_at = datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        await web_service.web_db.save_refresh_token(user_id, new_refresh_token, expires_at)
        
        return {
            "message": "Authentication configured successfully",
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "expires_in": JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.put("/api/auth/settings")
async def update_auth_settings(
    auth_enabled: bool,
    require_webhook_auth: bool,
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Update authentication settings"""
    # If disabling auth, ensure user is authenticated
    settings = await web_service.web_db.get_security_settings()
    
    if settings["auth_enabled"] and not auth_enabled:
        # Trying to disable auth - must be authenticated
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Must be authenticated to disable authentication"
            )
    
    await web_service.web_db.update_security_settings(auth_enabled, require_webhook_auth)
    
    if current_user:
        await web_service.web_db.log_audit(
            current_user.get("user_id"),
            "auth_settings_updated",
            f"Auth enabled: {auth_enabled}, Webhook auth: {require_webhook_auth}",
            None
        )
    
    return {"message": "Security settings updated", "auth_enabled": auth_enabled, "require_webhook_auth": require_webhook_auth}


@app.put("/api/auth/password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: Dict = Depends(get_current_user)
):
    """Change the current user's password"""
    try:
        # Verify current password
        async with aiosqlite.connect(WEB_DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT username FROM users WHERE id = ?",
                (current_user["user_id"],)
            )
            row = await cursor.fetchone()
            
            if not row:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found"
                )
            
            # Use web_db's verify_user method to check password
            user = await web_service.web_db.verify_user(row["username"], current_password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Update password using web_db method
            await web_service.web_db.update_user_password(current_user["user_id"], new_password)
        
        # Log the password change
        await web_service.web_db.log_audit(
            current_user["user_id"],
            "password_changed",
            "Password changed successfully",
            None
        )
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate, current_user: Optional[Dict] = Depends(check_auth_required)):
    """Register a new user (requires auth if enabled)"""
    # Check if auth is enabled
    settings = await web_service.web_db.get_security_settings()
    
    if settings["auth_enabled"] and not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to create users"
        )
    
    try:
        user_id = await web_service.web_db.create_user(
            user_create.username, 
            user_create.password,
            user_create.email
        )
        
        if current_user:
            await web_service.web_db.log_audit(
                current_user.get("user_id"), 
                "user_created", 
                f"Created user: {user_create.username}",
                None
            )
        
        return {"message": "User created successfully", "user_id": user_id}
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ==================== Webhook API Key Management ====================

@app.get("/api/webhook-keys")
async def get_webhook_api_keys(current_user: Optional[Dict] = Depends(check_webhook_key_auth)):
    """Get all webhook API keys"""
    logger.debug(f"Webhook API keys requested by user: {current_user.get('username') if current_user else 'anonymous/setup'}")
    
    try:
        keys = await web_service.web_db.get_webhook_api_keys()
        logger.debug(f"Returning {len(keys)} webhook API keys")
        return {"keys": keys}
    except Exception as e:
        logger.error(f"Failed to get webhook API keys: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve API keys")


@app.post("/api/webhook-keys")
async def create_webhook_api_key(
    request: Dict[str, str],
    current_user: Optional[Dict] = Depends(check_webhook_key_auth)
):
    """Create a new webhook API key"""
    name = request.get("name", "").strip()
    description = request.get("description", "").strip() or None
    
    if not name:
        raise HTTPException(status_code=400, detail="API key name is required")
    
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="API key name must be 100 characters or less")
    
    try:
        # Create the API key
        created_by = current_user.get("user_id") if current_user else None
        key_info = await web_service.web_db.create_webhook_api_key(name, description, created_by)
        
        logger.info(f"Created webhook API key '{name}' (ID: {key_info['id']}) by user: {current_user.get('username') if current_user else 'setup/anonymous'}")
        
        # Log audit event if user is authenticated
        if current_user:
            await web_service.web_db.log_audit(
                current_user.get("user_id"),
                "webhook_api_key_created",
                f"Created webhook API key: {name}",
                None  # IP address parameter, not metadata dict
            )
        
        return {
            "success": True,
            "key": key_info["key"],  # Return the actual key only on creation
            "id": key_info["id"],
            "name": key_info["name"],
            "message": "API key created successfully. Save this key securely - it cannot be viewed again."
        }
    except Exception as e:
        logger.error(f"Failed to create webhook API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to create API key")


@app.delete("/api/webhook-keys/{key_id}")
async def revoke_webhook_api_key(
    key_id: int,
    current_user: Optional[Dict] = Depends(check_webhook_key_auth)
):
    """Revoke a webhook API key"""
    try:
        revoked_by = current_user.get("user_id") if current_user else None
        success = await web_service.web_db.revoke_webhook_api_key(key_id, revoked_by)
        
        if success:
            logger.info(f"Revoked webhook API key ID: {key_id} by user: {current_user.get('username') if current_user else 'system'}")
            
            # Log audit event if user is authenticated
            if current_user:
                await web_service.web_db.log_audit(
                    current_user.get("user_id"),
                    "webhook_api_key_revoked",
                    f"Revoked webhook API key ID: {key_id}",
                    None  # IP address parameter
                )
            
            return {"success": True, "message": "API key revoked successfully"}
        else:
            raise HTTPException(status_code=404, detail="API key not found or already revoked")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke webhook API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke API key")


@app.get("/api/notifications")
async def get_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    hours: int = Query(4, ge=1, le=24),
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Get paginated notification history"""
    logger.debug(f"[API] Notifications requested - page: {page}, limit: {limit}, hours: {hours}")
    
    try:
        if web_service.web_db:
            # Calculate offset for pagination
            offset = (page - 1) * limit
            
            # Get total count (for pagination info)
            all_notifications = await web_service.web_db.get_recent_notifications(limit=1000, hours=hours)
            total_count = len(all_notifications)
            
            # Get paginated subset
            paginated_notifications = all_notifications[offset:offset + limit]
            
            return {
                "notifications": paginated_notifications,
                "page": page,
                "limit": limit,
                "total": total_count,
                "total_pages": (total_count + limit - 1) // limit  # Ceiling division
            }
        else:
            return {
                "notifications": [],
                "page": 1,
                "limit": limit,
                "total": 0,
                "total_pages": 0
            }
    except Exception as e:
        logger.error(f"[API] Error fetching notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch notifications: {str(e)}")


@app.get("/api/notifications/history")
async def get_notifications_history(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    hours: int = Query(4, ge=1, le=24),
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Get notification history (alias endpoint for compatibility)"""
    logger.debug(f"[API] Notifications history requested - page: {page}, limit: {limit}, hours: {hours}")
    
    try:
        if web_service.web_db:
            # Calculate offset for pagination
            offset = (page - 1) * limit
            
            # Get total count (for pagination info)
            all_notifications = await web_service.web_db.get_recent_notifications(limit=1000, hours=hours)
            total_count = len(all_notifications)
            
            # Get paginated subset
            paginated_notifications = all_notifications[offset:offset + limit]
            
            return {
                "notifications": paginated_notifications,
                "page": page,
                "limit": limit,
                "total": total_count,
                "total_pages": (total_count + limit - 1) // limit  # Ceiling division
            }
        else:
            return {
                "notifications": [],
                "page": 1,
                "limit": limit,
                "total": 0,
                "total_pages": 0
            }
    except Exception as e:
        logger.error(f"[API] Error fetching notification history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch notification history: {str(e)}")


@app.get("/api/overview", response_model=OverviewStats)
async def get_overview(current_user: Optional[Dict] = Depends(check_auth_required)):
    """Get overview statistics"""
    logger.info(f"[ENDPOINT] /api/overview called - user: {current_user.get('username') if current_user else 'anonymous'}")
    try:
        result = await web_service.get_overview_stats()
        logger.info(f"[ENDPOINT] /api/overview returning stats successfully")
        return result
    except Exception as e:
        logger.error(f"[ENDPOINT] /api/overview failed: {type(e).__name__}: {e}", exc_info=True)
        raise


@app.get("/api/config")
async def get_config(current_user: Optional[Dict] = Depends(check_auth_required)):
    """Get current configuration"""
    logger.debug(f"Config requested by user: {current_user.get('username') if current_user else 'anonymous'}")
    config = await web_service.get_config(include_sensitive=False)
    logger.debug(f"Returning config with {len(config)} sections")
    return config


@app.put("/api/config")
async def update_config(
    config_update: ConfigUpdate, 
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Update configuration value"""
    logger.debug(f"Config update request: {config_update.section}.{config_update.key} by user {current_user.get('username') if current_user else 'anonymous'}")
    
    # Log the value type but not the actual value (could be sensitive)
    value_type = type(config_update.value).__name__
    logger.debug(f"Value type: {value_type}, is_none: {config_update.value is None}")
    
    try:
        success = await web_service.update_config(
            config_update.section,
            config_update.key,
            config_update.value
        )
        
        if success:
            logger.info(f"Configuration updated: {config_update.section}.{config_update.key}")
        else:
            logger.warning(f"Configuration update failed: {config_update.section}.{config_update.key}")
        
        if current_user:
            await web_service.web_db.log_audit(
                current_user.get("user_id"),
                "config_updated",
                f"Updated {config_update.section}.{config_update.key}",
                None
            )
        
        return {"success": success, "message": "Configuration updated"}
        
    except Exception as e:
        logger.error(f"Error updating config {config_update.section}.{config_update.key}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.put("/api/config/full")
async def update_full_config(
    config_data: Dict[str, Any],
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Update entire configuration at once"""
    logger.debug(f"Full config update request by user {current_user.get('username') if current_user else 'anonymous'}")
    
    try:
        # Load current config
        config_path = Path("config/config.json")
        with open(config_path, 'r') as f:
            current_config = json.load(f)
        
        # Merge configs, preserving actual values where frontend sends "**HIDDEN**"
        def merge_configs(current: Dict, new: Dict, path: str = "") -> Dict:
            """Recursively merge configs, preserving values marked as hidden"""
            result = {}
            
            # Environment variable mappings for checking if values come from env
            env_var_map = {
                'jellyfin.api_key': 'JELLYFIN_API_KEY',
                'jellyfin.server_url': 'JELLYFIN_SERVER_URL',
                'jellyfin.user_id': 'JELLYFIN_USER_ID',
                'metadata_services.omdb.api_key': 'OMDB_API_KEY',
                'metadata_services.tmdb.api_key': 'TMDB_API_KEY',
                'metadata_services.tvdb.api_key': 'TVDB_API_KEY',
                'web_interface.jwt_secret': 'JWT_SECRET_KEY',
                'discord.webhooks.default.url': 'DISCORD_WEBHOOK_URL',
                'discord.webhooks.movies.url': 'DISCORD_WEBHOOK_MOVIES_URL',
                'discord.webhooks.tv.url': 'DISCORD_WEBHOOK_TV_URL',
                'discord.webhooks.music.url': 'DISCORD_WEBHOOK_MUSIC_URL',
            }
            
            for key, new_value in new.items():
                current_path = f"{path}.{key}" if path else key
                
                if key not in current:
                    # New key, use the new value
                    result[key] = new_value
                elif isinstance(new_value, dict) and isinstance(current.get(key), dict):
                    # Both are dicts, recursively merge
                    result[key] = merge_configs(current[key], new_value, current_path)
                elif new_value == "**HIDDEN**":
                    # Check if this field is from environment variable
                    env_var = env_var_map.get(current_path)
                    is_from_env = env_var and os.environ.get(env_var) is not None
                    
                    if is_from_env:
                        # It's OK to save **HIDDEN** because env var takes precedence
                        result[key] = new_value
                        logger.debug(f"Saving hidden placeholder for {current_path} (env var overrides)")
                    else:
                        # Preserve the existing value from config
                        result[key] = current[key]
                        logger.debug(f"Preserving existing value for {current_path} (not from env var)")
                else:
                    # Use the new value
                    result[key] = new_value
            
            # Include any keys from current that aren't in new (shouldn't happen but be safe)
            for key in current:
                if key not in result:
                    result[key] = current[key]
            
            return result
        
        # Merge the configurations
        merged_config = merge_configs(current_config, config_data)
        
        # Validate the merged configuration using Pydantic model
        from jellynouncer.config_models import AppConfig
        validated_config = AppConfig(**merged_config)
        
        # Save the merged config (with actual values, not hidden placeholders)
        with open(config_path, 'w') as f:
            json.dump(merged_config, f, indent=2)
        
        # Update in-memory config
        web_service.config = validated_config
        
        logger.info("Full configuration updated successfully")
        
        if current_user:
            await web_service.web_db.log_audit(
                current_user.get("user_id"),
                "config_updated",
                "Updated full configuration",
                None
            )
        
        return {"success": True, "message": "Configuration saved successfully"}
        
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e.errors()}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.errors()
        )
    except Exception as e:
        logger.error(f"Error updating full config: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/test/jellyfin")
async def test_jellyfin_connection(
    config: Dict[str, Any],
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Test Jellyfin server connection"""
    try:
        # Import Jellyfin API client and config model
        from jellynouncer.jellyfin_api import JellyfinAPI
        from jellynouncer.config_models import JellyfinConfig
        
        # Create temporary config object
        jellyfin_config = JellyfinConfig(
            server_url=config.get("server_url"),
            api_key=config.get("api_key"),
            user_id=config.get("user_id")
        )
        
        # Create temporary client with config object
        jellyfin = JellyfinAPI(jellyfin_config)
        
        # Test connection by getting server info
        server_info = await jellyfin.get_system_info()
        
        return {
            "success": True,
            "message": "Connection successful",
            "server_name": server_info.get("ServerName", "Unknown"),
            "version": server_info.get("Version", "Unknown")
        }
    except Exception as e:
        logger.error(f"Jellyfin test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection failed: {str(e)}"
        )


@app.post("/api/test/discord/{webhook_name}")
async def test_discord_webhook(
    webhook_name: str,
    config: Dict[str, Any],
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Test Discord webhook"""
    try:
        import aiohttp
        
        webhook_url = config.get("url")
        if not webhook_url:
            raise ValueError("Webhook URL is required")
        
        # Send test message
        async with aiohttp.ClientSession() as session:
            test_message = {
                "content": f"🧪 Test message from Jellynouncer",
                "embeds": [{
                    "title": "Webhook Test",
                    "description": f"This is a test message for the **{webhook_name}** webhook.",
                    "color": 0x9b59b6,  # Purple
                    "fields": [
                        {
                            "name": "Status",
                            "value": "✅ Connection successful",
                            "inline": True
                        },
                        {
                            "name": "Webhook Name",
                            "value": webhook_name,
                            "inline": True
                        }
                    ],
                    "footer": {
                        "text": "Jellynouncer Web Interface"
                    }
                }]
            }
            
            async with session.post(webhook_url, json=test_message) as response:
                if response.status == 204:
                    return {
                        "success": True,
                        "message": "Test message sent successfully"
                    }
                else:
                    error_text = await response.text()
                    raise ValueError(f"Discord returned {response.status}: {error_text}")
                    
    except Exception as e:
        logger.error(f"Discord webhook test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook test failed: {str(e)}"
        )


@app.get("/api/templates")
async def get_templates(current_user: Optional[Dict] = Depends(check_auth_required)):
    """Get list of available templates"""
    return await web_service.get_templates()


@app.get("/api/templates/{name}")
async def get_template(name: str, current_user: Optional[Dict] = Depends(check_auth_required)):
    """Get template content"""
    try:
        content = await web_service.get_template_content(name)
        return {"name": name, "content": content}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@app.put("/api/templates/{name}")
async def update_template(
    name: str,
    template_update: TemplateUpdate,
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Update or create template"""
    try:
        success = await web_service.save_template(name, template_update.content)
        
        if current_user:
            await web_service.web_db.log_audit(
                current_user.get("user_id"),
                "template_updated",
                f"Updated template: {name}",
                None
            )
        
        return {"success": success, "message": "Template saved"}
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/templates/{name}/restore")
async def restore_template(name: str, current_user: Optional[Dict] = Depends(check_auth_required)):
    """Restore template to default"""
    try:
        success = await web_service.restore_default_template(name)
        
        if current_user:
            await web_service.web_db.log_audit(
                current_user.get("user_id"),
                "template_restored",
                f"Restored template: {name}",
                None
            )
        
        return {"success": success, "message": "Template restored"}
        
    except NotImplementedError as e:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get("/api/logs/files")
async def get_log_files(current_user: Optional[Dict] = Depends(check_auth_required)):
    """Get list of available log files"""
    try:
        log_path = Path(LOG_DIR)
        
        # Try alternative paths if default doesn't exist
        if not log_path.exists():
            alt_paths = [
                Path("logs"),
                Path("/app/logs"),
                Path("../logs")
            ]
            for alt_path in alt_paths:
                if alt_path.exists():
                    log_path = alt_path
                    break
            else:
                return {"files": []}
        
        # Get all .log files in the directory, including rotated files
        log_files = []
        # Match .log files and rotated files like .log.1, .log.2, etc.
        for file in log_path.iterdir():
            if file.is_file() and (file.suffix == '.log' or (file.name.endswith('.log') or '.log.' in file.name)):
                # Get file size and last modified time
                stat = file.stat()
                log_files.append({
                    "name": file.name,
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "size_readable": f"{stat.st_size / 1024 / 1024:.2f} MB" if stat.st_size > 1024 * 1024 else f"{stat.st_size / 1024:.2f} KB"
                })
        
        # Sort log files: main logs first, then rotated by number
        def sort_key(file_info):
            name = file_info["name"]
            # Check if it's a rotated file
            if '.log.' in name:
                # Extract the rotation number
                try:
                    base, num = name.rsplit('.', 1)
                    return (base, int(num))
                except:
                    return (name, 0)
            else:
                # Main log file comes first
                return (name, -1)
        
        log_files.sort(key=sort_key)
        
        return {"files": log_files}
        
    except Exception as e:
        logger.error(f"Failed to list log files: {e}")
        return {"files": []}


@app.get("/api/logs/recent")
async def get_recent_logs(
    limit: int = Query(100, description="Number of recent log entries to retrieve"),
    level: Optional[str] = Query(None, description="Filter by log level (ERROR, WARNING, INFO, DEBUG)"),
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Get recent log entries without requiring a POST body"""
    try:
        # Create a LogQuery for recent logs
        log_query = LogQuery(
            log_file="jellynouncer-web.log",  # Default to web log
            limit=limit,
            level=level
        )
        logs = await web_service.get_logs(log_query)
        return {"logs": logs, "count": len(logs)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@app.post("/api/logs")
async def get_logs(log_query: LogQuery, current_user: Optional[Dict] = Depends(check_auth_required)):
    """Get log entries"""
    try:
        logs = await web_service.get_logs(log_query)
        return {"logs": logs, "count": len(logs)}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/logs/raw")
async def get_raw_logs(log_query: LogQuery, current_user: Optional[Dict] = Depends(check_auth_required)):
    """Get raw log content without parsing - preserves multi-line entries"""
    try:
        # Use the configured log directory
        log_path = Path(LOG_DIR) / log_query.file
        
        if not log_path.exists():
            # Try alternative paths
            alt_paths = [
                Path("logs") / log_query.file,
                Path("/app/logs") / log_query.file,
                Path("../logs") / log_query.file
            ]
            for alt_path in alt_paths:
                if alt_path.exists():
                    log_path = alt_path
                    break
            else:
                raise ValueError(f"Log file {log_query.file} not found")
        
        # Read the raw log content
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read all lines
            lines = f.readlines()
            
            # Get the last N lines as requested
            if log_query.lines and log_query.lines > 0:
                lines = lines[-log_query.lines:]
            
            # Join lines to preserve original formatting
            raw_content = ''.join(lines)
            
            # Apply simple text filtering if requested
            if log_query.search:
                filtered_lines = []
                for line in lines:
                    if log_query.search.lower() in line.lower():
                        filtered_lines.append(line)
                raw_content = ''.join(filtered_lines)
            
            if log_query.level:
                filtered_lines = []
                for line in lines:
                    if f"[{log_query.level}]" in line:
                        filtered_lines.append(line)
                raw_content = ''.join(filtered_lines)
            
            if log_query.component:
                filtered_lines = []
                for line in lines:
                    if f"[{log_query.component}" in line:
                        filtered_lines.append(line)
                raw_content = ''.join(filtered_lines)
        
        return {"content": raw_content, "type": "raw"}
        
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get raw logs: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/logs/client")
async def receive_client_logs(log_batch: ClientLogBatch):
    """
    Receive and process client-side logs from the React frontend.
    
    This endpoint accepts batched logs from the browser and writes them
    to the main jellynouncer.log file with proper formatting to distinguish
    them from server-side logs.
    
    Client logs are written with a [CLIENT] prefix and include session ID
    for correlation with user sessions.
    
    Note: This endpoint doesn't require authentication to ensure critical
    error logs can always be sent.
    """
    try:
        client_logger = get_web_logger("jellynouncer.web_client")
        
        # Process each log entry
        for log_entry in log_batch.logs:
            # Format the client log message with session context
            formatted_message = f"[CLIENT] [{log_entry.sessionId[:8]}] {log_entry.url} - {log_entry.message}"
            
            # Add metadata if present
            if log_entry.metadata:
                formatted_message += f" | Metadata: {json.dumps(log_entry.metadata)}"
            
            # Log at appropriate level
            level = log_entry.level.upper()
            if level == "DEBUG":
                client_logger.debug(formatted_message)
            elif level == "INFO":
                client_logger.info(formatted_message)
            elif level == "WARN" or level == "WARNING":
                client_logger.warning(formatted_message)
            elif level == "ERROR":
                client_logger.error(formatted_message)
            else:
                # Default to info for unknown levels
                client_logger.info(formatted_message)
        
        # Log batch summary at debug level
        client_logger.debug(f"Processed {len(log_batch.logs)} client logs from session {log_batch.sessionId[:8]}")
        
        return {
            "success": True,
            "processed": len(log_batch.logs),
            "sessionId": log_batch.sessionId
        }
        
    except Exception as e:
        logger.error(f"Failed to process client logs: {e}", exc_info=True)
        # Still return success to prevent client from retrying
        # We don't want logging failures to impact the client
        return {
            "success": False,
            "error": "Failed to process logs",
            "processed": 0
        }


@app.get("/api/health")
async def health_check():
    """Health check endpoint (no auth required)"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "Jellynouncer Web Interface"
    }


@app.get("/api/debug/static-files")
async def debug_static_files():
    """Debug endpoint to check static file configuration"""
    logger.info("Static files debug endpoint called")
    
    # Check which path we're using
    if os.path.exists('/.dockerenv'):
        web_dist_path = "/app/web/dist"
        environment = "Docker"
    else:
        web_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "dist")
        environment = "Local"
    
    result = {
        "environment": environment,
        "web_dist_path": web_dist_path,
        "absolute_path": os.path.abspath(web_dist_path),
        "exists": os.path.exists(web_dist_path),
        "contents": {},
        "routes": [],
        "specific_assets": {},
        "current_working_dir": os.getcwd()
    }
    
    # Check if directory exists and list contents
    if os.path.exists(web_dist_path):
        try:
            result["contents"]["root"] = os.listdir(web_dist_path)
            
            # Check assets directory
            assets_path = os.path.join(web_dist_path, "assets")
            if os.path.exists(assets_path):
                asset_files = os.listdir(assets_path)
                result["contents"]["assets"] = {
                    "count": len(asset_files),
                    "files": asset_files[:20]  # First 20 files
                }

            else:
                result["contents"]["assets"] = "Directory not found"
                
        except Exception as e:
            result["error"] = str(e)
            logger.error(f"Error in debug endpoint: {e}", exc_info=True)
    
    # List app routes (limit to first 20 to avoid huge response)
    for route in list(app.routes)[:20]:
        route_info = {
            "path": getattr(route, 'path', str(route)),
            "type": route.__class__.__name__
        }
        if hasattr(route, 'methods'):
            route_info["methods"] = list(route.methods)
        result["routes"].append(route_info)
    
    result["total_routes"] = len(app.routes)
    
    logger.info(f"Debug static files check complete - found: {result['exists']}")
    return result


# ==================== SSL Certificate Management ====================

@app.post("/api/ssl/upload")
async def upload_ssl_file(
    file: UploadFile = File(...),
    type: str = Form(...),
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Upload SSL certificate or key file"""
    try:
        from pathlib import Path
        
        # Validate file type
        if type not in ["cert", "key"]:
            raise HTTPException(status_code=400, detail="Invalid file type")
        
        # Create SSL directory if it doesn't exist
        ssl_dir = Path(web_service.config.server.data_dir) / "ssl"
        ssl_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file extension
        file_ext = ".crt" if type == "cert" else ".key"
        file_path = ssl_dir / f"{type}{file_ext}"
        
        # Save the file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Update configuration
        if type == "cert":
            await web_service.update_config("web_interface", "ssl_cert_path", str(file_path))
        else:
            await web_service.update_config("web_interface", "ssl_key_path", str(file_path))
        
        logger.info(f"SSL {type} file uploaded to {file_path}")
        
        return {"status": "success", "path": str(file_path)}
        
    except Exception as e:
        logger.error(f"Failed to upload SSL file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ssl/generate-csr")
async def generate_csr_endpoint(
    csr_data: Dict[str, Any],
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Generate a Certificate Signing Request"""
    try:
        # Extract CSR parameters
        common_name = csr_data.get("commonName", "localhost")
        country = csr_data.get("country", "US")
        state = csr_data.get("state", "State")
        locality = csr_data.get("locality", "City")
        organization = csr_data.get("organization", "Organization")
        organizational_unit = csr_data.get("organizationalUnit", "IT")
        email = csr_data.get("email")
        san_list = csr_data.get("sanList", [])
        
        # Generate CSR using SSL manager
        result = await web_service.ssl_manager.create_csr_request(
            common_name=common_name,
            country=country,
            state=state,
            locality=locality,
            organization=organization,
            organizational_unit=organizational_unit,
            email=email,
            san_list=san_list if san_list else None
        )
        
        logger.info(f"Generated CSR for {common_name}")
        
        return {
            "status": "success",
            "csr": result["csr"],
            "private_key_path": result["private_key_path"]
        }
        
    except Exception as e:
        logger.error(f"Failed to generate CSR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ssl/generate-self-signed")
async def generate_self_signed_cert(
    cert_data: Dict[str, Any],
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Generate a self-signed certificate"""
    try:
        from pathlib import Path
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from datetime import datetime, timedelta
        
        # Extract certificate parameters
        common_name = cert_data.get("commonName", "localhost")
        days = cert_data.get("days", 365)
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=days)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(common_name),
                x509.DNSName("localhost"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Save certificate and key
        ssl_dir = Path(web_service.config.server.data_dir) / "ssl"
        ssl_dir.mkdir(parents=True, exist_ok=True)
        
        cert_path = ssl_dir / "self_signed.crt"
        key_path = ssl_dir / "self_signed.key"
        
        # Write certificate
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        # Write private key
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # Update configuration
        await web_service.update_config("web_interface", "ssl_cert_path", str(cert_path))
        await web_service.update_config("web_interface", "ssl_key_path", str(key_path))
        await web_service.update_config("web_interface", "ssl_enabled", True)
        
        logger.info(f"Generated self-signed certificate for {common_name}")
        
        return {
            "status": "success",
            "cert_path": str(cert_path),
            "key_path": str(key_path),
            "valid_days": days
        }
        
    except Exception as e:
        logger.error(f"Failed to generate self-signed certificate: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BACKUP ENDPOINTS ====================

@app.get("/api/backup/status")
async def get_backup_status(current_user: Optional[Dict] = Depends(check_auth_required)):
    """Get backup system status and configuration"""
    try:
        # Debug logging
        logger.debug(f"Getting backup status - backup_manager exists: {web_service.backup_manager is not None}")
        logger.debug(f"Config object exists: {web_service.config is not None}")
        if web_service.config:
            logger.debug(f"Config has backup attr: {hasattr(web_service.config, 'backup')}")
            if hasattr(web_service.config, 'backup'):
                logger.debug(f"Backup config: {web_service.config.backup}")
        
        if not web_service.backup_manager:
            logger.warning("Backup manager not initialized - returning disabled status")
            return {"enabled": False, "message": "Backup system not initialized"}
        
        # Get current configuration
        config = web_service.config.backup.model_dump() if hasattr(web_service.config, 'backup') else {}
        logger.debug(f"Backup config retrieved: {config}")
        logger.info(f"Backup config details - enabled: {config.get('enabled')}, schedule: {config.get('schedule')}, backup_dir: {config.get('backup_dir')}")
        
        # Get backup statistics
        stats = await web_service.backup_manager.get_statistics()
        
        # Calculate estimated backup size
        db_size = 0
        config_size = 0
        template_size = 0
        
        # Database size
        db_path = Path("data/jellynouncer.db")
        if db_path.exists():
            db_size = db_path.stat().st_size
            for ext in [".wal", ".shm"]:
                wal_file = Path(str(db_path) + ext)
                if wal_file.exists():
                    db_size += wal_file.stat().st_size
        
        # Config size
        config_path = Path("/app/config/config.json")
        if not config_path.exists():
            config_path = Path("config/config.json")
        if config_path.exists():
            config_size = config_path.stat().st_size
        
        # Templates size
        template_dir = Path("/app/templates")
        if not template_dir.exists():
            template_dir = Path("templates")
        if template_dir.exists():
            template_size = sum(f.stat().st_size for f in template_dir.glob("*.j2"))
        
        estimated_size = db_size + config_size + template_size
        
        # The enabled field is IN the config, so we use it directly
        response = {
            "enabled": config.get("enabled", True),  # The enabled field from the backup config
            "config": config,
            "statistics": stats,
            "estimated_size": estimated_size,
            "estimated_size_mb": round(estimated_size / (1024 * 1024), 2),
            "next_backup": stats.get("next_scheduled") if stats else None
        }
        
        logger.info(f"Returning backup status response: enabled={response['enabled']}, has_config={bool(response['config'])}")
        logger.debug(f"Full response structure: {json.dumps(response, default=str)}")
        
        return response
    except Exception as e:
        logger.error(f"Failed to get backup status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backup/list")
async def list_backups(current_user: Optional[Dict] = Depends(check_auth_required)):
    """List all available backups"""
    try:
        if not web_service.backup_manager:
            raise HTTPException(status_code=503, detail="Backup system not initialized")
        
        backups = await web_service.backup_manager.list_backups()
        return {"backups": backups}
    except Exception as e:
        logger.error(f"Failed to list backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backup/create")
async def create_backup(
    description: str = Form(default="Manual backup"),
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Manually create a backup"""
    try:
        if not web_service.backup_manager:
            raise HTTPException(status_code=503, detail="Backup system not initialized")
        
        # Create backup
        backup_info = await web_service.backup_manager.create_backup(
            backup_type="manual",
            description=description
        )
        
        return {
            "success": True,
            "backup": backup_info,
            "message": f"Backup created successfully: {backup_info['filename']}"
        }
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backup/restore/{backup_name}")
async def restore_backup(
    backup_name: str,
    components: List[str] = Query(default=["config", "database", "templates"]),
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Restore from a specific backup"""
    try:
        if not web_service.backup_manager:
            raise HTTPException(status_code=503, detail="Backup system not initialized")
        
        # Create a pre-restore backup first
        logger.info(f"Creating pre-restore backup before restoring {backup_name}")
        pre_restore = await web_service.backup_manager.create_backup(
            backup_type="pre-restore",
            description=f"Automatic backup before restore from {backup_name}"
        )
        
        # Perform restore
        result = await web_service.backup_manager.restore_backup(
            backup_name,
            components=components
        )
        
        return {
            "success": True,
            "pre_restore_backup": pre_restore['filename'],
            "restored_components": result,
            "message": f"Successfully restored from {backup_name}"
        }
    except Exception as e:
        logger.error(f"Failed to restore backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/backup/{backup_name}")
async def delete_backup(
    backup_name: str,
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Delete a specific backup"""
    try:
        if not web_service.backup_manager:
            raise HTTPException(status_code=503, detail="Backup system not initialized")
        
        # Delete the backup
        success = await web_service.backup_manager.delete_backup(backup_name)
        
        if success:
            return {
                "success": True,
                "message": f"Backup {backup_name} deleted successfully"
            }
        else:
            raise HTTPException(status_code=404, detail=f"Backup {backup_name} not found")
    except Exception as e:
        logger.error(f"Failed to delete backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/backup/config")
async def update_backup_config(
    config: dict,
    current_user: Optional[Dict] = Depends(check_auth_required)
):
    """Update backup configuration"""
    try:
        # Update config in memory
        if hasattr(web_service.config, 'backup'):
            for key, value in config.items():
                if hasattr(web_service.config.backup, key):
                    setattr(web_service.config.backup, key, value)
        
        # Save to config file
        config_path = "/app/config/config.json"
        if not os.path.exists(config_path):
            config_path = "config/config.json"
        
        with open(config_path, 'r') as f:
            full_config = json.load(f)
        
        if 'backup' not in full_config:
            full_config['backup'] = {}
        
        full_config['backup'].update(config)
        
        with open(config_path, 'w') as f:
            json.dump(full_config, f, indent=2)
        
        # Reinitialize backup manager with new config
        if web_service.backup_manager:
            await web_service.backup_manager.update_config(config)
        
        return {
            "success": True,
            "message": "Backup configuration updated successfully",
            "config": config
        }
    except Exception as e:
        logger.error(f"Failed to update backup config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backup/test")
async def test_backup(current_user: Optional[Dict] = Depends(check_auth_required)):
    """Test backup system by creating a small test backup"""
    try:
        if not web_service.backup_manager:
            raise HTTPException(status_code=503, detail="Backup system not initialized")
        
        # Create a test backup with minimal components
        backup_info = await web_service.backup_manager.create_backup(
            backup_type="test",
            description="Test backup for system verification",
            components=["config"]  # Only backup config for test
        )
        
        # Immediately delete the test backup
        await web_service.backup_manager.delete_backup(backup_info['filename'])
        
        return {
            "success": True,
            "message": "Backup system test completed successfully"
        }
    except Exception as e:
        logger.error(f"Backup system test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Backup system test failed: {str(e)}")




# ==================== Static File Serving ====================
# IMPORTANT: This MUST come after all API route definitions
# to ensure API routes take precedence over the catch-all static route

logger.debug("=" * 60)
logger.debug("STATIC FILE SETUP - DEBUG MODE")
logger.debug("=" * 60)

# Determine the correct path for web dist
if os.path.exists('/.dockerenv'):
    # Running in Docker
    web_dist_path = "/app/web/dist"
    logger.debug("🐳 DOCKER ENVIRONMENT DETECTED")
    logger.debug(f"Looking for static files at: {web_dist_path}")
else:
    # Running locally
    web_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web", "dist")
    logger.debug("💻 LOCAL ENVIRONMENT DETECTED")
    logger.debug(f"Looking for static files at: {web_dist_path}")

# Check various possible paths (for debugging)
possible_paths = [
    web_dist_path,
    "/app/web/dist",
    os.path.join(os.path.dirname(__file__), "..", "web", "dist"),
    os.path.join(os.getcwd(), "web", "dist"),
    "web/dist"
]

logger.debug("Checking possible static file paths:")
for path in possible_paths:
    exists = os.path.exists(path) if path else False
    abs_path = os.path.abspath(path) if path else "N/A"
    logger.debug(f"  {path}: {'✓ EXISTS' if exists else '✗ NOT FOUND'} (abs: {abs_path})")

# Check if the build exists
if os.path.exists(web_dist_path):
    logger.info(f"✓ Web interface build found at {web_dist_path}")
    logger.debug(f"  Absolute path: {os.path.abspath(web_dist_path)}")
    
    # Debug: List ALL contents with details
    try:
        dist_contents = os.listdir(web_dist_path)
        logger.debug(f"📁 Dist directory contains {len(dist_contents)} items:")
        for item in dist_contents:
            item_path = os.path.join(web_dist_path, item)
            is_dir = os.path.isdir(item_path)
            if is_dir:
                try:
                    sub_items = os.listdir(item_path)
                    logger.debug(f"  📁 {item}/ ({len(sub_items)} items)")
                    # If it's the assets directory, list its contents
                    if item == "assets":
                        for asset in sub_items[:10]:  # First 10 assets
                            asset_size = os.path.getsize(os.path.join(item_path, asset))
                            logger.debug(f"    📄 {asset} ({asset_size:,} bytes)")
                except Exception as e:
                    logger.error(f"    Error listing {item}: {e}")
            else:
                size = os.path.getsize(item_path)
                logger.debug(f"  📄 {item} ({size:,} bytes)")
        
        # Specifically check for the assets that are failing
        assets_path = os.path.join(web_dist_path, "assets")
        if os.path.exists(assets_path):
            logger.debug("✓ Assets directory exists")

        else:
            logger.error(f"✗ Assets directory NOT FOUND at {assets_path}")
            
    except Exception as e:
        logger.error(f"Error listing directory contents: {e}", exc_info=True)
    
    # Mount the static files
    logger.debug("Attempting to mount static files...")
    
    # Add explicit SPA route handlers BEFORE mounting static files
    # These will serve index.html for the main SPA routes
    from fastapi.responses import FileResponse
    
    index_path = os.path.join(web_dist_path, "index.html")
    
    @app.get("/config")
    async def serve_config_spa():
        """Serve index.html for /config SPA route"""
        return FileResponse(index_path, media_type="text/html")
    
    @app.get("/templates")
    async def serve_templates_spa():
        """Serve index.html for /templates SPA route"""
        return FileResponse(index_path, media_type="text/html")
    
    @app.get("/logs")
    async def serve_logs_spa():
        """Serve index.html for /logs SPA route"""
        return FileResponse(index_path, media_type="text/html")
    
    @app.get("/overview")
    async def serve_overview_spa():
        """Serve index.html for /overview SPA route"""
        return FileResponse(index_path, media_type="text/html")
    
    logger.debug("Added explicit SPA route handlers for /config, /templates, /logs, /overview")
    
    # The order matters: specific routes first, then catch-all
    from fastapi.staticfiles import StaticFiles
    
    try:
        # Mount the entire dist directory as the root
        # The html=True option enables serving index.html for directory requests
        # But we've added explicit handlers above for the main SPA routes
        static_files = StaticFiles(directory=web_dist_path, html=True)
        app.mount("/", static_files, name="static")
        
        logger.info("✓ Static files mounted successfully with SPA support")
        
        # Log all registered routes for debugging
        logger.debug("Registered routes after static mount:")
        for route in app.routes:
            if hasattr(route, 'path'):
                logger.debug(f"  {route.path} -> {route.__class__.__name__}")
            else:
                logger.debug(f"  {route} -> {route.__class__.__name__}")
                
    except Exception as e:
        logger.error(f"✗ Failed to mount static files: {e}", exc_info=True)
        
else:
    logger.error(f"✗ Web interface build NOT FOUND at {web_dist_path}")
    logger.debug(f"  Absolute path checked: {os.path.abspath(web_dist_path)}")
    logger.warning("The React frontend needs to be built first.")
    logger.warning("Run 'npm install && npm run build' in the web directory")
    
    # List what IS in the parent directory
    parent_dir = os.path.dirname(web_dist_path)
    if os.path.exists(parent_dir):
        logger.debug(f"Contents of parent directory {parent_dir}:")
        try:
            for item in os.listdir(parent_dir):
                logger.debug(f"  - {item}")
        except Exception as e:
            logger.error(f"Could not list parent directory: {e}")
    
    # Add a fallback route for when the build doesn't exist
    @app.get("/")
    async def web_ui_not_built_root():
        return JSONResponse(
            status_code=503,
            content={
                "error": "Web interface not built",
                "message": "The web interface needs to be built before it can be served.",
                "instructions": [
                    "1. Navigate to the 'web' directory",
                    "2. Run 'npm install' to install dependencies",
                    "3. Run 'npm run build' to build the production files",
                    "4. Restart the Jellynouncer service"
                ],
                "api_status": "The API endpoints are still available at /api/*"
            }
        )
    
    # Note: When the build doesn't exist, the StaticFiles mount won't work,
    # so we don't need explicit catch-all routes - the root handler above will catch everything


# ==================== Main Entry Point ====================

async def get_ssl_config():
    """Get SSL configuration for server startup"""
    ssl_manager = SSLManager(WEB_DB_PATH)
    await ssl_manager.initialize()
    settings = await ssl_manager.get_ssl_settings()
    
    if settings.get("ssl_enabled"):
        context = ssl_manager.create_ssl_context(settings)
        if context:
            return {
                "ssl_keyfile": None,  # Handled by context
                "ssl_certfile": None,  # Handled by context
                "ssl_context": context,
                "port": settings.get("port", 9000)
            }
    
    return {"port": 1985}


if __name__ == "__main__":
    import asyncio
    
    # Get SSL configuration
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    ssl_config = loop.run_until_complete(get_ssl_config())
    
    # Run the web interface server
    uvicorn.run(
        "jellynouncer.web_api:app",
        host="0.0.0.0",
        port=ssl_config.get("port", 1985),
        ssl_keyfile=ssl_config.get("ssl_keyfile"),
        ssl_certfile=ssl_config.get("ssl_certfile"),
        reload=os.environ.get("JELLYNOUNCER_DEV_MODE") == "true" and not ssl_config.get("ssl_context")
    )