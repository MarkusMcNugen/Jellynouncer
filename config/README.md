# Jellynouncer Configuration Guide

This comprehensive guide covers all configuration options for Jellynouncer, a Discord webhook service for Jellyfin media server notifications. The configuration system supports both JSON/YAML files and environment variable overrides for flexible deployment scenarios.

## Table of Contents

- [Quick Start](#quick-start)
- [Configuration File Structure](#configuration-file-structure)
- [Core Configuration Sections](#core-configuration-sections)
  - [Jellyfin Settings](#jellyfin-settings)
  - [Discord Webhooks](#discord-webhooks)
  - [Database Configuration](#database-configuration)
  - [Template Settings](#template-settings)
  - [Notification Behavior](#notification-behavior)
  - [Web Server Settings](#web-server-settings)
  - [Library Synchronization](#library-synchronization)
  - [Rating Services](#rating-services)
- [Environment Variable Overrides](#environment-variable-overrides)
- [Configuration Examples](#configuration-examples)
- [Validation and Troubleshooting](#validation-and-troubleshooting)
- [Best Practices](#best-practices)

## Quick Start

### Minimal Configuration

Create a `config.json` file with the minimum required settings:

```json
{
  "jellyfin": {
    "server_url": "http://your-jellyfin-server:8096",
    "api_key": "your_jellyfin_api_key_here",
    "user_id": "your_user_id_here"
  },
  "discord": {
    "webhooks": {
      "default": {
        "name": "General Notifications",
        "enabled": true,
        "url": "https://discord.com/api/webhooks/your/webhook/url"
      }
    }
  }
}
```

### Using Environment Variables

For Docker deployments, you can override settings using environment variables:

```bash
export JELLYFIN_SERVER_URL="http://jellyfin:8096"
export JELLYFIN_API_KEY="your_api_key_here"
export JELLYFIN_USER_ID="your_user_id_here"
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

## Configuration File Structure

Jellynouncer supports both JSON and YAML configuration formats. The configuration is organized into logical sections:

```json
{
  "jellyfin": { /* Jellyfin server connection settings */ },
  "rating_services": { /* External rating APIs (OMDb, TMDb, TVDB) */ },
  "discord": { /* Discord webhook configurations */ },
  "database": { /* SQLite database settings */ },
  "templates": { /* Jinja2 template configuration */ },
  "notifications": { /* Notification behavior settings */ },
  "server": { /* Web server configuration */ },
  "sync": { /* Library synchronization settings */ }
}
```

## Core Configuration Sections

### Jellyfin Settings

The `jellyfin` section configures connection to your Jellyfin media server.

```json
{
  "jellyfin": {
    "server_url": null,
    "api_key": null,
    "user_id": null,
    "client_name": "Jellynouncer-Discord-Webhook",
    "client_version": "1.0.0",
    "device_name": "jellynouncer-webhook-service",
    "device_id": "jellynouncer-discord-webhook-001"
  }
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `server_url` | string | ✅ | Full URL to your Jellyfin server (e.g., `http://jellyfin:8096`) |
| `api_key` | string | ✅ | Jellyfin API key for authentication |
| `user_id` | string | ✅ | Jellyfin user ID for the account used for notifications |
| `client_name` | string | ❌ | Client identifier for Jellyfin API (default: "Jellynouncer-Discord-Webhook") |
| `client_version` | string | ❌ | Version identifier for the client (default: "2.0.0") |
| `device_name` | string | ❌ | Device name shown in Jellyfin dashboard (default: "jellynouncer-webhook-service") |
| `device_id` | string | ❌ | Unique device identifier (default: "jellynouncer-discord-webhook-001") |

**How to get these values:**
- **API Key**: Jellyfin Dashboard → API Keys → Create new key
- **User ID**: Jellyfin Dashboard → Users → Click your user → Copy ID from URL
- **Server URL**: Your Jellyfin server address (internal Docker network or public URL)

### Rating Services

The `rating_services` section configures external APIs for fetching movie/TV show ratings and metadata.

```json
{
  "rating_services": {
    "enabled": true,
    "omdb": {
      "enabled": false,
      "api_key": null,
      "base_url": "http://www.omdbapi.com/"
    },
    "tmdb": {
      "enabled": false,
      "api_key": null,
      "base_url": "https://api.themoviedb.org/3/"
    },
    "tvdb": {
      "enabled": false,
      "api_key": null,
      "base_url": "https://api4.thetvdb.com/v4/"
    },
    "cache_duration_hours": 168,
    "request_timeout_seconds": 10,
    "retry_attempts": 3
  }
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `enabled` | boolean | ❌ | Enable/disable all rating services |
| `omdb.enabled` | boolean | ❌ | Enable OMDb API for movie data |
| `omdb.api_key` | string | ❌ | OMDb API key (free tier: 1000 requests/day) |
| `omdb.base_url` | string | ❌ | OMDb API base URL |
| `tmdb.enabled` | boolean | ❌ | Enable TMDb API for movie/TV data |
| `tmdb.api_key` | string | ❌ | TMDb API key (free with registration) |
| `tmdb.base_url` | string | ❌ | TMDb API base URL |
| `tvdb.enabled` | boolean | ❌ | Enable TVDB API for TV show data |
| `tvdb.api_key` | string | ❌ | TVDB v4 API key |
| `tvdb.base_url` | string | ❌ | TVDB API base URL |
| `cache_duration_hours` | integer | ❌ | How long to cache rating data (default: 168 hours/7 days) |
| `request_timeout_seconds` | integer | ❌ | API request timeout |
| `retry_attempts` | integer | ❌ | Number of retry attempts for failed requests |

**Getting API Keys:**
- **OMDb**: Register at [omdbapi.com](http://www.omdbapi.com/apikey.aspx)
- **TMDb**: Register at [themoviedb.org](https://www.themoviedb.org/settings/api)
- **TVDB**: Register at [thetvdb.com](https://thetvdb.com/api-information)

### Discord Webhooks

The `discord` section configures Discord webhook routing and rate limiting.

```json
{
  "discord": {
    "webhooks": {
      "default": {
        "url": null,
        "name": "General",
        "enabled": true,
        "grouping": {
          "mode": "none",
          "delay_minutes": 5,
          "max_items": 25
        }
      },
      "movies": {
        "url": null,
        "name": "Movies",
        "enabled": false,
        "grouping": {
          "mode": "none",
          "delay_minutes": 5,
          "max_items": 25
        }
      },
      "tv": {
        "url": null,
        "name": "TV Shows",
        "enabled": false,
        "grouping": {
          "mode": "none",
          "delay_minutes": 5,
          "max_items": 25
        }
      },
      "music": {
        "url": null,
        "name": "Music",
        "enabled": false,
        "grouping": {
          "mode": "none",
          "delay_minutes": 5,
          "max_items": 25
        }
      }
    },
    "routing": {
      "enabled": false,
      "movie_types": ["Movie"],
      "tv_types": ["Episode", "Season", "Series"],
      "music_types": ["Audio", "MusicAlbum", "MusicArtist"],
      "fallback_webhook": "default"
    },
    "rate_limit": {
      "requests_per_period": 5,
      "period_seconds": 2,
      "channel_limit_per_minute": 30
    }
  }
}
```

#### Webhook Configuration

Each webhook (default, movies, tv, music) supports these parameters:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | ✅ | Discord webhook URL |
| `name` | string | ❌ | Display name for the webhook |
| `enabled` | boolean | ❌ | Enable/disable this webhook |
| `grouping.mode` | string | ❌ | Grouping mode: `"none"`, `"event_type"`, `"content_type"`, or `"both"` |
| `grouping.delay_minutes` | integer | ❌ | Minutes to wait before sending grouped notifications |
| `grouping.max_items` | integer | ❌ | Maximum items per grouped notification |

**Grouping Modes:**
- `"none"`: Individual notifications for each item
- `"event_type"`: Group by new/upgraded items
- `"content_type"`: Group by movie/TV/music type
- `"both"`: Group by both event and content type

#### Routing Configuration

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `enabled` | boolean | ❌ | Enable content-type routing |
| `movie_types` | array | ❌ | Jellyfin item types considered movies |
| `tv_types` | array | ❌ | Jellyfin item types considered TV content |
| `music_types` | array | ❌ | Jellyfin item types considered music |
| `fallback_webhook` | string | ❌ | Webhook to use if specific type webhook is disabled |

#### Rate Limiting

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `requests_per_period` | integer | ❌ | Maximum requests per period |
| `period_seconds` | integer | ❌ | Rate limit period in seconds |
| `channel_limit_per_minute` | integer | ❌ | Maximum messages per channel per minute |

### Database Configuration

The `database` section configures SQLite database settings.

```json
{
  "database": {
    "path": "/app/data/jellyfin_items.db",
    "wal_mode": true,
    "vacuum_interval_hours": 24
  }
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | ❌ | Path to SQLite database file (default: "/app/data/jellyfin_items.db") |
| `wal_mode` | boolean | ❌ | Enable WAL mode for better concurrent access (default: true) |
| `vacuum_interval_hours` | integer | ❌ | Hours between database VACUUM operations (default: 24) |

### Template Settings

The `templates` section configures Jinja2 template files for Discord embeds.

```json
{
  "templates": {
    "directory": "/app/templates",
    "new_item_template": "new_item.j2",
    "upgraded_item_template": "upgraded_item.j2",
    "new_items_by_event_template": "new_items_by_event.j2",
    "upgraded_items_by_event_template": "upgraded_items_by_event.j2",
    "new_items_by_type_template": "new_items_by_type.j2",
    "upgraded_items_by_type_template": "upgraded_items_by_type.j2",
    "new_items_grouped_template": "new_items_grouped.j2",
    "upgraded_items_grouped_template": "upgraded_items_grouped.j2"
  }
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `directory` | string | ❌ | Base directory containing template files |
| `new_item_template` | string | ❌ | Template for new item notifications |
| `upgraded_item_template` | string | ❌ | Template for item upgrade notifications |
| `new_items_by_event_template` | string | ❌ | Template for grouped new items |
| `upgraded_items_by_event_template` | string | ❌ | Template for grouped upgrades |
| `new_items_by_type_template` | string | ❌ | Template for new items grouped by type |
| `upgraded_items_by_type_template` | string | ❌ | Template for upgrades grouped by type |
| `new_items_grouped_template` | string | ❌ | Template for fully grouped new items |
| `upgraded_items_grouped_template` | string | ❌ | Template for fully grouped upgrades |

### Notification Behavior

The `notifications` section configures what changes trigger notifications and embed colors.

```json
{
  "notifications": {
    "watch_changes": {
      "resolution": true,
      "codec": true,
      "audio_codec": true,
      "audio_channels": true,
      "hdr_status": true,
      "file_size": true,
      "provider_ids": true
    },
    "colors": {
      "new_item": 65280,
      "resolution_upgrade": 16766720,
      "codec_upgrade": 16747520,
      "audio_upgrade": 9662683,
      "hdr_upgrade": 16716947,
      "provider_update": 2003199
    }
  }
}
```

#### Change Detection

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `resolution` | boolean | ❌ | Watch for resolution changes (1080p → 4K) |
| `codec` | boolean | ❌ | Watch for video codec changes (H.264 → H.265) |
| `audio_codec` | boolean | ❌ | Watch for audio codec changes (AC3 → DTS) |
| `audio_channels` | boolean | ❌ | Watch for audio channel changes (2.0 → 7.1) |
| `hdr_status` | boolean | ❌ | Watch for HDR status changes (SDR → HDR) |
| `file_size` | boolean | ❌ | Watch for significant file size changes |
| `provider_ids` | boolean | ❌ | Watch for metadata provider ID changes |

#### Embed Colors

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `new_item` | integer | ❌ | Color for new item notifications (green: 65280) |
| `resolution_upgrade` | integer | ❌ | Color for resolution upgrades (orange: 16766720) |
| `codec_upgrade` | integer | ❌ | Color for codec upgrades (yellow: 16747520) |
| `audio_upgrade` | integer | ❌ | Color for audio upgrades (purple: 9662683) |
| `hdr_upgrade` | integer | ❌ | Color for HDR upgrades (gold: 16716947) |
| `provider_update` | integer | ❌ | Color for metadata updates (blue: 2003199) |

### Web Server Settings

The `server` section configures the FastAPI web server.

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 1984,
    "log_level": "INFO"
  }
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `host` | string | ❌ | Host address to bind to |
| `port` | integer | ❌ | Port number for the web server |
| `log_level` | string | ❌ | Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL |

### Library Synchronization

The `sync` section configures periodic library synchronization to catch missed webhooks.

```json
{
  "sync": {
    "startup_sync": true,
    "sync_batch_size": 100,
    "api_request_delay": 0.1
  }
}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `startup_sync` | boolean | ❌ | Perform full library sync on startup |
| `sync_batch_size` | integer | ❌ | Number of items to process per batch |
| `api_request_delay` | float | ❌ | Delay between API requests (seconds) |

## Environment Variable Overrides

Environment variables provide a secure way to override configuration settings without modifying files. This is especially useful for Docker deployments and keeping sensitive data out of configuration files.

### Supported Environment Variables

| Environment Variable | Configuration Path | Description |
|---------------------|-------------------|-------------|
| `JELLYFIN_SERVER_URL` | `jellyfin.server_url` | Jellyfin server URL |
| `JELLYFIN_API_KEY` | `jellyfin.api_key` | Jellyfin API key |
| `JELLYFIN_USER_ID` | `jellyfin.user_id` | Jellyfin user ID |
| `DISCORD_WEBHOOK_URL` | `discord.webhooks.default.url` | Default Discord webhook |
| `DISCORD_WEBHOOK_URL_MOVIES` | `discord.webhooks.movies.url` | Movies webhook |
| `DISCORD_WEBHOOK_URL_TV` | `discord.webhooks.tv.url` | TV shows webhook |
| `DISCORD_WEBHOOK_URL_MUSIC` | `discord.webhooks.music.url` | Music webhook |
| `OMDB_API_KEY` | `rating_services.omdb.api_key` | OMDb API key |
| `TMDB_API_KEY` | `rating_services.tmdb.api_key` | TMDb API key |
| `TVDB_API_KEY` | `rating_services.tvdb.api_key` | TVDB API key |
| `TVDB_SUBSCRIBER_PIN` | `rating_services.tvdb.subscriber_pin` | TVDB subscriber PIN |

### Docker Environment File

Create a `.env` file for Docker deployments:

```bash
# Jellyfin Configuration
JELLYFIN_SERVER_URL=http://jellyfin:8096
JELLYFIN_API_KEY=your_jellyfin_api_key_here
JELLYFIN_USER_ID=your_user_id_here

# Discord Webhooks
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/webhook/url
DISCORD_WEBHOOK_URL_MOVIES=https://discord.com/api/webhooks/your/movies/webhook/url
DISCORD_WEBHOOK_URL_TV=https://discord.com/api/webhooks/your/tv/webhook/url
DISCORD_WEBHOOK_URL_MUSIC=https://discord.com/api/webhooks/your/music/webhook/url

# Rating Services (Optional)
OMDB_API_KEY=your_omdb_api_key_here
TMDB_API_KEY=your_tmdb_api_key_here
TVDB_API_KEY=your_tvdb_v4_api_key_here
TVDB_SUBSCRIBER_PIN=your_subscriber_pin_here

# System Settings
PUID=1000
PGID=1000
TZ=America/New_York
LOG_LEVEL=INFO
```

## Configuration Examples

### Minimal Setup

Perfect for getting started quickly:

```json
{
  "jellyfin": {
    "server_url": "http://localhost:8096",
    "api_key": "your_api_key_here",
    "user_id": "your_user_id_here"
  },
  "discord": {
    "webhooks": {
      "default": {
        "url": "https://discord.com/api/webhooks/your/webhook/url",
        "name": "Jellyfin Notifications",
        "enabled": true
      }
    }
  }
}
```

### Multi-Channel Setup

Route different content types to different Discord channels:

```json
{
  "jellyfin": {
    "server_url": "http://jellyfin:8096",
    "api_key": "your_api_key_here",
    "user_id": "your_user_id_here"
  },
  "discord": {
    "webhooks": {
      "default": {
        "url": "https://discord.com/api/webhooks/.../general",
        "name": "General",
        "enabled": true
      },
      "movies": {
        "url": "https://discord.com/api/webhooks/.../movies",
        "name": "🎬 Movies",
        "enabled": true,
        "grouping": {
          "mode": "event_type",
          "delay_minutes": 3,
          "max_items": 10
        }
      },
      "tv": {
        "url": "https://discord.com/api/webhooks/.../tv",
        "name": "📺 TV Shows",
        "enabled": true,
        "grouping": {
          "mode": "both",
          "delay_minutes": 5,
          "max_items": 15
        }
      },
      "music": {
        "url": "https://discord.com/api/webhooks/.../music",
        "name": "🎵 Music",
        "enabled": true
      }
    },
    "routing": {
      "enabled": true,
      "fallback_webhook": "default"
    }
  }
}
```

### Production Setup

Complete configuration with external rating services and optimized settings:

```json
{
  "jellyfin": {
    "server_url": "http://jellyfin:8096",
    "api_key": "your_api_key_here",
    "user_id": "your_user_id_here"
  },
  "rating_services": {
    "enabled": true,
    "omdb": {
      "enabled": true,
      "api_key": "your_omdb_key_here"
    },
    "tmdb": {
      "enabled": true,
      "api_key": "your_tmdb_key_here"
    },
    "tvdb": {
      "enabled": true,
      "api_key": "your_tvdb_key_here"
    },
    "cache_duration_hours": 168,
    "request_timeout_seconds": 10,
    "retry_attempts": 3
  },
  "discord": {
    "webhooks": {
      "default": {
        "url": "https://discord.com/api/webhooks/.../general",
        "name": "General",
        "enabled": true
      },
      "movies": {
        "url": "https://discord.com/api/webhooks/.../movies",
        "name": "🎬 Movies",
        "enabled": true,
        "grouping": {
          "mode": "event_type",
          "delay_minutes": 2,
          "max_items": 8
        }
      },
      "tv": {
        "url": "https://discord.com/api/webhooks/.../tv",
        "name": "📺 TV Shows",
        "enabled": true,
        "grouping": {
          "mode": "content_type",
          "delay_minutes": 3,
          "max_items": 12
        }
      }
    },
    "routing": {
      "enabled": true,
      "fallback_webhook": "default"
    },
    "rate_limit": {
      "requests_per_period": 3,
      "period_seconds": 2,
      "channel_limit_per_minute": 20
    }
  },
  "database": {
    "path": "/app/data/jellyfin_items.db",
    "wal_mode": true,
    "vacuum_interval_hours": 24
  },
  "notifications": {
    "watch_changes": {
      "resolution": true,
      "codec": true,
      "audio_codec": true,
      "audio_channels": true,
      "hdr_status": true,
      "file_size": true,
      "provider_ids": false
    }
  },
  "sync": {
    "startup_sync": true,
    "sync_batch_size": 50,
    "api_request_delay": 0.2
  }
}
```

### Advanced Grouping Configuration

Configure sophisticated notification grouping:

```json
{
  "discord": {
    "webhooks": {
      "movies": {
        "url": "https://discord.com/api/webhooks/.../movies",
        "name": "🎬 Movies",
        "enabled": true,
        "grouping": {
          "mode": "both",
          "delay_minutes": 5,
          "max_items": 20
        }
      },
      "tv": {
        "url": "https://discord.com/api/webhooks/.../tv", 
        "name": "📺 TV Shows",
        "enabled": true,
        "grouping": {
          "mode": "event_type",
          "delay_minutes": 3,
          "max_items": 15
        }
      }
    }
  }
}
```

## Validation and Troubleshooting

### Configuration Validation

Jellynouncer validates configuration on startup and provides detailed error messages:

```bash
# Check configuration validity
docker logs jellynouncer | grep -E "(ERROR|WARNING|Config)"
```

### Common Configuration Issues

**Invalid JSON Format:**
```
ERROR: Invalid configuration file format: Expecting ',' delimiter: line 15 column 5
```
Solution: Validate JSON syntax using [jsonlint.com](https://jsonlint.com/)

**Missing Required Fields:**
```
ERROR: Missing required Jellyfin server URL
```
Solution: Ensure all required fields are set in config.json or environment variables

**Invalid Webhook URL:**
```
WARNING: Invalid Discord webhook URL format
```
Solution: Verify webhook URL format matches `https://discord.com/api/webhooks/...`

**Database Permission Issues:**
```
ERROR: Cannot write to database path: /app/data/jellyfin_items.db
```
Solution: Check file permissions and ensure data directory is writable

### Testing Configuration

**Test webhook connectivity:**
```bash
curl -X POST "http://localhost:1984/test-webhook?webhook_name=default"
```

**Check service health:**
```bash
curl http://localhost:1984/health
```

**Validate API connectivity:**
```bash
curl http://localhost:1984/stats
```

## Best Practices

### Security

1. **Use Environment Variables**
   ```bash
   # Keep sensitive data out of config files
   export JELLYFIN_API_KEY="your_secure_api_key"
   export DISCORD_WEBHOOK_URL="your_webhook_url"
   ```

2. **Set Proper File Permissions**
   ```bash
   chmod 600 config/config.json  # Read/write for owner only
   ```

3. **Use Docker Secrets** (for Docker Swarm)
   ```yaml
   secrets:
     - jellyfin_api_key
     - discord_webhook_url
   ```

### Performance

1. **Enable WAL Mode**
   ```json
   {
     "database": {
       "wal_mode": true
     }
   }
   ```

2. **Optimize Rate Limiting**
   ```json
   {
     "discord": {
       "rate_limit": {
         "requests_per_period": 5,
         "period_seconds": 2,
         "channel_limit_per_minute": 30
       }
     }
   }
   ```

3. **Configure Appropriate Grouping**
   ```json
   {
     "discord": {
       "webhooks": {
         "default": {
           "grouping": {
             "mode": "both",
             "delay_minutes": 5,
             "max_items": 25
           }
         }
       }
     }
   }
   ```

### Monitoring

1. **Enable Appropriate Logging**
   ```json
   {
     "server": {
       "log_level": "INFO"
     }
   }
   ```

2. **Set Up Proper Filtering**
   ```json
   {
     "notifications": {
       "watch_changes": {
         "resolution": true,
         "codec": true,
         "audio_codec": true,
         "audio_channels": true,
         "hdr_status": true,
         "file_size": false,
         "provider_ids": false
       }
     }
   }
   ```

3. **Configure Regular Maintenance**
   ```json
   {
     "database": {
       "vacuum_interval_hours": 24
     }
   }
   ```

---

For more information about templates, see the [Templates README](../templates/README.md). For general usage and setup instructions, see the main project README.