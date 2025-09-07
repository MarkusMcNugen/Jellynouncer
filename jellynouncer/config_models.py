#!/usr/bin/env python3
"""
Jellynouncer Configuration Models and Validation

This module contains all Pydantic configuration models and the configuration
validation logic for the Jellynouncer application. It demonstrates advanced
data modeling and validation techniques using Pydantic, one of Python's most
powerful data validation libraries.

**Understanding Configuration Architecture:**
    Large applications need structured configuration management. This module
    implements a hierarchical configuration system where:
    - Each component has its own configuration model
    - Models validate data automatically and provide helpful error messages
    - Environment variables can override file-based configuration
    - All settings are type-safe and documented

**Why Pydantic for Configuration?**
    Pydantic provides automatic type conversion, validation, and clear error
    messages. It's like having a smart assistant that checks your configuration
    and tells you exactly what's wrong if something doesn't match.

Classes:
    Configuration Models:
        JellyfinConfig: Jellyfin server connection settings
        WebhookConfig: Individual Discord webhook configuration
        DiscordConfig: Overall Discord integration settings
        DatabaseConfig: SQLite database configuration
        TemplatesConfig: Jinja2 template file settings
        NotificationsConfig: Notification behavior settings
        ServerConfig: FastAPI web server configuration
        SyncConfig: Library synchronization settings
        MetadataServiceConfig: External metadata service settings
        TVDBConfig: Enhanced TVDB-specific settings
        AppConfig: Top-level application configuration

    Validation:
        ConfigurationValidator: Comprehensive configuration loading and validation

    Author: Mark Newton
    Project: Jellynouncer
    Version: 1.0.0
    License: MIT
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

import yaml
from pydantic import BaseModel, Field, ConfigDict, ValidationError, field_validator, model_validator
from .utils import get_logger


# ==================== JELLYFIN CONFIGURATION ====================

class JellyfinConfig(BaseModel):
    """
    Configuration model for Jellyfin server connection settings.

    This model handles all the settings needed to connect to and authenticate
    with a Jellyfin media server. It includes automatic URL validation and
    normalization to prevent common configuration mistakes.

    **Understanding Pydantic Models:**
        Pydantic models are classes that automatically validate data when you
        create them. If you try to create a JellyfinConfig with an invalid
        URL, Pydantic will immediately tell you what's wrong instead of failing
        later when the application tries to use it.

    **Field Validation Benefits:**
        Each field can have custom validation logic. For example, server_url
        is automatically normalized (trailing slashes removed) and validated
        to ensure it's a proper HTTP/HTTPS URL.

    Attributes:
        server_url (str): Jellyfin server URL (required, validated for proper format)
        api_key (str): Jellyfin API key for authentication (required)
        user_id (str): Jellyfin user ID for personalized access (required)
        client_name (str): How this app identifies itself to Jellyfin
        client_version (str): Version reported to Jellyfin
        device_name (str): Device name reported to Jellyfin
        device_id (str): Unique device identifier for this instance

    Example:
        ```python
        # Valid configuration
        config = JellyfinConfig(
            server_url="http://localhost:8096",
            api_key="your-api-key-here",
            user_id="user-id-from-jellyfin"
        )

        # This would raise a validation error:
        # JellyfinConfig(server_url="not-a-url", api_key="", user_id="")
        ```
    """
    # Configuration for Pydantic model behavior
    model_config = ConfigDict(
        extra='forbid',           # Don't allow unknown fields
        str_strip_whitespace=True # Automatically strip whitespace from strings
    )

    # Required fields with validation
    server_url: str = Field(..., description="Jellyfin server URL")
    api_key: str = Field(..., description="Jellyfin API key")
    user_id: str = Field(..., description="Jellyfin user ID")

    # Optional fields with defaults
    client_name: str = Field(default="Jellynouncer-Discord-Webhook")
    client_version: str = Field(default="1.0.0")
    device_name: str = Field(default="jellynouncer-webhook-service")
    device_id: str = Field(default="jellynouncer-discord-webhook-001")

    # noinspection PyDecorator
    @field_validator('server_url')
    @classmethod
    def validate_server_url(cls, v: str) -> str:
        """
        Validate and normalize Jellyfin server URL.

        This custom validator ensures the server URL is properly formatted
        and follows expected patterns. It also normalizes the URL by removing
        trailing slashes to prevent double-slash issues in API calls.

        **Understanding Class Methods in Validators:**
            The @classmethod decorator means this method is called on the class
            itself, not on an instance. Pydantic calls these validators
            automatically during object creation.

        Args:
            v (str): The server URL to validate

        Returns:
            str: Normalized and validated server URL

        Raises:
            ValueError: If URL is empty, improperly formatted, or uses wrong protocol

        Example:
            ```python
            # These URLs get normalized:
            "http://localhost:8096/" -> "http://localhost:8096"
            "https://jellyfin.example.com//" -> "https://jellyfin.example.com"

            # These would raise ValueError:
            "" (empty string)
            "localhost:8096" (missing protocol)
            "ftp://jellyfin.example.com" (wrong protocol)
            ```
        """
        if not v:
            raise ValueError("Jellyfin server URL cannot be empty")

        # Parse URL to validate structure using Python's built-in urlparse
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid Jellyfin server URL format: {v}")

        # Ensure we're using HTTP or HTTPS (security requirement)
        if parsed.scheme not in ['http', 'https']:
            raise ValueError(f"Jellyfin server URL must use http or https: {v}")

        # Remove trailing slash to prevent double slashes in API calls
        # "http://localhost:8096/" becomes "http://localhost:8096"
        return v.rstrip('/')

    # noinspection PyDecorator
    @field_validator('api_key', 'user_id')
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """
        Validate that required string fields are not empty or just whitespace.

        This validator ensures critical authentication fields actually contain
        meaningful data, not just empty strings or whitespace.

        **Understanding Multiple Field Validation:**
            By listing multiple field names in the decorator, we can use the
            same validation logic for multiple fields. This reduces code
            duplication and ensures consistency.

        Args:
            v (str): The string value to validate

        Returns:
            str: Trimmed string value

        Raises:
            ValueError: If field is empty or contains only whitespace
        """
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


# ==================== DISCORD CONFIGURATION ====================

class WebhookConfig(BaseModel):
    """
    Configuration for individual Discord webhooks.

    This model represents a single Discord webhook configuration. The application
    can use multiple webhooks to send different types of content to different
    Discord channels (e.g., movies to one channel, TV shows to another).

    **Understanding Webhook Routing:**
        Webhooks are Discord's way of allowing external applications to send
        messages to channels. Each webhook has a unique URL that acts like
        an address where messages should be delivered.

    Attributes:
        url (Optional[str]): Discord webhook URL (None if not configured)
        name (str): Human-readable name for this webhook (required)
        enabled (bool): Whether this webhook should receive notifications
        grouping (Dict[str, Any]): Configuration for notification grouping behavior

    Example:
        ```python
        # Movie channel webhook
        movie_webhook = WebhookConfig(
            url="https://discord.com/api/webhooks/123456/abcdef",
            name="Movies Channel",
            enabled=True,
            grouping={"mode": "type", "delay_minutes": 5}
        )

        # Disabled webhook (won't receive notifications)
        disabled_webhook = WebhookConfig(
            name="Test Channel",
            enabled=False
        )
        ```
    """
    model_config = ConfigDict(extra='forbid')

    url: Optional[str] = Field(default=None, description="Discord webhook URL")
    name: str = Field(..., description="Webhook display name")
    enabled: bool = Field(default=False, description="Whether webhook is enabled")
    grouping: Dict[str, Any] = Field(default_factory=dict, description="Grouping configuration")

    # noinspection PyDecorator
    @field_validator('url')
    @classmethod
    def validate_webhook_url(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate Discord webhook URL format.

        Discord webhooks must follow a specific URL pattern. This validator
        ensures the URL is correctly formatted to prevent runtime errors when
        trying to send notifications.

        **Understanding Optional Validation:**
            Since webhook URLs are optional (you might configure them later),
            we need to handle None values gracefully while still validating
            URLs that are provided.

        Args:
            v (Optional[str]): Webhook URL to validate (can be None)

        Returns:
            Optional[str]: Validated webhook URL or None

        Raises:
            ValueError: If URL doesn't match Discord webhook pattern

        Example:
            ```python
            # Valid Discord webhook URLs:
            "https://discord.com/api/webhooks/123456789/abcdefghijk"

            # Invalid URLs (would raise ValueError):
            "https://example.com/webhook"
            "http://discord.com/api/webhooks/123/abc" (not HTTPS)
            ```
        """
        # Handle None and empty string cases
        if v is None:
            return None
        if not v.strip():
            return None

        v = v.strip()

        # Discord webhooks always follow this specific URL pattern
        if not v.startswith('https://discord.com/api/webhooks/'):
            raise ValueError(
                f"Discord webhook URL must start with 'https://discord.com/api/webhooks/': {v}"
            )

        return v


