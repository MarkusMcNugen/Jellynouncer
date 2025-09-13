"""
Web Database Manager - Shared module for database operations

This module provides database access for both web_api and webhook_api,
allowing webhook authentication to be checked without circular imports.
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Database path
DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
WEB_DB_PATH = DATA_DIR / "web_interface.db"

logger = logging.getLogger(__name__)


class WebDatabaseManager:
    """Manages the web interface database"""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or WEB_DB_PATH
        self.initialized = False
        
    async def initialize(self):
        """Initialize database and create tables if needed"""
        if self.initialized:
            return
            
        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create tables if they don't exist
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS security_settings (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    auth_enabled BOOLEAN DEFAULT 0,
                    require_webhook_auth BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CHECK (id = 1)
                )
            """)
            
            # Insert default settings if not exists
            conn.execute("""
                INSERT OR IGNORE INTO security_settings (id, auth_enabled, require_webhook_auth) 
                VALUES (1, 0, 0)
            """)
            
            # Users table for authentication
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    is_admin BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                )
            """)
            
            # Sessions table for refresh tokens
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    refresh_token TEXT UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Audit log table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            
            # Create indexes for user tables
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(refresh_token)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
            
            # Create notification statistics table for historical data
            # Create webhook API keys table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    key_hash TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP,
                    active BOOLEAN DEFAULT 1,
                    created_by INTEGER,
                    revoked_at TIMESTAMP,
                    revoked_by INTEGER,
                    usage_count INTEGER DEFAULT 0,
                    last_ip TEXT
                )
            """)
            
            # Create index for key lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_webhook_api_keys_hash 
                ON webhook_api_keys(key_hash) WHERE active = 1
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    hour_bucket TEXT,      -- For hourly aggregation (YYYY-MM-DD HH:00)
                    day_bucket TEXT,       -- For daily aggregation (YYYY-MM-DD)
                    
                    -- Webhook received stats
                    webhooks_received INTEGER DEFAULT 0,
                    webhooks_processed INTEGER DEFAULT 0,
                    webhooks_failed INTEGER DEFAULT 0,
                    
                    -- Discord notification stats
                    notifications_sent INTEGER DEFAULT 0,
                    notifications_failed INTEGER DEFAULT 0,
                    notifications_queued INTEGER DEFAULT 0,
                    
                    -- Event type stats
                    new_items INTEGER DEFAULT 0,
                    upgraded_items INTEGER DEFAULT 0,
                    deleted_items INTEGER DEFAULT 0,
                    metadata_only_updates INTEGER DEFAULT 0,
                    
                    -- Filtering stats
                    renames_filtered INTEGER DEFAULT 0,
                    deletes_filtered INTEGER DEFAULT 0,
                    mass_renames_caught INTEGER DEFAULT 0,
                    
                    -- Content type stats
                    movies INTEGER DEFAULT 0,
                    tv_shows INTEGER DEFAULT 0,
                    episodes INTEGER DEFAULT 0,
                    music INTEGER DEFAULT 0,
                    
                    -- Discord channel routing stats
                    sent_to_default INTEGER DEFAULT 0,
                    sent_to_movies INTEGER DEFAULT 0,
                    sent_to_tv INTEGER DEFAULT 0,
                    sent_to_music INTEGER DEFAULT 0,
                    
                    -- Performance stats
                    library_scans INTEGER DEFAULT 0,
                    avg_processing_time_ms REAL,
                    queue_size_max INTEGER DEFAULT 0
                )
            """)
            
            # Create indexes for efficient querying
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notification_stats_hour 
                ON notification_stats(hour_bucket)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notification_stats_day 
                ON notification_stats(day_bucket)
            """)
            
            # Notification history table for tracking individual notifications
            conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_id TEXT NOT NULL,
                    item_name TEXT NOT NULL,
                    item_type TEXT,
                    event_type TEXT NOT NULL,  -- 'new', 'upgraded', 'deleted'
                    status TEXT NOT NULL,       -- 'pending', 'sent', 'failed'
                    discord_webhook TEXT,       -- Which webhook was used
                    error_message TEXT,         -- If failed, why
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processing_time_ms INTEGER,
                    metadata TEXT              -- JSON for additional data
                )
            """)
            
            # Indexes for efficient queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notification_history_timestamp 
                ON notification_history(timestamp DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notification_history_status 
                ON notification_history(status)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_notification_history_item 
                ON notification_history(item_id)
            """)
            
            # Add new columns to existing table if they don't exist (migration)
            cursor = conn.execute("PRAGMA table_info(notification_stats)")
            existing_columns = {row[1] for row in cursor.fetchall()}
            
            new_columns = [
                ("webhooks_received", "INTEGER DEFAULT 0"),
                ("webhooks_processed", "INTEGER DEFAULT 0"),
                ("webhooks_failed", "INTEGER DEFAULT 0"),
                ("notifications_queued", "INTEGER DEFAULT 0"),
                ("metadata_only_updates", "INTEGER DEFAULT 0"),
                ("renames_filtered", "INTEGER DEFAULT 0"),
                ("deletes_filtered", "INTEGER DEFAULT 0"),
                ("sent_to_default", "INTEGER DEFAULT 0"),
                ("sent_to_movies", "INTEGER DEFAULT 0"),
                ("sent_to_tv", "INTEGER DEFAULT 0"),
                ("sent_to_music", "INTEGER DEFAULT 0"),
                ("seasons", "INTEGER DEFAULT 0"),  # Track season notifications separately
                ("series", "INTEGER DEFAULT 0")    # Track series notifications separately (not episodes)
            ]
            
            for column_name, column_def in new_columns:
                if column_name not in existing_columns:
                    try:
                        conn.execute(f"ALTER TABLE notification_stats ADD COLUMN {column_name} {column_def}")
                        logger.debug(f"Added column {column_name} to notification_stats table")
                    except sqlite3.OperationalError:
                        pass  # Column already exists
            
            # Create jellyfin_stats table for storing server statistics
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jellyfin_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    server_name TEXT,
                    server_version TEXT,
                    server_id TEXT,
                    server_status TEXT,
                    total_users INTEGER DEFAULT 0,
                    active_users INTEGER DEFAULT 0,
                    movie_count INTEGER DEFAULT 0,
                    series_count INTEGER DEFAULT 0,
                    season_count INTEGER DEFAULT 0,
                    episode_count INTEGER DEFAULT 0,
                    music_count INTEGER DEFAULT 0,
                    music_album_count INTEGER DEFAULT 0,
                    photo_count INTEGER DEFAULT 0,
                    book_count INTEGER DEFAULT 0,
                    total_items INTEGER DEFAULT 0,
                    library_stats TEXT,  -- JSON string
                    plugin_stats TEXT,   -- JSON string
                    system_info TEXT,    -- JSON string
                    last_check TIMESTAMP
                )
            """)
            
            # Create index for faster lookups
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_jellyfin_stats_timestamp 
                ON jellyfin_stats(timestamp DESC)
            """)
            
            conn.commit()
        
        self.initialized = True
        logger.info(f"Web database initialized at {self.db_path}")
    
    async def get_security_settings(self) -> Dict[str, Any]:
        """Get current security settings"""
        if not self.initialized:
            await self.initialize()
            
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM security_settings WHERE id = 1")
            settings = cursor.fetchone()
            
        if settings:
            return {
                "auth_enabled": bool(settings["auth_enabled"]),
                "require_webhook_auth": bool(settings["require_webhook_auth"])
            }
        
        return {"auth_enabled": False, "require_webhook_auth": False}
    
    async def update_security_settings(self, auth_enabled: bool, require_webhook_auth: bool):
        """Update security settings"""
        if not self.initialized:
            await self.initialize()
            
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE security_settings 
                SET auth_enabled = ?, require_webhook_auth = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = 1
            """, (auth_enabled, require_webhook_auth))
            conn.commit()
        
        logger.info(f"Security settings updated: auth_enabled={auth_enabled}, require_webhook_auth={require_webhook_auth}")
    
    async def get_notification_stats(self, hours: int = 24) -> Dict[str, Any]:
        """Get notification statistics for the specified time period"""
        from datetime import datetime, timedelta
        
        if not self.initialized:
            await self.initialize()
        
        # Calculate time boundary
        cutoff_time = datetime.now() - timedelta(hours=hours)
        cutoff_str = cutoff_time.strftime('%Y-%m-%d %H:00')
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get hourly aggregated data with all new fields
            cursor = conn.execute("""
                SELECT 
                    hour_bucket,
                    SUM(webhooks_received) as webhooks_received,
                    SUM(webhooks_processed) as webhooks_processed,
                    SUM(webhooks_failed) as webhooks_failed,
                    SUM(notifications_sent) as sent,
                    SUM(notifications_failed) as failed,
                    SUM(notifications_queued) as queued,
                    SUM(new_items) as new,
                    SUM(upgraded_items) as upgraded,
                    SUM(deleted_items) as deleted,
                    SUM(metadata_only_updates) as metadata_only,
                    SUM(renames_filtered) as renames_filtered,
                    SUM(deletes_filtered) as deletes_filtered,
                    SUM(mass_renames_caught) as mass_renames,
                    SUM(movies) as movies,
                    SUM(tv_shows) as tv_shows,
                    SUM(episodes) as episodes,
                    SUM(music) as music,
                    SUM(sent_to_default) as sent_default,
                    SUM(sent_to_movies) as sent_movies,
                    SUM(sent_to_tv) as sent_tv,
                    SUM(sent_to_music) as sent_music,
                    SUM(library_scans) as library_scans
                FROM notification_stats
                WHERE hour_bucket >= ?
                GROUP BY hour_bucket
                ORDER BY hour_bucket DESC
                LIMIT 24
            """, (cutoff_str,))
            
            # Create a dictionary of existing data
            existing_data = {}
            for row in cursor.fetchall():
                existing_data[row["hour_bucket"]] = {
                    "hour": row["hour_bucket"],
                    "webhooks_received": row["webhooks_received"] or 0,
                    "webhooks_processed": row["webhooks_processed"] or 0,
                    "webhooks_failed": row["webhooks_failed"] or 0,
                    "sent": row["sent"] or 0,
                    "failed": row["failed"] or 0,
                    "queued": row["queued"] or 0,
                    "new": row["new"] or 0,
                    "upgraded": row["upgraded"] or 0,
                    "deleted": row["deleted"] or 0,
                    "metadata_only": row["metadata_only"] or 0,
                    "renames_filtered": row["renames_filtered"] or 0,
                    "deletes_filtered": row["deletes_filtered"] or 0,
                    "mass_renames": row["mass_renames"] or 0,
                    "movies": row["movies"] or 0,
                    "tv_shows": row["tv_shows"] or 0,
                    "episodes": row["episodes"] or 0,
                    "music": row["music"] or 0,
                    "sent_default": row["sent_default"] or 0,
                    "sent_movies": row["sent_movies"] or 0,
                    "sent_tv": row["sent_tv"] or 0,
                    "sent_music": row["sent_music"] or 0,
                    "library_scans": row["library_scans"] or 0
                }
            
            # Create all 24 hour buckets with zero values for missing hours
            hourly_data = []
            current_time = datetime.now()
            for i in range(24):
                hour_time = current_time - timedelta(hours=i)
                hour_bucket = hour_time.strftime('%Y-%m-%d %H:00')
                
                if hour_bucket in existing_data:
                    hourly_data.append(existing_data[hour_bucket])
                else:
                    # Add empty hour with all zeros
                    hourly_data.append({
                        "hour": hour_bucket,
                        "webhooks_received": 0,
                        "webhooks_processed": 0,
                        "webhooks_failed": 0,
                        "sent": 0,
                        "failed": 0,
                        "queued": 0,
                        "new": 0,
                        "upgraded": 0,
                        "deleted": 0,
                        "metadata_only": 0,
                        "renames_filtered": 0,
                        "deletes_filtered": 0,
                        "mass_renames": 0,
                        "movies": 0,
                        "tv_shows": 0,
                        "episodes": 0,
                        "music": 0,
                        "sent_default": 0,
                        "sent_movies": 0,
                        "sent_tv": 0,
                        "sent_music": 0,
                        "library_scans": 0
                    })
            
            # Get totals for the period
            cursor = conn.execute("""
                SELECT 
                    SUM(webhooks_received) as total_webhooks_received,
                    SUM(webhooks_processed) as total_webhooks_processed,
                    SUM(webhooks_failed) as total_webhooks_failed,
                    SUM(notifications_sent) as total_sent,
                    SUM(notifications_failed) as total_failed,
                    SUM(notifications_queued) as total_queued,
                    SUM(new_items) as total_new,
                    SUM(upgraded_items) as total_upgraded,
                    SUM(deleted_items) as total_deleted,
                    SUM(metadata_only_updates) as total_metadata_only,
                    SUM(renames_filtered) as total_renames_filtered,
                    SUM(deletes_filtered) as total_deletes_filtered,
                    SUM(mass_renames_caught) as total_mass_renames,
                    SUM(movies) as total_movies,
                    SUM(tv_shows) as total_tv_shows,
                    SUM(episodes) as total_episodes,
                    SUM(music) as total_music,
                    SUM(sent_to_default) as total_sent_default,
                    SUM(sent_to_movies) as total_sent_movies,
                    SUM(sent_to_tv) as total_sent_tv,
                    SUM(sent_to_music) as total_sent_music,
                    SUM(library_scans) as total_library_scans
                FROM notification_stats
                WHERE hour_bucket >= ?
            """, (cutoff_str,))
            
            totals_row = cursor.fetchone()
            totals = {
                "total_webhooks_received": totals_row["total_webhooks_received"] or 0 if totals_row else 0,
                "total_webhooks_processed": totals_row["total_webhooks_processed"] or 0 if totals_row else 0,
                "total_webhooks_failed": totals_row["total_webhooks_failed"] or 0 if totals_row else 0,
                "total_sent": totals_row["total_sent"] or 0 if totals_row else 0,
                "total_failed": totals_row["total_failed"] or 0 if totals_row else 0,
                "total_queued": totals_row["total_queued"] or 0 if totals_row else 0,
                "total_new": totals_row["total_new"] or 0 if totals_row else 0,
                "total_upgraded": totals_row["total_upgraded"] or 0 if totals_row else 0,
                "total_deleted": totals_row["total_deleted"] or 0 if totals_row else 0,
                "total_metadata_only": totals_row["total_metadata_only"] or 0 if totals_row else 0,
                "total_renames_filtered": totals_row["total_renames_filtered"] or 0 if totals_row else 0,
                "total_deletes_filtered": totals_row["total_deletes_filtered"] or 0 if totals_row else 0,
                "total_mass_renames": totals_row["total_mass_renames"] or 0 if totals_row else 0,
                "total_movies": totals_row["total_movies"] or 0 if totals_row else 0,
                "total_tv_shows": totals_row["total_tv_shows"] or 0 if totals_row else 0,
                "total_episodes": totals_row["total_episodes"] or 0 if totals_row else 0,
                "total_music": totals_row["total_music"] or 0 if totals_row else 0,
                "total_sent_default": totals_row["total_sent_default"] or 0 if totals_row else 0,
                "total_sent_movies": totals_row["total_sent_movies"] or 0 if totals_row else 0,
                "total_sent_tv": totals_row["total_sent_tv"] or 0 if totals_row else 0,
                "total_sent_music": totals_row["total_sent_music"] or 0 if totals_row else 0,
                "total_library_scans": totals_row["total_library_scans"] or 0 if totals_row else 0
            }
        
        return {
            "hourly": hourly_data,
            "totals": totals,
            "period_hours": hours
        }
    
    async def record_webhook_event(self, event_type: str, item_type: str = None, **kwargs):
        """
        Record webhook and notification events for comprehensive statistics.
        
        Args:
            event_type: Type of event (webhook_received, webhook_processed, notification_sent, etc.)
            item_type: Media item type (Movie, Episode, etc.)
            **kwargs: Additional event-specific data (channel, success, filtered_type, etc.)
        """
        from datetime import datetime
        
        if not self.initialized:
            await self.initialize()
        
        now = datetime.now()
        hour_bucket = now.strftime('%Y-%m-%d %H:00')
        day_bucket = now.strftime('%Y-%m-%d')
        
        # Initialize update dictionary with time buckets
        updates = {
            "hour_bucket": hour_bucket,
            "day_bucket": day_bucket
        }
        
        # Handle different event types
        if event_type == "webhook_received":
            updates["webhooks_received"] = 1
        elif event_type == "webhook_processed":
            updates["webhooks_processed"] = 1
        elif event_type == "webhook_failed":
            updates["webhooks_failed"] = 1
        elif event_type == "notification_sent":
            updates["notifications_sent"] = 1
            # Track channel routing
            channel = kwargs.get("channel", "default")
            if channel == "movies":
                updates["sent_to_movies"] = 1
            elif channel == "tv":
                updates["sent_to_tv"] = 1
            elif channel == "music":
                updates["sent_to_music"] = 1
            else:
                updates["sent_to_default"] = 1
        elif event_type == "notification_failed":
            updates["notifications_failed"] = 1
        elif event_type == "notification_queued":
            updates["notifications_queued"] = 1
        elif event_type == "new":
            updates["new_items"] = 1
        elif event_type == "upgraded":
            updates["upgraded_items"] = 1
        elif event_type == "deleted":
            updates["deleted_items"] = 1
        elif event_type == "metadata_only":
            updates["metadata_only_updates"] = 1
        elif event_type == "rename_filtered":
            updates["renames_filtered"] = 1
        elif event_type == "delete_filtered":
            updates["deletes_filtered"] = 1
        elif event_type == "mass_rename_filtered":
            updates["mass_renames_caught"] = 1
        elif event_type == "library_scan":
            updates["library_scans"] = 1
        
        # Update content type counters
        if item_type:
            item_type_lower = item_type.lower()
            if "movie" in item_type_lower:
                updates["movies"] = 1
            elif "episode" in item_type_lower:
                updates["episodes"] = 1
            elif "series" in item_type_lower or "show" in item_type_lower:
                updates["tv_shows"] = 1
            elif "music" in item_type_lower or "audio" in item_type_lower:
                updates["music"] = 1
        
        # Insert or update the hourly bucket
        with sqlite3.connect(self.db_path) as conn:
            # Try to update existing record first
            cursor = conn.execute("""
                UPDATE notification_stats
                SET webhooks_received = webhooks_received + ?,
                    webhooks_processed = webhooks_processed + ?,
                    webhooks_failed = webhooks_failed + ?,
                    notifications_sent = notifications_sent + ?,
                    notifications_failed = notifications_failed + ?,
                    notifications_queued = notifications_queued + ?,
                    new_items = new_items + ?,
                    upgraded_items = upgraded_items + ?,
                    deleted_items = deleted_items + ?,
                    metadata_only_updates = metadata_only_updates + ?,
                    renames_filtered = renames_filtered + ?,
                    deletes_filtered = deletes_filtered + ?,
                    mass_renames_caught = mass_renames_caught + ?,
                    movies = movies + ?,
                    tv_shows = tv_shows + ?,
                    episodes = episodes + ?,
                    music = music + ?,
                    sent_to_default = sent_to_default + ?,
                    sent_to_movies = sent_to_movies + ?,
                    sent_to_tv = sent_to_tv + ?,
                    sent_to_music = sent_to_music + ?,
                    library_scans = library_scans + ?
                WHERE hour_bucket = ?
            """, (
                updates.get("webhooks_received", 0),
                updates.get("webhooks_processed", 0),
                updates.get("webhooks_failed", 0),
                updates.get("notifications_sent", 0),
                updates.get("notifications_failed", 0),
                updates.get("notifications_queued", 0),
                updates.get("new_items", 0),
                updates.get("upgraded_items", 0),
                updates.get("deleted_items", 0),
                updates.get("metadata_only_updates", 0),
                updates.get("renames_filtered", 0),
                updates.get("deletes_filtered", 0),
                updates.get("mass_renames_caught", 0),
                updates.get("movies", 0),
                updates.get("tv_shows", 0),
                updates.get("episodes", 0),
                updates.get("music", 0),
                updates.get("sent_to_default", 0),
                updates.get("sent_to_movies", 0),
                updates.get("sent_to_tv", 0),
                updates.get("sent_to_music", 0),
                updates.get("library_scans", 0),
                hour_bucket
            ))
            
            # If no rows were updated, insert a new record
            if cursor.rowcount == 0:
                conn.execute("""
                    INSERT INTO notification_stats (
                        hour_bucket, day_bucket, 
                        webhooks_received, webhooks_processed, webhooks_failed,
                        notifications_sent, notifications_failed, notifications_queued,
                        new_items, upgraded_items, deleted_items, metadata_only_updates,
                        renames_filtered, deletes_filtered, mass_renames_caught,
                        movies, tv_shows, episodes, music,
                        sent_to_default, sent_to_movies, sent_to_tv, sent_to_music,
                        library_scans
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    hour_bucket, day_bucket,
                    updates.get("webhooks_received", 0),
                    updates.get("webhooks_processed", 0),
                    updates.get("webhooks_failed", 0),
                    updates.get("notifications_sent", 0),
                    updates.get("notifications_failed", 0),
                    updates.get("notifications_queued", 0),
                    updates.get("new_items", 0),
                    updates.get("upgraded_items", 0),
                    updates.get("deleted_items", 0),
                    updates.get("metadata_only_updates", 0),
                    updates.get("renames_filtered", 0),
                    updates.get("deletes_filtered", 0),
                    updates.get("mass_renames_caught", 0),
                    updates.get("movies", 0),
                    updates.get("tv_shows", 0),
                    updates.get("episodes", 0),
                    updates.get("music", 0),
                    updates.get("sent_to_default", 0),
                    updates.get("sent_to_movies", 0),
                    updates.get("sent_to_tv", 0),
                    updates.get("sent_to_music", 0),
                    updates.get("library_scans", 0)
                ))
            
            conn.commit()
    
    async def record_notification_event(self, event_type: str, item_type: str = None, success: bool = True):
        """
        Legacy method for backward compatibility.
        Redirects to the new record_webhook_event method.
        """
        # Map old event types to new ones
        if success:
            await self.record_webhook_event("notification_sent", item_type)
        else:
            await self.record_webhook_event("notification_failed", item_type)
        
        # Also record the event type
        if event_type in ["new", "upgraded", "deleted"]:
            await self.record_webhook_event(event_type, item_type)
    
    # ==================== API Key Management ====================
    
    async def create_webhook_api_key(self, name: str, description: str = None, created_by: int = None) -> Dict[str, str]:
        """
        Create a new API key for webhook authentication.
        
        Returns dict with 'id', 'key' (actual key), and 'name'
        """
        import secrets
        import hashlib
        
        if not self.initialized:
            await self.initialize()
        
        # Generate secure API key
        api_key = f"wh_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO webhook_api_keys (name, key_hash, description, created_by)
                VALUES (?, ?, ?, ?)
            """, (name, key_hash, description, created_by))
            
            conn.commit()
            key_id = cursor.lastrowid
        
        logger.info(f"Created new webhook API key: {name} (ID: {key_id})")
        
        return {
            "id": key_id,
            "key": api_key,  # Return actual key only on creation
            "name": name
        }
    
    async def validate_webhook_api_key(self, api_key: str, client_ip: str = None) -> Optional[Dict[str, Any]]:
        """
        Validate an API key and update usage statistics.
        
        Returns key info if valid, None otherwise
        """
        import hashlib
        
        if not self.initialized:
            await self.initialize()
        
        # Hash the provided key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Find matching active key
            cursor = conn.execute("""
                SELECT id, name, description, created_at, usage_count
                FROM webhook_api_keys
                WHERE key_hash = ? AND active = 1
            """, (key_hash,))
            
            key_info = cursor.fetchone()
            
            if key_info:
                # Update usage statistics
                conn.execute("""
                    UPDATE webhook_api_keys
                    SET last_used = CURRENT_TIMESTAMP,
                        usage_count = usage_count + 1,
                        last_ip = ?
                    WHERE id = ?
                """, (client_ip, key_info['id']))
                
                conn.commit()
                
                logger.debug(f"API key validated: {key_info['name']} (usage #{key_info['usage_count'] + 1})")
                
                return {
                    "id": key_info['id'],
                    "name": key_info['name'],
                    "description": key_info['description'],
                    "created_at": key_info['created_at'],
                    "usage_count": key_info['usage_count'] + 1
                }
        
        logger.warning(f"Invalid API key attempted from IP: {client_ip}")
        return None
    
    async def get_webhook_api_keys(self) -> list:
        """Get all API keys (without actual key values)"""
        if not self.initialized:
            await self.initialize()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT id, name, description, created_at, last_used, 
                       active, usage_count, last_ip
                FROM webhook_api_keys
                WHERE active = 1
                ORDER BY created_at DESC
            """)
            
            keys = []
            for row in cursor:
                keys.append({
                    "id": row['id'],
                    "name": row['name'],
                    "description": row['description'],
                    "created_at": row['created_at'],
                    "last_used": row['last_used'],
                    "usage_count": row['usage_count'],
                    "last_ip": row['last_ip']
                })
        
        return keys
    
    async def revoke_webhook_api_key(self, key_id: int, revoked_by: int = None) -> bool:
        """Revoke an API key"""
        if not self.initialized:
            await self.initialize()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE webhook_api_keys
                SET active = 0,
                    revoked_at = CURRENT_TIMESTAMP,
                    revoked_by = ?
                WHERE id = ? AND active = 1
            """, (revoked_by, key_id))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Revoked webhook API key ID: {key_id}")
                return True
        
        return False
    
    async def log_audit(self, user_id: Optional[int], action: str, details: Optional[str], ip: Optional[str]):
        """Log an audit event"""
        if not self.initialized:
            await self.initialize()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO audit_log (user_id, action, details, ip_address) VALUES (?, ?, ?, ?)",
                (user_id, action, details, ip)
            )
            conn.commit()
        
        logger.info(f"Audit: User {user_id} from {ip} performed {action}: {details}")
    
    # ==================== Notification History ====================
    
    async def add_notification_history(
        self, 
        item_id: str, 
        item_name: str, 
        item_type: str,
        event_type: str,
        status: str,
        discord_webhook: str = None,
        error_message: str = None,
        processing_time_ms: int = None,
        metadata: Dict = None
    ):
        """Add a notification to the history"""
        import json
        
        if not self.initialized:
            await self.initialize()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO notification_history (
                    item_id, item_name, item_type, event_type, status,
                    discord_webhook, error_message, processing_time_ms, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                item_id, item_name, item_type, event_type, status,
                discord_webhook, error_message, processing_time_ms, metadata_json
            ))
            conn.commit()
    
    async def get_recent_notifications(self, limit: int = 20, hours: int = 4) -> list:
        """
        Get recent notifications with their delivery status.
        Default: last 4 hours, max 20 items.
        """
        import json
        from datetime import datetime, timedelta
        
        if not self.initialized:
            await self.initialize()
        
        # Calculate cutoff time (default 4 hours)
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT 
                    item_id as id,
                    item_name as name,
                    item_type as type,
                    event_type as event,
                    status,
                    discord_webhook,
                    error_message,
                    timestamp,
                    processing_time_ms,
                    metadata
                FROM notification_history
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (cutoff_time, limit))
            
            notifications = []
            for row in cursor:
                notification = {
                    "id": row['id'],
                    "name": row['name'],
                    "type": row['type'],
                    "event": row['event'],
                    "status": row['status'],
                    "discord_webhook": row['discord_webhook'],
                    "error_message": row['error_message'],
                    "timestamp": row['timestamp'],
                    "processing_time_ms": row['processing_time_ms']
                }
                
                # Parse metadata if present
                if row['metadata']:
                    try:
                        notification['metadata'] = json.loads(row['metadata'])
                    except:
                        pass
                
                notifications.append(notification)
        
        return notifications
    
    async def add_notification_to_history(self, 
                                         item_id: str,
                                         item_name: str,
                                         item_type: str,
                                         event_type: str,
                                         discord_webhook: str = None,
                                         status: str = 'pending',
                                         error_message: str = None,
                                         processing_time_ms: int = None,
                                         metadata: dict = None):
        """
        Add a notification to the history table for tracking and display.
        
        Args:
            item_id: Jellyfin item ID
            item_name: Name of the item
            item_type: Type of media (Movie, Episode, etc.)
            event_type: Type of event (new, upgraded, deleted)
            discord_webhook: Webhook URL used (optional)
            status: Status of notification (pending, sent, failed)
            error_message: Error message if failed
            processing_time_ms: Processing time in milliseconds
            metadata: Additional metadata as dict
        """
        import json
        from datetime import datetime
        
        if not self.initialized:
            await self.initialize()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO notification_history 
                (item_id, item_name, item_type, event_type, discord_webhook, 
                 status, error_message, processing_time_ms, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (item_id, item_name, item_type, event_type, discord_webhook,
                  status, error_message, processing_time_ms, metadata_json, datetime.now()))
            
            conn.commit()
        
        logger.debug(f"Added notification to history: {item_name} ({event_type}) - Status: {status}")
        
        # Also update channel routing statistics if notification was sent successfully
        if status == "sent" and discord_webhook:
            await self._update_channel_routing_stats(discord_webhook, item_type)
    
    async def update_notification_status(self, item_id: str, status: str, error_message: str = None):
        """Update the status of a notification in history"""
        from datetime import datetime
        
        if not self.initialized:
            await self.initialize()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE notification_history
                SET status = ?, error_message = ?, sent_at = ?
                WHERE item_id = ? AND sent_at IS NULL
                ORDER BY timestamp DESC
                LIMIT 1
            """, (status, error_message, datetime.now() if status == 'sent' else None, item_id))
            
            conn.commit()
    
    async def cleanup_old_notifications(self, days: int = 7):
        """Remove notification history older than specified days"""
        from datetime import datetime, timedelta
        
        if not self.initialized:
            await self.initialize()
        
        cutoff_time = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM notification_history
                WHERE timestamp < ?
            """, (cutoff_time,))
            
            conn.commit()
            
            if cursor.rowcount > 0:
                logger.info(f"Cleaned up {cursor.rowcount} old notification records")
    
    # ==================== User Management Methods ====================
    # These methods are used by web_api.py for authentication
    
    @staticmethod
    def _generate_salt() -> str:
        """Generate a random salt for password hashing"""
        import secrets
        return secrets.token_hex(32)
    
    @staticmethod
    def _hash_password_with_salt(password: str, salt: str) -> str:
        """Hash password with salt using bcrypt"""
        import bcrypt
        # Combine password and salt, then hash with bcrypt
        salted_password = f"{password}{salt}".encode('utf-8')
        return bcrypt.hashpw(salted_password, bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def _verify_password_with_salt(password: str, salt: str, password_hash: str) -> bool:
        """Verify password against hash with salt"""
        import bcrypt
        salted_password = f"{password}{salt}".encode('utf-8')
        return bcrypt.checkpw(salted_password, password_hash.encode('utf-8'))
    
    async def create_user(self, username: str, password: str, email: Optional[str] = None, is_admin: bool = False) -> int:
        """Create a new user with salt and hash"""
        salt = self._generate_salt()
        hashed_password = self._hash_password_with_salt(password, salt)
        
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            try:
                cursor = await db.execute(
                    "INSERT INTO users (username, email, password_hash, salt, is_admin) VALUES (?, ?, ?, ?, ?)",
                    (username, email, hashed_password, salt, is_admin)
                )
                await db.commit()
                return cursor.lastrowid
            except aiosqlite.IntegrityError:
                raise ValueError(f"Username {username} already exists")
    
    async def verify_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user credentials with salt"""
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM users WHERE username = ? AND is_active = 1",
                (username,)
            )
            user = await cursor.fetchone()
            
            if user and self._verify_password_with_salt(password, user["salt"], user["password_hash"]):
                # Update last login
                await db.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                    (user["id"],)
                )
                await db.commit()
                return dict(user)
            
            return None
    
    async def update_user_password(self, user_id: int, new_password: str):
        """Update user password with new salt"""
        salt = self._generate_salt()
        hashed_password = self._hash_password_with_salt(new_password, salt)
        
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
                (hashed_password, salt, user_id)
            )
            await db.commit()
    
    async def save_refresh_token(self, user_id: int, token: str, expires_at):
        """Save refresh token to database"""
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO sessions (user_id, refresh_token, expires_at) VALUES (?, ?, ?)",
                (user_id, token, expires_at.isoformat())
            )
            await db.commit()
    
    async def verify_refresh_token(self, token: str) -> Optional[int]:
        """Verify refresh token and return user_id if valid"""
        import aiosqlite
        from datetime import datetime, timezone
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id, expires_at FROM sessions WHERE refresh_token = ?",
                (token,)
            )
            row = await cursor.fetchone()
            
            if row:
                user_id, expires_at = row
                if datetime.fromisoformat(expires_at) > datetime.now(timezone.utc):
                    return user_id
                else:
                    # Clean up expired token
                    await db.execute("DELETE FROM sessions WHERE refresh_token = ?", (token,))
                    await db.commit()
            
            return None
    
    async def _update_channel_routing_stats(self, discord_webhook: str, item_type: str = None):
        """Update channel routing statistics based on webhook URL"""
        from datetime import datetime, timezone
        
        # Determine which channel was used based on webhook URL
        channel_field = None
        if discord_webhook:
            if 'movies' in discord_webhook.lower() or 'Fj6s' in discord_webhook:
                channel_field = "sent_to_movies"
            elif 'tv' in discord_webhook.lower() or 'sQl2' in discord_webhook:
                channel_field = "sent_to_tv"
            elif 'music' in discord_webhook.lower():
                channel_field = "sent_to_music"
            else:
                channel_field = "sent_to_default"
        
        if channel_field:
            now = datetime.now(timezone.utc)
            hour_bucket = now.strftime("%Y-%m-%d %H:00")  # Fixed format to match database
            day_bucket = now.strftime("%Y-%m-%d")
            
            import aiosqlite
            async with aiosqlite.connect(self.db_path) as db:
                # First, try to insert a new record for this hour
                try:
                    await db.execute(
                        """INSERT INTO notification_stats (hour_bucket, day_bucket) 
                           VALUES (?, ?)""",
                        (hour_bucket, day_bucket)
                    )
                except:
                    # Record already exists for this hour, that's fine
                    pass
                
                # Update the channel routing counter
                await db.execute(
                    f"UPDATE notification_stats SET {channel_field} = {channel_field} + 1 WHERE hour_bucket = ?",
                    (hour_bucket,)
                )
                
                # Also update content type counter
                if item_type:
                    if item_type.lower() == "movie":
                        await db.execute(
                            "UPDATE notification_stats SET movies = movies + 1 WHERE hour_bucket = ?",
                            (hour_bucket,)
                        )
                    elif item_type.lower() in ["series", "episode"]:
                        await db.execute(
                            "UPDATE notification_stats SET tv_shows = tv_shows + 1 WHERE hour_bucket = ?",
                            (hour_bucket,)
                        )
                    elif item_type.lower() == "music":
                        await db.execute(
                            "UPDATE notification_stats SET music = music + 1 WHERE hour_bucket = ?",
                            (hour_bucket,)
                        )
                
                await db.commit()
                logger.debug(f"Updated channel routing stats: {channel_field} for {item_type}")
    
    async def update_notification_stats(self, stat_type: str, content_type: Optional[str] = None, count: int = 1):
        """Update notification statistics for the current hour"""
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        hour_bucket = now.strftime("%Y-%m-%d %H:00")  # Fixed format to be consistent
        day_bucket = now.strftime("%Y-%m-%d")
        
        import aiosqlite
        async with aiosqlite.connect(self.db_path) as db:
            # First, try to insert a new record for this hour
            try:
                await db.execute(
                    """INSERT INTO notification_stats (hour_bucket, day_bucket) 
                       VALUES (?, ?)""",
                    (hour_bucket, day_bucket)
                )
            except:
                # Record already exists for this hour, that's fine
                pass
            
            # Update the appropriate counter
            if stat_type == "sent":
                await db.execute(
                    "UPDATE notification_stats SET notifications_sent = notifications_sent + ? WHERE hour_bucket = ?",
                    (count, hour_bucket)
                )
            elif stat_type == "failed":
                await db.execute(
                    "UPDATE notification_stats SET notifications_failed = notifications_failed + ? WHERE hour_bucket = ?",
                    (count, hour_bucket)
                )
            elif stat_type == "new":
                await db.execute(
                    "UPDATE notification_stats SET new_items = new_items + ? WHERE hour_bucket = ?",
                    (count, hour_bucket)
                )
            elif stat_type == "upgraded":
                await db.execute(
                    "UPDATE notification_stats SET upgraded_items = upgraded_items + ? WHERE hour_bucket = ?",
                    (count, hour_bucket)
                )
            elif stat_type == "deleted":
                await db.execute(
                    "UPDATE notification_stats SET deleted_items = deleted_items + ? WHERE hour_bucket = ?",
                    (count, hour_bucket)
                )
            elif stat_type == "mass_rename":
                await db.execute(
                    "UPDATE notification_stats SET mass_renames_caught = mass_renames_caught + ? WHERE hour_bucket = ?",
                    (count, hour_bucket)
                )
            
            # Update content type counters if provided
            if content_type:
                if content_type.lower() == "movie":
                    await db.execute(
                        "UPDATE notification_stats SET movies = movies + ? WHERE hour_bucket = ?",
                        (count, hour_bucket)
                    )
                elif content_type.lower() in ["series", "episode"]:
                    await db.execute(
                        "UPDATE notification_stats SET tv_shows = tv_shows + ? WHERE hour_bucket = ?",
                        (count, hour_bucket)
                    )
                elif content_type.lower() == "music":
                    await db.execute(
                        "UPDATE notification_stats SET music = music + ? WHERE hour_bucket = ?",
                        (count, hour_bucket)
                    )
            
            await db.commit()
    
    async def save_jellyfin_stats(self, stats: Dict[str, Any]) -> None:
        """
        Save Jellyfin server statistics to the database.
        
        Args:
            stats: Dictionary containing server statistics
        """
        import json
        from datetime import datetime, timezone
        import aiosqlite
        
        async with aiosqlite.connect(self.db_path) as db:
            # Prepare JSON fields
            library_stats = json.dumps(stats.get('library_stats', {}))
            plugin_stats = json.dumps(stats.get('plugin_stats', {}))
            system_info = json.dumps(stats.get('system_info', {}))
            
            await db.execute("""
                INSERT INTO jellyfin_stats (
                    server_name, server_version, server_id, server_status,
                    total_users, active_users,
                    movie_count, series_count, season_count, episode_count,
                    music_count, music_album_count, photo_count, book_count,
                    total_items, library_stats, plugin_stats, system_info,
                    last_check
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                stats.get('server_name'),
                stats.get('server_version'),
                stats.get('server_id'),
                stats.get('server_status', 'online'),
                stats.get('total_users', 0),
                stats.get('active_users', 0),
                stats.get('movie_count', 0),
                stats.get('series_count', 0),
                stats.get('season_count', 0),
                stats.get('episode_count', 0),
                stats.get('music_count', 0),
                stats.get('music_album_count', 0),
                stats.get('photo_count', 0),
                stats.get('book_count', 0),
                stats.get('total_items', 0),
                library_stats,
                plugin_stats,
                system_info,
                datetime.now(timezone.utc).isoformat()
            ))
            await db.commit()
            logger.debug(f"Saved Jellyfin stats: {stats.get('total_items', 0)} total items, {stats.get('season_count', 0)} seasons")
    
    async def get_latest_jellyfin_stats(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent Jellyfin server statistics.
        
        Returns:
            Dictionary with server stats or None if not available
        """
        import json
        import aiosqlite
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM jellyfin_stats 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            row = await cursor.fetchone()
            
            if row:
                stats = dict(row)
                # Parse JSON fields
                if stats.get('library_stats'):
                    try:
                        stats['library_stats'] = json.loads(stats['library_stats'])
                    except:
                        stats['library_stats'] = {}
                if stats.get('plugin_stats'):
                    try:
                        stats['plugin_stats'] = json.loads(stats['plugin_stats'])
                    except:
                        stats['plugin_stats'] = {}
                if stats.get('system_info'):
                    try:
                        stats['system_info'] = json.loads(stats['system_info'])
                    except:
                        stats['system_info'] = {}
                logger.debug(f"Retrieved Jellyfin stats from database: {stats.get('total_items', 0)} items, {stats.get('season_count', 0)} seasons")
                return stats
            return None