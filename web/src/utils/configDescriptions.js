// Configuration field descriptions for tooltips
export const configDescriptions = {
  jellyfin: {
    server_url: "Full URL of your Jellyfin server including protocol and port (e.g., http://jellyfin:8096). This is where webhooks will be received from.",
    api_key: "API key from Jellyfin Dashboard → API Keys. Required for fetching library data and media metadata.",
    user_id: "Your Jellyfin user ID for API access. Found in Dashboard → Users → Select User → ID in URL.",
    client_name: "Identifier for this application in Jellyfin logs. Helps track API usage.",
    client_version: "Version string sent to Jellyfin. Used for compatibility tracking.",
    device_name: "Device name shown in Jellyfin active sessions.",
    device_id: "Unique identifier for this webhook service instance."
  },
  
  discord: {
    webhooks: {
      default: {
        url: "Discord webhook URL for general notifications. This is the fallback for all content types.",
        enabled: "Enable or disable this webhook without removing the URL.",
        grouping: {
          mode: "How to group multiple notifications: none (individual), time (batch by delay), or smart (group similar content).",
          delay_minutes: "Wait time before sending grouped notifications. Useful for library scans.",
          max_items: "Maximum items per grouped message. Discord limits embed count."
        }
      },
      movies: {
        url: "Dedicated webhook for movie notifications. Leave empty to use default.",
        enabled: "Route movie notifications to this dedicated channel.",
      },
      tv: {
        url: "Dedicated webhook for TV show and episode notifications.",
        enabled: "Route TV content to this dedicated channel.",
      },
      music: {
        url: "Dedicated webhook for music and audio content.",
        enabled: "Route music notifications to this dedicated channel.",
      }
    },
    routing: {
      enabled: "Enable content-based routing to different Discord channels.",
      movie_types: "Jellyfin item types to route to movies webhook.",
      tv_types: "Jellyfin item types to route to TV webhook.",
      music_types: "Jellyfin item types to route to music webhook.",
      fallback_webhook: "Which webhook to use when content type doesn't match routing rules."
    },
    rate_limit: {
      requests_per_period: "Maximum Discord API requests per time period.",
      period_seconds: "Time period for rate limit calculation.",
      channel_limit_per_minute: "Discord's per-channel message limit. Don't exceed 30/min."
    }
  },
  
  notifications: {
    watch_changes: {
      resolution: "Notify when video resolution improves (720p → 1080p → 4K).",
      video_codec: "Notify when video codec improves (H.264 → H.265/HEVC).",
      audio_codec: "Notify when audio codec changes (AAC → DTS → TrueHD).",
      audio_channels: "Notify when audio channels increase (Stereo → 5.1 → 7.1).",
      hdr_status: "Notify when HDR is added (SDR → HDR10 → Dolby Vision).",
      file_size: "Notify when file size changes significantly (>10% difference).",
      subtitles: "Notify when subtitle tracks are added or changed (language/format)."
    },
    colors: {
      new_item: "Discord embed color for new content (decimal format).",
      resolution_upgrade: "Color for resolution improvements.",
      codec_upgrade: "Color for codec improvements.",
      audio_upgrade: "Color for audio improvements.",
      hdr_upgrade: "Color for HDR upgrades."
    },
    filter_renames: "Detect and ignore mass renames to prevent notification spam.",
    filter_deletes: "Hide deletion notifications. Useful during library maintenance."
  },
  
  metadata_services: {
    enabled: "Enable external metadata fetching for richer notifications.",
    omdb: {
      enabled: "Fetch IMDb ratings and additional movie data.",
      api_key: "OMDb API key from omdbapi.com (1000 free requests/day).",
      base_url: "OMDb API endpoint. Rarely needs changing."
    },
    tmdb: {
      enabled: "Fetch movie and TV show metadata, posters, and overviews.",
      api_key: "TMDb API key from themoviedb.org (free with account).",
      base_url: "TMDb API endpoint. Rarely needs changing."
    },
    tvdb: {
      enabled: "Fetch detailed TV series and episode information.",
      api_key: "TVDb API key from thetvdb.com (requires subscription).",
      base_url: "TVDb API v4 endpoint.",
      subscriber_pin: "TVDb subscriber PIN for premium features."
    },
    cache_duration_hours: "How long to cache metadata before refreshing.",
    tvdb_cache_ttl_hours: "Specific cache duration for TVDb data.",
    request_timeout_seconds: "Maximum wait time for external API responses.",
    retry_attempts: "Number of retries for failed metadata requests."
  },
  
  server: {
    host: "Network interface to bind. Use 0.0.0.0 for all interfaces.",
    port: "Port for webhook service. Jellyfin sends webhooks here.",
    log_level: "Logging verbosity: DEBUG (everything), INFO (normal), WARNING (issues), ERROR (problems only).",
    run_mode: "Which services to run: all (both), webhook (notifications only), web (interface only).",
    development_mode: "Enable development features like debug endpoints and verbose errors.",
    show_docker_interfaces: "Display Docker network interfaces in logs and UI. Useful for container debugging.",
    force_color_output: "Force colored console output even in non-TTY environments like Docker logs.",
    disable_color_output: "Disable all colored output for compatibility with log parsers."
  },
  
  web_interface: {
    enabled: "Enable web management interface on separate port.",
    host: "Network interface for web UI. Use 0.0.0.0 for all interfaces.",
    port: "Port for web interface. Access UI at this port.",
    auth_enabled: "Require login to access web interface. Recommended for internet exposure.",
    require_webhook_auth: "Require Bearer token for Jellyfin webhooks. Adds security but needs Jellyfin configuration.",
    jwt_secret: "Secret key for token signing. Auto-generated if empty. Keep this secure!",
    username: "Admin username for web interface login.",
    password: "Admin password. Will be hashed before storage."
  },
  
  database: {
    path: "SQLite database location. Stores media history and change detection.",
    vacuum_interval_hours: "How often to optimize database storage.",
    wal_mode: "Write-Ahead Logging for better concurrent access. Keep enabled.",
    busy_timeout_ms: "Maximum wait time for database locks.",
    cache_size: "Database cache size in pages. Higher = more RAM, better performance.",
    synchronous: "Durability vs performance trade-off. NORMAL is balanced."
  },
  
  sync: {
    enabled: "Enable periodic library synchronization to catch missed webhooks.",
    interval_minutes: "How often to sync with Jellyfin library.",
    batch_size: "Items to process per database transaction.",
    max_retries: "Maximum sync attempts before giving up.",
    libraries: "Specific library IDs to sync. Empty = all libraries."
  },
  
  ssl: {
    enabled: "Enable HTTPS for web interface. Required for internet exposure.",
    cert_path: "Path to SSL certificate file (PEM format).",
    key_path: "Path to SSL private key file (PEM format).",
    pfx_path: "Path to PFX/PKCS12 certificate bundle (alternative to separate files).",
    pfx_password: "Password for PFX certificate file.",
    port: "HTTPS port for secure web interface."
  },
  
  templates: {
    directory: "Folder where Jinja2 template files are stored.",
    new_item_template: "Template for single new item notifications. Used when adding individual media.",
    upgraded_item_template: "Template for quality upgrade notifications. Used when media is replaced with better quality.",
    deleted_item_template: "Template for deletion notifications. Used when media is removed from library.",
    new_items_by_event_template: "Template for batch new items by event. Groups multiple additions from same scan.",
    upgraded_items_by_event_template: "Template for batch upgrades by event. Groups multiple upgrades from same scan.",
    new_items_by_type_template: "Template for new items grouped by type. Organizes additions by Movies/TV/Music.",
    upgraded_items_by_type_template: "Template for upgrades grouped by type. Organizes upgrades by Movies/TV/Music.",
    new_items_grouped_template: "Template for smart grouped new items. Intelligently batches similar content.",
    upgraded_items_grouped_template: "Template for smart grouped upgrades. Intelligently batches similar upgrades."
  }
};

// Shorter descriptions for inline use
export const quickDescriptions = {
  "Enable Web Interface": "Run the management dashboard on a separate port",
  "Require Authentication": "Protect the web interface with username/password",
  "Require Webhook Authentication": "Jellyfin must send Bearer token with webhooks",
  "Enable SSL/TLS": "Use HTTPS for secure connections",
  "Enable Routing": "Send different content types to different Discord channels",
  "Enable Sync": "Periodically check Jellyfin library for missed items",
  "Filter Renames": "Ignore mass rename events that spam notifications",
  "Filter Deletes": "Don't notify when content is removed from library"
};