class DiscordConfig(BaseModel):
    """
    Overall Discord integration configuration.

    This model manages all Discord-related settings including multiple webhooks,
    routing rules for different content types, and rate limiting parameters.

    **Understanding Configuration Composition:**
        Instead of putting all Discord settings in one flat structure, we
        organize them into logical groups. This makes the configuration easier
        to understand and maintain as the application grows.

    Attributes:
        webhooks (Dict[str, WebhookConfig]): Dictionary of webhook configurations by name
        routing (Dict[str, Any]): Rules for routing content to different webhooks
        rate_limit (Dict[str, Any]): Rate limiting parameters for Discord API calls

    Example:
        ```python
        discord_config = DiscordConfig(
            webhooks={
                "movies": WebhookConfig(name="Movies", enabled=True, url="..."),
                "tv": WebhookConfig(name="TV Shows", enabled=True, url="..."),
                "music": WebhookConfig(name="Music", enabled=False)
            },
            routing={
                "enabled": True,
                "fallback_webhook": "movies"
            },
            rate_limit={
                "requests_per_minute": 30,
                "burst_size": 5
            }
        )
        ```
    """
    model_config = ConfigDict(extra='forbid')

    webhooks: Dict[str, WebhookConfig] = Field(default_factory=dict)
    routing: Dict[str, Any] = Field(default_factory=dict)
    rate_limit: Dict[str, Any] = Field(default_factory=dict)


# ==================== DATABASE CONFIGURATION ====================

class DatabaseConfig(BaseModel):
    """
    SQLite database configuration and validation.

    This model handles database-related settings and validates that the
    database path is writable and the parent directory exists or can be created.
    It also manages performance-related database settings.

    **Understanding Database Configuration:**
        SQLite is a file-based database, so we need to ensure the file path
        is valid and writable. We also configure performance settings like
        WAL mode (Write-Ahead Logging) which allows better concurrent access.

    **Why Path Validation Matters:**
        Database path validation prevents runtime errors. It's better to fail
        fast during startup with a clear error message than to fail later when
        the application tries to write to an invalid path.

    Attributes:
        path (str): File path where SQLite database will be stored
        wal_mode (bool): Enable WAL mode for better concurrent access
        vacuum_interval_hours (int): How often to optimize database (1-168 hours)

    Example:
        ```python
        # Default configuration
        db_config = DatabaseConfig()  # Uses default path and settings

        # Custom configuration
        db_config = DatabaseConfig(
            path="/custom/path/jellynouncer.db",
            wal_mode=True,
            vacuum_interval_hours=24
        )
        ```
    """
    model_config = ConfigDict(extra='forbid')

    path: str = Field(default="/app/data/jellyfin_items.db")
    wal_mode: bool = Field(default=True)
    vacuum_interval_hours: int = Field(default=24, ge=1, le=168)  # 1 hour to 1 week

    # noinspection PyDecorator
    @field_validator('path')
    @classmethod
    def validate_db_path(cls, v: str) -> str:
        """
        Validate database path and ensure parent directory is writable.

        This validator performs several important checks:
        1. Ensures the path is not empty
        2. Creates parent directories if they don't exist
        3. Verifies write permissions on the parent directory

        **Understanding File System Validation:**
            Database files need a place to live, and we need permission to
            write to that location. This validator ensures both conditions
            are met before the application starts.

        Args:
            v (str): Database file path to validate

        Returns:
            str: Validated database path

        Raises:
            ValueError: If path is invalid or parent directory isn't writable

        Example:
            ```python
            # These paths would be validated and parent dirs created if needed:
            "/app/data/database.db"
            "/var/lib/jellynouncer/db.sqlite"

            # These would raise ValueError:
            "" (empty path)
            "/root/database.db" (if not running as root)
            ```
        """
        if not v:
            raise ValueError("Database path cannot be empty")

        path = Path(v)
        parent_dir = path.parent

        # Try to create parent directory if it doesn't exist
        try:
            parent_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            raise ValueError(f"Cannot create database directory {parent_dir}: {e}")

        # Check write permissions on parent directory
        if not os.access(parent_dir, os.W_OK):
            raise ValueError(f"No write permission for database directory: {parent_dir}")

        return str(path)


# ==================== TEMPLATE CONFIGURATION ====================

