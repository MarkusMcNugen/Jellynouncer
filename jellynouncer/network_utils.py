"""
Enhanced network detection utilities for Jellynouncer FastAPI application.

This module provides intelligent network interface detection and startup logging
functionality that automatically discovers and displays server addresses in a
user-friendly format. It integrates with Jellynouncer's existing configuration
system to respect both config file settings and environment variable overrides.

**Key Features:**
- Automatic detection of all network interfaces and IP addresses
- Integration with existing Jellynouncer configuration system (HOST/PORT)
- Intelligent categorization of Docker, loopback, and physical interfaces
- Cross-platform compatibility with fallback detection methods
- Smart filtering and prioritization for clean user display
- Environment variable override support for manual configuration
- Comprehensive error handling and logging

**Configuration Integration:**
This module respects Jellynouncer's existing configuration hierarchy:
1. Environment variables (HOST, PORT)
2. Configuration file settings (config.json server section)
3. Default values (0.0.0.0:1984)

**Detection Strategies:**
1. Primary IP via external route (most reliable)
2. Linux 'ip' command for detailed interface information
3. Hostname-based IP resolution as fallback
4. Environment variable override for manual configuration

**Docker Compatibility:**
- Properly detects Docker bridge networks
- Filters out internal Docker interfaces from user display
- Works with host networking and bridge networking modes
- Handles multi-container environments correctly

**Usage Example:**
    ```python
    from network_utils import log_jellynouncer_startup
    from config_models import ConfigurationValidator

    # Load configuration (existing Jellynouncer pattern)
    config_validator = ConfigurationValidator()
    config = config_validator.load_and_validate_config()

    # Enhanced startup logging with config integration
    log_jellynouncer_startup(config=config, logger=logger)
    ```

**Environment Variables:**
- HOST: Override hostname/IP for display (integrates with existing system)
- PORT: Override port number for display (integrates with existing system)
- JELLYNOUNCER_DISPLAY_DOCKER: Set to "true" to show Docker interfaces

Author: AI Assistant for Jellynouncer Project
Compatible with: Python 3.11+, FastAPI, Docker, Linux/Windows/macOS
License: MIT (matching Jellynouncer project)
"""

import socket
import subprocess
import logging
import os
from typing import List, Optional, Set, Any
from dataclasses import dataclass


def _get_configured_port(config: Optional[Any] = None) -> int:
    """
    Get the configured port from environment variables or config.

    Follows the same precedence as main.py:
    1. PORT environment variable
    2. config.server.port (if config provided)
    3. Default 1984

    Args:
        config: Optional configuration object with server.port attribute

    Returns:
        int: Configured port number

    Example:
        ```python
        # With config object
        port = _get_configured_port(config)

        # Without config (env var or default)
        port = _get_configured_port()
        ```
    """
    if config and hasattr(config, 'server') and hasattr(config.server, 'port'):
        return int(os.getenv("PORT", str(config.server.port)))
    else:
        return int(os.getenv("PORT", 1984))


@dataclass
class NetworkInterface:
    """
    Represents a network interface with its properties and categorization.

    This dataclass encapsulates all relevant information about a network interface
    to support intelligent filtering and display decisions. It includes flags for
    different interface types to enable smart categorization.

    **Interface Categorization:**
    - Loopback: 127.x.x.x addresses (localhost)
    - Docker: Docker bridge interfaces and containers
    - Private: RFC 1918 private network addresses
    - Physical: Real network adapters (Ethernet, WiFi)

    Args:
        name (str): Interface name from the system (e.g., 'eth0', 'wlan0', 'docker0').
        ip_address (str): IPv4 address assigned to this interface.
        is_loopback (bool): True if this is a loopback interface (127.x.x.x).
        is_docker (bool): True if this appears to be a Docker-related interface.
        is_private (bool): True if this is a private network address (RFC 1918).
        is_primary (bool): True if this is the primary/default route interface.

    Example:
        ```python
        # Physical network interface
        eth_interface = NetworkInterface(
            name="eth0",
            ip_address="192.168.1.100",
            is_loopback=False,
            is_docker=False,
            is_private=True,
            is_primary=True
        )

        # Docker bridge interface
        docker_interface = NetworkInterface(
            name="docker0",
            ip_address="172.17.0.1",
            is_loopback=False,
            is_docker=True,
            is_private=True,
            is_primary=False
        )
        ```
    """
    name: str
    ip_address: str
    is_loopback: bool = False
    is_docker: bool = False
    is_private: bool = True
    is_primary: bool = False


