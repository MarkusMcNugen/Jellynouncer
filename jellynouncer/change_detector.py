#!/usr/bin/env python3
"""
Jellynouncer Change Detector

This module implements intelligent change detection for media quality upgrades
and modifications between versions of the same media item. It provides the core
logic for distinguishing between genuinely new content and upgraded versions
of existing content.

The ChangeDetector class focuses on technical improvements that users care about,
such as resolution upgrades, codec improvements, and audio enhancements, while
filtering out trivial changes that don't warrant notifications.

Classes:
    ChangeDetector: Intelligent change detector for media quality upgrades

Author: Mark Newton
Project: Jellynouncer
Version: 1.0.0
License: MIT
"""

import logging
from typing import List, Dict, Any, Union, Optional

from .config_models import NotificationsConfig
from .media_models import MediaItem
from .database_models import DatabaseItem
from .utils import get_logger


class ChangeDetector:
    """
    Intelligent change detector for media quality upgrades and modifications.

    This class implements the core logic for detecting meaningful changes between
    versions of the same media item. It's designed to identify technical improvements
    that warrant user notification while ignoring trivial metadata changes that
    don't affect the viewing experience.

    **Understanding Change Detection for Beginners:**

    When media files are replaced (upgraded to better quality, re-encoded, etc.),
    we need to determine what actually changed to provide meaningful notifications.
    This class compares technical specifications between versions and identifies:

    - **Quality Upgrades**: 720p → 1080p → 4K resolution improvements
    - **Codec Improvements**: H.264 → H.265/HEVC → AV1 for better compression
    - **Audio Enhancements**: Stereo → 5.1 → 7.1 surround sound upgrades
    - **HDR Upgrades**: SDR → HDR10 → Dolby Vision for better visual quality
    - **File Replacements**: Complete file changes with new encoding

    **Why Change Detection Matters:**
    Without intelligent change detection, users would receive notifications for:
    - Every metadata update (which happens frequently)
    - Trivial file system changes (path updates, library reorganization)
    - Timestamp modifications (which occur during maintenance)

    This class filters these out to focus on changes users actually care about.

    **Configurable Monitoring:**
    Users can customize which types of changes trigger notifications:
    - Enable resolution monitoring for quality upgrades
    - Disable codec monitoring if not interested in technical details
    - Monitor audio improvements for home theater setups
    - Track HDR upgrades for compatible displays

    **Change Categories:**

    **Resolution Changes:**
    Probably the most important upgrade type - users care about quality improvements:
    - 480p → 720p: Significant quality jump
    - 720p → 1080p: Very noticeable improvement
    - 1080p → 4K: Major upgrade for large screens

    **Video Codec Changes:**
    Technical improvements that affect file size and quality:
    - H.264 → H.265 (HEVC): Better compression, smaller files
    - H.264 → AV1: Next-generation codec with superior efficiency
    - MPEG-2 → H.264: Legacy to modern codec upgrade

    **Audio Improvements:**
    Important for users with good audio systems:
    - Stereo → 5.1: Surround sound upgrade
    - AC3 → DTS: Higher quality audio codec
    - Lossy → Lossless: FLAC, DTS-HD for audiophiles

    **HDR Status Changes:**
    Critical for users with HDR-capable displays:
    - SDR → HDR10: Standard to high dynamic range
    - HDR10 → Dolby Vision: Premium HDR format
    - Any HDR format changes

    Attributes:
        config (NotificationsConfig): Configuration for notification behavior
        logger (logging.Logger): Logger instance for change detection operations
        watch_changes (Dict[str, bool]): Dictionary of change types to monitor

    Example:
        ```python
        # Initialize change detector
        notifications_config = NotificationsConfig(
            watch_changes={
                'resolution': True,      # Monitor resolution upgrades
                'video_codec': True,     # Monitor video codec improvements
                'audio_codec': True,    # Monitor audio upgrades
                'hdr_status': True,     # Monitor HDR changes
                'file_size': False      # Ignore file size changes
            }
        )

        detector = ChangeDetector(notifications_config, logger)

        # Compare old and new versions of the same movie
        old_movie = MediaItem(
            item_id="abc123",
            name="The Matrix",
            video_height=720,
            video_codec="h264",
            audio_codec="ac3",
            audio_channels=2
        )

        new_movie = MediaItem(
            item_id="abc123",
            name="The Matrix",
            video_height=1080,
            video_codec="hevc",
            audio_codec="dts",
            audio_channels=6
        )

        # Detect changes between versions
        changes = detector.detect_changes(old_movie, new_movie)

        # Process detected changes
        for change in changes:
            logger.info(f"Change detected: {change['description']}")
            # Output:
            # "Change detected: Resolution changed from 720p to 1080p"
            # "Change detected: Video codec changed from h264 to hevc"
            # "Change detected: Audio codec changed from ac3 to dts"
            # "Change detected: Audio channels changed from 2 to 6"
        ```

    Note:
        This class is designed to be stateless and thread-safe. It doesn't store
        any information between calls, making it suitable for concurrent webhook
        processing where multiple items might be compared simultaneously.
    """

    def __init__(self, config: NotificationsConfig):
        """
        Initialize change detector with configuration and logging.

        Sets up the change detector with user preferences for which types of
        changes should be monitored and reported. The configuration allows
        fine-grained control over notification behavior.

        **Configuration Options:**
        The NotificationsConfig includes a watch_changes dictionary that controls
        which change types are monitored:
        - 'resolution': Video resolution changes (720p → 1080p)
        - 'video_codec': Video codec changes (h264 → hevc)
        - 'audio_codec': Audio codec changes (ac3 → dts)
        - 'audio_channels': Audio channel count changes (2 → 6)
        - 'hdr_status': HDR format changes (SDR → HDR10)
        - 'file_size': File size changes (for complete replacements)
        - 'subtitles': Subtitle track and language changes

        Args:
            config (NotificationsConfig): Configuration for notification behavior
                including which change types to monitor

        Example:
            ```python
            # Configure which changes to monitor
            config = NotificationsConfig(
                watch_changes={
                    'resolution': True,      # Always notify for resolution upgrades
                    'video_codec': True,     # Notify for video codec improvements
                    'audio_codec': True,    # Audio improvements are important
                    'audio_channels': True, # Surround sound upgrades
                    'hdr_status': True,     # HDR upgrades for compatible displays
                    'file_size': False,     # Don't notify for size-only changes
                    'subtitles': True       # Notify for subtitle changes
                }
            )

            detector = ChangeDetector(config)
            ```
        """
        self.config = config
        self.logger = get_logger("jellynouncer.detector")
        self.watch_changes = config.watch_changes

        # Log initialization with monitoring configuration
        enabled_changes = [change_type for change_type, enabled in self.watch_changes.items() if enabled]
        self.logger.info(f"Change detector initialized - Monitoring: {', '.join(enabled_changes)}")

    def detect_changes(self, old_item: Union[MediaItem, DatabaseItem], new_item: Union[MediaItem, DatabaseItem]) -> List[Dict[str, Any]]:
        """
        Detect meaningful changes between two versions of the same media item.

        This is the core method that compares technical specifications between
        old and new versions of a media item to identify upgrades worth notifying
        users about. It only reports changes that are enabled in the configuration
        and that represent meaningful improvements or modifications.

        **Change Detection Process:**
        1. Compare video resolution for quality upgrades
        2. Check video codec changes for compression improvements
        3. Analyze audio codec and channel changes for sound upgrades
        4. Detect HDR status changes for display improvements
        5. Check file size changes for complete replacements
        6. Monitor subtitle track and language changes

        **Change Object Structure:**
        Each detected change is returned as a dictionary containing:
        - `type`: Change category (resolution, codec, audio_codec, etc.)
        - `field`: Database field that changed (video_height, video_codec, etc.)
        - `old_value`: Previous value (720, "h264", etc.)
        - `new_value`: Current value (1080, "hevc", etc.)
        - `description`: Human-readable description of the change

        **Error Handling:**
        This method is designed to never crash the webhook processing pipeline.
        All exceptions are logged and an empty change list is returned
        on error, allowing the service to continue operating.

        Args:
            old_item (MediaItem): Previous version of the media item
            new_item (MediaItem): Current version of the media item

        Returns:
            List[Dict[str, Any]]: List of detected changes with metadata

        Example:
            ```python
            changes = detector.detect_changes(old_version, new_version)

            for change in changes:
                change_type = change['type']
                description = change['description']

                if change_type == 'resolution':
                    logger.info(f"Quality upgrade: {description}")
                elif change_type == 'video_codec':
                    logger.info(f"Codec improvement: {description}")
                elif change_type == 'audio_codec':
                    logger.info(f"Audio upgrade: {description}")
            ```

        Note:
            This method is safe to call with any MediaItem objects, even if
            they have missing or None values for technical specifications.
            All exceptions are logged and an empty change list is returned
            on error, allowing the service to continue operating.
        """
        changes = []

        try:
            # Resolution changes (most common and important upgrade scenario)
            if (self.watch_changes.get('resolution', True) and
                    old_item.video_height != new_item.video_height and
                    old_item.video_height is not None and new_item.video_height is not None):
                changes.append({
                    'type': 'resolution',
                    'field': 'video_height',
                    'old_value': old_item.video_height,
                    'new_value': new_item.video_height,
                    'description': f"Resolution changed from {old_item.video_height}p to {new_item.video_height}p"
                })

            # Video codec changes (compression and efficiency improvements)
            if (self.watch_changes.get('video_codec', True) and
                    old_item.video_codec != new_item.video_codec and
                    (old_item.video_codec or new_item.video_codec)):
                changes.append({
                    'type': 'video_codec',
                    'field': 'video_codec',
                    'old_value': old_item.video_codec,
                    'new_value': new_item.video_codec,
                    'description': f"Video codec changed from {old_item.video_codec or 'Unknown'} to {new_item.video_codec or 'Unknown'}"
                })

            # Audio codec changes (sound quality improvements)
            if (self.watch_changes.get('audio_codec', True) and
                    old_item.audio_codec != new_item.audio_codec and
                    (old_item.audio_codec or new_item.audio_codec)):
                changes.append({
                    'type': 'audio_codec',
                    'field': 'audio_codec',
                    'old_value': old_item.audio_codec,
                    'new_value': new_item.audio_codec,
                    'description': f"Audio codec changed from {old_item.audio_codec or 'Unknown'} to {new_item.audio_codec or 'Unknown'}"
                })

            # Audio channel changes (surround sound upgrades)
            if (self.watch_changes.get('audio_channels', True) and
                    old_item.audio_channels != new_item.audio_channels and
                    old_item.audio_channels is not None and new_item.audio_channels is not None):
                changes.append({
                    'type': 'audio_channels',
                    'field': 'audio_channels',
                    'old_value': old_item.audio_channels,
                    'new_value': new_item.audio_channels,
                    'description': f"Audio channels changed from {old_item.audio_channels} to {new_item.audio_channels}"
                })

            # HDR status changes (display quality improvements)
            if self.watch_changes.get('hdr_status', True):
                old_hdr = self._normalize_hdr_status(old_item.video_range)
                new_hdr = self._normalize_hdr_status(new_item.video_range)

                if old_hdr != new_hdr:
                    changes.append({
                        'type': 'hdr_status',
                        'field': 'video_range',
                        'old_value': old_hdr,
                        'new_value': new_hdr,
                        'description': f"HDR status changed from {old_hdr} to {new_hdr}"
                    })

            # File size changes (complete file replacements)
            if (self.watch_changes.get('file_size', False) and
                    old_item.file_size != new_item.file_size and
                    old_item.file_size is not None and new_item.file_size is not None):
                # Only report significant size changes (>10% difference)
                size_diff_pct = abs(new_item.file_size - old_item.file_size) / old_item.file_size * 100
                if size_diff_pct > 10:
                    changes.append({
                        'type': 'file_size',
                        'field': 'file_size',
                        'old_value': old_item.file_size,
                        'new_value': new_item.file_size,
                        'description': f"File size changed significantly ({size_diff_pct:.1f}% difference)"
                    })

            # Subtitle changes (track count and language changes)
            if self.watch_changes.get('subtitles', True):
                # Check subtitle count changes
                old_sub_count = getattr(old_item, 'subtitle_count', 0) or 0
                new_sub_count = getattr(new_item, 'subtitle_count', 0) or 0
                
                if old_sub_count != new_sub_count:
                    changes.append({
                        'type': 'subtitles',
                        'field': 'subtitle_count',
                        'old_value': old_sub_count,
                        'new_value': new_sub_count,
                        'description': f"Subtitle tracks changed from {old_sub_count} to {new_sub_count}"
                    })
                
                # Check subtitle languages changes
                old_sub_langs = getattr(old_item, 'subtitle_languages', []) or []
                new_sub_langs = getattr(new_item, 'subtitle_languages', []) or []
                
                # Convert to sets for comparison
                old_langs_set = set(old_sub_langs) if old_sub_langs else set()
                new_langs_set = set(new_sub_langs) if new_sub_langs else set()
                
                added_langs = new_langs_set - old_langs_set
                removed_langs = old_langs_set - new_langs_set
                
                if added_langs or removed_langs:
                    if added_langs and not removed_langs:
                        desc = f"Added subtitle languages: {', '.join(sorted(added_langs))}"
                    elif removed_langs and not added_langs:
                        desc = f"Removed subtitle languages: {', '.join(sorted(removed_langs))}"
                    else:
                        desc = f"Subtitle languages changed (added: {', '.join(sorted(added_langs))}, removed: {', '.join(sorted(removed_langs))})"
                    
                    changes.append({
                        'type': 'subtitles',
                        'field': 'subtitle_languages',
                        'old_value': sorted(old_langs_set),
                        'new_value': sorted(new_langs_set),
                        'description': desc
                    })

            # Note: Provider ID changes are NOT tracked since they're not stored in the database
            # Provider IDs are fetched fresh from webhooks/API when needed for notifications

            # Log detection results for debugging and monitoring
            if changes:
                change_types = [change['type'] for change in changes]
                self.logger.debug(
                    f"Detected {len(changes)} changes for item {new_item.item_id}: {', '.join(change_types)}")
            else:
                self.logger.debug(f"No meaningful changes detected for item {new_item.item_id}")

        except Exception as e:
            # Log error but don't crash the webhook processing pipeline
            self.logger.error(f"Error detecting changes for item {new_item.item_id}: {e}")
            # Return empty list on error to allow processing to continue
            changes = []

        return changes

    async def is_rename(self, new_item: Union[MediaItem, DatabaseItem], 
                        existing_items: List[DatabaseItem]) -> tuple[bool, Optional[DatabaseItem]]:
        """
        Detect if a new item is actually a rename/move of an existing item.
        
        This method identifies when a file has been renamed or moved without content changes.
        It uses content hash and name comparison to detect renames without requiring
        ItemDeleted webhooks from Jellyfin.
        
        **Rename Detection Logic:**
        - Same content hash + same name = likely a rename/move
        - Different item_id (Jellyfin generates new IDs for renamed files)
        - No actual quality changes (verified by content hash)
        
        Args:
            new_item: The new item from webhook or sync
            existing_items: List of existing items from database
            
        Returns:
            tuple: (is_rename: bool, old_item: DatabaseItem or None)
                   Returns the old item if a rename is detected
        
        Example:
            ```python
            # Check if new webhook item is a rename
            existing = await db.get_items_by_name(new_item.name)
            is_rename, old_item = await detector.is_rename(new_item, existing)
            
            if is_rename:
                # Update database with new item_id, skip notification
                await db.replace_item(old_item.item_id, new_item)
            ```
        """
        # Get content hash for comparison
        new_hash = new_item.content_hash
        
        for existing_item in existing_items:
            # Check if same content (hash) and same name but different item_id
            if (existing_item.content_hash == new_hash and 
                existing_item.name == new_item.name and
                existing_item.item_id != new_item.item_id):
                
                self.logger.info(f"Rename detected for '{new_item.name}'")
                self.logger.debug(f"  Old ItemId: {existing_item.item_id}")
                self.logger.debug(f"  New ItemId: {new_item.item_id}")
                self.logger.debug(f"  Content Hash: {new_hash}")
                
                return True, existing_item
        
        return False, None
    
    @staticmethod
    def _normalize_hdr_status(video_range: str) -> str:
        """
        Normalize HDR status values for consistent comparison and reporting.

        This private method standardizes various HDR format names into consistent
        categories for change detection. Different sources might use different
        naming conventions for the same HDR formats.

        **HDR Format Normalization:**
        - SDR: Standard Dynamic Range (traditional video)
        - HDR10: Basic HDR with static metadata
        - HDR10+: Enhanced HDR with dynamic metadata
        - Dolby Vision: Premium HDR format with dynamic metadata
        - HLG: Hybrid Log-Gamma (broadcast HDR format)

        Args:
            video_range (str): Raw video range/HDR status from media metadata

        Returns:
            str: Normalized HDR status for consistent comparison

        Example:
            ```python
            # Internal normalization calls
            normalized = self._normalize_hdr_status("SMPTE2084")  # Returns "HDR10"
            normalized = self._normalize_hdr_status("DOVI")        # Returns "Dolby Vision"
            normalized = self._normalize_hdr_status(None)          # Returns "SDR"
            ```

        Note:
            This method handles various naming conventions and edge cases to
            provide consistent HDR status reporting across different media sources.
        """
        if not video_range:
            return "SDR"

        # Convert to lowercase for case-insensitive comparison
        range_lower = video_range.lower()

        # Map various HDR format indicators to standard names
        if any(hdr_indicator in range_lower for hdr_indicator in ['dovi', 'dolby', 'vision']):
            return "Dolby Vision"
        elif any(hdr_indicator in range_lower for hdr_indicator in ['hdr10+', 'hdr10plus']):
            return "HDR10+"
        elif any(hdr_indicator in range_lower for hdr_indicator in ['hdr10', 'hdr', 'smpte2084', 'bt2020']):
            return "HDR10"
        elif any(hdr_indicator in range_lower for hdr_indicator in ['hlg', 'hybrid']):
            return "HLG"
        else:
            return "SDR"

    def get_change_summary(self, changes: List[Dict[str, Any]]) -> str:
        """
        Generate a human-readable summary of detected changes for logging and notifications.

        This method creates a concise summary of all detected changes that can be
        used in log messages, Discord notifications, or administrative reports.
        It groups similar changes and provides an overview of upgrade types.

        **Summary Format:**
        The summary uses a structured format that highlights the most important
        changes first, followed by additional improvements:
        - "Resolution upgrade (720p → 1080p), codec improvement (h264 → hevc)"
        - "Audio enhancement (2ch → 6ch), HDR upgrade (SDR → HDR10)"
        - "Metadata update (added IMDb ID)"

        Args:
            changes (List[Dict[str, Any]]): List of detected changes from detect_changes()

        Returns:
            str: Human-readable summary of changes

        Example:
            ```python
            # Generate summary for Discord notification
            changes = detector.detect_changes(old_item, new_item)
            summary = detector.get_change_summary(changes)

            logger.info(summary)
            # Output: "Resolution upgrade (720p → 1080p), codec improvement (h264 → hevc), audio enhancement (2ch → 6ch)"

            # Use in Discord embed
            discord_embed = {
                "title": "Media Upgraded",
                "description": f"**Improvements:** {summary}"
            }
            ```

        Note:
            This method is useful for creating user-friendly change descriptions
            that can be displayed in Discord notifications or administrative
            dashboards without overwhelming users with technical details.
        """
        if not changes:
            return "No changes detected"

        try:
            summary_parts = []

            # Group changes by category for better readability
            change_categories = {
                'resolution': [],
                'video_codec': [],
                'audio_codec': [],
                'audio_channels': [],
                'hdr_status': [],
                'subtitles': [],
                'file_size': []
            }

            # Categorize changes
            for change in changes:
                change_type = change.get('type', 'unknown')
                if change_type in change_categories:
                    change_categories[change_type].append(change)

            # Build summary with prioritized order (most important first)
            priority_order = ['resolution', 'hdr_status', 'video_codec', 'audio_codec', 'audio_channels', 'subtitles', 'file_size']

            for category in priority_order:
                category_changes = change_categories[category]
                if not category_changes:
                    continue

                if category == 'resolution':
                    for change in category_changes:
                        summary_parts.append(f"Resolution upgrade ({change['old_value']}p → {change['new_value']}p)")

                elif category == 'hdr_status':
                    for change in category_changes:
                        summary_parts.append(f"HDR upgrade ({change['old_value']} → {change['new_value']})")

                elif category == 'video_codec':
                    for change in category_changes:
                        summary_parts.append(f"Codec improvement ({change['old_value']} → {change['new_value']})")

                elif category == 'audio_codec':
                    for change in category_changes:
                        summary_parts.append(f"Audio codec upgrade ({change['old_value']} → {change['new_value']})")

                elif category == 'audio_channels':
                    for change in category_changes:
                        old_ch = f"{change['old_value']}ch"
                        new_ch = f"{change['new_value']}ch"
                        summary_parts.append(f"Audio enhancement ({old_ch} → {new_ch})")

                elif category == 'subtitles':
                    for change in category_changes:
                        if change['field'] == 'subtitle_count':
                            summary_parts.append(f"Subtitle tracks ({change['old_value']} → {change['new_value']})")
                        elif change['field'] == 'subtitle_languages':
                            # Use the pre-formatted description for language changes
                            if 'Added' in change['description']:
                                summary_parts.append(change['description'])
                            else:
                                summary_parts.append("Subtitle languages changed")

                elif category == 'file_size':
                    summary_parts.append("File replacement")

            # Join summary parts with appropriate separators
            if len(summary_parts) <= 2:
                summary = " and ".join(summary_parts)
            else:
                summary = ", ".join(summary_parts[:-1]) + f", and {summary_parts[-1]}"

            self.logger.debug(f"Generated change summary: {summary}")
            return summary

        except Exception as e:
            self.logger.error(f"Error generating change summary: {e}")
            return f"{len(changes)} changes detected"