class TemplatesConfig(BaseModel):
    """
    Configuration for Jinja2 template files used to format Discord messages.

    This model manages paths to various template files used for different
    notification types. Templates allow customizing the appearance and content
    of Discord embed messages without changing code.

    **Understanding Template-Based Configuration:**
        Templates separate presentation from logic. Instead of hardcoding
        message formats in Python, we use Jinja2 templates that can be
        modified without changing the application code.

    **Template Types Explained:**
        - new_item: For completely new media items
        - upgraded_item: For existing items that got upgraded (better quality, etc.)
        - deleted_item: For items removed from the library
        - grouped templates: For batching multiple notifications together
        - by_event/by_type: Different grouping strategies

    Attributes:
        directory (str): Base directory containing template files
        Various template filenames for different notification types

    Example:
        ```python
        templates = TemplatesConfig(
            directory="/custom/templates",
            new_item_template="custom_new_item.j2",
            upgraded_item_template="custom_upgrade.j2"
        )
        ```
    """
    model_config = ConfigDict(extra='forbid')

    directory: str = Field(default="/app/templates")
    new_item_template: str = Field(default="new_item.j2")
    upgraded_item_template: str = Field(default="upgraded_item.j2")
    deleted_item_template: str = Field(default="deleted_item.j2")
    new_items_by_event_template: str = Field(default="new_items_by_event.j2")
    upgraded_items_by_event_template: str = Field(default="upgraded_items_by_event.j2")
    new_items_by_type_template: str = Field(default="new_items_by_type.j2")
    upgraded_items_by_type_template: str = Field(default="upgraded_items_by_type.j2")
    new_items_grouped_template: str = Field(default="new_items_grouped.j2")
    upgraded_items_grouped_template: str = Field(default="upgraded_items_grouped.j2")

    # noinspection PyDecorator
    @field_validator('directory')
    @classmethod
    def validate_template_directory(cls, v: str) -> str:
        """
        Validate that template directory exists and is readable.

        Template validation ensures the application can find and read the
        template files it needs. This prevents runtime errors when trying
        to render notifications.

        **Understanding Read Permission Checks:**
            Unlike database paths (which need write permission), template
            directories only need read permission since we're just reading
            template files, not modifying them.

        Args:
            v (str): Template directory path

        Returns:
            str: Validated directory path

        Raises:
            ValueError: If directory doesn't exist or isn't readable

        Example:
            ```python
            # Valid template directories:
            "/app/templates" (default)
            "/custom/notification/templates"

            # Invalid directories (would raise ValueError):
            "" (empty path)
            "/nonexistent/path"
            "/etc/passwd" (file, not directory)
            ```
        """
        if not v:
            raise ValueError("Template directory cannot be empty")

        path = Path(v)

        # Check that path exists
        if not path.exists():
            raise ValueError(f"Template directory does not exist: {path}")

        # Check that it's actually a directory, not a file
        if not path.is_dir():
            raise ValueError(f"Template path is not a directory: {path}")

        # Check read permissions
        if not os.access(path, os.R_OK):
            raise ValueError(f"No read permission for template directory: {path}")

        return str(path)


# ==================== NOTIFICATION CONFIGURATION ====================

class NotificationsConfig(BaseModel):
    """
    Configuration for notification behavior and appearance.

    This model controls which types of changes trigger notifications and what
    colors are used for different notification types. It's the central place
    for customizing notification behavior.

    **Understanding Change Monitoring:**
        Not all changes are interesting - we only want to notify users about
        meaningful changes like resolution upgrades or new content. This
        configuration lets you fine-tune what triggers notifications.

    **Color Coding Strategy:**
        Different types of notifications use different colors to help users
        quickly understand what happened. Colors are specified as integers
        representing hex color codes.

    Attributes:
        watch_changes (Dict[str, bool]): Which change types to monitor
        colors (Dict[str, int]): Color codes for different notification types

    Example:
        ```python
        notifications = NotificationsConfig(
            watch_changes={
                "resolution": True,      # Monitor resolution changes
                "video_codec": True,     # Monitor video codec changes
                "audio_codec": False,   # Ignore audio codec changes
                "audio_channels": True,  # Monitor audio channel changes
                "hdr_status": True,     # Monitor HDR changes
                "file_size": False,     # Ignore file size changes
                "subtitles": True       # Monitor subtitle changes
            },
            colors={
                "new_item": 0x00FF00,           # Green for new items
                "resolution_upgrade": 0xFFD700, # Gold for resolution upgrades
                "codec_upgrade": 0xFF8C00,      # Orange for codec upgrades
                "hdr_upgrade": 0xFF1493         # Pink for HDR upgrades
            }
        )
        ```
    """
    model_config = ConfigDict(extra='forbid')

    watch_changes: Dict[str, bool] = Field(default_factory=dict)
    colors: Dict[str, int] = Field(default_factory=dict)
    filter_renames: bool = Field(default=True, description="Filter out notifications for file renames (same content, different path)")
    filter_deletes: bool = Field(default=True, description="Filter out delete notifications for upgrades (delete followed by add of same item)")


# ==================== BACKUP CONFIGURATION ====================

class BackupConfig(BaseModel):
    """
    Backup and restore configuration settings.
    
    This model controls automated backup scheduling, retention policies,
    and what components are included in backups.
    
    Attributes:
        enabled (bool): Enable automatic backups
        backup_dir (str): Directory to store backup files
        schedule (str): Backup schedule (hourly, daily, weekly, disabled)
        backup_time (str): Time for daily/weekly backups (HH:MM format)
        retention_days (int): Days to retain backups before deletion
        max_backups (int): Maximum number of backups to keep
        compress (bool): Compress backup archives with gzip
        backup_config (bool): Include configuration files in backups
        backup_database (bool): Include database in backups
        backup_templates (bool): Include templates in backups
        backup_ssl (bool): Include SSL certificates in backups
        backup_logs (bool): Include log files in backups
        auto_backup_before_upgrade (bool): Automatically backup before upgrades
        notification_on_success (bool): Send notification on successful backup
        notification_on_failure (bool): Send notification on backup failure
    """
    model_config = ConfigDict(extra='forbid')
    
    enabled: bool = Field(default=True, description="Enable automatic backups")
    backup_dir: str = Field(default="data/backups", description="Backup directory path")
    schedule: str = Field(default="daily", description="Backup schedule: hourly, daily, weekly, disabled")
    backup_time: str = Field(default="02:00", description="Time for daily/weekly backups (HH:MM)")
    retention_days: int = Field(default=30, ge=1, description="Days to retain backups")
    max_backups: int = Field(default=10, ge=1, description="Maximum number of backups to keep")
    compress: bool = Field(default=True, description="Compress backup archives")
    backup_config: bool = Field(default=True, description="Include configuration in backups")
    backup_database: bool = Field(default=True, description="Include database in backups")
    backup_templates: bool = Field(default=True, description="Include templates in backups")
    backup_ssl: bool = Field(default=False, description="Include SSL certificates in backups")
    backup_logs: bool = Field(default=False, description="Include logs in backups")
    auto_backup_before_upgrade: bool = Field(default=True, description="Automatically backup before upgrades")
    notification_on_success: bool = Field(default=False, description="Send notification on successful backup")
    notification_on_failure: bool = Field(default=True, description="Send notification on backup failure")
    
    @field_validator('schedule')
    @classmethod
    def validate_schedule(cls, v: str) -> str:
        """Validate backup schedule"""
        valid_schedules = ['hourly', 'daily', 'weekly', 'disabled']
        if v.lower() not in valid_schedules:
            raise ValueError(f"Schedule must be one of: {', '.join(valid_schedules)}")
        return v.lower()
    
    @field_validator('backup_time')
    @classmethod
    def validate_backup_time(cls, v: str) -> str:
        """Validate backup time format (HH:MM)"""
        try:
            hour, minute = v.split(':')
            hour = int(hour)
            minute = int(minute)
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
            return f"{hour:02d}:{minute:02d}"
        except:
            raise ValueError("Backup time must be in HH:MM format (e.g., 02:00)")