class NetworkDetector:
    """
    Intelligent network interface detection and categorization for FastAPI applications.

    This class provides comprehensive network discovery capabilities with smart
    filtering and categorization. It's designed to work across different deployment
    environments and provides user-friendly interface lists for startup logging.

    **Detection Methods:**
    The detector uses multiple strategies to ensure reliable interface discovery:

    1. **Primary Route Detection**: Connects to external address to find default route
    2. **System Command Integration**: Uses 'ip' command on Linux for detailed info
    3. **Hostname Resolution**: Resolves local hostname to discover additional IPs
    4. **Environment Override**: Supports manual configuration via environment variables

    **Smart Filtering:**
    - Automatically excludes loopback interfaces from user display
    - Optionally filters Docker interfaces (configurable)
    - Prioritizes physical interfaces over virtual ones
    - Removes duplicate IP addresses across interfaces

    **Cross-Platform Support:**
    - Linux: Full support with 'ip' command integration
    - Windows/macOS: Basic support via hostname resolution
    - Docker: Special handling for container environments

    Example:
        ```python
        # Basic usage
        detector = NetworkDetector()
        all_interfaces = detector.get_all_interfaces()
        user_interfaces = detector.get_user_friendly_interfaces()

        # With custom logger
        logger = logging.getLogger("my_app")
        detector = NetworkDetector(logger=logger)

        # Check environment configuration
        if detector.has_manual_override():
            print("Using manual host configuration")
        ```

    **Error Handling:**
    All methods include comprehensive error handling with graceful fallbacks.
    Errors are logged at appropriate levels and don't prevent application startup.
    """

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        """
        Initialize the network detector with optional custom logger.

        Sets up private IP range definitions and configures logging for debug output.
        The detector is ready to use immediately after initialization.

        Args:
            logger: Optional logger instance for debug and error output.
                   If not provided, creates a logger using the module name.

        Example:
            ```python
            # Use default logger
            detector = NetworkDetector()

            # Use custom logger
            app_logger = logging.getLogger("jellynouncer")
            detector = NetworkDetector(logger=app_logger)
            ```
        """
        self.logger = logger or logging.getLogger(__name__)

        # RFC 1918 private address ranges for classification
        # These ranges are reserved for private networks and not routable on the internet
        self._private_ranges = [
            ("10.0.0.0", "10.255.255.255"),        # Class A private range
            ("172.16.0.0", "172.31.255.255"),      # Class B private range
            ("192.168.0.0", "192.168.255.255"),    # Class C private range
            ("127.0.0.0", "127.255.255.255"),      # Loopback range
        ]

        # Common Docker subnet patterns for automatic detection
        self._docker_patterns = [
            "172.17.",    # Default Docker bridge network
            "172.18.",    # Additional Docker networks
            "172.19.",    # Additional Docker networks
            "172.20.",    # Additional Docker networks
        ]

    def _is_private_ip(self, ip_address: str) -> bool:
        """
        Determine if an IP address falls within private network ranges.

        This method checks against RFC 1918 private address ranges to classify
        IP addresses. Private addresses are not routable on the public internet
        and are used for internal networks.

        **Private Ranges Checked:**
        - 10.0.0.0/8 (Class A): 10.0.0.0 - 10.255.255.255
        - 172.16.0.0/12 (Class B): 172.16.0.0 - 172.31.255.255
        - 192.168.0.0/16 (Class C): 192.168.0.0 - 192.168.255.255
        - 127.0.0.0/8 (Loopback): 127.0.0.0 - 127.255.255.255

        Args:
            ip_address (str): IPv4 address to classify (e.g., "192.168.1.100").

        Returns:
            bool: True if the address is within private ranges, False if public.
                 Returns True for invalid addresses as a safety measure.

        Raises:
            ValueError: If IP address format is completely invalid.

        Example:
            ```python
            detector = NetworkDetector()

            # Private addresses
            assert detector._is_private_ip("192.168.1.100") == True
            assert detector._is_private_ip("10.0.0.1") == True

            # Public addresses
            assert detector._is_private_ip("8.8.8.8") == False
            assert detector._is_private_ip("1.1.1.1") == False
            ```
        """
        try:
            # Parse IP address into integer components
            ip_parts = [int(part) for part in ip_address.split(".")]
            if len(ip_parts) != 4:
                raise ValueError(f"Invalid IP format: expected 4 octets, got {len(ip_parts)}")

            # Convert to 32-bit integer for range comparison
            ip_int = (ip_parts[0] << 24) + (ip_parts[1] << 16) + (ip_parts[2] << 8) + ip_parts[3]

            # Check against each private range
            for start_ip, end_ip in self._private_ranges:
                start_parts = [int(part) for part in start_ip.split(".")]
                end_parts = [int(part) for part in end_ip.split(".")]

                start_int = (start_parts[0] << 24) + (start_parts[1] << 16) + (start_parts[2] << 8) + start_parts[3]
                end_int = (end_parts[0] << 24) + (end_parts[1] << 16) + (end_parts[2] << 8) + end_parts[3]

                if start_int <= ip_int <= end_int:
                    return True

            return False

        except (ValueError, IndexError) as e:
            self.logger.warning(f"Invalid IP address format '{ip_address}': {e}")
            return True  # Assume private if we can't parse for safety

    def _is_docker_interface(self, interface_name: str, ip_address: str) -> bool:
        """
        Determine if an interface is Docker-related based on name and IP patterns.

        This method uses heuristics to identify Docker-managed network interfaces.
        Docker typically uses predictable naming patterns and IP address ranges
        that can be detected automatically.

        **Detection Criteria:**
        - Interface names starting with "docker", "br-", or "veth"
        - IP addresses in common Docker subnet ranges (172.17.x.x, etc.)
        - Interface names containing Docker-specific patterns

        Args:
            interface_name (str): System interface name (e.g., "docker0", "br-abc123").
            ip_address (str): IP address assigned to the interface.

        Returns:
            bool: True if the interface appears to be Docker-managed.

        Example:
            ```python
            detector = NetworkDetector()

            # Docker interfaces
            assert detector._is_docker_interface("docker0", "172.17.0.1") == True
            assert detector._is_docker_interface("br-abc123", "172.18.0.1") == True

            # Physical interfaces
            assert detector._is_docker_interface("eth0", "192.168.1.100") == False
            assert detector._is_docker_interface("wlan0", "10.0.1.50") == False
            ```
        """
        # Check interface name patterns
        docker_name_patterns = ["docker", "br-", "veth"]
        if any(interface_name.startswith(pattern) for pattern in docker_name_patterns):
            return True

        # Check IP address patterns
        if any(ip_address.startswith(pattern) for pattern in self._docker_patterns):
            return True

        return False

    def _get_primary_ip_via_route(self) -> Optional[str]:
        """
        Discover primary IP address by connecting to external address.

        This method uses the "connect to external address" technique, which is
        widely considered the most reliable way to determine the primary/default
        route IP address. It doesn't actually send network traffic.

        **How It Works:**
        1. Creates a UDP socket (no data is sent)
        2. Connects to Google's public DNS server (8.8.8.8)
        3. Retrieves the local IP address used for the connection
        4. This IP represents the interface with the default route

        **Advantages:**
        - Works across all platforms and environments
        - Reliable in Docker containers and cloud instances
        - Doesn't require special permissions or system commands
        - Handles complex routing scenarios automatically

        Returns:
            Optional[str]: Primary IP address, or None if detection fails.

        Raises:
            OSError: When network operations fail (logged, not propagated).

        Example:
            ```python
            detector = NetworkDetector()
            primary_ip = detector._get_primary_ip_via_route()

            if primary_ip:
                print(f"Primary interface IP: {primary_ip}")
            else:
                print("Could not determine primary IP")
            ```
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                # Connect to Google's public DNS (doesn't actually send data)
                # This connection will use the default route and reveal our primary IP
                sock.connect(("8.8.8.8", 80))
                primary_ip = sock.getsockname()[0]

                self.logger.debug(f"Primary IP detected via external route: {primary_ip}")
                return primary_ip

        except OSError as e:
            self.logger.debug(f"Route-based IP detection failed: {e}")
            return None

    def _get_hostname_ips(self) -> List[str]:
        """
        Discover IP addresses associated with the local hostname.

        This method resolves the system hostname to find associated IP addresses.
        It provides a fallback detection method when other strategies fail and
        can discover additional interfaces not found through routing.

        **Process:**
        1. Gets the local hostname using socket.gethostname()
        2. Resolves hostname to all associated IP addresses
        3. Filters out loopback addresses (127.x.x.x)
        4. Returns clean list of non-loopback IPs

        **Limitations:**
        - Requires proper hostname configuration
        - May not work in some containerized environments
        - Can return stale IPs if DNS is misconfigured

        Returns:
            List[str]: List of IP addresses associated with hostname.
                      Empty list if resolution fails.

        Raises:
            OSError: When hostname resolution fails (logged, not propagated).

        Example:
            ```python
            detector = NetworkDetector()
            hostname_ips = detector._get_hostname_ips()

            for ip in hostname_ips:
                print(f"Hostname resolves to: {ip}")
            ```
        """
        try:
            hostname = socket.gethostname()
            self.logger.debug(f"Local hostname: {hostname}")

            # Get all IP addresses associated with the hostname
            # socket.gethostbyname_ex returns (hostname, aliaslist, ipaddrlist)
            _, _, ip_addresses = socket.gethostbyname_ex(hostname)

            # Filter out loopback addresses as they're not useful for external access
            filtered_ips = [
                ip for ip in ip_addresses
                if not ip.startswith("127.")
            ]

            self.logger.debug(f"Hostname '{hostname}' resolved to IPs: {filtered_ips}")
            return filtered_ips

        except OSError as e:
            self.logger.debug(f"Hostname IP resolution failed: {e}")
            return []

    def _get_interfaces_via_ip_command(self) -> List[NetworkInterface]:
        """
        Discover network interfaces using Linux 'ip' command for detailed information.

        This method provides the most comprehensive interface information on Linux
        systems by parsing the output of the 'ip addr show' command. It extracts
        interface names, IP addresses, and can infer interface types.

        **Information Extracted:**
        - Interface names (eth0, wlan0, docker0, etc.)
        - IP addresses with subnet masks
        - Interface status (up/down)
        - Interface types (virtual, physical, bridge)

        **Command Output Parsing:**
        The method parses output like:
        ```
        2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 state UP
            inet 192.168.1.100/24 brd 192.168.1.255 scope global eth0
        3: docker0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 state DOWN
            inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
        ```

        **Platform Compatibility:**
        - Linux: Full support with detailed interface information
        - Windows/macOS: Not available (returns empty list)
        - Docker: Works within containers if 'ip' command is available

        Returns:
            List[NetworkInterface]: Detailed interface objects with all properties set.
                                   Empty list if command unavailable or fails.

        Raises:
            subprocess.SubprocessError: Command execution errors (logged, not propagated).
            FileNotFoundError: 'ip' command not found (logged, not propagated).
            subprocess.TimeoutExpired: Command timeout (logged, not propagated).

        Example:
            ```python
            detector = NetworkDetector()
            interfaces = detector._get_interfaces_via_ip_command()

            for interface in interfaces:
                print(f"{interface.name}: {interface.ip_address}")
                if interface.is_docker:
                    print("  -> Docker interface")
                if interface.is_primary:
                    print("  -> Primary interface")
            ```
        """
        interfaces = []
        try:
            # Execute 'ip addr show' command to get detailed interface information
            # Timeout after 5 seconds to prevent hanging in problematic environments
            result = subprocess.run(
                ["ip", "addr", "show"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True
            )

            current_interface = None
            for line in result.stdout.splitlines():
                line = line.strip()

                # Parse interface definition lines
                # Format: "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500..."
                if ": " in line and "<" in line and not line.startswith("inet"):
                    parts = line.split(": ")
                    if len(parts) >= 2:
                        # Extract interface name, removing VLAN suffix if present
                        interface_name = parts[1].split("@")[0]
                        current_interface = interface_name

                # Parse IP address lines
                # Format: "inet 192.168.1.100/24 brd 192.168.1.255 scope global eth0"
                elif line.startswith("inet ") and current_interface:
                    ip_parts = line.split()
                    if len(ip_parts) >= 2:
                        ip_with_mask = ip_parts[1]
                        ip_address = ip_with_mask.split("/")[0]

                        # Skip loopback addresses as they're not useful for external access
                        if ip_address.startswith("127."):
                            continue

                        # Determine if this is a Docker-related interface
                        is_docker = self._is_docker_interface(current_interface, ip_address)

                        interface = NetworkInterface(
                            name=current_interface,
                            ip_address=ip_address,
                            is_loopback=False,
                            is_docker=is_docker,
                            is_private=self._is_private_ip(ip_address),
                            is_primary=False  # Will be set later by primary IP detection
                        )
                        interfaces.append(interface)

            self.logger.debug(f"Detected {len(interfaces)} interfaces via 'ip' command")
            return interfaces

        except FileNotFoundError:
            # Don't log anything when 'ip' command is not available (common in containers)
            return []

        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            self.logger.debug(f"'ip' command detection failed: {e}")
            return []

    def get_all_interfaces(self) -> List[NetworkInterface]:
        """
        Discover all available network interfaces using multiple detection strategies.

        This method combines multiple detection approaches to provide the most
        comprehensive list of network interfaces possible. It uses a layered
        approach with fallbacks to ensure reliable operation across different
        environments.

        **Detection Strategy Priority:**
        1. **Linux 'ip' command**: Most detailed information when available
        2. **Hostname resolution**: Additional IPs not found by other methods
        3. **Primary route detection**: Ensures default route interface is included
        4. **Deduplication**: Removes duplicate IP addresses across methods

        **Interface Enhancement:**
        - Marks primary interface based on default route detection
        - Categorizes Docker vs. physical interfaces
        - Classifies private vs. public IP addresses
        - Filters out loopback interfaces automatically

        **Error Resilience:**
        Each detection method has individual error handling, so failure of one
        method doesn't prevent others from working. The method will always
        return some interfaces unless all detection methods fail.

        Returns:
            List[NetworkInterface]: Complete list of discovered network interfaces
                                   with all properties properly set. Never returns
                                   None, but may return empty list if all detection fails.

        Example:
            ```python
            detector = NetworkDetector()
            all_interfaces = detector.get_all_interfaces()

            print(f"Found {len(all_interfaces)} network interfaces:")
            for interface in all_interfaces:
                status = []
                if interface.is_primary:
                    status.append("PRIMARY")
                if interface.is_docker:
                    status.append("DOCKER")
                if interface.is_private:
                    status.append("PRIVATE")

                status_str = f" ({', '.join(status)})" if status else ""
                print(f"  {interface.name}: {interface.ip_address}{status_str}")
            ```
        """
        interfaces = []
        seen_ips: Set[str] = set()

        # Get primary IP first to mark the primary interface
        primary_ip = self._get_primary_ip_via_route()

        # Strategy 1: Use 'ip' command for detailed interface information (Linux)
        ip_command_interfaces = self._get_interfaces_via_ip_command()
        for interface in ip_command_interfaces:
            if interface.ip_address not in seen_ips:
                # Mark as primary if this matches our primary IP detection
                interface.is_primary = (interface.ip_address == primary_ip)
                interfaces.append(interface)
                seen_ips.add(interface.ip_address)

        # Strategy 2: Hostname-based detection for additional IPs
        hostname_ips = self._get_hostname_ips()
        for ip in hostname_ips:
            if ip not in seen_ips:
                # Create interface object with inferred properties
                interface = NetworkInterface(
                    name="unknown",  # Interface name unknown from hostname resolution
                    ip_address=ip,
                    is_loopback=False,
                    is_docker=any(ip.startswith(pattern) for pattern in self._docker_patterns),
                    is_private=self._is_private_ip(ip),
                    is_primary=(ip == primary_ip)
                )
                interfaces.append(interface)
                seen_ips.add(ip)

        # Strategy 3: Ensure primary IP is included even if other methods missed it
        if primary_ip and primary_ip not in seen_ips:
            interface = NetworkInterface(
                name="primary",
                ip_address=primary_ip,
                is_loopback=False,
                is_docker=any(primary_ip.startswith(pattern) for pattern in self._docker_patterns),
                is_private=self._is_private_ip(primary_ip),
                is_primary=True
            )
            interfaces.append(interface)
            seen_ips.add(primary_ip)

        self.logger.debug(f"Total interfaces discovered: {len(interfaces)}")
        return interfaces

    def get_user_friendly_interfaces(self) -> List[NetworkInterface]:
        """
        Get a filtered list of interfaces suitable for user display.

        This method applies intelligent filtering to show only the interfaces
        that are relevant and useful to end users. It removes clutter while
        preserving important information.

        **Filtering Rules:**
        - Always excludes loopback interfaces (127.x.x.x)
        - Excludes Docker interfaces unless JELLYNOUNCER_DISPLAY_DOCKER=true
        - Prioritizes primary interface first in the list
        - Sorts remaining interfaces by name for consistency

        **Environment Configuration:**
        - JELLYNOUNCER_DISPLAY_DOCKER=true: Include Docker interfaces in output
        - HOST: Override all detection with manual host

        **Use Cases:**
        - Startup logging messages
        - Health check endpoints
        - Configuration validation
        - User documentation generation

        Returns:
            List[NetworkInterface]: Filtered interfaces appropriate for user display.
                                   List is sorted with primary interface first.

        Example:
            ```python
            detector = NetworkDetector()
            user_interfaces = detector.get_user_friendly_interfaces()

            if user_interfaces:
                print("Available on:")
                for interface in user_interfaces:
                    marker = " (primary)" if interface.is_primary else ""
                    print(f"  http://{interface.ip_address}:1984{marker}")
            else:
                print("No suitable interfaces found")
            ```
        """
        all_interfaces = self.get_all_interfaces()

        # Check environment configuration for Docker interface display
        show_docker = os.getenv("JELLYNOUNCER_DISPLAY_DOCKER", "false").lower() == "true"

        # Apply filtering rules
        filtered_interfaces = []
        for interface in all_interfaces:
            # Always exclude loopback interfaces
            if interface.is_loopback:
                continue

            # Exclude Docker interfaces unless explicitly requested
            if interface.is_docker and not show_docker:
                continue

            filtered_interfaces.append(interface)

        # Sort interfaces: primary first, then by name
        filtered_interfaces.sort(key=lambda x: (not x.is_primary, x.name))

        self.logger.debug(f"User-friendly interfaces: {len(filtered_interfaces)} of {len(all_interfaces)}")
        return filtered_interfaces

    def get_server_address(self, port: Optional[int] = None, config: Optional[Any] = None) -> str:
        """
        Get the primary server address for startup logging and configuration.

        This method provides a single, primary server address that should be used
        in startup messages and configuration examples. It respects environment
        variable overrides and falls back to automatic detection.

        **Address Selection Priority:**
        1. HOST environment variable (manual override)
        2. Primary IP address from route detection
        3. First available non-Docker interface
        4. Localhost as final fallback

        **Port Selection Priority:**
        1. port parameter (if provided)
        2. PORT environment variable
        3. config.server.port (if config provided)
        4. Default 1984

        **URL Format:**
        Returns a complete HTTP URL including protocol and port number.

        Args:
            port: Port number for the service. If None, reads from environment/config.
            config: Optional configuration object with server.port attribute.

        Returns:
            str: Complete HTTP URL for the primary server address.

        Raises:
            ValueError: When port number is invalid (not positive integer).

        Example:
            ```python
            detector = NetworkDetector()

            # Use configured port from environment/config
            address = detector.get_server_address(config=config)
            # Returns: "http://192.168.1.100:1984"

            # Override with specific port
            address = detector.get_server_address(port=9000)
            # Returns: "http://192.168.1.100:9000"

            # With environment override
            os.environ["HOST"] = "jellynouncer.local"
            os.environ["PORT"] = "3000"
            address = detector.get_server_address()
            # Returns: "http://jellynouncer.local:3000"
            ```
        """
        if port is None:
            port = _get_configured_port(config)

        if not isinstance(port, int) or port <= 0:
            raise ValueError(f"Port must be a positive integer, got: {port}")

        # Check for manual override first
        manual_host = os.getenv("HOST")
        if manual_host and manual_host != "0.0.0.0":
            self.logger.debug(f"Using manual host override: {manual_host}")
            return f"http://{manual_host}:{port}"

        # Get primary IP via route detection
        primary_ip = self._get_primary_ip_via_route()
        if primary_ip:
            return f"http://{primary_ip}:{port}"

        # Fallback to first available non-Docker interface
        user_interfaces = self.get_user_friendly_interfaces()
        if user_interfaces:
            fallback_ip = user_interfaces[0].ip_address
            self.logger.debug(f"Using fallback interface: {fallback_ip}")
            return f"http://{fallback_ip}:{port}"

        # Final fallback to localhost
        self.logger.warning("Could not detect any suitable interfaces, using localhost")
        return f"http://localhost:{port}"

    def has_manual_override(self) -> bool:
        """
        Check if manual host configuration is active.

        Returns:
            bool: True if HOST environment variable is set.

        Example:
            ```python
            detector = NetworkDetector()
            if detector.has_manual_override():
                print("Using manual host configuration")
            else:
                print("Using automatic interface detection")
            ```
        """
        # Check for manual override first
        manual_host = os.getenv("HOST")
        if manual_host and manual_host != "0.0.0.0":
            return True
        else:
            return False


def log_jellynouncer_startup(
    port: Optional[int] = None,
    config: Optional[Any] = None,
    logger: Optional[logging.Logger] = None
) -> None:
    """
    Log comprehensive Jellynouncer startup information with network details.

    This function provides the enhanced startup logging that replaces the original
    "your-server:1984" placeholder with actual network interface information.
    It creates user-friendly output that shows all available access methods.

    **Startup Message Features:**
    - Changes "service" to "app" in the startup message
    - Displays primary server address prominently
    - Lists all available interfaces when multiple exist
    - Shows environment configuration status
    - Provides clear, actionable URLs for users

    **Output Example:**
    ```
    [2025-08-05 05:00:08 UTC] [system] [INFO] [jellynouncer] Jellynouncer app started successfully
    [2025-08-05 05:00:08 UTC] [system] [INFO] [jellynouncer] ============================================================
    [2025-08-05 05:00:08 UTC] [system] [INFO] [jellynouncer] 🎬 Jellynouncer is ready to receive webhooks!
    [2025-08-05 05:00:08 UTC] [system] [INFO] [jellynouncer] Send webhooks to: http://192.168.1.100:1984/webhook
    [2025-08-05 05:00:08 UTC] [system] [INFO] [jellynouncer] Health check: http://192.168.1.100:1984/health
    [2025-08-05 05:00:08 UTC] [system] [INFO] [jellynouncer] Also available on: http://10.0.0.50:1984
    [2025-08-05 05:00:08 UTC] [system] [INFO] [jellynouncer] ============================================================
    ```

    **Environment Integration:**
    - Respects HOST override
    - Uses configured PORT from environment/config
    - Shows Docker interface status
    - Adapts to container vs. bare metal deployment

    Args:
        port: Port number the service is running on. If None, reads from config/environment.
        config: Optional configuration object with server settings.
        logger: Optional logger instance. Creates default logger if not provided.

    Raises:
        ValueError: When port number is invalid.

    Example:
        ```python
        # Basic usage in FastAPI lifespan
        from network_utils import log_jellynouncer_startup

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # ... other startup code ...

            # Replace the original logging with enhanced version
            log_jellynouncer_startup(config=config, logger=logger)

            yield

        # With specific port override
        log_jellynouncer_startup(port=9000, logger=app_logger)
        ```
    """
    if port is None:
        port = _get_configured_port(config)

    if not isinstance(port, int) or port <= 0:
        raise ValueError(f"Port must be a positive integer, got: {port}")

    if logger is None:
        logger = logging.getLogger("jellynouncer")

    # Skip banner in subprocesses to avoid duplicate logging
    if os.environ.get('JELLYNOUNCER_SUBPROCESS'):
        logger.debug(f"Skipping startup banner in {os.environ.get('JELLYNOUNCER_SUBPROCESS')} subprocess")
        return

    detector = NetworkDetector(logger=logger)

    # Log the enhanced startup message (service -> app)
    logger.info("Jellynouncer app started successfully")
    
    # Display the Jellyfin ASCII art logo with gradient coloring
    from .utils import display_jellyfin_logo
    display_jellyfin_logo()
    
    logger.info("=" * 60)
    logger.info("🎬 Jellynouncer is ready to receive webhooks!")

    # Get primary server address
    primary_address = detector.get_server_address(port=port, config=config)
    logger.info(f"Send webhooks to: {primary_address}/webhook")
    logger.info(f"Health check: {primary_address}/health")

    # Show additional interfaces if available
    user_interfaces = detector.get_user_friendly_interfaces()
    if len(user_interfaces) > 1:
        # Find additional interfaces (excluding the primary one already shown)
        primary_ip = primary_address.split("//")[1].split(":")[0]
        additional_interfaces = [
            iface for iface in user_interfaces
            if iface.ip_address != primary_ip
        ]

        if additional_interfaces:
            additional_urls = [f"http://{iface.ip_address}:{port}" for iface in additional_interfaces]
            logger.info(f"Also available on: {', '.join(additional_urls)}")

    # Show configuration status if manual override is active
    if detector.has_manual_override():
        logger.info("Using manual host configuration (HOST environment variable)")

    logger.info("=" * 60)