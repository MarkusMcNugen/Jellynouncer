#!/usr/bin/env python3
"""
Backup Manager for Jellynouncer

This module provides automated backup and restore functionality for:
- Configuration files (config.json)
- Database files (jellynouncer.db)
- Template files
- SSL certificates

Features:
- Scheduled automatic backups
- Manual backup/restore via API
- Compression and encryption options
- Retention policies

Author: Mark Newton
Project: Jellynouncer
Version: 1.0.0
License: MIT
"""

import os
import json
import shutil
import tarfile
import asyncio
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
import hashlib
import aiofiles
import aiosqlite
from jellynouncer.utils import get_logger

logger = get_logger("jellynouncer.backup")


class BackupManager:
    """Manages backup and restore operations for Jellynouncer"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize backup manager with configuration
        
        Args:
            config: Backup configuration dictionary
        """
        self.config = config or {}
        
        # Log the config we received for debugging
        logger.info(f"BackupManager initialized with config: {self.config}")
        logger.info(f"Config has enabled: {self.config.get('enabled')}, schedule: {self.config.get('schedule')}")
        
        # Default configuration
        self.backup_dir = Path(self.config.get("backup_dir", "data/backups"))
        self.max_backups = self.config.get("max_backups", 10)
        self.backup_schedule = self.config.get("schedule", "daily")  # daily, weekly, hourly
        self.backup_time = self.config.get("backup_time", "02:00")  # 2 AM default
        self.retention_days = self.config.get("retention_days", 30)
        self.compress = self.config.get("compress", True)
        self.include_logs = self.config.get("include_logs", False)
        
        # Components to backup
        self.backup_components = {
            "config": self.config.get("backup_config", True),
            "database": self.config.get("backup_database", True),
            "templates": self.config.get("backup_templates", True),
            "ssl": self.config.get("backup_ssl", False),
            "logs": self.config.get("backup_logs", False)
        }
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Track scheduled task
        self.scheduler_task = None
        
        logger.info(f"Backup manager initialized with directory: {self.backup_dir}")
        logger.info(f"Backup schedule: {self.backup_schedule} at {self.backup_time}")
        logger.info(f"Retention: {self.retention_days} days, max {self.max_backups} backups")
    
    async def start_scheduler(self):
        """Start the automatic backup scheduler"""
        if self.backup_schedule == "disabled":
            logger.info("Automatic backups are disabled")
            return
        
        self.scheduler_task = asyncio.create_task(self._backup_scheduler())
        logger.info("Backup scheduler started")
    
    async def stop_scheduler(self):
        """Stop the automatic backup scheduler"""
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
            logger.info("Backup scheduler stopped")
    
    async def _backup_scheduler(self):
        """Background task that runs scheduled backups"""
        while True:
            try:
                # Calculate next backup time
                next_backup = self._calculate_next_backup()
                wait_seconds = (next_backup - datetime.now(timezone.utc)).total_seconds()
                
                if wait_seconds > 0:
                    logger.info(f"Next backup scheduled for {next_backup} ({wait_seconds/3600:.1f} hours)")
                    await asyncio.sleep(wait_seconds)
                
                # Perform backup
                logger.info("Starting scheduled backup...")
                backup_path = await self.create_backup(auto=True)
                logger.info(f"Scheduled backup completed: {backup_path}")
                
                # Clean old backups
                await self.cleanup_old_backups()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduled backup failed: {e}", exc_info=True)
                # Wait before retry
                await asyncio.sleep(3600)  # 1 hour
    
    def _calculate_next_backup(self) -> datetime:
        """Calculate the next backup time based on schedule"""
        now = datetime.now(timezone.utc)
        
        if self.backup_schedule == "hourly":
            # Next hour
            next_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        elif self.backup_schedule == "daily":
            # Parse backup time (HH:MM)
            hour, minute = map(int, self.backup_time.split(":"))
            next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # If time has passed today, schedule for tomorrow
            if next_time <= now:
                next_time += timedelta(days=1)
        
        elif self.backup_schedule == "weekly":
            # Weekly on Sunday at specified time
            hour, minute = map(int, self.backup_time.split(":"))
            days_until_sunday = (6 - now.weekday()) % 7
            if days_until_sunday == 0 and now.hour >= hour:
                days_until_sunday = 7
            
            next_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            next_time += timedelta(days=days_until_sunday)
        
        else:
            # Default to daily
            next_time = now + timedelta(days=1)
        
        return next_time
    
    async def create_backup(self, auto: bool = False) -> str:
        """
        Create a backup of all configured components
        
        Args:
            auto: Whether this is an automatic scheduled backup
            
        Returns:
            Path to the created backup file
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_type = "auto" if auto else "manual"
        backup_name = f"jellynouncer_backup_{backup_type}_{timestamp}"
        
        # Create temporary directory for staging
        temp_dir = self.backup_dir / f"temp_{timestamp}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Backup configuration
            if self.backup_components["config"]:
                await self._backup_config(temp_dir)
            
            # Backup database
            if self.backup_components["database"]:
                await self._backup_database(temp_dir)
            
            # Backup templates
            if self.backup_components["templates"]:
                await self._backup_templates(temp_dir)
            
            # Backup SSL certificates
            if self.backup_components["ssl"]:
                await self._backup_ssl(temp_dir)
            
            # Backup logs
            if self.backup_components["logs"]:
                await self._backup_logs(temp_dir)
            
            # Create metadata file
            await self._create_metadata(temp_dir, backup_type)
            
            # Create archive
            if self.compress:
                archive_path = self.backup_dir / f"{backup_name}.tar.gz"
                await self._create_archive(temp_dir, archive_path, compress=True)
            else:
                archive_path = self.backup_dir / backup_name
                shutil.move(str(temp_dir), str(archive_path))
            
            logger.info(f"Backup created: {archive_path}")
            return str(archive_path)
            
        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    async def _backup_config(self, dest_dir: Path):
        """Backup configuration files"""
        config_dir = Path("config")
        if config_dir.exists():
            dest_config = dest_dir / "config"
            shutil.copytree(config_dir, dest_config)
            logger.debug("Configuration files backed up")
    
    async def _backup_database(self, dest_dir: Path):
        """Backup database with proper locking"""
        db_path = Path("data/jellynouncer.db")
        if db_path.exists():
            dest_db = dest_dir / "database"
            dest_db.mkdir(exist_ok=True)
            
            # Use SQLite backup API for consistency
            async with aiosqlite.connect(db_path) as source_db:
                async with aiosqlite.connect(dest_db / "jellynouncer.db") as dest_conn:
                    await source_db.backup(dest_conn)
            
            # Also backup WAL and SHM files if they exist
            for ext in [".wal", ".shm"]:
                wal_file = Path(str(db_path) + ext)
                if wal_file.exists():
                    shutil.copy2(wal_file, dest_db / wal_file.name)
            
            logger.debug("Database backed up")
    
    async def _backup_templates(self, dest_dir: Path):
        """Backup template files"""
        templates_dir = Path("templates")
        if templates_dir.exists():
            dest_templates = dest_dir / "templates"
            shutil.copytree(templates_dir, dest_templates)
            logger.debug("Templates backed up")
    
    async def _backup_ssl(self, dest_dir: Path):
        """Backup SSL certificates"""
        ssl_dir = Path("data/ssl")
        if ssl_dir.exists():
            dest_ssl = dest_dir / "ssl"
            shutil.copytree(ssl_dir, dest_ssl)
            logger.debug("SSL certificates backed up")
    
    async def _backup_logs(self, dest_dir: Path):
        """Backup log files"""
        logs_dir = Path("logs")
        if logs_dir.exists():
            dest_logs = dest_dir / "logs"
            shutil.copytree(logs_dir, dest_logs)
            logger.debug("Log files backed up")
    
    async def _create_metadata(self, backup_dir: Path, backup_type: str):
        """Create backup metadata file"""
        metadata = {
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": backup_type,
            "components": self.backup_components,
            "files": []
        }
        
        # List all files in backup with checksums
        for root, dirs, files in os.walk(backup_dir):
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(backup_dir)
                
                # Calculate checksum
                with open(file_path, 'rb') as f:
                    checksum = hashlib.sha256(f.read()).hexdigest()
                
                metadata["files"].append({
                    "path": str(relative_path),
                    "size": file_path.stat().st_size,
                    "checksum": checksum
                })
        
        # Save metadata
        metadata_path = backup_dir / "backup_metadata.json"
        async with aiofiles.open(metadata_path, 'w') as f:
            await f.write(json.dumps(metadata, indent=2))
    
    async def _create_archive(self, source_dir: Path, archive_path: Path, compress: bool = True):
        """Create tar archive from directory"""
        mode = "w:gz" if compress else "w"
        
        with tarfile.open(archive_path, mode) as tar:
            tar.add(source_dir, arcname=archive_path.stem)
    
    async def restore_backup(self, backup_path: str, components: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Restore from a backup file
        
        Args:
            backup_path: Path to backup file
            components: List of components to restore (None = all)
            
        Returns:
            Dictionary with restore results
        """
        backup_file = Path(backup_path)
        if not backup_file.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")
        
        # Extract to temporary directory
        temp_dir = self.backup_dir / f"restore_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "success": True,
            "restored": [],
            "errors": []
        }
        
        try:
            # Extract archive
            if backup_file.suffix == ".gz":
                with tarfile.open(backup_file, "r:gz") as tar:
                    tar.extractall(temp_dir)
            elif backup_file.suffix == ".tar":
                with tarfile.open(backup_file, "r") as tar:
                    tar.extractall(temp_dir)
            else:
                # Assume it's a directory
                shutil.copytree(backup_file, temp_dir / backup_file.name)
            
            # Find extracted backup directory
            backup_dirs = list(temp_dir.glob("*"))
            if not backup_dirs:
                raise ValueError("Invalid backup archive structure")
            
            extracted_dir = backup_dirs[0]
            
            # Read metadata
            metadata_path = extracted_dir / "backup_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {}
            
            # Determine what to restore
            if components is None:
                components = ["config", "database", "templates", "ssl", "logs"]
            
            # Restore each component
            for component in components:
                try:
                    if component == "config" and (extracted_dir / "config").exists():
                        await self._restore_config(extracted_dir / "config")
                        results["restored"].append("config")
                    
                    elif component == "database" and (extracted_dir / "database").exists():
                        await self._restore_database(extracted_dir / "database")
                        results["restored"].append("database")
                    
                    elif component == "templates" and (extracted_dir / "templates").exists():
                        await self._restore_templates(extracted_dir / "templates")
                        results["restored"].append("templates")
                    
                    elif component == "ssl" and (extracted_dir / "ssl").exists():
                        await self._restore_ssl(extracted_dir / "ssl")
                        results["restored"].append("ssl")
                    
                    elif component == "logs" and (extracted_dir / "logs").exists():
                        await self._restore_logs(extracted_dir / "logs")
                        results["restored"].append("logs")
                    
                except Exception as e:
                    results["errors"].append(f"Failed to restore {component}: {str(e)}")
                    results["success"] = False
            
            logger.info(f"Restore completed: {results}")
            return results
            
        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    async def _restore_config(self, source_dir: Path):
        """Restore configuration files"""
        dest_dir = Path("config")
        
        # Backup existing config first
        if dest_dir.exists():
            backup_dir = dest_dir.parent / f"config_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            shutil.move(str(dest_dir), str(backup_dir))
        
        # Copy restored config
        shutil.copytree(source_dir, dest_dir)
        logger.info("Configuration restored")
    
    async def _restore_database(self, source_dir: Path):
        """Restore database"""
        db_path = Path("data/jellynouncer.db")
        
        # Backup existing database first
        if db_path.exists():
            backup_path = db_path.parent / f"jellynouncer_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(db_path, backup_path)
        
        # Copy restored database
        source_db = source_dir / "jellynouncer.db"
        if source_db.exists():
            shutil.copy2(source_db, db_path)
            
            # Also restore WAL and SHM files if they exist
            for ext in [".wal", ".shm"]:
                source_file = source_dir / f"jellynouncer.db{ext}"
                if source_file.exists():
                    shutil.copy2(source_file, Path(str(db_path) + ext))
        
        logger.info("Database restored")
    
    async def _restore_templates(self, source_dir: Path):
        """Restore template files"""
        dest_dir = Path("templates")
        
        # Backup existing templates first
        if dest_dir.exists():
            backup_dir = dest_dir.parent / f"templates_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            shutil.move(str(dest_dir), str(backup_dir))
        
        # Copy restored templates
        shutil.copytree(source_dir, dest_dir)
        logger.info("Templates restored")
    
    async def _restore_ssl(self, source_dir: Path):
        """Restore SSL certificates"""
        dest_dir = Path("data/ssl")
        
        # Backup existing SSL files first
        if dest_dir.exists():
            backup_dir = dest_dir.parent / f"ssl_backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            shutil.move(str(dest_dir), str(backup_dir))
        
        # Copy restored SSL files
        shutil.copytree(source_dir, dest_dir)
        logger.info("SSL certificates restored")
    
    async def _restore_logs(self, source_dir: Path):
        """Restore log files"""
        dest_dir = Path("logs")
        
        # Don't backup existing logs, just merge
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy restored logs with timestamp suffix to avoid overwriting
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        for log_file in source_dir.glob("*"):
            if log_file.is_file():
                dest_file = dest_dir / f"{log_file.stem}_restored_{timestamp}{log_file.suffix}"
                shutil.copy2(log_file, dest_file)
        
        logger.info("Log files restored")
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        backups = []
        
        for backup_file in self.backup_dir.glob("jellynouncer_backup_*"):
            try:
                stat = backup_file.stat()
                
                # Parse backup name for type and timestamp
                parts = backup_file.stem.split("_")
                backup_type = parts[2] if len(parts) > 2 else "unknown"
                
                backup_info = {
                    "filename": backup_file.name,
                    "path": str(backup_file),
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat(),
                    "type": backup_type,
                    "compressed": backup_file.suffix == ".gz"
                }
                
                # Try to read metadata if it's accessible
                if backup_file.is_dir():
                    metadata_path = backup_file / "backup_metadata.json"
                    if metadata_path.exists():
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            backup_info["metadata"] = metadata
                
                backups.append(backup_info)
                
            except Exception as e:
                logger.warning(f"Could not read backup info for {backup_file}: {e}")
        
        # Sort by creation time, newest first
        backups.sort(key=lambda x: x["created"], reverse=True)
        
        return backups
    
    async def cleanup_old_backups(self):
        """Remove old backups based on retention policy"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        backups = await self.list_backups()
        
        # Keep at least min_backups regardless of age
        min_backups = 3
        
        removed = []
        for i, backup in enumerate(backups):
            # Skip if within minimum count
            if i < min_backups:
                continue
            
            # Skip if within max_backups limit
            if i < self.max_backups:
                # Check age
                created = datetime.fromisoformat(backup["created"])
                if created > cutoff_date:
                    continue
            
            # Remove old backup
            try:
                backup_path = Path(backup["path"])
                if backup_path.exists():
                    if backup_path.is_dir():
                        shutil.rmtree(backup_path)
                    else:
                        backup_path.unlink()
                    removed.append(backup["filename"])
                    logger.info(f"Removed old backup: {backup['filename']}")
            except Exception as e:
                logger.error(f"Failed to remove backup {backup['filename']}: {e}")
        
        if removed:
            logger.info(f"Cleaned up {len(removed)} old backups")
        
        return removed


# Global backup manager instance
backup_manager = None


def initialize_backup_manager(config: Optional[Dict[str, Any]] = None) -> BackupManager:
    """Initialize the global backup manager"""
    global backup_manager
    backup_manager = BackupManager(config)
    return backup_manager


def get_backup_manager() -> Optional[BackupManager]:
    """Get the global backup manager instance"""
    return backup_manager