# ==================== SERVER CONFIGURATION ====================

class ServerConfig(BaseModel):
    """
    FastAPI web server configuration.

    This model controls how the web server runs, including bind address, port,
    and logging level. These settings affect how the application listens for
    incoming webhook requests from Jellyfin.

    **Understanding Network Configuration:**
        - host: Which network interface to bind to (0.0.0.0 = all interfaces)
        - port: Which TCP port to listen on for incoming requests
        - log_level: How verbose the logging should be

    Attributes:
        host (str): IP address to bind to ("0.0.0.0" for all interfaces)
        port (int): TCP port to listen on (1024-65535, avoiding system ports)
        log_level (str): Python logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Example:
        ```python
        # Default configuration (listens on all interfaces, port 1984)
        server = ServerConfig()

        # Custom configuration
        server = ServerConfig(
            host="127.0.0.1",  # Only localhost
            port=9000,         # Custom port
            log_level="DEBUG"  # Verbose logging
        )
        ```
    """
    model_config = ConfigDict(extra='forbid')

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=1984, ge=1024, le=65535)  # Avoid system ports (<1024)
    log_level: str = Field(default="INFO")
    run_mode: str = Field(default="all", description="Which services to run: all, webhook, or web")
    data_dir: str = Field(default="/app/data", description="Directory for application data")
    log_dir: str = Field(default="/app/logs", description="Directory for log files")
    environment: str = Field(default="production", description="Environment mode: production or development")
    development_mode: bool = Field(default=False, description="Enable development features like auto-reload")
    show_docker_interfaces: bool = Field(default=False, description="Show Docker network interfaces in startup messages")
    allowed_hosts: List[str] = Field(default_factory=list, description="Allowed hosts for security (empty = allow all)")
    force_color_output: bool = Field(default=False, description="Force colored console output even without TTY")
    disable_color_output: bool = Field(default=False, description="Disable all colored console output")

    # noinspection PyDecorator
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """
        Validate logging level against Python's standard levels.

        Python's logging module has specific level names. This validator
        ensures only valid levels are used and normalizes them to uppercase.

        **Understanding Python Logging Levels:**
            - DEBUG: Very detailed information, typically only of interest when diagnosing problems
            - INFO: Confirmation that things are working as expected
            - WARNING: An indication that something unexpected happened
            - ERROR: A serious problem occurred, the software couldn't perform some function
            - CRITICAL: A very serious error occurred, the program itself may be unable to continue

        Args:
            v (str): Log level string (case insensitive)

        Returns:
            str: Uppercase log level string

        Raises:
            ValueError: If log level is not recognized

        Example:
            ```python
            # These are all valid and get normalized to uppercase:
            "debug" -> "DEBUG"
            "Info" -> "INFO"
            "WARNING" -> "WARNING"

            # This would raise ValueError:
            "VERBOSE" (not a standard Python log level)
            ```
        """
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v
    
    # noinspection PyDecorator
    @field_validator('run_mode')
    @classmethod
    def validate_run_mode(cls, v: str) -> str:
        """Validate run mode is one of the allowed values."""
        valid_modes = ['all', 'both', 'webhook', 'web']
        v_lower = v.lower()
        if v_lower not in valid_modes:
            raise ValueError(f"Invalid run mode: {v}. Must be one of {valid_modes}")
        return v_lower
    
    # noinspection PyDecorator
    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is either production or development."""
        valid_envs = ['production', 'development']
        v_lower = v.lower()
        if v_lower not in valid_envs:
            raise ValueError(f"Invalid environment: {v}. Must be one of {valid_envs}")
        return v_lower



# ==================== WEB INTERFACE CONFIGURATION ====================

class WebInterfaceConfig(BaseModel):
    """
    Web interface configuration for the management UI.
    
    Controls the web-based management interface that allows configuration
    and monitoring of the Jellynouncer service.
    
    Attributes:
        enabled (bool): Whether the web interface is enabled
        port (int): Port for the web interface (default: 1985)
        host (str): Host to bind the web interface to
        jwt_secret (Optional[str]): Secret key for JWT tokens (auto-generated if None)
        auth_enabled (bool): Whether authentication is required
        username (Optional[str]): Username for basic auth
        password (Optional[str]): Password for basic auth
        ssl_enabled (bool): Whether SSL/HTTPS is enabled
        ssl_cert_path (Optional[str]): Path to SSL certificate file
        ssl_key_path (Optional[str]): Path to SSL private key file
        ssl_port (int): Port for HTTPS connections (default: 9000)
    """
    model_config = ConfigDict(extra='forbid')
    
    enabled: bool = Field(default=True, description="Enable web management interface")
    port: int = Field(default=1985, ge=1024, le=65535, description="HTTP port for web interface")
    host: str = Field(default="0.0.0.0", description="Host to bind web interface to")
    jwt_secret: Optional[str] = Field(default=None, description="Secret for JWT tokens (auto-generated if None)")
    auth_enabled: bool = Field(default=False, description="Require authentication for web interface")
    username: Optional[str] = Field(default=None, description="Basic auth username")
    password: Optional[str] = Field(default=None, description="Basic auth password")
    ssl_enabled: bool = Field(default=False, description="Enable HTTPS for web interface")
    ssl_cert_path: Optional[str] = Field(default=None, description="Path to SSL certificate file")
    ssl_key_path: Optional[str] = Field(default=None, description="Path to SSL private key file")
    ssl_port: int = Field(default=9000, ge=1024, le=65535, description="HTTPS port for web interface")

    @model_validator(mode='after')
    def validate_auth(self) -> 'WebInterfaceConfig':
        """Validate authentication settings when enabled."""
        if self.auth_enabled:
            if not self.username or not self.password:
                raise ValueError("Username and password required when auth is enabled")
        return self


# ==================== SSL/TLS CONFIGURATION ====================

class SSLConfig(BaseModel):
    """
    SSL/TLS configuration for securing the webhook and web interface.

    This model handles all SSL-related settings including certificate paths,
    types (PEM vs PFX), and security headers like HSTS. It supports both
    PEM (separate cert/key files) and PFX/PKCS12 (bundled) formats.

    **Understanding SSL/TLS Configuration:**
        SSL/TLS provides encrypted communication between clients and the server.
        This is essential when exposing the webhook or web interface over the
        internet to prevent credential theft and data tampering.

    **Certificate Format Support:**
        - PEM: Separate certificate (.crt/.pem) and key (.key) files
        - PFX/PKCS12: Single file (.pfx/.p12) containing cert, key, and chain

    **Security Headers:**
        - HSTS: Forces browsers to use HTTPS for all future connections
        - force_https: Redirects all HTTP requests to HTTPS

    Attributes:
        enabled (bool): Whether SSL is enabled for the server
        cert_type (str): Certificate format - 'pem' or 'pfx'
        cert_path (Optional[str]): Path to certificate file (.crt/.pem for PEM, .pfx for PFX)
        key_path (Optional[str]): Path to private key file (PEM only)
        chain_path (Optional[str]): Path to certificate chain file (PEM only)
        pfx_password (Optional[str]): Password for PFX file (PFX only)
        port (int): HTTPS port to listen on (default: 9000)
        force_https (bool): Redirect all HTTP to HTTPS
        hsts_enabled (bool): Enable HTTP Strict Transport Security
        hsts_max_age (int): HSTS max-age in seconds (default: 1 year)

    Example:
        ```python
        # PEM certificate configuration
        ssl = SSLConfig(
            enabled=True,
            cert_type="pem",
            cert_path="/app/certs/cert.pem",
            key_path="/app/certs/key.pem",
            chain_path="/app/certs/chain.pem",
            port=9000,
            force_https=True,
            hsts_enabled=True
        )

        # PFX certificate configuration
        ssl = SSLConfig(
            enabled=True,
            cert_type="pfx",
            cert_path="/app/certs/certificate.pfx",
            pfx_password="certificate_password",
            port=443,
            force_https=True
        )

        # Disabled SSL (HTTP only)
        ssl = SSLConfig(enabled=False)
        ```
    """
    model_config = ConfigDict(extra='forbid')

    enabled: bool = Field(default=False, description="Enable SSL/TLS for the server")
    cert_type: Optional[str] = Field(default=None, description="Certificate type: 'pem' or 'pfx'")
    cert_path: Optional[str] = Field(default=None, description="Path to certificate file")
    key_path: Optional[str] = Field(default=None, description="Path to private key file (PEM only)")
    chain_path: Optional[str] = Field(default=None, description="Path to certificate chain file (PEM only)")
    pfx_password: Optional[str] = Field(default=None, description="Password for PFX file (PFX only)")
    port: int = Field(default=9000, ge=1024, le=65535, description="HTTPS port")
    force_https: bool = Field(default=False, description="Redirect HTTP to HTTPS")
    hsts_enabled: bool = Field(default=False, description="Enable HSTS header")
    hsts_max_age: int = Field(default=31536000, ge=0, description="HSTS max-age in seconds")

    @field_validator('cert_type')
    @classmethod
    def validate_cert_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate certificate type is either 'pem' or 'pfx'."""
        if v is not None:
            v = v.lower()
            if v not in ['pem', 'pfx']:
                raise ValueError("cert_type must be 'pem' or 'pfx'")
        return v

    @model_validator(mode='after')
    def validate_ssl_config(self) -> 'SSLConfig':
        """
        Validate SSL configuration has required fields when enabled.
        
        When SSL is enabled, we need:
        - cert_type specified
        - For PEM: cert_path and key_path
        - For PFX: cert_path and optionally pfx_password
        """
        if self.enabled:
            if not self.cert_type:
                raise ValueError("cert_type must be specified when SSL is enabled")
            
            if self.cert_type == 'pem':
                if not self.cert_path:
                    raise ValueError("cert_path is required for PEM certificates")
                if not self.key_path:
                    raise ValueError("key_path is required for PEM certificates")
            elif self.cert_type == 'pfx':
                if not self.cert_path:
                    raise ValueError("cert_path is required for PFX certificates")
        
        return self


