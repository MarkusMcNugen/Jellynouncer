# Jellynouncer Templates Guide

A comprehensive guide for creating and customizing Discord webhook notifications using Jinja2 templates in Jellynouncer.

## Table of Contents

- [🚨 Discord Webhook Limitations](#-discord-webhook-limitations)
- [📚 Jellyfin Item Properties](#-jellyfin-item-properties)
- [🎨 Global Template Variables](#-global-template-variables)
- [📈 Changes Structure (Upgrade Notifications)](#-changes-structure-upgrade-notifications)
- [🌐 External Metadata Properties (API Keys Required)](#-external-metadata-properties-api-keys-required)
- [📖 Jinja2 Template Basics](#-jinja2-template-basics)
- [🎯 Basic Template Examples](#-basic-template-examples)
- [🚀 Advanced Template Techniques](#-advanced-template-techniques)
- [📊 Using External Metadata in Templates](#-using-external-metadata-in-templates)
- [🌟 Complete Real-World Example](#-complete-real-world-example)
- [🔧 Troubleshooting Guide](#-troubleshooting-guide)
- [📝 Configuration](#-configuration)
- [🎯 Best Practices](#-best-practices)
- [📚 Additional Resources](#-additional-resources)

## 🚨 Discord Webhook Limitations

Before creating templates, understand Discord's embed limitations to avoid errors:

| Component | Limit | Notes |
|-----------|-------|-------|
| **Total Embeds** | 10 per message | Each webhook can contain up to 10 embeds |
| **Total Characters** | 6000 per message | Combined character count of all embeds |
| **Embed Title** | 256 characters | Title field of an embed |
| **Embed Description** | 4096 characters | Main text body of the embed |
| **Field Count** | 25 per embed | Maximum number of field objects |
| **Field Name** | 256 characters | Field title text |
| **Field Value** | 1024 characters | Field content text |
| **Footer Text** | 2048 characters | Footer content |
| **Author Name** | 256 characters | Author field text |
| **URL Length** | 2048 characters | Any URL in the embed |
| **File Size** | 8 MB | For attached files/images |

## 📚 Jellyfin Item Properties

These are the base item properties that are pulled from Jellyfin via an API call when a webhook is received

<details>
<summary>Click to expand complete Jellyfin item properties table</summary>

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `item.air_time` | string | Original air time for TV episodes | "2024-03-15" |
| `item.album` | string | Album name (music) | "Dark Side of the Moon" |
| `item.album_artist` | string | Primary album artist | "Pink Floyd" |
| `item.artists` | list | List of artist names | ["Artist1", "Artist2"] |
| `item.aspect_ratio` | string | Display aspect ratio | "16:9", "2.35:1" |
| `item.audio_bitrate` | integer | Audio bitrate in bps | 320000 |
| `item.audio_channels` | integer | Number of audio channels | 2, 6, 8 |
| `item.audio_codec` | string | Audio codec | "aac", "dts", "flac" |
| `item.audio_default` | boolean | Default audio track | true/false |
| `item.audio_language` | string | Audio language code | "eng", "spa", "fra" |
| `item.audio_samplerate` | integer | Sample rate in Hz | 48000, 96000 |
| `item.audio_title` | string | Audio stream title | "English 5.1" |
| `item.audio_type` | string | Stream type identifier | "Audio" |
| `item.date_created` | string | When added to Jellyfin | "2024-03-15T10:30:00Z" |
| `item.date_modified` | string | Last modification date | "2024-03-16T15:45:00Z" |
| `item.episode_number` | integer | Episode number | 5 |
| `item.episode_number_padded` | string | Padded episode number | "05" |
| `item.episode_number_padded_3` | string | 3-digit padded episode | "005" |
| `item.file_path` | string | Full file path | "/media/movies/movie.mkv" |
| `item.file_size` | integer | File size in bytes | 5368709120 |
| `item.genres` | list | List of genres | ["Action", "Sci-Fi"] |
| `item.height` | integer | Image height (photos) | 1080 |
| `item.imdb_id` | string | IMDb identifier | "tt0133093" |
| `item.item_id` | string | Jellyfin item ID | "abc123def456" |
| `item.item_type` | string | Media type | "Movie", "Episode", "Audio" |
| `item.library_name` | string | Jellyfin library name | "Movies", "TV Shows" |
| `item.name` | string | Media title | "The Matrix" |
| `item.notification_type` | string | Notification event type | "ItemAdded" |
| `item.official_rating` | string | Content rating | "PG-13", "TV-MA" |
| `item.overview` | string | Description/synopsis | "A computer hacker..." |
| `item.premiere_date` | string | Original release date | "1999-03-31" |
| `item.runtime_formatted` | string | Human-readable runtime | "2h 16m" |
| `item.runtime_ticks` | integer | Duration in ticks | 81600000000 |
| `item.season_id` | string | Season Jellyfin ID | "xyz789ghi123" |
| `item.season_number` | integer | Season number | 1 |
| `item.season_number_padded` | string | Padded season number | "01" |
| `item.season_number_padded_3` | string | 3-digit padded season | "001" |
| `item.series_id` | string | Series Jellyfin ID | "def456abc789" |
| `item.series_name` | string | TV series name | "Breaking Bad" |
| `item.series_premiere_date` | string | Series premiere date | "2008-01-20" |
| `item.server_id` | string | Jellyfin server ID | "server123" |
| `item.server_name` | string | Server name | "My Jellyfin" |
| `item.server_url` | string | Server URL | "https://jellyfin.example.com" |
| `item.server_version` | string | Jellyfin version | "10.8.13" |
| `item.studios` | list | Production companies | ["Warner Bros", "Village Roadshow"] |
| `item.subtitle_codec` | string | Subtitle format | "srt", "ass", "pgs" |
| `item.subtitle_default` | boolean | Default subtitle track | true/false |
| `item.subtitle_external` | boolean | External subtitle file | true/false |
| `item.subtitle_forced` | boolean | Forced subtitles | true/false |
| `item.subtitle_language` | string | Subtitle language | "eng", "spa" |
| `item.subtitle_title` | string | Subtitle stream title | "English (SDH)" |
| `item.subtitle_type` | string | Subtitle type | "Subtitle" |
| `item.tagline` | string | Marketing tagline | "Welcome to the Real World" |
| `item.tags` | list | User tags | ["favorite", "classic"] |
| `item.timestamp` | string | Local timestamp | "2024-03-15T10:30:00-05:00" |
| `item.timestamp_created` | string | Object creation time | "2024-03-15T10:30:00Z" |
| `item.tmdb_id` | string | TMDb identifier | "603" |
| `item.tvdb_id` | string | TVDb identifier | "81189" |
| `item.tvdb_slug` | string | TVDb URL slug | "breaking-bad" |
| `item.utc_timestamp` | string | UTC timestamp | "2024-03-15T15:30:00Z" |
| `item.video_bitdepth` | integer | Color bit depth | 8, 10, 12 |
| `item.video_bitrate` | integer | Video bitrate in bps | 15000000 |
| `item.video_codec` | string | Video codec | "h264", "hevc", "av1" |
| `item.video_colorprimaries` | string | Color primaries | "bt709", "bt2020" |
| `item.video_colorspace` | string | Color space | "bt709", "bt2020nc" |
| `item.video_colortransfer` | string | Color transfer | "bt709", "smpte2084" |
| `item.video_framerate` | float | Frames per second | 23.976, 60 |
| `item.video_height` | integer | Resolution height | 1080, 2160 |
| `item.video_interlaced` | boolean | Interlaced video | true/false |
| `item.video_language` | string | Video language | "eng" |
| `item.video_level` | string | Codec level | "4.1", "5.1" |
| `item.video_pixelformat` | string | Pixel format | "yuv420p", "yuv420p10le" |
| `item.video_profile` | string | Codec profile | "High", "Main10" |
| `item.video_range` | string | Dynamic range | "SDR", "HDR10", "Dolby Vision" |
| `item.video_refframes` | integer | Reference frames | 4 |
| `item.video_title` | string | Video stream title | "1080p HEVC" |
| `item.video_type` | string | Stream type | "Video" |
| `item.video_width` | integer | Resolution width | 1920, 3840 |
| `item.width` | integer | Image width (photos) | 1920 |
| `item.year` | integer | Release year | 1999 |
</details>

## 🎨 Global Template Variables
These variables are available in all templates

<details>
<summary>Click to expand complete global template variables reference tables</summary>

| Variable | Type | Description | Example |
|----------|------|-------------|---------|
| `color` | integer | Notification color | 65280 (green) |
| `timestamp` | string | ISO 8601 timestamp | "2024-03-15T15:30:00Z" |
| `jellyfin_url` | string | Jellyfin server URL | "https://jellyfin.example.com" |
| `server_url` | string | Same as jellyfin_url | "https://jellyfin.example.com" |
| `action` | string | Notification action | "new_item", "upgraded_item" |
| `changes` | list | List of change objects (upgrades only) | See Changes Structure below |
| `thumbnail_url` | string | Thumbnail image URL | "https://..." |
| `tvdb_attribution_needed` | boolean | Show TVDb attribution | true/false |
| `image_quality` | integer | Image quality setting | 90 |
| `image_max_width` | integer | Max image width | 500 |
| `image_max_height` | integer | Max image height | 400 |

### For Grouped Notifications

| Variable | Type | Description |
|----------|------|-------------|
| `items` | list | List of media items |
| `total_items` | integer | Total item count |
| `movies` | list | Movie items only |
| `episodes` | list | TV episode items |
| `audio_items` | list | Music/audio items |
</details>

## 📈 Changes Structure (Upgrade Notifications)

When `action` is "upgraded_item", the `changes` variable contains a list of change objects describing what was upgraded
<details>
<summary>Click to expand complete change object reference tables</summary>

### Change Object Properties

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `type` | string | Type of change | "resolution", "codec", "audio_codec", "audio_channels", "hdr_status", "file_size", "provider_ids" |
| `field` | string | Database field that changed | "video_height", "video_codec", "audio_codec" |
| `old_value` | any | Previous value | 720, "h264", "aac", 2 |
| `new_value` | any | New/current value | 1080, "hevc", "dts", 6 |
| `description` | string | Human-readable description | "Resolution changed from 720p to 1080p" |

### Change Types

| Change Type | Description | Old/New Value Types | Example |
|------------|-------------|-------------------|---------|
| `resolution` | Video resolution upgrade | integer (height in pixels) | 720 → 1080 |
| `codec` | Video codec change | string | "h264" → "hevc" |
| `audio_codec` | Audio codec change | string | "aac" → "dts" |
| `audio_channels` | Audio channel upgrade | integer | 2 → 6 (stereo to 5.1) |
| `hdr_status` | HDR upgrade | string | "SDR" → "HDR10" |
| `file_size` | File replacement | integer (bytes) | File size in bytes |
| `provider_ids` | Metadata update | varies | External ID changes |
</details>

### Using Changes in Templates

```jinja2
{# Check if there are any changes #}
{% if changes and changes | length > 0 %}
  
  {# Loop through all changes #}
  {% for change in changes %}
    {% if change.type == 'resolution' %}
      📐 Resolution: {{ change.old_value }}p → {{ change.new_value }}p
    {% elif change.type == 'codec' %}
      🎞️ Video Codec: {{ change.old_value }} → {{ change.new_value | upper }}
    {% elif change.type == 'audio_codec' %}
      🔊 Audio: {{ change.old_value }} → {{ change.new_value | upper }}
    {% elif change.type == 'audio_channels' %}
      🔊 Channels: {{ change.old_value }}ch → {{ change.new_value }}ch
    {% elif change.type == 'hdr_status' %}
      🌈 HDR: {{ change.old_value }} → {{ change.new_value }}
    {% elif change.type == 'file_size' %}
      💾 File replaced ({{ "%.1f" % (change.new_value / 1073741824) }} GB)
    {% endif %}
  {% endfor %}
  
  {# Show only first 3 changes with count #}
  {% for change in changes[:3] %}
    <!-- Display change -->
  {% endfor %}
  {% if changes | length > 3 %}
    +{{ changes | length - 3 }} more changes
  {% endif %}
  
{% endif %}
```

### Formatted Change Display

```jinja2
{# Compact inline change summary #}
"fields": [
  {% for change in changes[:5] %}
  {
    "name": "{% if change.type == 'resolution' %}📐 Resolution Upgrade{% elif change.type == 'codec' %}🎞️ Video Codec{% elif change.type == 'audio_codec' %}🔊 Audio Upgrade{% elif change.type == 'audio_channels' %}🔊 Channel Upgrade{% elif change.type == 'hdr_status' %}🌈 HDR Upgrade{% else %}🔄 {{ change.type | title }}{% endif %}",
    "value": "{{ change.old_value or 'Unknown' }} → **{{ change.new_value or 'Unknown' }}**",
    "inline": true
  }{% if not loop.last %},{% endif %}
  {% endfor %}
]
```

### Grouped Notification Changes

For grouped notifications, changes are attached to each item:

```jinja2
{% for item_data in upgraded_items %}
  **{{ item_data.item.name }}**
  {% if item_data.changes | length > 0 %}
    Changes: 
    {% for change in item_data.changes[:2] %}
      {% if change.type == 'resolution' %}
        {{ change.old_value }}p→{{ change.new_value }}p
      {% elif change.type == 'codec' %}
        {{ change.old_value }}→{{ change.new_value }}
      {% endif %}
      {% if not loop.last %} • {% endif %}
    {% endfor %}
  {% endif %}
{% endfor %}
```

## 🌐 External Metadata Properties (API Keys Required)

When API keys are configured, additional metadata is fetched and attached to items as nested objects:

<details>
<summary>Click to expand complete external metadata properties reference tables</summary>

### OMDb Metadata (`item.omdb`)

Available when OMDb API key is configured:

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `item.omdb.imdb_id` | string | IMDb identifier | "tt0133093" |
| `item.omdb.title` | string | Movie/show title | "The Matrix" |
| `item.omdb.year` | string | Release year | "1999" |
| `item.omdb.rated` | string | MPAA rating | "R", "PG-13" |
| `item.omdb.released` | string | Release date | "31 Mar 1999" |
| `item.omdb.runtime` | string | Duration | "136 min" |
| `item.omdb.runtime_minutes` | integer | Duration in minutes | 136 |
| `item.omdb.genre` | string | Comma-separated genres | "Action, Sci-Fi" |
| `item.omdb.genres_list` | list | Genres as list | ["Action", "Sci-Fi"] |
| `item.omdb.director` | string | Director name(s) | "Lana Wachowski, Lilly Wachowski" |
| `item.omdb.writer` | string | Writer name(s) | "Lilly Wachowski, Lana Wachowski" |
| `item.omdb.actors` | string | Comma-separated cast | "Keanu Reeves, Laurence Fishburne" |
| `item.omdb.actors_list` | list | Cast as list | ["Keanu Reeves", "Laurence Fishburne"] |
| `item.omdb.plot` | string | Synopsis | "A computer hacker learns..." |
| `item.omdb.language` | string | Languages | "English" |
| `item.omdb.languages_list` | list | Languages as list | ["English"] |
| `item.omdb.country` | string | Countries | "United States, Australia" |
| `item.omdb.countries_list` | list | Countries as list | ["United States", "Australia"] |
| `item.omdb.awards` | string | Awards won | "Won 4 Oscars. 42 wins & 51 nominations" |
| `item.omdb.poster` | string | Poster URL | "https://m.media-amazon.com/..." |
| `item.omdb.metascore` | string | Metacritic score | "73" |
| `item.omdb.imdb_rating` | string | IMDb rating | "8.7" |
| `item.omdb.imdb_votes` | string | IMDb vote count | "1,971,245" |
| `item.omdb.box_office` | string | Box office earnings | "$171,479,930" |
| `item.omdb.production` | string | Production company | "Warner Bros. Pictures" |
| `item.omdb.website` | string | Official website | "http://www.whatisthematrix.com" |
| `item.omdb.total_seasons` | string | Number of seasons (TV) | "5" |
| `item.omdb.ratings` | list | All ratings | See ratings section |
| `item.omdb.ratings_dict` | dict | Ratings by source | `{"imdb": ..., "rotten_tomatoes": ...}` |

### TVDb Metadata (`item.tvdb`)

Available when TVDb API key is configured (TV shows only):

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `item.tvdb.tvdb_id` | integer | TVDb identifier | 81189 |
| `item.tvdb.name` | string | Series name | "Breaking Bad" |
| `item.tvdb.slug` | string | URL slug | "breaking-bad" |
| `item.tvdb.overview` | string | Series synopsis | "Walter White, a struggling..." |
| `item.tvdb.status` | string | Series status | "Ended", "Continuing" |
| `item.tvdb.first_aired` | string | Premiere date | "2008-01-20" |
| `item.tvdb.last_aired` | string | Last episode date | "2013-09-29" |
| `item.tvdb.next_aired` | string | Next episode date | null |
| `item.tvdb.rating` | float | TVDb rating | 9.3 |
| `item.tvdb.rating_count` | integer | Number of ratings | 15234 |
| `item.tvdb.score` | float | TVDb score | 98.5 |
| `item.tvdb.average_runtime` | integer | Average episode runtime | 47 |
| `item.tvdb.genres` | list | Genre names | ["Crime", "Drama", "Thriller"] |
| `item.tvdb.tags` | list | Tag names | ["drug cartel", "cancer", "meth"] |
| `item.tvdb.original_country` | string | Country of origin | "us" |
| `item.tvdb.original_language` | string | Original language | "eng" |
| `item.tvdb.poster_url` | string | Poster image URL | "https://artworks.thetvdb.com/..." |
| `item.tvdb.banner_url` | string | Banner image URL | "https://artworks.thetvdb.com/..." |
| `item.tvdb.fanart_url` | string | Fanart image URL | "https://artworks.thetvdb.com/..." |
| `item.tvdb.year` | string | Year premiered | "2008" |
| `item.tvdb.companies` | list | Production companies | List of company objects |
| `item.tvdb.characters` | list | Character information | List of character objects |
| `item.tvdb.artworks` | list | Available artwork | List of artwork objects |

### TMDb Metadata (`item.tmdb`)

Available when TMDb API key is configured:

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `item.tmdb.tmdb_id` | integer | TMDb identifier | 603 |
| `item.tmdb.imdb_id` | string | IMDb identifier | "tt0133093" |
| `item.tmdb.title` | string | Title/name | "The Matrix" |
| `item.tmdb.original_title` | string | Original language title | "The Matrix" |
| `item.tmdb.tagline` | string | Marketing tagline | "Welcome to the Real World" |
| `item.tmdb.overview` | string | Synopsis | "Set in the 22nd century..." |
| `item.tmdb.status` | string | Release status | "Released" |
| `item.tmdb.release_date` | string | Release date (movies) | "1999-03-30" |
| `item.tmdb.first_air_date` | string | First air date (TV) | "2008-01-20" |
| `item.tmdb.last_air_date` | string | Last air date (TV) | "2013-09-29" |
| `item.tmdb.vote_average` | float | Average rating (0-10) | 8.7 |
| `item.tmdb.vote_count` | integer | Number of votes | 24536 |
| `item.tmdb.popularity` | float | Popularity score | 98.432 |
| `item.tmdb.runtime` | integer | Runtime in minutes | 136 |
| `item.tmdb.budget` | integer | Production budget | 63000000 |
| `item.tmdb.revenue` | integer | Box office revenue | 467222728 |
| `item.tmdb.genres` | list | Genre objects (raw) | [{"id": 28, "name": "Action"}] |
| `item.tmdb.genres_list` | list | Genre names (processed) | ["Action", "Adventure", "Sci-Fi"] |
| `item.tmdb.production_companies` | list | Production companies | [{"name": "Warner Bros."}] |
| `item.tmdb.poster_path` | string | Poster path | "/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg" |
| `item.tmdb.backdrop_path` | string | Backdrop path | "/fNG7i7RqMErkcqhohV2a6cV1Ehy.jpg" |
| `item.tmdb.poster_url` | string | Full poster URL | "https://image.tmdb.org/t/p/w500/..." |
| `item.tmdb.backdrop_url` | string | Full backdrop URL | "https://image.tmdb.org/t/p/original/..." |
| `item.tmdb.number_of_seasons` | integer | Season count (TV) | 5 |
| `item.tmdb.number_of_episodes` | integer | Episode count (TV) | 62 |
| `item.tmdb.in_production` | boolean | Still in production (TV) | false |
| `item.tmdb.networks` | list | TV networks | [{"name": "AMC"}] |
| `item.tmdb.created_by` | list | Show creators (TV) | [{"name": "Vince Gilligan"}] |

### Simplified Ratings Dictionary (`item.ratings`)

A simplified ratings dictionary that aggregates all external API rating sources:

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `item.ratings.imdb` | dict | IMDb rating info | `{"value": "8.7/10", "normalized": 8.7}` |
| `item.ratings.rotten_tomatoes` | dict | RT rating info | `{"value": "88%", "normalized": 8.8}` |
| `item.ratings.metacritic` | dict | Metacritic info | `{"value": "73/100", "normalized": 7.3}` |
| `item.ratings.imdb_score` | string | Direct IMDb score | "8.7" |
| `item.ratings.imdb_votes` | string | IMDb vote count | "1,971,245" |
| `item.ratings.metascore` | string | Metacritic score | "73" |
| `item.ratings.tvdb` | dict | TVDb rating | `{"value": 9.3, "count": 15234}` |
| `item.ratings.tmdb` | dict | TMDb rating | `{"value": "8.7/10", "normalized": 8.7, "count": 24536}` |
</details>

## 📖 Jinja2 Template Basics

### What is Jinja2?

Jinja2 is a templating engine that allows you to create dynamic content by combining templates with data. In Jellynouncer, it generates Discord webhook JSON.

### Core Syntax

#### Variables
Display a variable's value:
```jinja2
{{ item.name }}                    <!-- Output: "The Matrix" -->
{{ item.year }}                    <!-- Output: 1999 -->
```

#### Conditionals
Show content based on conditions:
```jinja2
{% if item.year %}
  Released in {{ item.year }}
{% endif %}

{% if item.video_height >= 2160 %}
  4K Ultra HD
{% elif item.video_height >= 1080 %}
  Full HD
{% else %}
  Standard Definition
{% endif %}
```

#### Loops
Iterate over lists:
```jinja2
{% for genre in item.genres %}
  {{ genre }}{% if not loop.last %}, {% endif %}
{% endfor %}
<!-- Output: Action, Sci-Fi, Thriller -->
```

#### Filters
Transform data using filters:
```jinja2
{{ item.name | upper }}            <!-- THE MATRIX -->
{{ item.name | lower }}            <!-- the matrix -->
{{ item.name | title }}            <!-- The Matrix -->
{{ item.overview[:100] }}          <!-- First 100 characters -->
{{ item.genres | join(", ") }}     <!-- Action, Sci-Fi -->
{{ item.file_size / 1073741824 | round(2) }} GB
```

#### String Formatting
Format numbers and strings using Python-style formatting:
```jinja2
{# Correct syntax for formatting numbers #}
{{ "%.1f" % (item.file_size / 1073741824) }} GB     <!-- 1.5 GB -->
{{ "%.2f" % (item.file_size / 1073741824) }} GB     <!-- 1.50 GB -->
{{ "%02d" % item.season_number }}                   <!-- 01, 02, 03... -->
{{ "%03d" % item.episode_number }}                  <!-- 001, 002, 003... -->

{# Incorrect syntax - DO NOT USE #}
{{ '%.1f' | format(value) }}                        <!-- WRONG - Will cause template errors -->
{{ '%02d' | format(value) }}                        <!-- WRONG - Will cause template errors -->
```

#### Comments
Add notes that won't appear in output:
```jinja2
{# This is a comment and won't be in the JSON output #}
```

### Important: Handling Null/Missing Values

**Always check if a property exists before using it:**

```jinja2
{# WRONG - Will cause error if property is null #}
{{ item.video_height }}p

{# CORRECT - Safe null checking #}
{% if item.video_height %}{{ item.video_height }}p{% endif %}

{# ALTERNATIVE - Using 'is defined' #}
{% if item.video_height is defined and item.video_height %}
  {{ item.video_height }}p
{% endif %}

{# DEFAULT VALUES - Provide fallback #}
{{ item.year or "Unknown Year" }}
{{ item.video_height or 0 }}
```

## 🎯 Basic Template Examples

### Minimal New Item Template

```jinja2
{
  "embeds": [
    {
      "title": "New {{ item.item_type }} Added",
      "description": "**{{ item.name }}**",
      "color": {{ color }}
    }
  ]
}
```

### Basic Movie Template with Safe Checks

```jinja2
{
  "embeds": [
    {
      "title": "🎬 New Movie Added",
      "description": "**{{ item.name }}**{% if item.year %} ({{ item.year }}){% endif %}",
      "color": {{ color }},
      "fields": [
        {% set fields = [] %}
        {% if item.video_height %}
          {% set _ = fields.append(1) %}
        {
          "name": "Quality",
          "value": "{{ item.video_height }}p",
          "inline": true
        }{% if item.runtime_ticks or item.genres %},{% endif %}
        {% endif %}
        {% if item.runtime_ticks %}
          {% set _ = fields.append(1) %}
        {
          "name": "Runtime",
          "value": "{{ (item.runtime_ticks / 600000000) | int }} minutes",
          "inline": true
        }{% if item.genres %},{% endif %}
        {% endif %}
        {% if item.genres and item.genres | length > 0 %}
        {
          "name": "Genres",
          "value": "{{ item.genres[:3] | join(', ') }}",
          "inline": true
        }
        {% endif %}
      ]
    }
  ]
}
```

### TV Episode Template

```jinja2
{
  "embeds": [
    {
      "title": "📺 New Episode",
      "description": "**{{ item.series_name }}**\nS{{ "%02d" % (item.season_number or 0) }}E{{ "%02d" % (item.episode_number or 0) }} - {{ item.name }}",
      "color": {{ color }},
      "fields": [
        {% if item.overview %}
        {
          "name": "Synopsis",
          "value": "{{ (item.overview[:200] + '...') if item.overview | length > 200 else item.overview }}",
          "inline": false
        },
        {% endif %}
        {% if item.video_height %}
        {
          "name": "Quality",
          "value": "{{ item.video_height }}p{% if item.video_range and item.video_range != 'SDR' %} {{ item.video_range }}{% endif %}",
          "inline": true
        },
        {% endif %}
        {% if item.audio_codec %}
        {
          "name": "Audio",
          "value": "{{ item.audio_codec | upper }}{% if item.audio_channels %} {{ item.audio_channels }}.{% if item.audio_channels > 2 %}1{% else %}0{% endif %}{% endif %}",
          "inline": true
        }
        {% endif %}
      ],
      {% if item.series_id %}
      "thumbnail": {
        "url": "{{ jellyfin_url }}/Items/{{ item.series_id }}/Images/Primary?maxHeight=300"
      },
      {% endif %}
      "timestamp": "{{ timestamp }}"
    }
  ]
}
```

### Using Changes in Templates

```jinja2
{# Check if there are any changes #}
{% if changes and changes | length > 0 %}
  
  {# Loop through all changes #}
  {% for change in changes %}
    {% if change.type == 'resolution' %}
      📐 Resolution: {{ change.old_value }}p → {{ change.new_value }}p
    {% elif change.type == 'codec' %}
      🎞️ Video Codec: {{ change.old_value }} → {{ change.new_value | upper }}
    {% elif change.type == 'audio_codec' %}
      🔊 Audio: {{ change.old_value }} → {{ change.new_value | upper }}
    {% elif change.type == 'audio_channels' %}
      🔊 Channels: {{ change.old_value }}ch → {{ change.new_value }}ch
    {% elif change.type == 'hdr_status' %}
      🌈 HDR: {{ change.old_value }} → {{ change.new_value }}
    {% elif change.type == 'file_size' %}
      💾 File replaced ({{ "%.1f" % (change.new_value / 1073741824) }} GB)
    {% endif %}
  {% endfor %}
  
  {# Show only first 3 changes with count #}
  {% for change in changes[:3] %}
    <!-- Display change -->
  {% endfor %}
  {% if changes | length > 3 %}
    +{{ changes | length - 3 }} more changes
  {% endif %}
  
{% endif %}
```

### Formatted Change Display

```jinja2
{# Compact inline change summary #}
"fields": [
  {% for change in changes[:5] %}
  {
    "name": "{% if change.type == 'resolution' %}📐 Resolution Upgrade{% elif change.type == 'codec' %}🎞️ Video Codec{% elif change.type == 'audio_codec' %}🔊 Audio Upgrade{% elif change.type == 'audio_channels' %}🔊 Channel Upgrade{% elif change.type == 'hdr_status' %}🌈 HDR Upgrade{% else %}🔄 {{ change.type | title }}{% endif %}",
    "value": "{{ change.old_value or 'Unknown' }} → **{{ change.new_value or 'Unknown' }}**",
    "inline": true
  }{% if not loop.last %},{% endif %}
  {% endfor %}
]
```

### Grouped Notification Changes

For grouped notifications, changes are attached to each item:

```jinja2
{% for item_data in upgraded_items %}
  **{{ item_data.item.name }}**
  {% if item_data.changes | length > 0 %}
    Changes: 
    {% for change in item_data.changes[:2] %}
      {% if change.type == 'resolution' %}
        {{ change.old_value }}p→{{ change.new_value }}p
      {% elif change.type == 'codec' %}
        {{ change.old_value }}→{{ change.new_value }}
      {% endif %}
      {% if not loop.last %} • {% endif %}
    {% endfor %}
  {% endif %}
{% endfor %}
```

## 🚀 Advanced Template Techniques

### Dynamic Field Generation with Counter

Prevent Discord's 25-field limit:

```jinja2
{
  "embeds": [
    {
      "title": "New {{ item.item_type }}",
      "description": "**{{ item.name }}**",
      "color": {{ color }},
      "fields": [
        {% set field_count = namespace(value=0) %}
        
        {% if item.video_height and field_count.value < 20 %}
          {% if field_count.value > 0 %},{% endif %}
          {% set field_count.value = field_count.value + 1 %}
        {
          "name": "Resolution",
          "value": "{{ item.video_height }}p",
          "inline": true
        }
        {% endif %}
        
        {% if item.video_codec and field_count.value < 20 %}
          {% if field_count.value > 0 %},{% endif %}
          {% set field_count.value = field_count.value + 1 %}
        {
          "name": "Video Codec",
          "value": "{{ item.video_codec | upper }}",
          "inline": true
        }
        {% endif %}
        
        {# Continue for other fields... #}
      ]
    }
  ]
}
```

### Smart Audio Channel Display

```jinja2
{% if item.audio_channels %}
  {% if item.audio_channels == 2 %}
    Stereo
  {% elif item.audio_channels == 6 %}
    5.1 Surround
  {% elif item.audio_channels == 8 %}
    7.1 Surround
  {% else %}
    {{ item.audio_channels }} channels
  {% endif %}
{% endif %}
```

### File Size Formatting

```jinja2
{% if item.file_size %}
  {% if item.file_size < 1073741824 %}
    {{ "%.2f" | format(item.file_size / 1048576) }} MB
  {% elif item.file_size < 1099511627776 %}
    {{ "%.2f" | format(item.file_size / 1073741824) }} GB
  {% else %}
    {{ "%.2f" | format(item.file_size / 1099511627776) }} TB
  {% endif %}
{% endif %}
```

### Runtime Conversion

```jinja2
{% if item.runtime_ticks %}
  {% set total_seconds = (item.runtime_ticks / 10000000) | int %}
  {% set hours = (total_seconds / 3600) | int %}
  {% set minutes = ((total_seconds % 3600) / 60) | int %}
  {% if hours > 0 %}
    {{ hours }}h {{ minutes }}m
  {% else %}
    {{ minutes }} minutes
  {% endif %}
{% endif %}
```

### Quality Badge System

```jinja2
{% if item.video_height %}
  {% if item.video_height >= 2160 %}
    📺 **4K UHD**
  {% elif item.video_height >= 1440 %}
    📺 **QHD**
  {% elif item.video_height >= 1080 %}
    📺 **FHD**
  {% elif item.video_height >= 720 %}
    📺 **HD**
  {% else %}
    📺 **SD**
  {% endif %}
  {% if item.video_range and item.video_range != 'SDR' %}
    • 🌈 **{{ item.video_range }}**
  {% endif %}
{% endif %}
```

### Upgrade Change Detection

For upgrade templates with change tracking:

```jinja2
{% if changes and changes | length > 0 %}
  "fields": [
    {
      "name": "🔄 Upgrades",
      "value": "{% for change in changes[:5] -%}
        {%- if change.type == 'resolution' -%}
          📐 {{ change.old_value or 'Unknown' }}p → **{{ change.new_value }}p**
        {%- elif change.type == 'codec' -%}
          🎞️ {{ change.old_value or 'Unknown' }} → **{{ change.new_value | upper }}**
        {%- elif change.type == 'audio_codec' -%}
          🔊 {{ change.old_value or 'Unknown' }} → **{{ change.new_value | upper }}**
        {%- elif change.type == 'hdr_status' -%}
          🌈 {{ change.old_value or 'SDR' }} → **{{ change.new_value }}**
        {%- endif -%}
        {%- if not loop.last %}
{{ '' }}{%- endif -%}
      {%- endfor %}",
      "inline": false
    }
  ]
{% endif %}
```

## 📊 Using External Metadata in Templates

### Displaying Ratings from Multiple Sources

```jinja2
{% if item.ratings %}
  {# Display IMDb rating if available #}
  {% if item.ratings.imdb_score %}
    ⭐ IMDb: {{ item.ratings.imdb_score }}/10
    {% if item.ratings.imdb_votes %}({{ item.ratings.imdb_votes }} votes){% endif %}
  {% endif %}
  
  {# Display Rotten Tomatoes if available #}
  {% if item.ratings.rotten_tomatoes %}
    🍅 RT: {{ item.ratings.rotten_tomatoes.value }}
  {% endif %}
  
  {# Display Metacritic if available #}
  {% if item.ratings.metascore %}
    📊 Metacritic: {{ item.ratings.metascore }}/100
  {% endif %}
  
  {# Display TVDb rating for TV shows #}
  {% if item.ratings.tvdb %}
    📺 TVDb: {{ item.ratings.tvdb.value }}/10 ({{ item.ratings.tvdb.count }} ratings)
  {% endif %}
{% endif %}
```

### Using TMDb Metadata

```jinja2
{% if item.tmdb %}
  {# Use genres_list for processed genre names #}
  {% if item.tmdb.genres_list %}
    Genres: {{ item.tmdb.genres_list | join(", ") }}
    <!-- Output: "Action, Adventure, Science Fiction" -->
  {% endif %}
  
  {# DO NOT use item.tmdb.genres | map(attribute='name') #}
  {# item.tmdb.genres contains raw objects, use genres_list instead #}
  
  {# Display vote average and count #}
  {% if item.tmdb.vote_average %}
    Rating: {{ item.tmdb.vote_average }}/10 ({{ item.tmdb.vote_count }} votes)
  {% endif %}
{% endif %}
```

### Using OMDb Metadata

```jinja2
{% if item.omdb %}
  "fields": [
    {% if item.omdb.imdb_rating %}
    {
      "name": "⭐ Ratings",
      "value": "**IMDb:** {{ item.omdb.imdb_rating }}/10{% if item.omdb.metascore %}\n**Metacritic:** {{ item.omdb.metascore }}/100{% endif %}{% if item.omdb.ratings_dict.rotten_tomatoes %}\n**Rotten Tomatoes:** {{ item.omdb.ratings_dict.rotten_tomatoes.value }}{% endif %}",
      "inline": true
    },
    {% endif %}
    {% if item.omdb.awards %}
    {
      "name": "🏆 Awards",
      "value": "{{ item.omdb.awards }}",
      "inline": false
    },
    {% endif %}
    {% if item.omdb.box_office %}
    {
      "name": "💰 Box Office",
      "value": "{{ item.omdb.box_office }}",
      "inline": true
    }
    {% endif %}
  ]
{% endif %}
```

### Using TVDb Metadata

```jinja2
{% if item.tvdb %}
  {# Series information with TVDb data #}
  "description": "**{{ item.tvdb.name or item.name }}**\n{{ item.tvdb.overview or item.overview }}",
  "fields": [
    {% if item.tvdb.status %}
    {
      "name": "📺 Status",
      "value": "{{ item.tvdb.status }}",
      "inline": true
    },
    {% endif %}
    {% if item.tvdb.genres %}
    {
      "name": "🎭 Genres",
      "value": "{{ item.tvdb.genres[:5] | join(', ') }}",
      "inline": true
    },
    {% endif %}
    {% if item.tvdb.rating %}
    {
      "name": "⭐ TVDb Rating",
      "value": "{{ item.tvdb.rating }}/10 ({{ item.tvdb.rating_count }} votes)",
      "inline": true
    }
    {% endif %}
  ],
  {% if item.tvdb.poster_url %}
  "thumbnail": {
    "url": "{{ item.tvdb.poster_url }}"
  },
  {% endif %}
  {% if tvdb_attribution_needed %}
  "footer": {
    "text": "Metadata provided by TheTVDB",
    "icon_url": "{{ jellyfin_url }}/web/favicon.ico"
  }
  {% endif %}
{% endif %}
```

### Using TMDb Metadata

```jinja2
{% if item.tmdb %}
  "fields": [
    {% if item.tmdb.vote_average %}
    {
      "name": "⭐ TMDb Rating",
      "value": "{{ item.tmdb.vote_average }}/10 ({{ item.tmdb.vote_count }} votes)",
      "inline": true
    },
    {% endif %}
    {% if item.tmdb.budget and item.tmdb.revenue %}
    {
      "name": "💰 Financial",
      "value": "**Budget:** ${{ '{:,}'.format(item.tmdb.budget) }}\n**Revenue:** ${{ '{:,}'.format(item.tmdb.revenue) }}",
      "inline": false
    },
    {% endif %}
    {% if item.tmdb.tagline %}
    {
      "name": "📝 Tagline",
      "value": "*{{ item.tmdb.tagline }}*",
      "inline": false
    }
    {% endif %}
  ],
  {% if item.tmdb.backdrop_url %}
  "image": {
    "url": "{{ item.tmdb.backdrop_url }}"
  }
  {% endif %}
{% endif %}
```

### Complete Example with All Metadata Sources

```jinja2
{
  "embeds": [
    {
      "title": "🎬 {{ item.name }}{% if item.year %} ({{ item.year }}){% endif %}",
      
      {# Use best available synopsis #}
      "description": "{{ item.tmdb.overview or item.omdb.plot or item.overview or 'No description available' }}",
      
      "color": {{ color }},
      
      "fields": [
        {# Aggregated ratings field #}
        {% if item.ratings and (item.ratings.imdb_score or item.ratings.metascore or item.ratings.rotten_tomatoes) %}
        {
          "name": "⭐ Ratings",
          "value": "{% if item.ratings.imdb_score %}**IMDb:** {{ item.ratings.imdb_score }}/10{% endif %}{% if item.ratings.rotten_tomatoes %}{% if item.ratings.imdb_score %}\n{% endif %}**RT:** {{ item.ratings.rotten_tomatoes.value }}{% endif %}{% if item.ratings.metascore %}{% if item.ratings.imdb_score or item.ratings.rotten_tomatoes %}\n{% endif %}**Metacritic:** {{ item.ratings.metascore }}/100{% endif %}",
          "inline": true
        },
        {% endif %}
        
        {# Cast from OMDb #}
        {% if item.omdb and item.omdb.actors_list %}
        {
          "name": "🎭 Cast",
          "value": "{{ item.omdb.actors_list[:3] | join(', ') }}",
          "inline": true
        },
        {% endif %}
        
        {# Runtime with fallback #}
        {% if item.omdb.runtime_minutes or item.tmdb.runtime or item.runtime_ticks %}
        {
          "name": "⏱️ Runtime",
          "value": "{% if item.omdb.runtime_minutes %}{{ item.omdb.runtime_minutes }} min{% elif item.tmdb.runtime %}{{ item.tmdb.runtime }} min{% elif item.runtime_ticks %}{{ (item.runtime_ticks / 600000000) | int }} min{% endif %}",
          "inline": true
        },
        {% endif %}
        
        {# Technical specs #}
        {% if item.video_height %}
        {
          "name": "📐 Quality",
          "value": "{{ item.video_height }}p{% if item.video_range and item.video_range != 'SDR' %} {{ item.video_range }}{% endif %}",
          "inline": true
        },
        {% endif %}
        
        {# Awards if available #}
        {% if item.omdb and item.omdb.awards and item.omdb.awards != 'N/A' %}
        {
          "name": "🏆 Awards",
          "value": "{{ item.omdb.awards }}",
          "inline": false
        }
        {% endif %}
      ],
      
      {# Use best available image #}
      {% if item.tmdb and item.tmdb.poster_url %}
      "thumbnail": {
        "url": "{{ item.tmdb.poster_url }}"
      },
      {% elif item.tvdb and item.tvdb.poster_url %}
      "thumbnail": {
        "url": "{{ item.tvdb.poster_url }}"
      },
      {% elif item.omdb and item.omdb.poster %}
      "thumbnail": {
        "url": "{{ item.omdb.poster }}"
      },
      {% else %}
      "thumbnail": {
        "url": "{{ jellyfin_url }}/Items/{{ item.item_id }}/Images/Primary?maxHeight=300"
      },
      {% endif %}
      
      {# Footer with attributions #}
      "footer": {
        "text": "{{ item.library_name or 'Jellyfin' }}{% if tvdb_attribution_needed %} • Metadata from TheTVDB{% endif %}",
        "icon_url": "{{ jellyfin_url }}/web/favicon.ico"
      },
      
      "timestamp": "{{ timestamp }}"
    }
  ]
}
```

## 🌟 Complete Real-World Example

Here's a production-ready template with all best practices:

```jinja2
{# 
  Production-Ready New Item Template
  Handles all media types with proper null checking
#}
{
  "embeds": [
    {
      {# Dynamic title based on media type #}
      "title": "{% if item.item_type == 'Movie' %}🎬 New Movie{% elif item.item_type == 'Episode' %}📺 New Episode{% elif item.item_type == 'Audio' %}🎵 New Music{% else %}📁 New {{ item.item_type }}{% endif %}",
      
      {# Rich description with safe property access #}
      "description": "{% if item.item_type == 'Episode' and item.series_name -%}
        **{{ item.series_name }}**
        S{{ "%02d" % (item.season_number or 0) }}E{{ "%02d" % (item.episode_number or 0) }} - {{ item.name }}
      {%- else -%}
        **{{ item.name }}**{% if item.year %} ({{ item.year }}){% endif %}
      {%- endif -%}
      {%- if item.tagline %}
*{{ item.tagline }}*{% endif -%}
      {%- if item.overview %}

{{ (item.overview[:300] + '...') if item.overview | length > 300 else item.overview }}{% endif %}",
      
      "color": {{ color }},
      
      {# Smart field generation with limit checking #}
      "fields": [
        {% set fields_added = namespace(count=0) %}
        
        {# Technical specifications row #}
        {% if item.video_height and item.item_type not in ['Audio', 'MusicAlbum'] and fields_added.count < 20 %}
          {% if fields_added.count > 0 %},{% endif %}
          {% set fields_added.count = fields_added.count + 1 %}
        {
          "name": "📐 Quality",
          "value": "{{ item.video_height }}p{% if item.video_range and item.video_range != 'SDR' %} {{ item.video_range }}{% endif %}",
          "inline": true
        }
        {% endif %}
        
        {% if item.video_codec and item.item_type not in ['Audio', 'MusicAlbum'] and fields_added.count < 20 %}
          {% if fields_added.count > 0 %},{% endif %}
          {% set fields_added.count = fields_added.count + 1 %}
        {
          "name": "🎞️ Video",
          "value": "{{ item.video_codec | upper }}{% if item.video_profile %} {{ item.video_profile }}{% endif %}",
          "inline": true
        }
        {% endif %}
        
        {% if item.audio_codec and fields_added.count < 20 %}
          {% if fields_added.count > 0 %},{% endif %}
          {% set fields_added.count = fields_added.count + 1 %}
        {
          "name": "🔊 Audio",
          "value": "{{ item.audio_codec | upper }}{% if item.audio_channels %} {% if item.audio_channels == 2 %}Stereo{% elif item.audio_channels == 6 %}5.1{% elif item.audio_channels == 8 %}7.1{% else %}{{ item.audio_channels }}ch{% endif %}{% endif %}",
          "inline": true
        }
        {% endif %}
        
        {# Metadata row #}
        {% if item.runtime_ticks and fields_added.count < 20 %}
          {% if fields_added.count > 0 %},{% endif %}
          {% set fields_added.count = fields_added.count + 1 %}
        {
          "name": "⏱️ Runtime",
          "value": "{% set minutes = (item.runtime_ticks / 600000000) | int %}{% set hours = (minutes / 60) | int %}{% set mins = minutes % 60 %}{% if hours > 0 %}{{ hours }}h {{ mins }}m{% else %}{{ mins }} min{% endif %}",
          "inline": true
        }
        {% endif %}
        
        {% if item.genres and item.genres | length > 0 and fields_added.count < 20 %}
          {% if fields_added.count > 0 %},{% endif %}
          {% set fields_added.count = fields_added.count + 1 %}
        {
          "name": "🎭 Genres",
          "value": "{{ item.genres[:3] | join(', ') }}{% if item.genres | length > 3 %} +{{ item.genres | length - 3 }}{% endif %}",
          "inline": true
        }
        {% endif %}
        
        {% if item.file_size and fields_added.count < 20 %}
          {% if fields_added.count > 0 %},{% endif %}
          {% set fields_added.count = fields_added.count + 1 %}
        {
          "name": "💾 Size",
          "value": "{{ \"%.1f\" % (item.file_size / 1073741824) }} GB",
          "inline": true
        }
        {% endif %}
      ],
      
      {# Thumbnail with fallback #}
      {% if item.item_type == 'Episode' and item.series_id %}
      "thumbnail": {
        "url": "{{ jellyfin_url }}/Items/{{ item.series_id }}/Images/Primary?maxHeight=300&quality=90"
      },
      {% elif item.item_id %}
      "thumbnail": {
        "url": "{{ jellyfin_url }}/Items/{{ item.item_id }}/Images/Primary?maxHeight=300&quality=90"
      },
      {% endif %}
      
      {# Footer with attribution #}
      "footer": {
        "text": "{{ item.library_name or 'Jellyfin' }}{% if item.server_name %} • {{ item.server_name }}{% endif %}{% if tvdb_attribution_needed %}
Metadata from TheTVDB{% endif %}",
        "icon_url": "{{ jellyfin_url }}/web/favicon.ico"
      },
      
      {# Clickable link to item #}
      {% if item.item_id %}
      "url": "{{ jellyfin_url }}/web/index.html#!/details?id={{ item.item_id }}",
      {% endif %}
      
      "timestamp": "{{ timestamp }}"
    }
  ]
}
```

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

#### Template Not Loading
- **Check**: File exists at configured path
- **Check**: File has `.j2` extension
- **Check**: Path in `config.json` is correct
- **Solution**: Verify `/app/templates/` directory exists and is readable

#### JSON Syntax Errors
- **Check**: All `{% %}` and `{{ }}` tags are properly closed
- **Check**: Commas between fields (but not after the last one)
- **Check**: Quotes around string values
- **Solution**: Use a JSON validator to check output

#### Missing Data in Notifications
- **Check**: Property exists with `{% if item.property %}`
- **Check**: Property name is spelled correctly
- **Solution**: Always use conditional checks for optional properties

#### Discord Webhook Errors
- **Check**: Total embed size < 6000 characters
- **Check**: Field count < 25
- **Check**: Field values < 1024 characters
- **Solution**: Add length limits and field counters

#### Character Encoding Issues
- **Check**: Special characters in text
- **Solution**: Use `| e` filter for escaping: `{{ item.name | e }}`

### Debug Mode

Enable debug logging to troubleshoot template issues:

```json
{
  "server": {
    "log_level": "DEBUG"
  }
}
```

⚠️ **Warning**: Debug mode generates extensive logs. Only enable when troubleshooting, as it can quickly fill disk space and overwrite older logs.

## 📝 Configuration

Update your `config.json` to use custom templates:

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

## 🎯 Best Practices

1. **Always Check for Null Values**: Use `{% if item.property %}` before accessing
2. **Limit Text Length**: Truncate long text to avoid Discord limits
3. **Count Fields**: Track field count to stay under 25-field limit
4. **Use Meaningful Icons**: Emojis help users quickly identify content types
5. **Format Numbers**: Use filters for readable file sizes and durations
6. **Provide Fallbacks**: Use default values when properties are missing
7. **Test Templates**: Validate JSON output before deploying
8. **Comment Complex Logic**: Help future maintainers understand your templates
9. **Handle All Media Types**: Account for movies, TV, music, photos
10. **Respect Discord Limits**: Stay within character and field limits

## 📚 Additional Resources

- [Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Discord Webhook Guide](https://discord.com/developers/docs/resources/webhook)
- [Discord Embed Limits](https://discord.com/developers/docs/resources/channel#embed-limits)
- [JSON Validator](https://jsonlint.com/)

---

*For more examples and advanced techniques, check the `/app/templates/` directory for the included template files.*
