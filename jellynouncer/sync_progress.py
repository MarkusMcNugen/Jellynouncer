#!/usr/bin/env python3
"""
Sync Progress Display Module

Provides beautiful, colored progress bars and status displays for library synchronization
with comprehensive fallback support for different terminal capabilities.

Features:
- True color (24-bit RGB) support with fallback to 256 colors and 16 colors
- Unicode UI elements with ASCII fallback
- Smooth color gradients for progress indication
- Dynamic error coloring based on batch size
- Emoji support detection and fallback

Author: Assistant
Version: 1.0.0
"""

import os
import sys
import time
import locale
from colorama import init, Fore

# Initialize colorama for Windows support
init(autoreset=False)


class SyncProgressDisplay:
    """
    Beautiful colored progress display with Unicode UI and comprehensive fallbacks.
    
    This class provides a rich, colorful progress display for library syncs with
    automatic detection and fallback for terminal capabilities.
    """
    
    # Unicode character sets for different support levels
    UI_CHARS = {
        'full': {
            # Box drawing with rounded corners
            'box_tl': '╭', 'box_tr': '╮', 'box_bl': '╰', 'box_br': '╯',
            'box_h': '─', 'box_v': '│', 'box_cross': '┼',
            'box_h_thick': '━', 'box_v_thick': '┃',
            # Tree characters
            'tree_mid': '├', 'tree_end': '└', 'tree_vert': '│',
            # Progress bar characters
            'progress_full': '█', 'progress_empty': '░',
            'progress_partial': ['▏', '▎', '▍', '▌', '▋', '▊', '▉', '█'],
            # Icons (emojis)
            'icons': {
                'start': '🚀', 'stats': '📊', 'batch': '📦', 
                'speed': '⚡', 'time': '⏱️ ', 'success': '✅',
                'error': '❌', 'new': '🆕', 'update': '🔄',
                'complete': '🎉', 'warning': '⚠️ ', 'info': 'ℹ️ ',
                'processing': '⚙️ ', 'database': '💾', 'network': '🌐'
            }
        },
        'unicode': {
            # Box drawing without emojis
            'box_tl': '╭', 'box_tr': '╮', 'box_bl': '╰', 'box_br': '╯',
            'box_h': '─', 'box_v': '│', 'box_cross': '┼',
            'box_h_thick': '═', 'box_v_thick': '║',
            # Tree characters
            'tree_mid': '├', 'tree_end': '└', 'tree_vert': '│',
            # Progress bar characters
            'progress_full': '█', 'progress_empty': '░',
            'progress_partial': ['▏', '▎', '▍', '▌', '▋', '▊', '▉', '█'],
            # Icons (Unicode symbols without emojis)
            'icons': {
                'start': '▶', 'stats': '◈', 'batch': '▣',
                'speed': '»', 'time': '◔', 'success': '✓',
                'error': '✗', 'new': '◆', 'update': '↻',
                'complete': '★', 'warning': '▲', 'info': 'ⓘ',
                'processing': '◉', 'database': '◫', 'network': '◈'
            }
        },
        'ascii': {
            # Pure ASCII characters
            'box_tl': '+', 'box_tr': '+', 'box_bl': '+', 'box_br': '+',
            'box_h': '-', 'box_v': '|', 'box_cross': '+',
            'box_h_thick': '=', 'box_v_thick': '|',
            # Tree characters
            'tree_mid': '|-', 'tree_end': '`-', 'tree_vert': '|',
            # Progress bar characters
            'progress_full': '#', 'progress_empty': '-',
            'progress_partial': ['#'],
            # Icons (ASCII text)
            'icons': {
                'start': '[>]', 'stats': '[*]', 'batch': '[#]',
                'speed': '[>>]', 'time': '[@]', 'success': '[OK]',
                'error': '[ERR]', 'new': '[NEW]', 'update': '[UPD]',
                'complete': '[DONE]', 'warning': '[WARN]', 'info': '[INFO]',
                'processing': '[...]', 'database': '[DB]', 'network': '[NET]'
            }
        }
    }
    
    def __init__(self, total_items: int, batch_size: int = 200, 
                 sync_type: str = "initial", logger=None, console_only: bool = True):
        """
        Initialize the sync progress display.
        
        Args:
            total_items: Total number of items to sync
            batch_size: Size of each batch (for error coloring)
            sync_type: Type of sync ("initial" or "background")
            logger: Logger instance for output
            console_only: If True, progress bars will only show in console, not in log files
        """
        self.total_items = total_items
        self.batch_size = batch_size
        self.sync_type = sync_type
        self.logger = logger
        self.console_only = console_only
        
        # Timing and statistics
        self.start_time = time.time()
        self.items_processed = 0
        self.items_fetched = 0
        self.errors = 0
        self.new_items = 0
        self.updated_items = 0
        self.current_batch = 0
        
        # ETA estimation with progressive refinement
        self.initial_estimate_per_item = self._get_initial_time_estimate()
        self.batch_times = []  # Track last N batch times for moving average
        self.max_batch_history = 10  # Keep last 10 batches for average
        
        # Detect terminal capabilities
        self.color_support = SyncProgressDisplay._detect_color_support()
        self.unicode_level = SyncProgressDisplay._detect_unicode_support()
        self.chars = self.UI_CHARS[self.unicode_level]
        
        # Color reset code
        self.reset = '\033[0m' if self.color_support != 'none' else ''
        
        # Log detection results for debugging
        if logger:
            logger.debug(f"Terminal capabilities - Colors: {self.color_support}, Unicode: {self.unicode_level}")
    
    @staticmethod
    def _detect_color_support() -> str:
        """
        Detect the maximum level of color support in Linux/Docker terminals.
        
        Returns:
            'truecolor': 24-bit RGB colors supported
            '256': 256 colors supported
            'basic': 16 colors supported
            'none': No color support
        """
        # Check if colors are explicitly disabled
        if os.environ.get('NO_COLOR'):
            return 'none'
        
        # Check TERM environment variable
        term = os.environ.get('TERM', '').lower()
        if term == 'dumb' or not term:
            # In Docker without TTY, TERM might not be set
            # Check if we're in Docker container
            if os.path.exists('/.dockerenv'):
                return 'basic'  # Docker supports basic colors via logs
            return 'none'
        
        # Check for true color (24-bit) support
        # Most modern Linux terminals support this
        colorterm = os.environ.get('COLORTERM', '').lower()
        if colorterm in ['truecolor', '24bit']:
            return 'truecolor'
        
        # Check for 256 color support (common in Linux)
        if '256color' in term:
            return '256'
        
        # Common Linux terminal types
        if any(x in term for x in ['xterm', 'screen', 'tmux', 'rxvt', 'konsole', 'gnome', 'linux']):
            # Most Linux terminals support at least 256 colors
            if 'xterm' in term or 'screen' in term or 'tmux' in term:
                return '256'  # These usually support 256 colors
            return 'basic'
        
        # Docker container environment
        if os.path.exists('/.dockerenv'):
            # Docker logs support ANSI colors
            return 'basic'
        
        # Check if running in common CI/CD environments
        if any(os.environ.get(var) for var in ['CI', 'GITHUB_ACTIONS', 'GITLAB_CI', 'JENKINS_URL']):
            return 'basic'  # Most CI systems support basic ANSI colors
        
        # Default to basic colors for Linux
        return 'basic'
    
    @staticmethod
    def _detect_unicode_support() -> str:
        """
        Detect Unicode support level in Linux/Docker terminals.
        
        Returns:
            'full': Full Unicode with emoji support
            'unicode': Unicode without emojis
            'ascii': ASCII only
        """
        # Check locale encoding
        try:
            encoding = locale.getpreferredencoding() or 'ascii'
            
            # Check for UTF-8 support (standard in modern Linux)
            if 'utf-8' in encoding.lower() or 'utf8' in encoding.lower():
                # UTF-8 locale, check terminal capabilities
                term = os.environ.get('TERM', '').lower()
                
                # Modern terminals that support emojis well
                if any(x in term for x in ['xterm-256color', 'screen-256color', 'tmux']):
                    # Test if we can actually encode emojis
                    try:
                        test_emoji = '🚀📊✅'
                        test_emoji.encode('utf-8')
                        return 'full'
                    except (UnicodeEncodeError, AttributeError):
                        return 'unicode'
                
                # Docker environment - usually supports Unicode but not always emojis
                if os.path.exists('/.dockerenv'):
                    # Try emojis first
                    try:
                        test_emoji = '🚀'
                        test_emoji.encode('utf-8')
                        # Docker logs might not render emojis well
                        # Check if TTY is attached
                        if sys.stdout.isatty():
                            return 'full'
                        else:
                            # Docker logs command - safer to avoid emojis
                            return 'unicode'
                    except (UnicodeEncodeError, AttributeError):
                        return 'unicode'
                
                # Standard Linux terminal - supports Unicode
                return 'unicode'
            
            # Non-UTF-8 locale, test what we can support
            try:
                test_unicode = '█░├└─│╭╮╰╯'
                test_unicode.encode(encoding)
                return 'unicode'
            except (UnicodeEncodeError, LookupError):
                return 'ascii'
                
        except (AttributeError, LookupError):
            # Error getting encoding, fallback to ASCII
            return 'ascii'
        
        # Default fallback (unreachable but kept for clarity)
        # return 'ascii'
    
    def _rgb_color(self, r: int, g: int, b: int) -> str:
        """
        Generate ANSI color code based on terminal support.
        
        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
            
        Returns:
            Appropriate ANSI color code or empty string
        """
        if self.color_support == 'none':
            return ''
        elif self.color_support == 'truecolor':
            return f'\033[38;2;{r};{g};{b}m'
        elif self.color_support == '256':
            # Convert RGB to nearest 256 color
            color_code = SyncProgressDisplay._rgb_to_256(r, g, b)
            return f'\033[38;5;{color_code}m'
        else:  # basic 16 colors
            # Map to nearest basic color
            return SyncProgressDisplay._rgb_to_basic(r, g, b)
    
    @staticmethod
    def _rgb_to_256(r: int, g: int, b: int) -> int:
        """Convert RGB to nearest 256 color palette index."""
        # Use the 216 color cube (16-231) for better color matching
        if r == g == b:
            # Use grayscale ramp (232-255)
            gray = int(r / 255 * 23)
            return 232 + gray
        else:
            # Map to 6x6x6 color cube
            r = int(r / 255 * 5)
            g = int(g / 255 * 5)
            b = int(b / 255 * 5)
            return 16 + (36 * r) + (6 * g) + b
    
    @staticmethod
    def _rgb_to_basic(r: int, g: int, b: int) -> str:
        """Convert RGB to nearest 16-color ANSI code."""
        # Determine the nearest basic color
        brightness = (r + g + b) / 3
        
        if brightness < 64:
            return Fore.BLACK
        elif r > g and r > b:
            return Fore.LIGHTRED_EX if brightness > 128 else Fore.RED
        elif g > r and g > b:
            return Fore.LIGHTGREEN_EX if brightness > 128 else Fore.GREEN
        elif b > r and b > g:
            return Fore.LIGHTBLUE_EX if brightness > 128 else Fore.BLUE
        elif r > b:  # r and g are high
            return Fore.LIGHTYELLOW_EX if brightness > 128 else Fore.YELLOW
        elif g > r:  # g and b are high
            return Fore.LIGHTCYAN_EX if brightness > 128 else Fore.CYAN
        elif r > g:  # r and b are high
            return Fore.LIGHTMAGENTA_EX if brightness > 128 else Fore.MAGENTA
        else:
            return Fore.WHITE if brightness > 192 else Fore.LIGHTWHITE_EX
    
    def _get_gradient_color(self, percent: float) -> str:
        """
        Get gradient color based on progress percentage.
        
        Args:
            percent: Progress percentage (0-100)
            
        Returns:
            Color code for the given percentage
        """
        # Smooth gradient with many steps
        if self.sync_type == "initial":
            # Red → Orange → Yellow → Green gradient (10 steps)
            if percent < 10:
                r, g, b = 255, 0, 0  # Red to Red-Orange
            elif percent < 20:
                r, g, b = 255, int(25.5 + (percent - 10) * 2.55), 0  # Red-Orange
            elif percent < 30:
                r, g, b = 255, int(51 + (percent - 20) * 2.55), 0  # Orange
            elif percent < 40:
                r, g, b = 255, int(76.5 + (percent - 30) * 2.55), 0  # Orange
            elif percent < 50:
                r, g, b = 255, int(102 + (percent - 40) * 2.55), 0  # Orange-Yellow
            elif percent < 60:
                r, g, b = 255, int(127.5 + (percent - 50) * 2.55), 0  # Yellow-Orange
            elif percent < 70:
                r, g, b = int(255 - (percent - 60) * 2.55), 255, 0  # Yellow
            elif percent < 80:
                r, g, b = int(230 - (percent - 70) * 2.55), 255, 0  # Yellow-Green
            elif percent < 90:
                r, g, b = int(204 - (percent - 80) * 2.55), 255, 0  # Light Green
            else:
                r, g, b = int(max(0, int(178 - (percent - 90) * 2.55))), 255, 0  # Green
        else:
            # Background sync: White → Light Green → Green gradient
            if percent < 20:
                intensity = 255
                r, g, b = intensity, 255, intensity  # White
            elif percent < 40:
                intensity = int(255 - (percent - 20) * 2.55)
                r, g, b = intensity, 255, intensity  # White to Light Green
            elif percent < 60:
                intensity = int(204 - (percent - 40) * 2.55)
                r, g, b = intensity, 255, intensity  # Light Green
            elif percent < 80:
                intensity = int(153 - (percent - 60) * 2.55)
                r, g, b = intensity, 255, intensity  # Soft Green
            else:
                intensity = int(max(0, int(102 - (percent - 80) * 2.55)))
                r, g, b = intensity, 255, intensity  # Pure Green
        
        return self._rgb_color(r, g, b)
    
    def _get_error_color(self, error_count: int) -> str:
        """
        Get color based on error count relative to batch size.
        
        Args:
            error_count: Number of errors
            
        Returns:
            Color code for the error count
        """
        if error_count == 0:
            return self._rgb_color(0, 255, 0)  # Bright green
        elif error_count < self.batch_size:
            # Yellow gradient based on percentage of batch
            percent = error_count / self.batch_size
            r = int(255 * percent)
            g = 255 - int(100 * percent)
            b = 0
            return self._rgb_color(r, g, b)
        elif error_count < self.batch_size * 2:
            # Orange to red for 1-2 batches worth
            percent = (error_count - self.batch_size) / self.batch_size
            r = 255
            g = int(128 * (1 - percent))
            b = 0
            return self._rgb_color(r, g, b)
        else:
            # Deep red for > 2 batches worth of errors
            return self._rgb_color(200, 0, 0)
    
    def _get_speed_color(self, speed: float) -> str:
        """Get color for processing speed."""
        if speed > 500:
            return self._rgb_color(0, 255, 255)  # Cyan for very fast
        elif speed > 200:
            return self._rgb_color(0, 200, 255)  # Blue for fast
        elif speed > 100:
            return self._rgb_color(0, 255, 0)  # Green for normal
        elif speed > 50:
            return self._rgb_color(255, 255, 0)  # Yellow for slow
        else:
            return self._rgb_color(255, 128, 0)  # Orange for very slow
    
    def _get_eta_color(self, eta_seconds: float) -> str:
        """Get color for ETA."""
        if eta_seconds < 60:
            return self._rgb_color(0, 255, 0)  # Green for < 1 min
        elif eta_seconds < 300:
            return self._rgb_color(255, 255, 0)  # Yellow for < 5 min
        elif eta_seconds < 900:
            return self._rgb_color(255, 128, 0)  # Orange for < 15 min
        else:
            return self._rgb_color(255, 0, 0)  # Red for > 15 min
    
    def _get_initial_time_estimate(self) -> float:
        """
        Get initial time estimate per item based on library size.
        
        Returns:
            Estimated seconds per item
        """
        # Estimates based on library size and complexity
        # These are conservative estimates that will be refined
        if self.total_items < 1000:
            # Small library: ~0.05 seconds per item (20 items/sec)
            return 0.05
        elif self.total_items < 5000:
            # Medium library: ~0.04 seconds per item (25 items/sec)
            return 0.04
        elif self.total_items < 10000:
            # Large library: ~0.03 seconds per item (33 items/sec)
            return 0.03
        elif self.total_items < 50000:
            # Very large library: ~0.025 seconds per item (40 items/sec)
            return 0.025
        else:
            # Huge library: ~0.02 seconds per item (50 items/sec)
            return 0.02
    
    def _calculate_adaptive_eta(self, current_items: int, batch_time: float = None) -> float:
        """
        Calculate ETA with progressive refinement.
        
        Uses initial estimate, then refines based on actual batch processing times.
        
        Args:
            current_items: Number of items processed so far
            batch_time: Time taken for the current batch (optional)
            
        Returns:
            Estimated seconds remaining
        """
        remaining_items = self.total_items - current_items
        
        if batch_time is not None and self.batch_size > 0:
            # Add current batch time to history
            time_per_item = batch_time / self.batch_size
            self.batch_times.append(time_per_item)
            
            # Keep only the last N batches
            if len(self.batch_times) > self.max_batch_history:
                self.batch_times.pop(0)
        
        # Calculate ETA based on available data
        if len(self.batch_times) >= 3:
            # We have enough history, use weighted moving average
            # Give more weight to recent batches
            weights = [i + 1 for i in range(len(self.batch_times))]
            weighted_sum = sum(t * w for t, w in zip(self.batch_times, weights))
            total_weight = sum(weights)
            avg_time_per_item = weighted_sum / total_weight
            
            # Smooth the estimate with the initial estimate (10% weight to initial)
            avg_time_per_item = (avg_time_per_item * 0.9) + (self.initial_estimate_per_item * 0.1)
        elif len(self.batch_times) > 0:
            # Limited history, blend with initial estimate
            avg_batch_time = sum(self.batch_times) / len(self.batch_times)
            # Give 50% weight to actual data, 50% to initial estimate
            avg_time_per_item = (avg_batch_time * 0.5) + (self.initial_estimate_per_item * 0.5)
        else:
            # No history yet, use initial estimate
            avg_time_per_item = self.initial_estimate_per_item
        
        # Calculate ETA
        eta_seconds = remaining_items * avg_time_per_item
        
        # Add a small buffer for database operations (5% overhead)
        eta_seconds *= 1.05
        
        return eta_seconds
    
    @staticmethod
    def _calculate_display_width(text: str) -> int:
        """
        Calculate the actual display width of text, accounting for emojis and ANSI codes.
        
        Args:
            text: Text that may contain emojis and ANSI color codes
            
        Returns:
            Display width in terminal columns
        """
        import re
        import unicodedata
        
        # Remove ANSI color codes for width calculation
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text_no_ansi = ansi_escape.sub('', text)
        
        # Calculate display width accounting for wide characters
        width = 0
        for char in text_no_ansi:
            # Get East Asian Width property
            char_width = unicodedata.east_asian_width(char)
            
            # Check if it's an emoji or wide character
            # 'W' = Wide, 'F' = Fullwidth (both take 2 columns)
            # Most emojis are 'W' or have Emoji property
            if char_width in ('W', 'F'):
                width += 2
            # Check for emoji using Unicode category and common emoji ranges
            elif ord(char) in range(0x1F300, 0x1F9FF):  # Emoticons, symbols, etc.
                width += 2
            elif ord(char) in range(0x2600, 0x27BF):  # Miscellaneous symbols (includes ⚡)
                width += 2  
            elif ord(char) in range(0x2300, 0x23FF):  # Technical symbols
                width += 2
            elif ord(char) in range(0x2700, 0x27BF):  # Dingbats
                width += 2
            elif ord(char) == 0x2705:  # ✅ Check mark
                width += 2
            elif ord(char) == 0x274C:  # ❌ Cross mark
                width += 2
            elif ord(char) in range(0x1F000, 0x1FFFF):  # Various emoji blocks
                width += 2
            # Zero-width characters (combining marks, etc.)
            elif char_width in ('Mn', 'Me', 'Cf') or unicodedata.category(char) in ('Mn', 'Me', 'Cf'):
                width += 0
            else:
                # Normal width character
                width += 1
        
        return width
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds into human-readable time."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds / 3600)
            mins = int((seconds % 3600) / 60)
            return f"{hours}h {mins}m"
    
    def create_progress_bar(self, current: int, total: int, width: int = 60) -> str:
        """
        Create a colored progress bar.
        
        Args:
            current: Current progress value
            total: Total value
            width: Width of the progress bar in characters
            
        Returns:
            Formatted progress bar string
        """
        percent = (current / total * 100) if total > 0 else 0
        filled = int(width * percent / 100)
        
        # Build gradient bar
        bar_chars = []
        
        for i in range(width):
            if i < filled:
                # Calculate color for each character position
                char_percent = (i / width) * 100
                color = self._get_gradient_color(char_percent)
                bar_chars.append(f"{color}{self.chars['progress_full']}")
            else:
                # Empty part
                bar_chars.append(self.chars['progress_empty'])
        
        bar = ''.join(bar_chars)
        # Add reset code at the end if colors were used
        if filled > 0 and self.color_support != 'none':
            bar += '\033[0m'  # Reset all attributes
        
        # Format with percentage and numbers
        percent_str = f"{percent:.1f}%"
        numbers_str = f"{current:,}/{total:,}"
        
        return f"[{bar}{self.reset}] {percent_str} ({numbers_str})"
    
    def _output(self, message: str, level: str = "info", force_log: bool = False):
        """
        Output helper that can write to console-only or to both console and log file.
        
        Args:
            message: The message to output
            level: Log level ("info", "debug", "warning", "error")
            force_log: If True, always write to log file even in console_only mode
        """
        if self.console_only and not force_log:
            # Write directly to console, bypassing file logger
            print(message, flush=True)
        else:
            # Use logger which writes to both console and file
            if self.logger:
                log_func = getattr(self.logger, level, self.logger.info)
                log_func(message)
    
    def log_sync_start(self):
        """Log the sync start message with beautiful formatting."""
        icon = self.chars['icons']
        
        # Box width configuration (total width including borders)
        box_width = 68  # Total width of the box including borders
        inner_width = box_width - 4  # Subtract 2 for "│ " and 2 for " │"
        
        # Always log the start message to file for record keeping
        if self.unicode_level == 'full':
            # Beautiful Unicode box with rounded corners and emojis
            # Note: Emojis can be 2 characters wide in terminals
            border_line = "─" * (box_width - 2)  # -2 for corner characters
            self._output(f"╭{border_line}╮", force_log=True)
            
            title = f"{icon['start']} Library Sync Started ({self.sync_type.title()} Sync)"
            # Use the display width calculator to get accurate width
            title_display_width = self._calculate_display_width(title)
            padding_needed = inner_width - title_display_width
            padding_needed = max(0, padding_needed)  # Ensure non-negative
            self._output(f"│ {title}{' ' * padding_needed} │", force_log=True)
            
            self._output(f"├{border_line}┤", force_log=True)
            
            # Format stats with proper spacing
            stats_lines = [
                (icon['stats'], f"Total items: {self.total_items:,}"),
                (icon['batch'], f"Batch size: {self.batch_size} (adaptive)"),
                (icon['speed'], "Mode: Streaming (producer-consumer)")
            ]
            
            for emoji, text in stats_lines:
                line_content = f"{emoji}  {text}"  # Two spaces after emoji for visual balance
                content_display_width = self._calculate_display_width(line_content)
                padding = inner_width - content_display_width
                padding = max(0, padding)  # Ensure non-negative
                self._output(f"│ {line_content}{' ' * padding} │", force_log=True)
            
            self._output(f"╰{border_line}╯", force_log=True)
        elif self.unicode_level == 'unicode':
            # Unicode without emojis  
            border_line = "─" * (box_width - 2)
            self._output(f"╭{border_line}╮", force_log=True)
            
            title = f"{icon['start']} Library Sync Started ({self.sync_type.title()} Sync)"
            title_display_width = self._calculate_display_width(title)
            padding_needed = inner_width - title_display_width
            padding_needed = max(0, padding_needed)
            self._output(f"│ {title}{' ' * padding_needed} │", force_log=True)
            
            self._output(f"├{border_line}┤", force_log=True)
            
            # Format stats lines
            stats_lines = [
                f"{icon['stats']} Total items: {self.total_items:,}",
                f"{icon['batch']} Batch size: {self.batch_size} (adaptive)",
                f"{icon['speed']} Mode: Streaming (producer-consumer)"
            ]
            
            for line in stats_lines:
                line_display_width = self._calculate_display_width(line)
                padding = inner_width - line_display_width
                padding = max(0, padding)
                self._output(f"│ {line}{' ' * padding} │", force_log=True)
            
            self._output(f"╰{border_line}╯", force_log=True)
        else:
            # ASCII fallback
            # ASCII boxes are simpler - no multi-byte characters
            border_line = "-" * (box_width - 2)
            self._output(f"+{border_line}+", force_log=True)
            
            title = f"{icon['start']} Library Sync Started ({self.sync_type.title()} Sync)"
            # For ASCII, icons are multi-char like "[>]" so we still need display width
            title_display_width = self._calculate_display_width(title)
            padding_needed = inner_width - title_display_width
            padding_needed = max(0, padding_needed)
            self._output(f"| {title}{' ' * padding_needed} |", force_log=True)
            
            self._output(f"+{border_line}+", force_log=True)
            
            stats_lines = [
                f"{icon['stats']} Total items: {self.total_items:,}",
                f"{icon['batch']} Batch size: {self.batch_size} (adaptive)",
                f"{icon['speed']} Mode: Streaming (producer-consumer)"
            ]
            
            for line in stats_lines:
                line_display_width = self._calculate_display_width(line)
                padding = inner_width - line_display_width
                padding = max(0, padding)
                self._output(f"| {line}{' ' * padding} |", force_log=True)
            
            self._output(f"+{border_line}+", force_log=True)
    
    def log_batch_progress(self, batch_num: int, items_in_batch: int, 
                          total_fetched: int, items_processed: int,
                          errors: int = 0, new_items: int = 0, 
                          updated_items: int = 0, batch_time: float = None):
        """
        Log progress for each batch with colors and formatting.
        
        Args:
            batch_num: Current batch number
            items_in_batch: Number of items in this batch
            total_fetched: Total items fetched so far
            items_processed: Total items processed so far
            errors: Total error count
            new_items: Total new items found
            updated_items: Total updated items found
            batch_time: Time taken to process this batch (for ETA refinement)
        """
        # Update statistics
        self.current_batch = batch_num
        self.items_fetched = total_fetched
        self.items_processed = items_processed
        self.errors = errors
        self.new_items = new_items
        self.updated_items = updated_items
        
        # Calculate metrics
        # Calculate percentage for display (not currently used but may be needed later)
        # percent = (total_fetched / self.total_items * 100) if self.total_items > 0 else 0
        elapsed = time.time() - self.start_time
        speed = total_fetched / elapsed if elapsed > 0 else 0
        
        # Use adaptive ETA calculation
        eta = self._calculate_adaptive_eta(total_fetched, batch_time)
        
        # Create progress bar
        progress_bar = self.create_progress_bar(total_fetched, self.total_items)
        
        # Get colors for stats
        speed_color = self._get_speed_color(speed)
        error_color = self._get_error_color(errors)
        eta_color = self._get_eta_color(eta)
        new_color = self._rgb_color(0, 255, 128)  # Green for new
        update_color = self._rgb_color(0, 128, 255)  # Blue for updates
        
        # Icons
        icon = self.chars['icons']
        tree = self.chars
        
        # Progress bar to console only, summary info to log file
        self._output(f"Sync Progress: {progress_bar}")
        
        # Log a simplified summary to the file (no progress bar)
        if self.logger and not self.console_only:
            # Only log key stats to file, not the visual progress bar
            self.logger.info(f"Sync batch #{batch_num}: {total_fetched:,}/{self.total_items:,} items fetched, {items_processed:,} processed, {new_items} new, {updated_items} updated, {errors} errors")
        
        # Detailed stats to console only
        if self.unicode_level == 'full' or self.unicode_level == 'unicode':
            # Use proper tree characters with spacing
            self._output(f"{tree['tree_mid']}  {icon['batch']}  Batch: #{batch_num} ({items_in_batch} items)  │  Total: {total_fetched:,}/{self.total_items:,}", level="debug")
            self._output(f"{tree['tree_mid']}  {icon['speed']}  Speed: {speed_color}{speed:.0f} items/sec{self.reset}", level="debug")
            self._output(f"{tree['tree_mid']}  {icon['time']}  ETA: {eta_color}~{SyncProgressDisplay._format_time(eta)}{self.reset}", level="debug")
            self._output(f"{tree['tree_mid']}  {icon['success']}  Processed: {items_processed:,}  │  {icon['error']}  Errors: {error_color}{errors}{self.reset}", level="debug")
            self._output(f"{tree['tree_end']}  {icon['new']}  New: {new_color}{new_items}{self.reset}  │  {icon['update']}  Updated: {update_color}{updated_items}{self.reset}", level="debug")
        else:
            # ASCII fallback with simpler formatting
            self._output(f"{tree['tree_mid']} {icon['batch']} Batch: #{batch_num} ({items_in_batch} items) | Total: {total_fetched:,}/{self.total_items:,}", level="debug")
            self._output(f"{tree['tree_mid']} {icon['speed']} Speed: {speed_color}{speed:.0f} items/sec{self.reset}", level="debug")
            self._output(f"{tree['tree_mid']} {icon['time']} ETA: {eta_color}~{SyncProgressDisplay._format_time(eta)}{self.reset}", level="debug")
            self._output(f"{tree['tree_mid']} {icon['success']} Processed: {items_processed:,} | {icon['error']} Errors: {error_color}{errors}{self.reset}", level="debug")
            self._output(f"{tree['tree_end']} {icon['new']} New: {new_color}{new_items}{self.reset} | {icon['update']} Updated: {update_color}{updated_items}{self.reset}", level="debug")
    
    def log_sync_complete(self, success: bool = True):
        """
        Log sync completion message.
        
        Args:
            success: Whether the sync completed successfully
        """
        elapsed = time.time() - self.start_time
        icon = self.chars['icons']
        
        if success:
            status_icon = icon['complete']
            status_text = "Sync Complete"
            status_color = self._rgb_color(0, 255, 0)
        else:
            status_icon = icon['error']
            status_text = "Sync Failed"
            status_color = self._rgb_color(255, 0, 0)
        
        # Box width configuration
        box_width = 68  # Total width of the box including borders
        inner_width = box_width - 4  # Subtract 2 for "│ " and 2 for " │"
        
        # Always log completion to file for record keeping
        if self.unicode_level == 'full':
            border_line = "─" * (box_width - 2)
            self._output(f"╭{border_line}╮", force_log=True)
            
            # Format status line with proper padding accounting for color codes
            status_line = f"{status_icon}  {status_text}: {self.items_processed:,} items in {SyncProgressDisplay._format_time(elapsed)}"
            # Use display width calculator for accurate width (excludes ANSI codes)
            status_display_width = self._calculate_display_width(status_line)
            padding_needed = inner_width - status_display_width
            padding_needed = max(0, padding_needed)
            # Note: color codes go around the content, not affecting padding
            self._output(f"│ {status_color}{status_line}{self.reset}{' ' * padding_needed} │", force_log=True)
            
            self._output(f"├{border_line}┤", force_log=True)
            
            # Format stats with consistent spacing
            stats_lines = [
                (icon['new'], f"New items: {self.new_items:,}"),
                (icon['update'], f"Updated: {self.updated_items:,}"),
                (icon['error'], f"Errors: {self.errors:,}")
            ]
            
            for emoji, text in stats_lines:
                line_content = f"{emoji}  {text}"  # Two spaces after emoji
                content_display_width = self._calculate_display_width(line_content)
                padding = inner_width - content_display_width
                padding = max(0, padding)
                self._output(f"│ {line_content}{' ' * padding} │", force_log=True)
            
            self._output(f"╰{border_line}╯", force_log=True)
        elif self.unicode_level == 'unicode':
            border_line = "─" * (box_width - 2)
            self._output(f"╭{border_line}╮", force_log=True)
            
            status_line = f"{status_icon} {status_text}: {self.items_processed:,} items in {SyncProgressDisplay._format_time(elapsed)}"
            status_display_width = self._calculate_display_width(status_line)
            padding_needed = inner_width - status_display_width
            padding_needed = max(0, padding_needed)
            self._output(f"│ {status_color}{status_line}{self.reset}{' ' * padding_needed} │", force_log=True)
            
            self._output(f"├{border_line}┤", force_log=True)
            
            stats_lines = [
                f"{icon['new']} New items: {self.new_items:,}",
                f"{icon['update']} Updated: {self.updated_items:,}",
                f"{icon['error']} Errors: {self.errors:,}"
            ]
            
            for line in stats_lines:
                line_display_width = self._calculate_display_width(line)
                padding = inner_width - line_display_width
                padding = max(0, padding)
                self._output(f"│ {line}{' ' * padding} │", force_log=True)
            
            self._output(f"╰{border_line}╯", force_log=True)
        else:
            border_line = "-" * (box_width - 2)
            self._output(f"+{border_line}+", force_log=True)
            
            status_line = f"{status_icon} {status_text}: {self.items_processed:,} items in {SyncProgressDisplay._format_time(elapsed)}"
            status_display_width = self._calculate_display_width(status_line)
            padding_needed = inner_width - status_display_width
            padding_needed = max(0, padding_needed)
            self._output(f"| {status_line}{' ' * padding_needed} |", force_log=True)
            
            self._output(f"+{border_line}+", force_log=True)
            
            stats_lines = [
                f"{icon['new']} New items: {self.new_items:,}",
                f"{icon['update']} Updated: {self.updated_items:,}",
                f"{icon['error']} Errors: {self.errors:,}"
            ]
            
            for line in stats_lines:
                line_display_width = self._calculate_display_width(line)
                padding = inner_width - line_display_width
                padding = max(0, padding)
                self._output(f"| {line}{' ' * padding} |", force_log=True)
            
            self._output(f"+{border_line}+", force_log=True)


# Export the main class
__all__ = ['SyncProgressDisplay']