# ==================== WEB INTERFACE CONFIGURATION ====================
# Note: WebInterfaceConfig is already defined above with SSL support at line 713


# ==================== METADATA SERVICES CONFIGURATION ====================

class MetadataServiceConfig(BaseModel):
    """
    Configuration for individual metadata service (OMDb, TMDb, etc.).

    This model represents settings for a single external metadata service.
    Multiple instances are used for different services like OMDb, TMDb, and TVDb.

    **Understanding External API Integration:**
        Metadata services provide additional metadata like ratings, reviews, and
        enhanced descriptions. Each service has its own API with different
        authentication requirements.

    Attributes:
        enabled (bool): Whether this metadata service should be used
        api_key (Optional[str]): API key for authentication (service-specific)
        base_url (str): Base URL for the service API

    Example:
        ```python
        # OMDb configuration
        omdb = MetadataServiceConfig(
            enabled=True,
            api_key="your-omdb-key",
            base_url="http://www.omdbapi.com/"
        )
        ```
    """
    model_config = ConfigDict(extra='forbid')

    enabled: bool = Field(default=False, description="Whether metadata service is enabled")
    api_key: Optional[str] = Field(default=None, description="API key for the service")
    base_url: str = Field(..., description="Base URL for the service API")


class TVDBConfig(BaseModel):
    """
    Enhanced TVDB configuration supporting both licensed and subscriber models.

    TVDB (The TV Database) has a more complex authentication system than other
    metadata services, supporting both subscriber pins and licensed access modes.

    **Understanding TVDB's Authentication Model:**
        TVDB offers different access levels:
        - Free: Limited access with API key only
        - Subscriber: Enhanced access with API key + subscriber PIN
        - Licensed: Commercial access with different authentication

    Attributes:
        enabled (bool): Whether TVDB service is enabled
        api_key (Optional[str]): TVDB API key
        subscriber_pin (Optional[str]): Subscriber PIN for enhanced access
        base_url (str): TVDB API base URL
        access_mode (str): Access mode (auto, subscriber, licensed)

    Example:
        ```python
        # Subscriber configuration
        tvdb = TVDBConfig(
            enabled=True,
            api_key="your-tvdb-key",
            subscriber_pin="your-pin",
            access_mode="subscriber"
        )
        ```
    """
    model_config = ConfigDict(extra='forbid')

    enabled: bool = Field(default=False, description="Whether TVDB is enabled")
    api_key: Optional[str] = Field(default=None, description="TVDB API key")
    subscriber_pin: Optional[str] = Field(default=None, description="TVDB subscriber PIN")
    base_url: str = Field(default="https://api4.thetvdb.com/v4/", description="TVDB API base URL")
    access_mode: str = Field(default="auto", description="Access mode (auto, subscriber, licensed)")

    # noinspection PyDecorator
    @field_validator('api_key', 'subscriber_pin')
    @classmethod
    def validate_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate optional string fields by trimming whitespace.

        For optional fields, we want to convert empty strings to None
        and trim whitespace from non-empty values.

        Args:
            v (Optional[str]): String to validate

        Returns:
            Optional[str]: Trimmed string or None
        """
        if v is None:
            return None
        if not v.strip():
            return None
        return v.strip()

    # noinspection PyDecorator
    @field_validator('access_mode')
    @classmethod
    def validate_access_mode(cls, v: str) -> str:
        """
        Validate TVDB access mode against allowed values.

        Args:
            v (str): Access mode to validate

        Returns:
            str: Lowercase access mode

        Raises:
            ValueError: If access mode is not recognized
        """
        valid_modes = ['auto', 'subscriber', 'licensed']
        if v.lower() not in valid_modes:
            raise ValueError(f"Access mode must be one of: {valid_modes}")
        return v.lower()


class MetadataServicesConfig(BaseModel):
    """
    Configuration for all external metadata services.

    This model brings together all the individual metadata service configurations
    and adds global settings that apply to all services.

    **Understanding Service Composition:**
        Instead of having one monolithic configuration, we compose multiple
        service configurations together. This makes it easy to enable/disable
        individual services and manage their settings independently.

    Attributes:
        enabled (bool): Global metadata services enabled flag
        omdb (MetadataServiceConfig): OMDb service configuration
        tmdb (MetadataServiceConfig): TMDb service configuration
        tvdb (TVDBConfig): TVDB service configuration (enhanced model)
        cache_duration_hours (int): How long to cache rating data (1-8760 hours)
        tvdb_cache_ttl_hours (int): How long to cache TVDB metadata (1-8760 hours)
        request_timeout_seconds (int): HTTP request timeout (1-60 seconds)
        retry_attempts (int): Number of retry attempts for failed requests (1-10)

    Example:
        ```python
        metadata_services = MetadataServicesConfig(
            enabled=True,
            omdb=MetadataServiceConfig(enabled=True, api_key="omdb-key", base_url="..."),
            tmdb=MetadataServiceConfig(enabled=True, api_key="tmdb-key", base_url="..."),
            tvdb=TVDBConfig(enabled=True, api_key="tvdb-key", subscriber_pin="pin"),
            cache_duration_hours=72,         # Cache ratings for 3 days
            tvdb_cache_ttl_hours=24,        # Cache TVDB metadata for 1 day
            request_timeout_seconds=15,      # 15 second timeout
            retry_attempts=3                 # Retry 3 times on failure
        )
        ```
    """
    model_config = ConfigDict(extra='forbid')

    enabled: bool = Field(default=True, description="Global metadata services enabled flag")

    # Individual service configurations
    omdb: MetadataServiceConfig = Field(
        default_factory=lambda: MetadataServiceConfig(
            enabled=False,
            api_key=None,
            base_url="http://www.omdbapi.com/"
        )
    )
    tmdb: MetadataServiceConfig = Field(
        default_factory=lambda: MetadataServiceConfig(
            enabled=False,
            api_key=None,
            base_url="https://api.themoviedb.org/3/"
        )
    )
    tvdb: TVDBConfig = Field(
        default_factory=lambda: TVDBConfig(
            enabled=False,
            api_key=None,
            subscriber_pin=None
        )
    )

    # Global settings for all metadata services
    cache_duration_hours: int = Field(default=168, ge=1, le=8760, description="Rating cache duration in hours")
    tvdb_cache_ttl_hours: int = Field(default=24, ge=1, le=8760, description="TVDB metadata cache duration in hours")
    request_timeout_seconds: int = Field(default=10, ge=1, le=60, description="HTTP request timeout")
    retry_attempts: int = Field(default=3, ge=1, le=10, description="Number of retry attempts")


# ==================== TOP-LEVEL CONFIGURATION ====================

class AppConfig(BaseModel):
    """
    Top-level application configuration that combines all sub-configurations.

    This is the main configuration class that validates and holds all
    application settings. It uses composition to organize related settings
    into logical groups, making the configuration easier to understand and maintain.

    **Understanding Configuration Hierarchy:**
        Large applications have many settings, so we organize them hierarchically:
        - AppConfig (top level)
          - JellyfinConfig (Jellyfin settings)
          - DiscordConfig (Discord settings)
          - DatabaseConfig (Database settings)
          - etc.

    **Required vs Optional Configuration:**
        Some configurations are required (jellyfin, discord) because the
        application can't function without them. Others are optional and
        have sensible defaults.

    Attributes:
        jellyfin (JellyfinConfig): Jellyfin server connection settings (required)
        discord (DiscordConfig): Discord webhook and notification settings (required)
        database (DatabaseConfig): SQLite database configuration (optional, has defaults)
        templates (TemplatesConfig): Jinja2 template settings (optional, has defaults)
        notifications (NotificationsConfig): Notification behavior settings (optional)
        server (ServerConfig): Web server configuration (optional, has defaults)
        metadata_services (MetadataServicesConfig): External metadata services config (optional)

    Example:
        ```python
        # Minimal configuration (required fields only)
        config = AppConfig(
            jellyfin=JellyfinConfig(
                server_url="http://localhost:8096",
                api_key="your-key",
                user_id="your-user-id"
            ),
            discord=DiscordConfig(
                webhooks={
                    "default": WebhookConfig(
                        name="Default",
                        enabled=True,
                        url="your-webhook-url"
                    )
                }
            )
            # All other configs use defaults
        )
        ```
    """
    model_config = ConfigDict(extra='ignore')  # Ignore extra fields like deprecated 'sync' config

    # Required configurations
    jellyfin: JellyfinConfig
    discord: DiscordConfig

    # Optional configurations with factory defaults
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    templates: TemplatesConfig = Field(default_factory=TemplatesConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    ssl: SSLConfig = Field(default_factory=SSLConfig)
    web_interface: WebInterfaceConfig = Field(default_factory=WebInterfaceConfig)
    metadata_services: MetadataServicesConfig = Field(default_factory=MetadataServicesConfig)
    backup: BackupConfig = Field(default_factory=BackupConfig)


# ==================== CONFIGURATION VALIDATION ====================

class ConfigurationValidator:
    """
    Comprehensive configuration validator with environment variable support.

    This class handles the complex process of loading configuration from multiple
    sources (JSON files, environment variables) and validating that all required
    settings are present and correctly formatted.

    **Understanding Multi-Source Configuration:**
        Modern applications need flexible configuration that can come from:
        1. Default values (in the code)
        2. Configuration files (JSON/YAML)
        3. Environment variables (for deployment flexibility)
        4. Command line arguments (for debugging)

    **The Validation Process:**
        1. Load base configuration from JSON/YAML files
        2. Apply environment variable overrides
        3. Create Pydantic models (automatic validation)
        4. Perform additional custom validation
        5. Report errors and warnings

    **Error Handling Strategy:**
        Configuration errors are collected rather than immediately failing.
        This allows reporting multiple issues at once, making it easier for
        users to fix all problems in one go.

    Attributes:
        logger (logging.Logger): Logger for reporting validation progress
        errors (List[str]): Validation errors that prevent startup
        warnings (List[str]): Validation warnings that don't prevent startup

    Example:
        ```python
        validator = ConfigurationValidator(logger)

        try:
            config = validator.load_and_validate_config("/app/config/config.json")
            # Configuration is valid and ready to use
        except SystemExit:
            # Configuration validation failed, errors were logged
            pass
        ```
    """

    def __init__(self):
        """
        Initialize validator with logger and empty error/warning lists.
        """
        self.logger = get_logger("jellynouncer.config")
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def load_and_validate_config(self, config_path: str = "/app/config/config.json") -> AppConfig:
        """
        Load configuration from file and environment, then validate.

        This is the main entry point for configuration loading. It orchestrates
        the entire process of loading, merging, and validating configuration data.

        **The Multi-Step Process:**
        1. Load from file (JSON/YAML) - provides base configuration
        2. Apply environment overrides - allows deployment-time customization
        3. Pydantic validation - automatic type checking and conversion
        4. Custom validation - business logic checks
        5. Report results - comprehensive error/warning reporting

        Args:
            config_path (str): Path to JSON or YAML configuration file

        Returns:
            AppConfig: Fully validated application configuration

        Raises:
            SystemExit: If validation fails with errors

        Example:
            ```python
            # Load with default path
            config = validator.load_and_validate_config()

            # Load with custom path
            config = validator.load_and_validate_config("/custom/config.yaml")
            ```
        """
        try:
            self.logger.info(f"Loading configuration from {config_path}")

            # Step 1: Load base configuration from file
            config_data = self._load_config_file(config_path)

            # Step 2: Apply environment variable overrides
            self._apply_env_overrides(config_data)
            
            # Step 2.5: Ensure all watch_changes fields are present with proper defaults
            self._ensure_watch_changes_defaults(config_data)

            # Step 3: Validate using Pydantic models (automatic type conversion and validation)
            config = AppConfig(**config_data)

            # Step 4: Perform additional custom validation
            self._validate_jellyfin_config(config.jellyfin)
            self._validate_discord_config(config.discord)
            self._validate_template_files(config.templates)

            # Step 5: Report results and exit if there are errors
            self._report_validation_results()

            self.logger.info("Configuration loaded and validated successfully")
            return config

        except ValidationError as e:
            # Pydantic validation errors - format them nicely
            self.logger.error("Configuration model validation failed:")
            for error in e.errors():
                field_path = " -> ".join(str(x) for x in error['loc'])
                self.logger.error(f"  {field_path}: {error['msg']}")
            raise SystemExit(1)
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise SystemExit(1)

    def _load_config_file(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration data from JSON or YAML file.

        This method supports both JSON and YAML configuration files,
        automatically detecting the format based on file extension.

        **Understanding File Format Support:**
            - JSON: Strict format, good for programmatic generation
            - YAML: Human-friendly format, supports comments and multi-line strings

        Args:
            config_path (str): Path to configuration file

        Returns:
            Dict[str, Any]: Dictionary containing configuration data

        Raises:
            Various exceptions for file not found, invalid JSON/YAML, etc.
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                # Auto-detect format based on file extension
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    return yaml.safe_load(f) or {}
                else:
                    return json.load(f) or {}

        except FileNotFoundError:
            self.logger.warning(f"Configuration file not found: {config_path}, using defaults")
            return {}  # Return empty dict to use all defaults
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            self.errors.append(f"Invalid configuration file format: {e}")
            raise
        except Exception as e:
            self.errors.append(f"Error reading configuration file: {e}")
            raise

    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> None:
        """
        Apply environment variable overrides to configuration data.

        Environment variables provide a way to override configuration settings
        without modifying files. This is essential for containerized deployments
        where configuration files might be read-only.

        **Environment Variable Mapping:**
            Environment variables use a specific naming pattern:
            - JELLYFIN_SERVER_URL -> config_data['jellyfin']['server_url']
            - DISCORD_WEBHOOK_URL -> config_data['discord']['webhooks']['default']['url']

        Args:
            config_data (Dict[str, Any]): Configuration data to modify
        """
        # Initialize nested structure if needed
        if 'jellyfin' not in config_data:
            config_data['jellyfin'] = {}
        if 'discord' not in config_data:
            config_data['discord'] = {'webhooks': {}}
        if 'webhooks' not in config_data['discord']:
            config_data['discord']['webhooks'] = {}
        if 'server' not in config_data:
            config_data['server'] = {}
        if 'database' not in config_data:
            config_data['database'] = {}
        if 'metadata_services' not in config_data:
            config_data['metadata_services'] = {}

        # Jellyfin overrides
        env_mappings = {
            'JELLYFIN_SERVER_URL': ['jellyfin', 'server_url'],
            'JELLYFIN_API_KEY': ['jellyfin', 'api_key'],
            'JELLYFIN_USER_ID': ['jellyfin', 'user_id'],

            # Discord webhook overrides
            'DISCORD_WEBHOOK_URL': ['discord', 'webhooks', 'default', 'url'],
            'DISCORD_WEBHOOK_URL_MOVIES': ['discord', 'webhooks', 'movies', 'url'],
            'DISCORD_WEBHOOK_URL_TV': ['discord', 'webhooks', 'tv', 'url'],
            'DISCORD_WEBHOOK_URL_MUSIC': ['discord', 'webhooks', 'music', 'url'],

            # Server configuration overrides
            'LOG_LEVEL': ['server', 'log_level'],
            'HOST': ['server', 'host'],
            'PORT': ['server', 'port'],

            # Database configuration overrides
            'DATABASE_PATH': ['database', 'path'],
            'DATABASE_WAL_MODE': ['database', 'wal_mode'],

            # Metadata services overrides
            'OMDB_API_KEY': ['metadata_services', 'omdb', 'api_key'],
            'TMDB_API_KEY': ['metadata_services', 'tmdb', 'api_key'],
            'TVDB_API_KEY': ['metadata_services', 'tvdb', 'api_key'],
            'TVDB_SUBSCRIBER_PIN': ['metadata_services', 'tvdb', 'subscriber_pin'],
            'TVDB_CACHE_TTL_HOURS': ['metadata_services', 'tvdb', 'cache_ttl_hours'],
            # New notification filter options
            'FILTER_RENAMES': ['notifications', 'filter_renames'],
            'FILTER_DELETES': ['notifications', 'filter_deletes'],
            
            # Backup configuration overrides
            'BACKUP_ENABLED': ['backup', 'enabled'],
            'BACKUP_DIR': ['backup', 'backup_dir'],
            'BACKUP_SCHEDULE': ['backup', 'schedule'],
            'BACKUP_TIME': ['backup', 'backup_time'],
            'BACKUP_RETENTION_DAYS': ['backup', 'retention_days'],
            'BACKUP_MAX_COUNT': ['backup', 'max_backups'],
            'BACKUP_COMPRESS': ['backup', 'compress'],
            'BACKUP_INCLUDE_CONFIG': ['backup', 'backup_config'],
            'BACKUP_INCLUDE_DATABASE': ['backup', 'backup_database'],
            'BACKUP_INCLUDE_TEMPLATES': ['backup', 'backup_templates'],
            'BACKUP_INCLUDE_SSL': ['backup', 'backup_ssl'],
            'BACKUP_INCLUDE_LOGS': ['backup', 'backup_logs'],
        }

        for env_var, path in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                # Navigate/create nested structure
                current = config_data
                for key in path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]

                # Handle type conversions for specific environment variables
                if env_var == 'PORT':
                    try:
                        value = int(value)
                    except ValueError:
                        self.logger.warning(f"Invalid PORT value '{value}', skipping override")
                        continue
                elif env_var in ('DATABASE_WAL_MODE', 'FILTER_RENAMES', 'FILTER_DELETES'):
                    # Convert string to boolean
                    value = value.lower() in ('true', '1', 'yes', 'on')

                # Set the value
                current[path[-1]] = value
                self.logger.debug(f"Applied environment override: {env_var}")

        # Create default webhook configurations if URLs were provided
        webhook_defaults = {
            'default': {'name': 'Default Webhook', 'enabled': True},
            'movies': {'name': 'Movies Webhook', 'enabled': True},
            'tv': {'name': 'TV Shows Webhook', 'enabled': True},
            'music': {'name': 'Music Webhook', 'enabled': True},
        }

        for webhook_name, defaults in webhook_defaults.items():
            if webhook_name in config_data['discord']['webhooks']:
                # Apply defaults for missing fields
                webhook_config = config_data['discord']['webhooks'][webhook_name]
                for key, value in defaults.items():
                    if key not in webhook_config:
                        webhook_config[key] = value

    def _ensure_watch_changes_defaults(self, config_data: Dict[str, Any]) -> None:
        """
        Ensure all watch_changes fields are present in the configuration.
        
        This prevents issues where missing fields are not displayed in the web UI.
        """
        # Define all expected watch_changes fields with their defaults
        default_watch_changes = {
            'resolution': True,
            'video_codec': True,  # Renamed from 'codec' for clarity
            'audio_codec': True,
            'audio_channels': True,
            'hdr_status': True,
            'file_size': False,
            'subtitles': True
        }
        
        # Handle legacy 'codec' field - rename to 'video_codec'
        if 'notifications' in config_data and 'watch_changes' in config_data['notifications']:
            watch_changes = config_data['notifications']['watch_changes']
            if 'codec' in watch_changes and 'video_codec' not in watch_changes:
                self.logger.info("Migrating 'codec' to 'video_codec' in watch_changes")
                watch_changes['video_codec'] = watch_changes.pop('codec')
        
        # Ensure notifications section exists
        if 'notifications' not in config_data:
            config_data['notifications'] = {}
        
        # Ensure watch_changes exists
        if 'watch_changes' not in config_data['notifications']:
            config_data['notifications']['watch_changes'] = {}
        
        # Apply defaults for any missing fields
        watch_changes = config_data['notifications']['watch_changes']
        for field, default_value in default_watch_changes.items():
            if field not in watch_changes:
                self.logger.debug(f"Adding missing watch_changes field '{field}' with default value {default_value}")
                watch_changes[field] = default_value
    
    def _validate_jellyfin_config(self, jellyfin_config: JellyfinConfig) -> None:
        """
        Validate Jellyfin configuration and perform additional checks.

        Pydantic models handle basic validation, but this method can be extended
        for additional checks like testing connectivity or validating API permissions.

        Args:
            jellyfin_config (JellyfinConfig): Jellyfin configuration to validate

        Note:
            Currently performs basic validation only. Could be extended with:
            - Connectivity testing
            - API key validation
            - Permission checking
        """
        # Pydantic models already handle most validation
        # This method can be extended for additional checks like:
        # - Testing connectivity to Jellyfin server
        # - Validating API key format
        # - Checking user permissions
        pass

    def _validate_discord_config(self, discord_config: DiscordConfig) -> None:
        """
        Validate Discord webhook configuration and report status.

        This method checks that at least one webhook is configured and enabled,
        which is required for the application to function.

        Args:
            discord_config (DiscordConfig): Discord configuration to validate
        """
        # Find all enabled webhooks with valid URLs
        enabled_webhooks = [
            name for name, webhook in discord_config.webhooks.items()
            if webhook.enabled and webhook.url
        ]

        if not enabled_webhooks:
            self.errors.append("No Discord webhooks are configured and enabled")
        else:
            self.logger.info(f"Enabled Discord webhooks: {', '.join(enabled_webhooks)}")

    def _validate_template_files(self, templates_config: TemplatesConfig) -> None:
        """
        Validate that required template files exist and are readable.

        This method checks for the existence of essential template files,
        ensuring the application can render notifications properly.

        Args:
            templates_config (TemplatesConfig): Templates configuration to validate
        """
        template_dir = Path(templates_config.directory)

        # Check that essential templates exist
        required_templates = [
            templates_config.new_item_template,
            templates_config.upgraded_item_template,
        ]

        for template_name in required_templates:
            template_path = template_dir / template_name
            if not template_path.exists():
                self.errors.append(f"Required template file not found: {template_path}")
            elif not template_path.is_file():
                self.errors.append(f"Template path is not a file: {template_path}")

    def _report_validation_results(self) -> None:
        """
        Report validation results and exit if there are errors.

        This method provides comprehensive reporting of all validation issues,
        separating warnings (non-fatal) from errors (fatal).

        Raises:
            SystemExit: If any validation errors occurred
        """
        # Report warnings first
        if self.warnings:
            self.logger.warning("Configuration warnings:")
            for warning in self.warnings:
                self.logger.warning(f"  - {warning}")

        # Report errors and exit if any exist
        if self.errors:
            self.logger.error("Configuration errors:")
            for error in self.errors:
                self.logger.error(f"  - {error}")
            raise SystemExit(1)

        self.logger.info("Configuration validation completed successfully")