#!/usr/bin/env python3
"""
Jellynouncer Jellyfin API Client

This module provides a comprehensive async interface to the Jellyfin media server API.
It handles authentication, connection management, item retrieval, and data conversion
with robust error handling and retry logic for production reliability.

The JellyfinAPI class serves as the primary interface between Jellynouncer and Jellyfin,
abstracting away the complexities of the Jellyfin API while providing efficient access
to media metadata and library information.

Classes:
    JellyfinAPI: Async Jellyfin API client with retry logic and connection management

Author: Mark Newton
Project: Jellynouncer
Version: 1.0.0
License: MIT
"""

import asyncio
import time
import ssl
from datetime import datetime, timezone
import logging
from typing import Dict, Any, Optional, List, Callable, Union, Tuple, AsyncGenerator

from jellyfin_apiclient_python import JellyfinClient

from .config_models import JellyfinConfig
from .media_models import MediaItem
from .utils import get_logger


class JellyfinAPI:
    """
    Async Jellyfin API client with comprehensive error handling and retry logic.

    This class provides a high-level interface to the Jellyfin media server API,
    handling authentication, connection management, and data retrieval. It's designed
    for production use with robust error handling and automatic retry capabilities.

    **Understanding Jellyfin API Authentication:**

    Jellyfin supports multiple authentication methods, but this client uses API keys
    for service-to-service communication. API keys provide several advantages:

    **API Key Benefits:**
    - No password exposure in configuration files
    - Can be easily revoked and regenerated
    - Limited scope and permissions for security
    - Perfect for automated service authentication

    **Connection Management:**
    The client maintains connection state and automatically reconnects when needed.
    Connection health is checked periodically to ensure reliability during long
    running operations like library synchronization.

    **Retry Logic:**
    Network operations can fail for many reasons (temporary network issues,
    server restarts, high load). This client implements intelligent retry
    with exponential backoff to handle temporary failures gracefully.

    Attributes:
        config (JellyfinConfig): Jellyfin server configuration settings
        logger (logging.Logger): Logger instance for API operations
        client (JellyfinClient): Official Jellyfin API client instance
        last_connection_check (float): Timestamp of last connection verification
        connection_check_interval (int): Seconds between connection health checks
        max_retries (int): Maximum connection attempts before giving up
        retry_delay (int): Base delay between connection retry attempts

    Example:
        ```python
        # Initialize and connect to Jellyfin
        jellyfin_config = JellyfinConfig(
            server_url="http://jellyfin:8096",
            api_key="your_api_key_here",
            user_id="your_user_id_here"
        )

        jellyfin_api = JellyfinAPI(jellyfin_config, logger)

        # Establish connection with retry logic
        if await jellyfin_api.connect():
            logger.info("Successfully connected to Jellyfin")

            # Get specific item details
            item_data = await jellyfin_api.get_item("item_id_123")
            if item_data:
                media_item = jellyfin_api.extract_media_item(item_data)
                logger.info(f"Retrieved: {media_item.name}")

            # Batch retrieve library items
            all_items = await jellyfin_api.get_all_items(batch_size=100)
            logger.info(f"Found {len(all_items)} items in library")
        else:
            logger.error("Failed to connect to Jellyfin server")
        ```

    Note:
        This class is designed to be long-lived and reused across multiple
        operations. The connection state is cached and periodically verified
        to minimize authentication overhead while ensuring reliability.
    """

    def __init__(self, config: JellyfinConfig):
        """
        Initialize Jellyfin API client with configuration and logging.

        Sets up the client with configuration parameters and initializes
        connection tracking variables. The actual connection is established
        separately via the connect() method.

        **Constructor Pattern:**
        This follows the pattern of lightweight construction with separate
        initialization. The constructor sets up the object state without
        performing expensive operations like network connections.

        Args:
            config (JellyfinConfig): Jellyfin server configuration including
                server URL, API key, and user ID

        Example:
            ```python
            config = JellyfinConfig(
                server_url="http://jellyfin:8096",
                api_key="your_api_key",
                user_id="your_user_id"
            )

            jellyfin_api = JellyfinAPI(config)
            logger.info(f"Jellyfin API client created for {config.server_url}")
            ```
        """
        self.config = config
        self.logger = get_logger("jellynouncer.jellyfin")
        self.client = None

        # Cache for server information with TTL
        self._cached_server_info = None
        self._server_info_cache_time = 0
        self._server_info_cache_ttl = 3600  # Cache server info for 1 hour

        # Connection management
        self.last_connection_check = 0
        self.connection_check_interval = 300  # 5 minutes
        self.max_retries = 3
        self.retry_delay = 2  # seconds

        self.logger.info(f"Jellyfin API client initialized for {config.server_url}")

    async def connect(self) -> bool:
        """
        Establish connection to Jellyfin server with retry logic.

        This method attempts to connect to the Jellyfin server using the
        configured API key and user ID. It implements retry logic with
        exponential backoff to handle temporary network issues.

        **Connection Process:**
        1. Create Jellyfin client instance
        2. Configure server URL and authentication
        3. Verify connection with test API call
        4. Log connection status and server information

        **Retry Strategy:**
        - Exponential backoff: 2s, 4s, 8s between retries
        - Maximum 3 connection attempts
        - Different error messages for different failure types

        Returns:
            bool: True if connection successful, False otherwise

        Example:
            ```python
            if await jellyfin_api.connect():
                logger.info("Ready to make API calls")
            else:
                logger.error("Cannot proceed without Jellyfin connection")
                return False
            ```

        Note:
            This method should be called once during service initialization.
            The connection is reused for all subsequent API calls.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                self.logger.debug(f"Jellyfin connection attempt {attempt}/{self.max_retries}")

                # Create and configure Jellyfin client
                self.client = JellyfinClient()
                self.client.config.app("Jellynouncer", "1.0.0", "jellynouncer", "1.0.0")

                # Auto-enable SSL verification for HTTPS URLs
                if self.config.server_url.lower().startswith('https://'):
                    self.client.config.data["auth.ssl"] = True
                    self.logger.debug("SSL verification enabled for HTTPS connection")
                else:
                    self.client.config.data["auth.ssl"] = False
                    self.logger.debug("SSL verification disabled for HTTP connection")

                # Set server and authentication
                self.client.config.data['auth.server'] = self.config.server_url
                self.client.config.data['auth.server-name'] = "Jellyfin Server"
                self.client.config.data['auth.user_id'] = self.config.user_id
                self.client.config.data['auth.token'] = self.config.api_key

                # Test connection with system info call
                system_info = await self.get_system_info()
                if system_info:
                    # Try different possible field names for version
                    server_name = system_info.get('ServerName', 'Unknown')
                    server_version = (
                        system_info.get('Version') or 
                        system_info.get('version') or 
                        system_info.get('ServerVersion') or 
                        system_info.get('serverVersion') or
                        'Unknown'
                    )

                    self.logger.info(f"Connected to Jellyfin server: {server_name} v{server_version}")
                    self.last_connection_check = time.time()
                    return True
                else:
                    raise Exception("Failed to retrieve system information")

            except ssl.SSLError as e:
                self.logger.error(f"SSL certificate verification failed: {e}")
                self.logger.error("Please ensure your Jellyfin server has a valid SSL certificate")

                if attempt == self.max_retries:
                    raise ConnectionError(f"SSL verification failed: {e}")

            except Exception as e:
                self.logger.warning(f"Connection attempt {attempt} failed: {e}")

                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                    self.logger.debug(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    self.logger.error(f"Failed to connect to Jellyfin after {self.max_retries} attempts")

        return False

    async def is_connected(self) -> bool:
        """
        Check if client is connected to Jellyfin server.

        This method verifies the connection status and optionally performs
        a health check if enough time has passed since the last check.
        It's designed to be lightweight for frequent calls.

        **Connection Verification Strategy:**
        - Cached result for recent checks (within 5 minutes)
        - Periodic health check with system info API call
        - Automatic reconnection on connection loss

        Returns:
            bool: True if connected and healthy, False otherwise

        Example:
            ```python
            if await jellyfin_api.is_connected():
                # Safe to make API calls
                items = await jellyfin_api.get_all_items()
            else:
                logger.warning("Jellyfin connection lost - attempting reconnect")
                await jellyfin_api.connect()
            ```

        Note:
            This method is called frequently, so it uses caching to minimize
            API calls while still ensuring connection reliability.
        """
        if not self.client:
            return False

        # Check if we need to verify connection health
        time_since_check = time.time() - self.last_connection_check

        if time_since_check > self.connection_check_interval:
            try:
                # Perform lightweight health check
                system_info = await self.get_system_info()
                if system_info:
                    self.last_connection_check = time.time()
                    self.logger.debug("Connection health check passed")
                    return True
                else:
                    self.logger.warning("Connection health check failed")
                    return False
            except Exception as e:
                self.logger.warning(f"Connection health check error: {e}")
                return False
        else:
            # Use cached connection status
            return True

    async def get_system_info(self) -> Optional[Dict[str, Any]]:
        """
        Get Jellyfin server system information with caching.

        This method retrieves basic system information from the Jellyfin server,
        including server name, version, and operational status. It's used for
        connection verification and diagnostic purposes.

        **System Information Uses:**
        - Connection health verification
        - Server identification in logs
        - Version compatibility checking
        - Diagnostic and monitoring data

        **Caching Strategy:**
        - Results cached for 1 hour to reduce API calls
        - Cache automatically refreshed after TTL expires
        - Significantly improves batch sync performance

        Returns:
            Optional[Dict[str, Any]]: System information dictionary if successful, None otherwise

        Example:
            ```python
            system_info = await jellyfin_api.get_system_info()
            if system_info:
                logger.info(f"Server: {system_info['ServerName']} v{system_info['Version']}")
                logger.info(f"Operating System: {system_info.get('OperatingSystem', 'Unknown')}")
            ```

        Note:
            This method is used internally for connection verification but
            can also be called directly for diagnostic purposes.
            Results are cached for 1 hour to reduce API calls during batch operations.
        """
        # Return cached info if still valid
        if (self._cached_server_info and 
            time.time() - self._server_info_cache_time < self._server_info_cache_ttl):
            self.logger.debug("Returning cached server info")
            return self._cached_server_info
        
        if not self.client:
            return None

        try:
            # First try to get public system info which contains version
            try:
                public_info = self.client.jellyfin.try_server()
                if public_info:
                    self.logger.debug("Successfully retrieved public system information")
                    self.logger.debug(f"Public system info response type: {type(public_info)}")
                    self.logger.debug(f"Public system info keys: {list(public_info.keys()) if isinstance(public_info, dict) else 'Not a dict'}")
                    
                    if isinstance(public_info, dict):
                        self.logger.debug(f"ServerName: {public_info.get('ServerName', 'Not found')}")
                        self.logger.debug(f"Version: {public_info.get('Version', 'Not found')}")
                        self.logger.debug(f"ProductName: {public_info.get('ProductName', 'Not found')}")
                        self.logger.debug(f"LocalAddress: {public_info.get('LocalAddress', 'Not found')}")
                        self.logger.debug(f"Id: {public_info.get('Id', 'Not found')}")
                        # Cache the server info
                        self._cached_server_info = public_info
                        self._server_info_cache_time = time.time()
                    
                    return public_info
            except Exception as e:
                self.logger.debug(f"Could not get public system info: {e}")
            
            # Fallback to configuration endpoint (doesn't have version but better than nothing)
            response = self.client.jellyfin.get_system_info()
            if response:
                self.logger.debug("Successfully retrieved system configuration")
                self.logger.debug(f"System config response type: {type(response)}")
                
                # Cache the server info
                self._cached_server_info = response
                self._server_info_cache_time = time.time()
                
                # This endpoint doesn't have version, but return it anyway
                return response
            else:
                self.logger.warning("Empty response from system info API")
                return None
        except Exception as e:
            self.logger.error(f"Failed to get system info: {e}")
            return None

    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve detailed information for a specific media item.

        This method fetches comprehensive metadata for a single item from
        Jellyfin, including media streams, provider IDs, and extended metadata
        not available in webhook payloads.

        **API Call Details:**
        Uses Jellyfin's Items API WITHOUT field filtering to get ALL available
        metadata. This is intentionally different from get_all_items() which
        uses minimal fields for performance during sync operations.

        Args:
            item_id (str): Unique Jellyfin item identifier

        Returns:
            Optional[Dict[str, Any]]: Item data dictionary if found, None otherwise

        Example:
            ```python
            # Get detailed item information
            item_data = await jellyfin_api.get_item("abc123def456")
            if item_data:
                logger.info(f"Item: {item_data['Name']}")
                logger.info(f"Type: {item_data['Type']}")

                # Convert to MediaItem for internal use
                media_item = await jellyfin_api.convert_to_media_item(item_data)
            else:
                logger.warning("Item not found or access denied")
            ```

        Note:
            This method requires an active connection. It will return None
            if the connection is lost or the item doesn't exist/isn't accessible.
        """
        if not await self.is_connected():
            self.logger.error("Cannot retrieve item: not connected to Jellyfin")
            return None

        try:
            # Request comprehensive item data with all metadata fields
            response = self.client.jellyfin.get_item(item_id)

            if response:
                self.logger.debug(f"Retrieved item: {response.get('Name', 'Unknown')} ({item_id})")
                return response
            else:
                self.logger.warning(f"Item not found: {item_id}")
                return None

        except Exception as e:
            self.logger.error(f"Failed to retrieve item {item_id}: {e}")
            return None

    def _calculate_optimal_batch_size(self, total_items: int) -> int:
        """
        Calculate optimal batch size based on library size.
        
        Adaptive sizing ensures good performance across different library sizes:
        - Small libraries (<1000): Use smaller batches for quick response
        - Medium libraries (1000-10000): Balanced batch size
        - Large libraries (>10000): Larger batches to reduce API calls
        
        Args:
            total_items: Total number of items in library
            
        Returns:
            int: Optimal batch size (100-500)
        """
        if total_items < 1000:
            return 100  # Small library, small batches
        elif total_items < 10000:
            return 200  # Medium library, balanced
        else:
            return 500  # Large library, but controlled for stability
    
    def _calculate_request_timeout(self, batch_size: int) -> float:
        """
        Calculate dynamic timeout based on batch size.
        
        Formula: base_timeout + (batch_size * per_item_overhead) + buffer
        This prevents timeouts on large batches while keeping responsiveness.
        
        Args:
            batch_size: Number of items in the batch
            
        Returns:
            float: Timeout in seconds
        """
        base_timeout = 30  # Base timeout for any request
        per_item_overhead = 0.015  # 15ms per item for processing
        network_buffer = 10  # Extra buffer for network latency
        
        timeout = base_timeout + (batch_size * per_item_overhead) + network_buffer
        return min(timeout, 120)  # Cap at 2 minutes max
    
    async def get_server_stats(self) -> Dict[str, Any]:
        """
        Collect comprehensive server statistics from Jellyfin.
        
        Returns:
            Dictionary containing server stats
        """
        try:
            stats = {}
            
            # Get server info
            try:
                server_info = self.client.jellyfin.get_system_info()
                if server_info:
                    stats['server_name'] = server_info.get('ServerName', 'Unknown')
                    stats['server_version'] = server_info.get('Version', 'Unknown')
                    stats['server_id'] = server_info.get('Id', 'Unknown')
                    stats['server_status'] = 'online'
            except Exception as e:
                self.logger.warning(f"Could not get server info: {e}")
                stats['server_status'] = 'error'
                stats['last_error'] = str(e)
            
            # Get user statistics
            try:
                users = self.client.jellyfin.get_users()
                stats['total_users'] = len(users) if users else 0
                # Count active users (logged in within last 30 days)
                active_count = 0
                if users:
                    for user in users:
                        if user.get('LastActivityDate'):
                            last_activity = datetime.fromisoformat(user['LastActivityDate'].replace('Z', '+00:00'))
                            if (datetime.now(timezone.utc) - last_activity).days <= 30:
                                active_count += 1
                stats['active_users'] = active_count
            except Exception as e:
                self.logger.warning(f"Could not get user stats: {e}")
            
            # Get library statistics
            try:
                libraries = self.client.jellyfin.get_views()
                library_stats = {}
                total_items = 0
                movie_count = 0
                series_count = 0
                episode_count = 0
                music_count = 0
                music_album_count = 0
                photo_count = 0
                book_count = 0
                
                if libraries and 'Items' in libraries:
                    for library in libraries['Items']:
                        lib_name = library.get('Name', 'Unknown')
                        lib_type = library.get('CollectionType', 'mixed')
                        lib_id = library.get('Id')
                        
                        # Get item count for this library
                        try:
                            lib_items = self.client.jellyfin.user_items(
                                params={
                                    'ParentId': lib_id,
                                    'Recursive': True,
                                    'Limit': 1,
                                    'IncludeItemTypes': 'Movie,Series,Episode,Audio,MusicAlbum,Photo,Book'
                                }
                            )
                            
                            item_count = lib_items.get('TotalRecordCount', 0) if lib_items else 0
                            total_items += item_count
                            
                            library_stats[lib_name] = {
                                'type': lib_type,
                                'id': lib_id,
                                'item_count': item_count
                            }
                            
                            # Count by type
                            if lib_type == 'movies':
                                movie_count += item_count
                            elif lib_type == 'tvshows':
                                # Get series and episode counts separately
                                series_items = self.client.jellyfin.user_items(
                                    params={'ParentId': lib_id, 'Recursive': True, 'Limit': 1, 'IncludeItemTypes': 'Series'}
                                )
                                episode_items = self.client.jellyfin.user_items(
                                    params={'ParentId': lib_id, 'Recursive': True, 'Limit': 1, 'IncludeItemTypes': 'Episode'}
                                )
                                series_count += series_items.get('TotalRecordCount', 0) if series_items else 0
                                episode_count += episode_items.get('TotalRecordCount', 0) if episode_items else 0
                            elif lib_type == 'music':
                                music_count += item_count
                                album_items = self.client.jellyfin.user_items(
                                    params={'ParentId': lib_id, 'Recursive': True, 'Limit': 1, 'IncludeItemTypes': 'MusicAlbum'}
                                )
                                music_album_count += album_items.get('TotalRecordCount', 0) if album_items else 0
                            elif lib_type == 'photos':
                                photo_count += item_count
                            elif lib_type == 'books':
                                book_count += item_count
                                
                        except Exception as e:
                            self.logger.warning(f"Could not get stats for library {lib_name}: {e}")
                
                stats['total_items'] = total_items
                stats['movie_count'] = movie_count
                stats['series_count'] = series_count
                stats['episode_count'] = episode_count
                stats['music_count'] = music_count
                stats['music_album_count'] = music_album_count
                stats['photo_count'] = photo_count
                stats['book_count'] = book_count
                stats['library_stats'] = library_stats
                
            except Exception as e:
                self.logger.warning(f"Could not get library stats: {e}")
            
            # Get system info
            try:
                system_info = self.client.jellyfin.get_system_info()
                if system_info:
                    stats['system_info'] = {
                        'operating_system': system_info.get('OperatingSystem', 'Unknown'),
                        'architecture': system_info.get('SystemArchitecture', 'Unknown'),
                        'has_update': system_info.get('HasUpdateAvailable', False),
                        'encoding_threads': system_info.get('EncodingThreadCount', 0),
                        'transcoding_temp_path': system_info.get('TranscodingTempPath', ''),
                        'cache_path': system_info.get('CachePath', ''),
                    }
            except Exception as e:
                self.logger.warning(f"Could not get system info: {e}")
            
            # Get plugin info
            try:
                plugins = self.client.jellyfin.get_plugins()
                if plugins:
                    plugin_list = []
                    for plugin in plugins:
                        plugin_list.append({
                            'name': plugin.get('Name', 'Unknown'),
                            'version': plugin.get('Version', 'Unknown'),
                            'enabled': plugin.get('Status', '') == 'Active'
                        })
                    stats['plugin_stats'] = plugin_list
            except Exception as e:
                self.logger.warning(f"Could not get plugin info: {e}")
            
            # Calculate storage size (approximate based on media items)
            # This is a rough estimate - actual implementation would need different approach
            stats['total_size_gb'] = 0  # Would need to aggregate from individual items
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to collect server stats: {e}")
            return {
                'server_status': 'error',
                'last_error': str(e)
            }
    
    async def get_all_items(self,
                            batch_size: Optional[int] = None,
                            progress_callback: Optional[Callable[[int, int], None]] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all items from Jellyfin library with efficient batch processing.

        This method implements paginated retrieval to handle large libraries
        efficiently without overwhelming the server or consuming excessive memory.
        It supports progress callbacks for monitoring long-running operations.

        **Pagination Strategy:**
        - Requests items in configurable batch sizes
        - Processes batches sequentially to control memory usage
        - Continues until all items are retrieved
        - Handles API rate limiting gracefully

        **Memory Efficiency:**
        Large libraries can contain thousands of items. Batch processing
        prevents memory exhaustion and provides better progress feedback.

        **Optimized Field Selection:**
        This method now requests only the specific fields that correspond to
        webhook payload data, improving API performance and reducing bandwidth.
        Fields are mapped directly to webhook field equivalents for complete
        synchronization coverage.

        Args:
            batch_size (Optional[int]): Number of items per request. If None, uses adaptive sizing
            progress_callback (Optional[Callable[[int, int], None]]): Optional callback
                function called with (current_count, total_count) for progress updates

        Returns:
            List[Dict[str, Any]]: List of all library items with webhook-equivalent metadata

        Example:
            ```python
            # Simple retrieval
            all_items = await jellyfin_api.get_all_items()
            logger.info(f"Retrieved {len(all_items)} items from library")

            # With progress callback
            def show_progress(current, total):
                pct = (current / total) * 100 if total > 0 else 0
                logger.info(f"Library sync progress: {current}/{total} ({pct:.1f}%)")

            all_items = await jellyfin_api.get_all_items(
                batch_size=50,
                progress_callback=show_progress
            )
            ```

        Note:
            This method can take significant time for large libraries.
            Use the progress callback to provide user feedback during
            long-running operations like initial library synchronization.
        """
        if not await self.is_connected():
            self.logger.error("Cannot retrieve items: not connected to Jellyfin")
            return []

        try:
            all_items = []
            start_index = 0
            
            # Hardcoded optimal API request delay (based on research of other projects)
            api_request_delay = 0.1  # 100ms between requests, standard for Jellyfin projects
            
            # Get initial count to determine adaptive batch size
            if batch_size is None:
                # Make a small request to get total count
                initial_response = self.client.jellyfin.user_items(
                    params={
                        'StartIndex': 0,
                        'Limit': 1,
                        'Recursive': True
                    }
                )
                if initial_response and 'TotalRecordCount' in initial_response:
                    total_record_count = initial_response['TotalRecordCount']
                    batch_size = self._calculate_optimal_batch_size(total_record_count)
                    self.logger.info(f"Library has {total_record_count} items, using adaptive batch size of {batch_size}")
                else:
                    batch_size = 200  # Default if we can't get count
                    self.logger.info(f"Could not determine library size, using default batch size of {batch_size}")
            else:
                self.logger.info(f"Using specified batch size of {batch_size}")
            
            # Calculate timeout for this batch size
            request_timeout = self._calculate_request_timeout(batch_size)
            self.logger.debug(f"Using request timeout of {request_timeout:.1f} seconds for batch size {batch_size}")

            while True:
                try:
                    # Request ONLY fields needed for DatabaseItem and content hash
                    # This minimal field set reduces API payload by ~70% for faster syncing
                    # Note: Path field removed - rename detection uses content hash + name instead
                    sync_fields = ",".join([
                        # Media stream information (required for change detection)
                        "MediaStreams",  # → Video/Audio/Subtitle specs for content hash
                        "MediaSources",  # → File size and container info

                        # TV Series hierarchy (required for episode identification)
                        "IndexNumber",  # → Episode/Season number
                        "ParentIndexNumber",  # → Season number for episodes
                        "SeriesName",  # → Series name for episodes
                        "SeriesId",  # → Series ID for hierarchy
                        "SeasonId",  # → Season ID for hierarchy
                        "ProductionYear"  # → Year for identification
                    ])

                    # Add delay between requests to avoid overwhelming the server
                    if start_index > 0:  # No delay for first request
                        await asyncio.sleep(api_request_delay)
                    
                    response = self.client.jellyfin.user_items(
                        params={
                            'StartIndex': start_index,
                            'Limit': batch_size,
                            'Recursive': True,
                            'Fields': sync_fields,
                            'IncludeItemTypes': 'Movie,Series,Season,Episode,Audio,MusicAlbum,MusicArtist,MusicVideo,Video'
                        }
                    )

                    if not response or 'Items' not in response:
                        self.logger.warning(f"Empty or invalid response at index {start_index}")
                        break

                    batch_items = response['Items']
                    total_record_count = response.get('TotalRecordCount', 0)

                    if not batch_items:
                        self.logger.debug("No more items to retrieve")
                        break

                    all_items.extend(batch_items)

                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(len(all_items), total_record_count)

                    self.logger.info(f"Retrieved batch: {len(batch_items)} items (total: {len(all_items)})")

                    # Check if we've retrieved all items
                    if len(all_items) >= total_record_count:
                        break

                    start_index += batch_size

                    # Brief pause to avoid overwhelming the server
                    await asyncio.sleep(0.1)

                except Exception as e:
                    self.logger.error(f"Error retrieving batch at index {start_index}: {e}")
                    break

            self.logger.info(f"Library retrieval completed: {len(all_items)} items retrieved")
            return all_items

        except Exception as e:
            self.logger.error(f"Failed to retrieve library items: {e}")
            return []

    async def get_items_stream(
        self,
        batch_size: Optional[int] = None
    ) -> AsyncGenerator[Tuple[List[Dict[str, Any]], int], None]:
        """
        Stream library items in batches as an async generator.
        
        This method yields batches of items as they're fetched from the Jellyfin API,
        enabling true streaming processing without accumulating all items in memory.
        Each yield provides a tuple of (batch_items, total_count) to track progress.
        
        **Streaming Architecture:**
        - Yields batches immediately after fetching from API
        - No accumulation of items in memory
        - Enables concurrent processing while fetching continues
        - Provides backpressure control through async iteration
        
        **Memory Efficiency:**
        - Only one batch in memory at a time within the generator
        - Garbage collection happens naturally after each yield
        - Suitable for libraries with millions of items
        
        **Error Handling:**
        - Yields successfully fetched batches even if later batches fail
        - Logs errors but continues attempting to fetch remaining batches
        - Consumer can decide how to handle partial results
        
        Args:
            batch_size (Optional[int]): Number of items per request. If None, uses adaptive sizing
            
        Yields:
            Tuple[List[Dict[str, Any]], int]: Tuple of (batch_items, total_record_count)
                where batch_items is the current batch and total_record_count is the
                total number of items in the library for progress tracking
                
        Example:
            ```python
            # Stream and process batches as they arrive
            async for batch, total_count in jellyfin_api.get_items_stream(batch_size=50):
                logger.info(f"Processing batch of {len(batch)} items (total: {total_count})")
                
                # Process batch immediately without waiting for all items
                for item in batch:
                    await process_item(item)
                    
                # Calculate progress
                items_processed += len(batch)
                progress = (items_processed / total_count) * 100
                logger.info(f"Progress: {progress:.1f}%")
            ```
            
        Note:
            This generator maintains connection to Jellyfin throughout iteration.
            Ensure proper exception handling in the consumer to avoid connection leaks.
        """
        if not await self.is_connected():
            self.logger.error("Cannot stream items: not connected to Jellyfin")
            return
            
        try:
            start_index = 0
            total_record_count = None  # Initialize to None to avoid reference before assignment
            
            # Hardcoded optimal API request delay
            api_request_delay = 0.1  # 100ms between requests
            
            # Get initial count to determine adaptive batch size if not specified
            if batch_size is None:
                initial_response = self.client.jellyfin.user_items(
                    params={
                        'StartIndex': 0,
                        'Limit': 1,
                        'Recursive': True
                    }
                )
                if initial_response and 'TotalRecordCount' in initial_response:
                    total_record_count = initial_response['TotalRecordCount']
                    batch_size = self._calculate_optimal_batch_size(total_record_count)
                    self.logger.info(f"Library streaming: {total_record_count} items, using adaptive batch size of {batch_size}")
                else:
                    batch_size = 200  # Default if we can't get count
                    self.logger.info(f"Library streaming: using default batch size of {batch_size}")
            else:
                self.logger.info(f"Library streaming: using specified batch size of {batch_size}")
            
            while True:
                try:
                    # Use minimal sync fields for streaming (same as get_all_items)
                    sync_fields = ",".join([
                        # Media stream information (required for change detection)
                        "MediaStreams",  # → Video/Audio/Subtitle specs for content hash
                        "MediaSources",  # → File size and container info
                        # TV Series hierarchy (required for episode identification)
                        "IndexNumber",  # → Episode/Season number
                        "ParentIndexNumber",  # → Season number for episodes
                        "SeriesName",  # → Series name for episodes
                        "SeriesId",  # → Series ID for hierarchy
                        "SeasonId",  # → Season ID for hierarchy
                        "ProductionYear"  # → Year for identification
                    ])
                    
                    # Add delay between requests to avoid overwhelming the server
                    if start_index > 0:  # No delay for first request
                        await asyncio.sleep(api_request_delay)
                    
                    response = self.client.jellyfin.user_items(
                        params={
                            'StartIndex': start_index,
                            'Limit': batch_size,
                            'Recursive': True,
                            'Fields': sync_fields,
                            'IncludeItemTypes': 'Movie,Series,Season,Episode,Audio,MusicAlbum,Book,Photo',
                            'EnableTotalRecordCount': True
                        }
                    )
                    
                    batch_items = response.get('Items', [])
                    total_record_count = response.get('TotalRecordCount', 0)
                    
                    if not batch_items:
                        self.logger.debug("No more items to retrieve")
                        break
                        
                    # Yield the batch immediately for streaming processing
                    yield batch_items, total_record_count
                    
                    self.logger.debug(
                        f"Streamed batch at index {start_index}: {len(batch_items)} items "
                        f"(total: {total_record_count})"
                    )
                    
                    # Check if we've retrieved all items
                    if start_index + len(batch_items) >= total_record_count:
                        break
                        
                    start_index += batch_size
                    
                    # Brief pause to avoid overwhelming the server
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(f"Error retrieving batch at index {start_index}: {e}")
                    # Continue trying to fetch remaining batches
                    start_index += batch_size
                    if total_record_count and start_index >= total_record_count:
                        break
                    await asyncio.sleep(1)  # Wait longer after an error
                    
            self.logger.info("Library streaming completed")
            
        except Exception as e:
            self.logger.error(f"Failed during library streaming: {e}")
            # Generator will naturally terminate on exception
            
    async def convert_to_database_item(self, item_data: Dict[str, Any]):
        """
        Convert Jellyfin API response directly to DatabaseItem for efficient syncs.
        
        This method extracts only the essential fields needed for database storage
        and change detection, skipping all the extra metadata that's not needed
        during syncs. This significantly speeds up sync operations.
        
        Args:
            item_data: Raw item data from Jellyfin API
            
        Returns:
            DatabaseItem: Slim item for database storage
            
        Example:
            ```python
            # During sync - fast conversion to DatabaseItem
            item_data = await jellyfin_api.get_item("item123")
            db_item = await jellyfin_api.convert_to_database_item(item_data)
            await database.save_item(db_item)
            ```
        """
        from .database_models import DatabaseItem
        
        try:
            # Extract only essential fields for database storage
            item_id = item_data.get('Id', 'unknown')
            name = item_data.get('Name', 'Unknown Item')
            item_type = item_data.get('Type', 'Unknown')
            
            # TV series data
            series_name = item_data.get('SeriesName')
            series_id = item_data.get('SeriesId')
            season_number = item_data.get('ParentIndexNumber')
            episode_number = item_data.get('IndexNumber')
            year = item_data.get('ProductionYear')
            
            # File information
            file_path = item_data.get('Path')
            file_size = None
            library_name = None
            
            # Get file size from MediaSources
            if item_data.get('MediaSources'):
                for source in item_data['MediaSources']:
                    if 'Size' in source:
                        file_size = source['Size']
                        break
            
            # Process media streams for technical specs
            media_streams = []
            if item_data.get('MediaSources'):
                for source in item_data['MediaSources']:
                    if 'MediaStreams' in source:
                        media_streams.extend(source['MediaStreams'])
            elif 'MediaStreams' in item_data:
                media_streams = item_data['MediaStreams']
            
            # Extract video specs (only first stream for efficiency)
            video_height = None
            video_width = None
            video_codec = None
            video_profile = None
            video_range = None
            video_framerate = None
            video_bitrate = None
            video_bitdepth = None
            
            video_streams = [s for s in media_streams if s.get('Type') == 'Video']
            if video_streams:
                video = video_streams[0]
                video_height = video.get('Height')
                video_width = video.get('Width')
                video_codec = video.get('Codec')
                video_profile = video.get('Profile')
                video_range = video.get('VideoRange')
                video_framerate = video.get('RealFrameRate')
                video_bitrate = video.get('BitRate')
                video_bitdepth = video.get('BitDepth')
            
            # Extract audio specs (only first stream for efficiency)
            audio_codec = None
            audio_channels = None
            audio_language = None
            audio_bitrate = None
            audio_samplerate = None
            
            audio_streams = [s for s in media_streams if s.get('Type') == 'Audio']
            if audio_streams:
                audio = audio_streams[0]
                audio_codec = audio.get('Codec')
                audio_channels = audio.get('Channels')
                audio_language = audio.get('Language')
                audio_bitrate = audio.get('BitRate')
                audio_samplerate = audio.get('SampleRate')
            
            # Process subtitle information for change detection
            subtitle_streams = [s for s in media_streams if s.get('Type') == 'Subtitle']
            subtitle_count = len(subtitle_streams)
            subtitle_languages = []
            subtitle_formats = []
            
            for sub_stream in subtitle_streams:
                lang = sub_stream.get('Language')
                if lang and lang not in subtitle_languages:
                    subtitle_languages.append(lang)
                
                codec = sub_stream.get('Codec')
                if codec and codec not in subtitle_formats:
                    subtitle_formats.append(codec)
            
            # Create DatabaseItem with only essential fields
            return DatabaseItem(
                item_id=item_id,
                name=name,
                item_type=item_type,
                series_name=series_name,
                series_id=series_id,
                season_number=season_number,
                episode_number=episode_number,
                year=year,
                video_height=video_height,
                video_width=video_width,
                video_codec=video_codec,
                video_profile=video_profile,
                video_range=video_range,
                video_framerate=video_framerate,
                video_bitrate=video_bitrate,
                video_bitdepth=video_bitdepth,
                audio_codec=audio_codec,
                audio_channels=audio_channels,
                audio_language=audio_language,
                audio_bitrate=audio_bitrate,
                audio_samplerate=audio_samplerate,
                subtitle_count=subtitle_count,
                subtitle_languages=subtitle_languages,
                subtitle_formats=subtitle_formats,
                file_path=file_path,
                file_size=file_size,
                library_name=library_name
            )
            
        except Exception as e:
            self.logger.error(f"Failed to convert item to DatabaseItem: {e}")
            # Return minimal DatabaseItem to prevent complete failure
            return DatabaseItem(
                item_id=item_data.get('Id', 'unknown'),
                name=item_data.get('Name', 'Unknown Item'),
                item_type=item_data.get('Type', 'Unknown')
            )
    
    async def convert_to_media_item(self, item_data: Dict[str, Any]) -> MediaItem:
        """
        Convert Jellyfin API response to internal MediaItem format.

        This method transforms the complex Jellyfin API response format into
        our simplified MediaItem dataclass, extracting and normalizing the
        most important metadata fields for notification purposes.

        **Data Transformation Process:**
        1. Extract basic metadata (name, type, year, etc.)
        2. Parse media stream information (video/audio specs)
        3. Extract provider IDs (IMDb, TMDb, TVDb)
        4. Normalize and clean data values
        5. Generate content hash for change detection

        **Stream Processing:**
        Jellyfin provides detailed media stream information including multiple
        video and audio tracks. This method extracts the primary streams and
        their technical specifications.

        **Enhanced Field Mapping:**
        This method now maps ALL webhook fields to ensure complete database
        synchronization and template compatibility. It includes server information,
        comprehensive media stream data, TV series hierarchy, timestamps, and
        all technical specifications that appear in webhook payloads.

        Args:
            item_data (Dict[str, Any]): Raw item data from Jellyfin API

        Returns:
            MediaItem: Normalized media item for internal use

        Example:
            ```python
            # Convert API response to MediaItem
            raw_data = await jellyfin_api.get_item("item123")
            if raw_data:
                media_item = await jellyfin_api.convert_to_media_item(raw_data)

                logger.info(f"Converted: {media_item.name}")
                logger.info(f"Quality: {media_item.video_height}p")
                logger.info(f"Codec: {media_item.video_codec}")
            ```

        Note:
            This method handles missing or malformed data gracefully,
            providing sensible defaults to ensure MediaItem creation
            succeeds even with incomplete Jellyfin data.
        """
        try:
            # ==================== DEBUG LOGGING ====================
            self.logger.debug("=" * 60)
            self.logger.debug(f"JELLYFIN API RESPONSE DEBUG for item: {item_data.get('Name', 'Unknown')}")
            self.logger.debug(f"Item Type: {item_data.get('Type', 'Unknown')}")
            self.logger.debug(f"Item ID: {item_data.get('Id', 'Unknown')}")

            # Log the ImageTags structure
            image_tags = item_data.get('ImageTags', {})
            self.logger.debug(f"ImageTags present: {bool(image_tags)}")
            if image_tags:
                self.logger.debug(f"ImageTags content: {image_tags}")
                self.logger.debug(f"  - Primary: {image_tags.get('Primary', 'NOT SET')}")
                self.logger.debug(f"  - Backdrop: {image_tags.get('Backdrop', 'NOT SET')}")
                self.logger.debug(f"  - Logo: {image_tags.get('Logo', 'NOT SET')}")
                self.logger.debug(f"  - Thumb: {image_tags.get('Thumb', 'NOT SET')}")
                self.logger.debug(f"  - Banner: {image_tags.get('Banner', 'NOT SET')}")
            else:
                self.logger.debug("No ImageTags in API response!")

            # Log episode-specific tags
            if item_data.get('Type') == 'Episode':
                self.logger.debug(f"SeriesPrimaryImageTag: {item_data.get('SeriesPrimaryImageTag', 'NOT SET')}")
                self.logger.debug(f"ParentBackdropImageTags: {item_data.get('ParentBackdropImageTags', 'NOT SET')}")
                self.logger.debug(f"ParentLogoImageTag: {item_data.get('ParentLogoImageTag', 'NOT SET')}")

            self.logger.debug("=" * 60)
            # ==================== CORE IDENTIFICATION ====================
            # Extract basic item information (always required)
            item_id = item_data.get('Id', '')
            name = item_data.get('Name', 'Unknown')
            item_type = item_data.get('Type', 'Unknown')
            year = item_data.get('ProductionYear')
            overview = item_data.get('Overview', '')

            # ==================== SERVER INFORMATION ====================
            # Server info for webhook compatibility (fetch if needed)
            server_id = None
            server_name = None
            server_version = None
            server_url = self.config.server_url

            # Try to get server info (using cached version if available)
            try:
                # get_system_info now handles caching internally
                server_info = await self.get_system_info()
                if server_info:
                    server_id = server_info.get('Id')
                    server_name = server_info.get('ServerName')
                    server_version = server_info.get('Version')
            except Exception as e:
                self.logger.debug(f"Could not fetch server info: {e}")

            # ==================== THUMBNAILS ====================
            # Add image tags from webhook data
            primary_image_tag = item_data.get('ImageTags', {}).get('Primary')
            backdrop_image_tag = item_data.get('ImageTags', {}).get('Backdrop')
            logo_image_tag = item_data.get('ImageTags', {}).get('Logo')
            thumb_image_tag = item_data.get('ImageTags', {}).get('Thumb')
            banner_image_tag = item_data.get('ImageTags', {}).get('Banner')

            # For episodes, also capture series image tags
            series_primary_image_tag = item_data.get('SeriesPrimaryImageTag')
            parent_backdrop_image_tag = item_data.get('ParentBackdropImageTags', [None])[0] if item_data.get(
                'ParentBackdropImageTags') else None
            parent_logo_image_tag = item_data.get('ParentLogoImageTag')

            # DEBUG: Log what we extracted
            self.logger.debug(f"Extracted image tags:")
            self.logger.debug(f"  primary_image_tag: {primary_image_tag}")
            self.logger.debug(f"  backdrop_image_tag: {backdrop_image_tag}")
            self.logger.debug(f"  logo_image_tag: {logo_image_tag}")
            self.logger.debug(f"  Type of primary_image_tag: {type(primary_image_tag)}")

            # ==================== PROVIDER IDS ====================
            # Extract external provider IDs (IMDb, TMDb, TVDb, etc.)
            provider_ids = item_data.get('ProviderIds', {})
            imdb_id = provider_ids.get('Imdb')
            tmdb_id = provider_ids.get('Tmdb')
            tvdb_id = provider_ids.get('Tvdb')
            tvdb_slug = provider_ids.get('Tvdbslug')
            
            # Debug logging for provider IDs
            if provider_ids:
                self.logger.debug(f"Provider IDs from Jellyfin for {item_data.get('Name', 'Unknown')}:")
                self.logger.debug(f"  - Raw ProviderIds: {provider_ids}")
                self.logger.debug(f"  - IMDB: {imdb_id}")
                self.logger.debug(f"  - TMDB: {tmdb_id}")
                self.logger.debug(f"  - TVDB: {tvdb_id}")
                self.logger.debug(f"  - TVDB Slug: {tvdb_slug}")
            else:
                self.logger.debug(f"No provider IDs found for {item_data.get('Name', 'Unknown')}")

            # ==================== TV SERIES HIERARCHY ====================
            # Extract TV series information for episodes and seasons
            series_name = item_data.get('SeriesName')
            series_id = item_data.get('SeriesId')
            series_premiere_date = None
            season_id = item_data.get('SeasonId')
            season_number = item_data.get('ParentIndexNumber')  # Season number for episodes
            episode_number = item_data.get('IndexNumber')  # Episode number for episodes
            air_time = item_data.get('AirTime')

            # For seasons, IndexNumber is the season number
            if item_type == 'Season':
                season_number = item_data.get('IndexNumber')

            # Generate padded season/episode numbers (webhook SeasonNumber00, etc.)
            season_number_padded = None
            season_number_padded_3 = None
            episode_number_padded = None
            episode_number_padded_3 = None

            if season_number is not None:
                season_number_padded = f"{season_number:02d}"
                season_number_padded_3 = f"{season_number:03d}"

            if episode_number is not None:
                episode_number_padded = f"{episode_number:02d}"
                episode_number_padded_3 = f"{episode_number:03d}"

            # ==================== RUNTIME INFORMATION ====================
            # Extract runtime and convert to different formats
            runtime_ticks = item_data.get('RunTimeTicks')
            runtime_formatted = None

            if runtime_ticks:
                # Convert ticks to HH:MM:SS format (10,000 ticks = 1ms)
                total_seconds = runtime_ticks // 10000000
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                runtime_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

            # ==================== MEDIA STREAM PROCESSING ====================
            # Extract comprehensive media stream information
            video_height = None
            video_width = None
            video_codec = None
            video_profile = None
            video_level = None
            video_framerate = None
            video_range = None
            video_interlaced = None
            video_bitrate = None
            video_bitdepth = None
            video_colorspace = None
            video_colortransfer = None
            video_colorprimaries = None
            video_pixelformat = None
            video_refframes = None
            aspect_ratio = None

            # Video stream properties for webhook compatibility
            video_title = None
            video_type = None
            video_language = None

            # Audio stream properties
            audio_codec = None
            audio_channels = None
            audio_bitrate = None
            audio_samplerate = None
            audio_title = None
            audio_type = None
            audio_language = None
            audio_default = None

            # Subtitle stream properties are extracted later from media_streams

            # Get media streams from different possible locations
            media_streams = []

            # Try MediaSources first (most common)
            if item_data.get('MediaSources'):
                for source in item_data['MediaSources']:
                    if 'MediaStreams' in source:
                        media_streams.extend(source['MediaStreams'])
            # Fallback to direct MediaStreams
            elif 'MediaStreams' in item_data:
                media_streams = item_data['MediaStreams']

            # Process video streams (map to Video_0_* webhook fields)
            video_streams = [s for s in media_streams if s.get('Type') == 'Video']
            if video_streams:
                video_stream = video_streams[0]  # Primary video stream

                # Core video properties
                video_height = video_stream.get('Height')
                video_width = video_stream.get('Width')
                video_codec = video_stream.get('Codec', '').lower()
                video_profile = video_stream.get('Profile')
                video_level = video_stream.get('Level')
                video_framerate = video_stream.get('RealFrameRate')
                video_range = video_stream.get('VideoRange', 'SDR')
                video_interlaced = video_stream.get('IsInterlaced')
                video_bitrate = video_stream.get('BitRate')
                aspect_ratio = video_stream.get('AspectRatio')

                # Extended video properties for webhook compatibility
                video_title = video_stream.get('DisplayTitle')
                video_type = 'Video'
                video_language = video_stream.get('Language')
                video_bitdepth = video_stream.get('BitDepth')
                video_colorspace = video_stream.get('ColorSpace')
                video_colortransfer = video_stream.get('ColorTransfer')
                video_colorprimaries = video_stream.get('ColorPrimaries')
                video_pixelformat = video_stream.get('PixelFormat')
                video_refframes = video_stream.get('RefFrames')

            # Process audio streams (map to Audio_0_* webhook fields)
            audio_streams = [s for s in media_streams if s.get('Type') == 'Audio']
            if audio_streams:
                audio_stream = audio_streams[0]  # Primary audio stream

                # Core audio properties
                audio_codec = audio_stream.get('Codec', '').lower()
                audio_channels = audio_stream.get('Channels')
                audio_bitrate = audio_stream.get('BitRate')
                audio_samplerate = audio_stream.get('SampleRate')

                # Extended audio properties for webhook compatibility
                audio_title = audio_stream.get('DisplayTitle')
                audio_type = 'Audio'
                audio_language = audio_stream.get('Language')
                audio_default = audio_stream.get('IsDefault')

            # Process subtitle streams for both single-stream webhook fields and aggregation
            subtitle_streams = [s for s in media_streams if s.get('Type') == 'Subtitle']
            
            # Single subtitle stream properties (for webhook compatibility)
            subtitle_title = None
            subtitle_type = None
            subtitle_language = None
            subtitle_codec = None
            subtitle_default = None
            subtitle_forced = None
            subtitle_external = None
            
            if subtitle_streams:
                # First subtitle stream for webhook compatibility
                subtitle_stream = subtitle_streams[0]
                subtitle_title = subtitle_stream.get('DisplayTitle')
                subtitle_type = 'Subtitle'
                subtitle_language = subtitle_stream.get('Language')
                subtitle_codec = subtitle_stream.get('Codec')
                subtitle_default = subtitle_stream.get('IsDefault')
                subtitle_forced = subtitle_stream.get('IsForced')
                subtitle_external = subtitle_stream.get('IsExternal')
            
            # Aggregate subtitle information for change detection
            subtitle_languages = []
            subtitle_formats = []
            
            for sub_stream in subtitle_streams:
                # Collect unique languages
                lang = sub_stream.get('Language')
                if lang and lang not in subtitle_languages:
                    subtitle_languages.append(lang)
                
                # Collect unique formats/codecs
                codec = sub_stream.get('Codec')
                if codec and codec not in subtitle_formats:
                    subtitle_formats.append(codec)

            # ==================== FILE INFORMATION ====================
            # Extract file system information
            file_path = item_data.get('Path')
            file_size = None
            library_name = None

            # Try to get file size from MediaSources
            if item_data.get('MediaSources'):
                for source in item_data['MediaSources']:
                    if 'Size' in source:
                        file_size = source['Size']
                        break

            # Try to extract library name from path or other sources
            # This may require additional API calls in some cases
            if 'ParentId' in item_data:
                # For episodes/seasons, the library info might be in parent data
                pass  # Could enhance this with additional API calls if needed

            # ==================== METADATA COLLECTIONS ====================
            # Extract collection information (genres, studios, tags)
            genres = []
            if 'Genres' in item_data:
                genres = [genre.get('Name', '') if isinstance(genre, dict) else str(genre)
                          for genre in item_data['Genres']]

            studios = []
            if 'Studios' in item_data:
                studios = [studio.get('Name', '') if isinstance(studio, dict) else str(studio)
                           for studio in item_data['Studios']]

            tags = item_data.get('Tags', [])

            # ==================== MUSIC-SPECIFIC FIELDS ====================
            # Handle music-specific metadata
            album = item_data.get('Album')
            album_artist = item_data.get('AlbumArtist')
            artists = []

            if item_type in ['Audio', 'MusicVideo', 'MusicAlbum']:
                # Extract artists from ArtistItems or Artists field
                if 'ArtistItems' in item_data:
                    artists = [artist.get('Name', '') for artist in item_data['ArtistItems']]
                elif 'Artists' in item_data:
                    artists = item_data['Artists']

            # ==================== TIMESTAMP INFORMATION ====================
            # Extract and format timestamp information
            current_time = datetime.now(timezone.utc)

            # Use current time for webhook-style timestamps
            timestamp = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + current_time.strftime('%z')
            if not timestamp.endswith('Z') and not timestamp[-6] in ['+', '-']:
                # Ensure proper timezone format
                utc_timestamp = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            else:
                utc_timestamp = current_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

            # Extract creation and modification dates
            date_created = item_data.get('DateCreated')
            date_modified = item_data.get('DateLastMediaAdded') or item_data.get('DateModified')
            premiere_date = item_data.get('PremiereDate', '')

            # ==================== ADDITIONAL METADATA ====================
            # Extract additional metadata fields
            official_rating = item_data.get('OfficialRating')
            tagline = item_data.get('Tagline', '')

            # ==================== PHOTO-SPECIFIC METADATA ====================
            # For image/photo content
            width = None
            height = None
            if item_type in ['Photo', 'Image']:
                width = item_data.get('Width')
                height = item_data.get('Height')

            # ==================== CREATE COMPREHENSIVE MEDIAITEM ====================
            # Create MediaItem with ALL webhook fields mapped
            media_item = MediaItem(
                # Core identification (required fields)
                item_id=item_id,
                name=name,
                item_type=item_type,

                # Server information
                server_id=server_id,
                server_name=server_name,
                server_version=server_version,
                server_url=server_url,

                # Content metadata
                year=year,
                series_name=series_name,
                season_number=season_number,
                episode_number=episode_number,
                overview=overview,

                # Image/thumbnail metadata
                primary_image_tag=primary_image_tag,
                backdrop_image_tag=backdrop_image_tag,
                logo_image_tag=logo_image_tag,
                thumb_image_tag=thumb_image_tag,
                banner_image_tag=banner_image_tag,
                series_primary_image_tag=series_primary_image_tag,
                parent_backdrop_image_tag=parent_backdrop_image_tag,
                parent_logo_image_tag=parent_logo_image_tag,

                # Video technical specifications
                video_height=video_height,
                video_width=video_width,
                video_codec=video_codec,
                video_profile=video_profile,
                video_range=video_range,
                video_framerate=video_framerate,
                aspect_ratio=aspect_ratio,

                # Additional video properties for webhook compatibility
                video_title=video_title,
                video_type=video_type,
                video_language=video_language,
                video_level=video_level,
                video_interlaced=video_interlaced,
                video_bitrate=video_bitrate,
                video_bitdepth=video_bitdepth,
                video_colorspace=video_colorspace,
                video_colortransfer=video_colortransfer,
                video_colorprimaries=video_colorprimaries,
                video_pixelformat=video_pixelformat,
                video_refframes=video_refframes,

                # Audio technical specifications
                audio_codec=audio_codec,
                audio_channels=audio_channels,
                audio_bitrate=audio_bitrate,
                audio_samplerate=audio_samplerate,

                # Additional audio properties for webhook compatibility
                audio_title=audio_title,
                audio_type=audio_type,
                audio_language=audio_language,
                audio_default=audio_default,

                # Subtitle information for webhook compatibility
                subtitle_title=subtitle_title,
                subtitle_type=subtitle_type,
                subtitle_language=subtitle_language,
                subtitle_codec=subtitle_codec,
                subtitle_default=subtitle_default,
                subtitle_forced=subtitle_forced,
                subtitle_external=subtitle_external,

                # External provider IDs
                imdb_id=imdb_id,
                tmdb_id=tmdb_id,
                tvdb_id=tvdb_id,
                tvdb_slug=tvdb_slug,

                # TV series hierarchy fields
                series_id=series_id,
                series_premiere_date=series_premiere_date,
                season_id=season_id,
                season_number_padded=season_number_padded,
                season_number_padded_3=season_number_padded_3,
                episode_number_padded=episode_number_padded,
                episode_number_padded_3=episode_number_padded_3,
                air_time=air_time,

                # File system information
                file_path=file_path,
                library_name=library_name,

                # Timestamp information
                timestamp=timestamp,
                utc_timestamp=utc_timestamp,
                premiere_date=premiere_date,

                # Extended metadata from API
                date_created=date_created,
                date_modified=date_modified,
                runtime_ticks=runtime_ticks,
                runtime_formatted=runtime_formatted,
                official_rating=official_rating,
                tagline=tagline,
                genres=genres,
                studios=studios,
                tags=tags,

                # Music-specific metadata
                album=album,
                artists=artists,
                album_artist=album_artist,

                # Photo-specific metadata
                width=width,
                height=height,

                # Internal tracking
                file_size=file_size
            )

            self.logger.debug(f"Converted Jellyfin item to comprehensive MediaItem: {name}")
            return media_item

        except Exception as e:
            self.logger.error(f"Failed to convert item data: {e}")
            # Return minimal MediaItem to prevent complete failure
            return MediaItem(
                item_id=item_data.get('Id', 'unknown'),
                name=item_data.get('Name', 'Unknown Item'),
                item_type=item_data.get('Type', 'Unknown'),
            )

    # jellyfin_api.py - Optimized enrichment method

    async def enrich_media_item_for_notification(
            self,
            media_item: MediaItem,
            item_data: Optional[Dict[str, Any]] = None,
            retry_on_failure: bool = True
    ) -> MediaItem:
        """
        Enrich a MediaItem with ADDITIONAL Jellyfin fields not present in webhook.

        This method adds fields that are useful for Discord notifications but
        aren't included in the webhook payload and don't need database storage.
        It only fetches and adds fields that are missing, not overwriting existing data.

        Args:
            media_item: Base MediaItem with webhook fields already populated
            item_data: Optional pre-fetched item data to avoid re-fetching
            retry_on_failure: Whether to retry once on API failure

        Returns:
            MediaItem: Same instance enriched with additional type-specific fields

        Note:
            Checks each field before setting to avoid overwriting webhook data.
            Only fetches fields that webhooks don't provide.
        """
        try:
            # Fetch full item data if not provided
            if not item_data:
                self.logger.debug(
                    f"Fetching additional data for enrichment: {media_item.item_id} ({media_item.item_type})")
                try:
                    item_data = await self.get_item(media_item.item_id)
                except Exception as e:
                    if retry_on_failure:
                        self.logger.warning(f"First enrichment fetch failed, retrying: {e}")
                        await asyncio.sleep(0.5)
                        try:
                            item_data = await self.get_item(media_item.item_id)
                        except Exception as retry_error:
                            self.logger.error(f"Enrichment fetch retry failed: {retry_error}")
                            return media_item
                    else:
                        self.logger.error(f"Enrichment fetch failed: {e}")
                        return media_item

            if not item_data:
                self.logger.warning(f"Could not fetch enrichment data for {media_item.item_id}")
                return media_item

            # Track fields we're adding for logging
            added_fields = []

            # ==================== FIELDS NOT IN WEBHOOK PAYLOAD ====================
            # Only add fields that webhooks don't provide

            # Original title (not in webhook)
            if not hasattr(media_item, 'original_title') or not media_item.original_title:
                media_item.original_title = item_data.get('OriginalTitle')
                if media_item.original_title:
                    added_fields.append('original_title')

            # Image tags beyond primary (webhook only has Video_0_PrimaryImageItemId)
            image_tags = item_data.get('ImageTags', {})
            if not hasattr(media_item, 'logo_image_tag'):
                media_item.logo_image_tag = image_tags.get('Logo')
                media_item.thumb_image_tag = image_tags.get('Thumb')
                media_item.banner_image_tag = image_tags.get('Banner')
                media_item.art_image_tag = image_tags.get('Art')
                media_item.disc_image_tag = image_tags.get('Disc')
                media_item.box_image_tag = image_tags.get('Box')
                if any([media_item.logo_image_tag, media_item.thumb_image_tag, media_item.banner_image_tag]):
                    added_fields.append('additional_images')

            # Backdrop images (not in webhook)
            if not hasattr(media_item, 'backdrop_image_tags'):
                media_item.backdrop_image_tags = item_data.get('BackdropImageTags', [])
                if media_item.backdrop_image_tags:
                    added_fields.append('backdrop_images')

            # Screenshots (not in webhook)
            if not hasattr(media_item, 'screenshot_image_tags'):
                media_item.screenshot_image_tags = item_data.get('ScreenshotImageTags', [])
                if media_item.screenshot_image_tags:
                    added_fields.append('screenshots')

            # Ratings not in webhook
            if not hasattr(media_item, 'critic_rating') or media_item.critic_rating is None:
                media_item.critic_rating = item_data.get('CriticRating')
                media_item.critic_rating_summary = item_data.get('CriticRatingSummary')
                if media_item.critic_rating:
                    added_fields.append('critic_rating')

            if not hasattr(media_item, 'community_rating') or media_item.community_rating is None:
                media_item.community_rating = item_data.get('CommunityRating')
                media_item.vote_count = item_data.get('VoteCount')
                if media_item.community_rating:
                    added_fields.append('community_rating')

            # External URLs (not in webhook)
            if not hasattr(media_item, 'external_urls'):
                media_item.external_urls = item_data.get('ExternalUrls', [])
                media_item.home_page_url = item_data.get('HomePageUrl')
                if media_item.external_urls or media_item.home_page_url:
                    added_fields.append('external_urls')

            # Additional provider IDs not in webhook (webhook has imdb, tmdb, tvdb, tvdbslug)
            provider_ids = item_data.get('ProviderIds', {})
            if not hasattr(media_item, 'zap2it_id'):
                media_item.zap2it_id = provider_ids.get('Zap2It')
                media_item.musicbrainz_id = provider_ids.get('MusicBrainz')
                media_item.audiodbartist_id = provider_ids.get('AudioDbArtist')
                media_item.audiodbalbum_id = provider_ids.get('AudioDbAlbum')
                media_item.gamesdb_id = provider_ids.get('GamesDb')
                if any([media_item.zap2it_id, media_item.musicbrainz_id]):
                    added_fields.append('additional_provider_ids')

            # ==================== MEDIA TYPE SPECIFIC ENRICHMENT ====================
            media_type = media_item.item_type.lower() if media_item.item_type else ""

            if media_type == 'movie':
                self._enrich_movie_only_fields(media_item, item_data, added_fields)
            elif media_type in ['series', 'season', 'episode']:
                self._enrich_tv_only_fields(media_item, item_data, media_type, added_fields)
            elif media_type in ['audio', 'musicalbum', 'musicartist']:
                self._enrich_music_only_fields(media_item, item_data, added_fields)
            elif media_type == 'photo':
                self._enrich_photo_only_fields(media_item, item_data, added_fields)

            # ALL media streams (webhook only has first of each type)
            self._enrich_all_media_streams(media_item, item_data, added_fields)

            # Mark item as enriched
            if added_fields:
                media_item.is_enriched = True
                media_item.enrichment_timestamp = datetime.now(timezone.utc).isoformat()
                media_item.enriched_fields = added_fields

                self.logger.info(f"Enriched {media_item.name} ({media_item.item_type}) with {len(added_fields)} "
                                 f"additional field groups: {', '.join(added_fields[:5])}")
            else:
                self.logger.debug(f"No additional enrichment needed for {media_item.name} - webhook data sufficient")

            return media_item

        except Exception as e:
            self.logger.error(f"Failed to enrich media item {media_item.item_id}: {e}", exc_info=True)
            return media_item

    def _enrich_movie_only_fields(self, media_item: MediaItem, item_data: Dict[str, Any],
                                  added_fields: List[str]) -> None:
        """
        Add movie-specific fields NOT present in webhook.
        """
        # Financial information (not in webhook)
        if not hasattr(media_item, 'budget'):
            media_item.budget = item_data.get('Budget')
            media_item.revenue = item_data.get('Revenue')
            if media_item.budget or media_item.revenue:
                added_fields.append('financial_info')

        # Awards and metascore (not in webhook)
        if not hasattr(media_item, 'awards'):
            media_item.awards = item_data.get('Awards')
            media_item.metascore = item_data.get('Metascore')
            if media_item.awards or media_item.metascore:
                added_fields.append('awards_scores')

        # Collection info (not in webhook)
        if not hasattr(media_item, 'tmdb_collection_name'):
            media_item.tmdb_collection_name = item_data.get('TmdbCollectionName')
            if media_item.tmdb_collection_name:
                added_fields.append('collection_info')

        # Additional taglines (webhook may have one in Tagline field)
        if not hasattr(media_item, 'taglines'):
            media_item.taglines = item_data.get('Taglines', [])
            if media_item.taglines:
                added_fields.append('taglines')

        # Trailers (not in webhook)
        if not hasattr(media_item, 'remote_trailers'):
            media_item.remote_trailers = []
            for trailer in item_data.get('RemoteTrailers', []):
                media_item.remote_trailers.append({
                    'url': trailer.get('Url'),
                    'name': trailer.get('Name'),
                    'type': trailer.get('Type'),
                    'is_direct_link': trailer.get('IsDirectLink', False)
                })
            if media_item.remote_trailers:
                added_fields.append('trailers')

        # Special features count (not in webhook)
        if not hasattr(media_item, 'special_feature_count'):
            media_item.local_trailer_count = item_data.get('LocalTrailerCount', 0)
            media_item.special_feature_count = item_data.get('SpecialFeatureCount', 0)
            if media_item.special_feature_count > 0:
                added_fields.append('special_features')

        # Technical details not in webhook
        if not hasattr(media_item, 'video_type'):
            media_item.video_type = item_data.get('VideoType')  # BluRay, DVD, File
            media_item.iso_type = item_data.get('IsoType')
            media_item.video_3d_format = item_data.get('Video3DFormat')
            if media_item.video_type:
                added_fields.append('media_format')

        # Recommendations (not in webhook)
        if not hasattr(media_item, 'recommendations'):
            media_item.recommendations = item_data.get('Recommendations', [])
            if media_item.recommendations:
                added_fields.append('recommendations')

    def _enrich_tv_only_fields(self, media_item: MediaItem, item_data: Dict[str, Any],
                               media_type: str, added_fields: List[str]) -> None:
        """
        Add TV-specific fields NOT present in webhook.
        """
        # Series status and schedule (not in webhook)
        if media_type == 'series' and not hasattr(media_item, 'status'):
            media_item.status = item_data.get('Status')  # Continuing/Ended
            media_item.air_days = item_data.get('AirDays', [])
            media_item.air_time = item_data.get('AirTime')
            if media_item.status:
                added_fields.append('series_status')

        # Episode alternate numbering (not in webhook)
        if media_type == 'episode':
            if not hasattr(media_item, 'absolute_episode_number'):
                media_item.absolute_episode_number = item_data.get('AbsoluteEpisodeNumber')
                media_item.dvd_season_number = item_data.get('DvdSeasonNumber')
                media_item.dvd_episode_number = item_data.get('DvdEpisodeNumber')
                media_item.airs_before_season_number = item_data.get('AirsBeforeSeasonNumber')
                media_item.airs_after_season_number = item_data.get('AirsAfterSeasonNumber')
                media_item.airs_before_episode_number = item_data.get('AirsBeforeEpisodeNumber')
                if media_item.absolute_episode_number or media_item.dvd_episode_number:
                    added_fields.append('alternate_numbering')

            # Season name (not in webhook)
            if not hasattr(media_item, 'season_name'):
                media_item.season_name = item_data.get('SeasonName')
                if media_item.season_name:
                    added_fields.append('season_name')

    def _enrich_music_only_fields(self, media_item: MediaItem, item_data: Dict[str, Any],
                                  added_fields: List[str]) -> None:
        """
        Add music-specific fields NOT present in webhook.
        """
        # Detailed artist information (webhook only has basic artists list)
        if not hasattr(media_item, 'album_artists_data'):
            media_item.album_artists_data = item_data.get('AlbumArtists', [])
            media_item.artist_items = item_data.get('ArtistItems', [])
            if media_item.album_artists_data or media_item.artist_items:
                added_fields.append('detailed_artists')

        # Music metadata not in webhook
        if not hasattr(media_item, 'composers'):
            media_item.composers = item_data.get('Composers', [])
            media_item.contributors = item_data.get('Contributors', [])
            media_item.moods = item_data.get('Moods', [])
            media_item.styles = item_data.get('Styles', [])
            if any([media_item.composers, media_item.contributors, media_item.moods]):
                added_fields.append('music_metadata')

        # Lyrics (not in webhook)
        if not hasattr(media_item, 'lyrics'):
            media_item.lyrics = item_data.get('Lyrics')
            if media_item.lyrics:
                added_fields.append('lyrics')

        # MusicBrainz IDs (webhook doesn't have these)
        if not hasattr(media_item, 'musicbrainz_artist_id'):
            media_item.musicbrainz_artist_id = item_data.get('MusicBrainzArtistId')
            media_item.musicbrainz_album_id = item_data.get('MusicBrainzAlbumId')
            media_item.musicbrainz_album_artist_id = item_data.get('MusicBrainzAlbumArtistId')
            media_item.musicbrainz_track_id = item_data.get('MusicBrainzTrackId')
            media_item.musicbrainz_release_group_id = item_data.get('MusicBrainzReleaseGroupId')
            if media_item.musicbrainz_track_id:
                added_fields.append('musicbrainz_ids')

        # Track/disc numbers (not always in webhook)
        if not hasattr(media_item, 'track_number'):
            media_item.track_number = item_data.get('IndexNumber')
            media_item.disc_number = item_data.get('ParentIndexNumber')
            media_item.total_discs = item_data.get('TotalDiscs')
            if media_item.track_number:
                added_fields.append('track_info')

    def _enrich_photo_only_fields(self, media_item: MediaItem, item_data: Dict[str, Any],
                                  added_fields: List[str]) -> None:
        """
        Add photo-specific EXIF fields NOT present in webhook.
        """
        # Camera information (not in webhook)
        if not hasattr(media_item, 'camera_make'):
            media_item.camera_make = item_data.get('CameraMake')
            media_item.camera_model = item_data.get('CameraModel')
            media_item.software = item_data.get('Software')
            if media_item.camera_make or media_item.camera_model:
                added_fields.append('camera_info')

        # Photo settings (not in webhook)
        if not hasattr(media_item, 'exposure_time'):
            media_item.exposure_time = item_data.get('ExposureTime')
            media_item.focal_length = item_data.get('FocalLength')
            media_item.aperture = item_data.get('Aperture')
            media_item.shutter_speed = item_data.get('ShutterSpeed')
            media_item.iso_speed_rating = item_data.get('IsoSpeedRating')
            if media_item.exposure_time or media_item.focal_length:
                added_fields.append('photo_settings')

        # GPS information (not in webhook)
        if not hasattr(media_item, 'latitude'):
            media_item.latitude = item_data.get('Latitude')
            media_item.longitude = item_data.get('Longitude')
            media_item.altitude = item_data.get('Altitude')
            if media_item.latitude and media_item.longitude:
                added_fields.append('gps_location')

    def _enrich_all_media_streams(self, media_item: MediaItem, item_data: Dict[str, Any],
                                  added_fields: List[str]) -> None:
        """
        Add ALL media streams - webhook only provides first of each type.

        Webhook provides Video_0_*, Audio_0_*, Subtitle_0_*
        This adds all additional streams for multi-track media.
        """
        all_streams = item_data.get('MediaStreams', [])

        # Get all video streams (webhook only has Video_0)
        video_streams = [s for s in all_streams if s.get('Type') == 'Video']
        if len(video_streams) > 1:  # Only add if there are multiple
            media_item.video_streams = video_streams
            media_item.video_stream_count = len(video_streams)
            added_fields.append('multiple_video_streams')

        # Get all audio streams (webhook only has Audio_0)
        audio_streams = [s for s in all_streams if s.get('Type') == 'Audio']
        if len(audio_streams) > 1:  # Only add if there are multiple
            media_item.audio_streams = audio_streams
            media_item.audio_stream_count = len(audio_streams)
            added_fields.append('multiple_audio_streams')

        # Get all subtitle streams (webhook only has Subtitle_0)
        subtitle_streams = [s for s in all_streams if s.get('Type') == 'Subtitle']
        if len(subtitle_streams) > 1:  # Only add if there are multiple
            media_item.subtitle_streams = subtitle_streams
            media_item.subtitle_stream_count = len(subtitle_streams)
            added_fields.append('multiple_subtitle_streams')

        # Default stream indices (not in webhook)
        if not hasattr(media_item, 'default_audio_stream_index'):
            media_item.default_audio_stream_index = item_data.get('DefaultAudioStreamIndex')
            media_item.default_subtitle_stream_index = item_data.get('DefaultSubtitleStreamIndex')

        # Media sources for multi-version items
        media_sources = item_data.get('MediaSources', [])
        if len(media_sources) > 1:
            media_item.all_media_sources = media_sources
            media_item.media_source_count = len(media_sources)
            added_fields.append('multiple_versions')

    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Jellyfin and return diagnostic information.

        This method performs a comprehensive connection test including
        authentication verification, API accessibility, and server information
        retrieval. It's useful for troubleshooting connection issues.

        **Test Components:**
        - Network connectivity to server
        - API key authentication validity
        - User ID accessibility
        - Basic API functionality
        - Server version compatibility

        Returns:
            Dict[str, Any]: Comprehensive connection test results

        Example:
            ```python
            test_results = await jellyfin_api.test_connection()

            if test_results['connected']:
                logger.info(f"Connection OK: {test_results['server_info']['ServerName']}")
            else:
                logger.error(f"Connection failed: {test_results['error']}")
            ```

        Note:
            This method is primarily used for diagnostic purposes and
            during initial service configuration validation.
        """
        test_results: Dict[str, Union[bool, Optional[str], Optional[Dict], Optional[float]]] = {
            'connected': False,  # bool
            'server_info': None,  # Optional[Dict]
            'error': None,  # Optional[str]
            'response_time': None  # Optional[float]
        }

        try:
            start_time = time.time()

            # Test basic connection
            if not await self.connect():
                test_results[
                    'error'] = "Failed to establish connection"  # This is valid - assigning str to Optional[str]
                return test_results

            # Get server information
            system_info = await self.get_system_info()
            if not system_info:
                test_results['error'] = "Connected but cannot retrieve server info"
                return test_results

            # Test item retrieval capability (try to get first item)
            try:
                response = self.client.jellyfin.user_items(
                    params={
                        'Limit': 1
                    }
                )
                if not response:
                    test_results['error'] = "Cannot access library - check user permissions"
                    return test_results
            except Exception as e:
                test_results['error'] = f"Library access failed: {str(e)}"
                return test_results

            # Calculate response time
            response_time = time.time() - start_time

            # Success - populate results
            test_results.update({
                'connected': True,
                'server_info': system_info,
                'response_time': round(response_time, 3),
                'error': None  # Explicitly set to None on success
            })

            self.logger.info(f"Connection test passed in {response_time:.3f}s")
            return test_results

        except Exception as e:
            test_results['error'] = str(e)
            self.logger.error(f"Connection test failed: {e}")
            return test_results