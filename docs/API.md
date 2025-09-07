# 🔌 Jellynouncer API Documentation

<div align="center">

![API Version](https://img.shields.io/badge/API_Version-2.0-blue)
![REST](https://img.shields.io/badge/Type-REST-green)
![WebSocket](https://img.shields.io/badge/WebSocket-Supported-orange)
![JWT Auth](https://img.shields.io/badge/Auth-JWT-red)

**Complete API documentation for Jellynouncer webhook and web services**

[Quick Start](#-quick-start) • [Authentication](#-authentication) • [Webhook API](#-webhook-api) • [Web API](#-web-api) • [WebSocket](#-websocket-api) • [Integration](#-integration-guides)

</div>

---

## 📚 Table of Contents

- [🚀 Quick Start](#-quick-start)
- [🔐 Authentication](#-authentication)
  - [JWT Authentication](#jwt-authentication)
  - [Webhook Authentication](#webhook-authentication)
  - [Configuring Jellyfin Plugin](#configuring-jellyfin-plugin)
- [🔒 SSL/TLS Security](#-ssltls-security)
- [📡 Webhook API (Port 1984)](#-webhook-api-port-1984)
- [🌐 Web API (Port 1985)](#-web-api-port-1985)
- [🔄 WebSocket API](#-websocket-api)
- [📊 Response Formats](#-response-formats)
- [🔧 Integration Guides](#-integration-guides)
- [📝 Examples](#-examples)
- [⚠️ Error Handling](#️-error-handling)
- [📈 Rate Limiting](#-rate-limiting)

---

## 🚀 Quick Start

### Base URLs

```
Webhook Service: http://localhost:1984
Web Interface:   http://localhost:1985
HTTPS (if SSL):  https://localhost:9000
```

### Basic Request Example

```bash
# Test webhook endpoint (no auth)
curl -X POST "http://localhost:1984/test-webhook?webhook_name=default"

# Get health status
curl http://localhost:1984/health

# Web API with JWT token
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
     http://localhost:1985/api/overview
```

---

## 🔐 Authentication

### JWT Authentication

The web interface and optionally the webhook endpoint use JWT (JSON Web Tokens) for authentication.

#### Token Types

| Type | Expiration | Purpose | Usage |
|------|------------|---------|-------|
| **Access Token** | 30 minutes | API requests | Bearer token in Authorization header |
| **Refresh Token** | 7 days | Get new access tokens | Used at `/api/auth/refresh` endpoint |

#### Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Database
    
    Client->>API: POST /api/auth/login
    API->>Database: Verify credentials
    Database-->>API: User valid
    API-->>Client: Access + Refresh tokens
    
    Note over Client,API: Subsequent requests
    Client->>API: GET /api/config [Bearer token]
    API-->>Client: Protected resource
    
    Note over Client,API: Token expired (30 min)
    Client->>API: POST /api/auth/refresh
    API-->>Client: New access token
```

#### Login Request

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "user_id": 1,
    "username": "admin",
    "email": "admin@example.com"
  }
}
```

#### Using Tokens

```http
GET /api/config
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

#### Refresh Token

```http
POST /api/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Webhook Authentication

The webhook endpoint (`/webhook`) can optionally require authentication for enhanced security.

#### Enabling Webhook Authentication

1. **Via Web Interface:**
   - Navigate to Settings → Security
   - Enable "Require Webhook Authentication"
   - Copy the displayed Bearer token

2. **Via API:**
   ```http
   PUT /api/auth/settings
   Authorization: Bearer YOUR_ADMIN_TOKEN
   Content-Type: application/json
   
   {
     "require_webhook_auth": true
   }
   ```

#### Authentication Methods

The webhook endpoint accepts multiple authentication methods:

1. **API Keys** (Recommended)
   - Format: `Authorization: ApiKey wh_xxxxx...`
   - Never expire - perfect for service-to-service communication
   - Can be revoked without affecting other systems
   - Usage statistics tracked automatically

2. **JWT Tokens**
   - Format: `Authorization: Bearer eyJxxxxx...`
   - Access Tokens (30-minute expiry)
   - Refresh Tokens (7-day expiry) - Better for Jellyfin
   - Compatible with web interface authentication

#### Authentication Flow

```python
# Webhook authentication priority
1. Check if webhook auth is enabled in settings
2. Check Authorization header:
   a. If starts with "ApiKey" → Validate API key
   b. If starts with "Bearer" → Validate JWT token
3. Track usage statistics for API keys
4. Log successful authentication with method used
```

### Configuring Jellyfin Plugin

To configure the Jellyfin webhook plugin to authenticate with Jellynouncer:

#### Step 1: Install Webhook Plugin

1. In Jellyfin Dashboard → Plugins → Catalog
2. Search for "Webhook" 
3. Install the official Jellyfin Webhook plugin

#### Step 2: Configure Authentication Headers

1. Navigate to Dashboard → Plugins → Webhook → Settings
2. Add a new webhook destination:
   - **Webhook URL:** `http://your-jellynouncer:1984/webhook`
   - **Webhook Name:** `Jellynouncer`

3. Add custom request headers:
   
   **Recommended - API Key Authentication:**
   | Header Key | Header Value |
   |------------|--------------|
   | `Authorization` | `ApiKey YOUR_API_KEY_HERE` |
   | `Content-Type` | `application/json` |
   
   **Alternative - JWT Authentication:**
   | Header Key | Header Value |
   |------------|--------------|
   | `Authorization` | `Bearer YOUR_JWT_TOKEN_HERE` |
   | `Content-Type` | `application/json` |

4. **Important:** 
   - **API Keys** are recommended - they never expire and are purpose-built for webhooks
   - If using JWT, use a **refresh token** (7-day expiry) rather than an access token (30-minute expiry)

#### Step 3: Select Notification Types

Enable the events you want to notify on:
- ✅ Item Added
- ✅ Item Updated  
- ✅ Item Deleted
- ✅ Library Scan Started/Completed
- ✅ User actions (optional)

#### Step 4: Template Configuration (Optional)

The Jellyfin webhook plugin supports Handlebars templates. For Jellynouncer, use the default template or minimal JSON:

```json
{
  "Event": "{{EventType}}",
  "Item": {{Item}},
  "User": {{User}},
  "Server": {{Server}}
}
```

#### Getting Authentication Credentials

**Option 1: Generate API Key (Recommended)**
1. Login to Jellynouncer web interface
2. Navigate to Configuration → Web Interface
3. Enable "Require Webhook Authentication"
4. Click "Generate New API Key"
5. Save the key securely - it won't be shown again
6. Use in Jellyfin: `Authorization: ApiKey wh_xxxxx...`

**Option 2: Via API**
```bash
# Generate API Key
curl -X POST http://localhost:1985/api/webhook-keys \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Jellyfin Server","description":"Main Jellyfin webhook"}'

# Response includes the API key (only shown once)
{
  "success": true,
  "key": "wh_KL3mx9Aa7Bc4Def5Ghi6Jkl8Mno9Pqr2Stu3Vwx",
  "id": 1,
  "name": "Jellyfin Server"
}
```

**Option 3: Use JWT Token**
```bash
# Login to get tokens
curl -X POST http://localhost:1985/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# Use the refresh_token (longer expiry) for Jellyfin
```

---

## 🔒 SSL/TLS Security

Both services support SSL/TLS for secure communication.

### SSL Configuration

```json
{
  "ssl": {
    "enabled": true,
    "cert_type": "pem",  // or "pfx"
    "cert_path": "/app/certs/cert.pem",
    "key_path": "/app/certs/key.pem",
    "port": 9000,
    "force_https": true,
    "hsts_enabled": true
  }
}
```

### Certificate Formats

#### PEM Format
```bash
# Separate certificate and key files
cert_path: /app/certs/cert.pem
key_path: /app/certs/key.pem
chain_path: /app/certs/chain.pem  # Optional
```

#### PFX/PKCS12 Format
```bash
# Combined certificate bundle
cert_path: /app/certs/certificate.pfx
pfx_password: "certificate_password"  # Optional
```

### HTTPS Endpoints

When SSL is enabled:
- Webhook: `https://localhost:9000/webhook`
- Web API: `https://localhost:9000/api/*`

### Security Headers

With SSL enabled, the following headers are set:
- `Strict-Transport-Security`: HSTS header if enabled
- `X-Content-Type-Options`: nosniff
- `X-Frame-Options`: DENY
- `X-XSS-Protection`: 1; mode=block

---

## 📡 Webhook API (Port 1984)

The webhook service receives notifications from Jellyfin and processes them.

### Core Endpoints

#### POST /webhook
**Purpose:** Receive webhook notifications from Jellyfin

**Authentication:** Optional (configurable)

**Headers:**
```http
Authorization: Bearer YOUR_TOKEN  # If auth enabled
Content-Type: application/json
```

**Request Body:**
```json
{
  "Event": "ItemAdded",
  "Item": {
    "Id": "abc123",
    "Name": "Movie Title",
    "Type": "Movie",
    "Path": "/media/movies/movie.mkv",
    "Overview": "Movie description...",
    "ProductionYear": 2024,
    // ... extensive item metadata
  },
  "User": {
    "Id": "user123",
    "Name": "username"
  },
  "Server": {
    "Id": "server123",
    "Name": "Jellyfin Server"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Webhook processed",
  "item_id": "abc123",
  "action": "notification_sent"
}
```

#### GET /health
**Purpose:** Service health check

**Response:**
```json
{
  "status": "healthy",
  "service": "Jellynouncer Webhook Service",
  "version": "2.0.0",
  "uptime_seconds": 3600,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### GET /stats
**Purpose:** Service statistics

**Response:**
```json
{
  "webhooks_received": 150,
  "notifications_sent": 145,
  "notifications_failed": 5,
  "items_tracked": 5000,
  "discord_queue": 0,
  "database_size_mb": 42.5,
  "uptime_seconds": 86400
}
```

#### POST /test-webhook
**Purpose:** Send test notification

**Query Parameters:**
- `webhook_name`: Which webhook to test (default, movies, tv, music)

**Response:**
```json
{
  "status": "success",
  "webhook": "movies",
  "message": "Test notification sent"
}
```

#### POST /sync
**Purpose:** Trigger manual library sync

**Authentication:** Required if enabled

**Query Parameters:**
- `library_id`: Optional specific library to sync

**Response:**
```json
{
  "status": "started",
  "total_items": 5000,
  "sync_id": "sync_123",
  "estimated_time_seconds": 300
}
```

#### GET /sync/status
**Purpose:** Get sync operation status

**Response:**
```json
{
  "active_sync": true,
  "sync_id": "sync_123",
  "progress": 2500,
  "total": 5000,
  "percent_complete": 50,
  "items_processed": {
    "new": 10,
    "updated": 5,
    "deleted": 2
  }
}
```

#### GET /validate-templates
**Purpose:** Validate Jinja2 templates

**Response:**
```json
{
  "valid": true,
  "templates": {
    "new_item.j2": "valid",
    "upgraded_item.j2": "valid",
    "deleted_item.j2": "valid"
  },
  "errors": []
}
```

---

## 🌐 Web API (Port 1985)

The web interface API provides configuration management and monitoring.

### Authentication Endpoints

#### POST /api/auth/login
**Purpose:** User login

**Request:**
```json
{
  "username": "admin",
  "password": "password"
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "user_id": 1,
    "username": "admin",
    "email": "admin@example.com"
  }
}
```

#### POST /api/auth/refresh
**Purpose:** Refresh access token

**Request:**
```json
{
  "refresh_token": "eyJ..."
}
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

#### POST /api/auth/logout
**Purpose:** Logout user

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

#### GET /api/auth/status
**Purpose:** Check auth requirements

**Response:**
```json
{
  "auth_enabled": false,
  "require_webhook_auth": false,
  "setup_required": false
}
```

#### POST /api/auth/setup
**Purpose:** Initial admin setup

**Request:**
```json
{
  "username": "admin",
  "password": "secure_password",
  "email": "admin@example.com"
}
```

#### PUT /api/auth/settings
**Purpose:** Update auth settings

**Authentication:** Required

**Request:**
```json
{
  "auth_enabled": true,
  "require_webhook_auth": true
}
```

#### PUT /api/auth/password
**Purpose:** Change user password

**Authentication:** Required

**Request:**
```json
{
  "current_password": "old_password",
  "new_password": "new_secure_password"
}
```

### Webhook API Key Management

#### GET /api/webhook-keys
**Purpose:** List all webhook API keys

**Authentication:** Required if enabled

**Response:**
```json
{
  "keys": [
    {
      "id": 1,
      "name": "Jellyfin Server",
      "description": "Main Jellyfin webhook",
      "created_at": "2024-01-01T12:00:00Z",
      "last_used": "2024-01-15T14:30:00Z",
      "usage_count": 150,
      "last_ip": "192.168.1.100"
    }
  ]
}
```

#### POST /api/webhook-keys
**Purpose:** Generate new API key

**Authentication:** Required if enabled

**Request:**
```json
{
  "name": "Jellyfin Server",
  "description": "Main Jellyfin instance webhook"
}
```

**Response:**
```json
{
  "success": true,
  "key": "wh_KL3mx9Aa7Bc4Def5Ghi6Jkl8Mno9Pqr2Stu3Vwx",
  "id": 1,
  "name": "Jellyfin Server",
  "message": "API key created successfully. Save this key securely - it cannot be viewed again."
}
```

**Important:** The actual API key is only returned once during creation. Store it securely.

#### DELETE /api/webhook-keys/{key_id}
**Purpose:** Revoke an API key

**Authentication:** Required if enabled

**Response:**
```json
{
  "success": true,
  "message": "API key revoked successfully"
}
```

### Configuration Endpoints

#### GET /api/config
**Purpose:** Get current configuration

**Authentication:** Optional

**Response:**
```json
{
  "jellyfin": {
    "server_url": "http://jellyfin:8096",
    "api_key": "**HIDDEN**",
    // ...
  },
  "discord": {
    "webhooks": {
      // ...
    }
  },
  // ... full config
}
```

#### PUT /api/config
**Purpose:** Update single config value

**Authentication:** Required if enabled

**Request:**
```json
{
  "section": "jellyfin",
  "key": "server_url",
  "value": "http://new-server:8096"
}
```

#### PUT /api/config/full
**Purpose:** Update entire configuration

**Authentication:** Required if enabled

**Request:**
```json
{
  "jellyfin": { /* ... */ },
  "discord": { /* ... */ },
  // ... complete config
}
```

### Overview & Statistics

#### GET /api/overview
**Purpose:** Dashboard statistics

**Response:**
```json
{
  "service_status": {
    "webhook_service": "running",
    "web_service": "running",
    "uptime": 86400
  },
  "jellyfin_stats": {
    "server_name": "My Jellyfin",
    "version": "10.8.0",
    "total_items": 5000,
    "libraries": [
      {
        "name": "Movies",
        "item_count": 1500
      }
    ]
  },
  "discord_stats": {
    "webhooks_configured": 4,
    "webhooks_enabled": 3,
    "notifications_sent_today": 25
  },
  "database_stats": {
    "total_items": 5000,
    "database_size_mb": 42.5,
    "last_sync": "2024-01-01T12:00:00Z"
  }
}
```

#### GET /api/health
**Purpose:** Health check

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "service": "Jellynouncer Web Interface"
}
```

### Template Management

#### GET /api/templates
**Purpose:** List available templates

**Response:**
```json
{
  "templates": [
    {
      "name": "new_item.j2",
      "path": "/app/templates/new_item.j2",
      "size": 2048,
      "modified": "2024-01-01T12:00:00Z"
    }
  ]
}
```

#### GET /api/templates/{template_name}
**Purpose:** Get template content

**Response:**
```json
{
  "name": "new_item.j2",
  "content": "{{ template_content }}",
  "syntax": "jinja2"
}
```

#### PUT /api/templates/{template_name}
**Purpose:** Update template

**Authentication:** Required

**Request:**
```json
{
  "content": "{{ updated_template }}"
}
```

#### POST /api/templates/{template_name}/restore
**Purpose:** Restore default template

**Authentication:** Required

### Log Management

#### GET /api/logs
**Purpose:** Retrieve logs

**Query Parameters:**
- `service`: webhook or web
- `lines`: Number of lines (max 1000)
- `level`: Filter by level (DEBUG, INFO, WARNING, ERROR)
- `search`: Search text

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "level": "INFO",
      "component": "webhook",
      "message": "Webhook received"
    }
  ]
}
```

#### POST /api/logs/client
**Purpose:** Send client-side logs

**Request:**
```json
{
  "logs": [
    {
      "timestamp": "2024-01-01T12:00:00Z",
      "level": "error",
      "message": "Client error",
      "url": "/config",
      "metadata": {}
    }
  ],
  "sessionId": "session_123",
  "userAgent": "Mozilla/5.0..."
}
```

### Testing Endpoints

#### POST /api/test/jellyfin
**Purpose:** Test Jellyfin connection

**Request:**
```json
{
  "server_url": "http://jellyfin:8096",
  "api_key": "test_key",
  "user_id": "test_user"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Connection successful",
  "server_name": "My Jellyfin",
  "version": "10.8.0"
}
```

#### POST /api/test/discord/{webhook_name}
**Purpose:** Test Discord webhook

**Request:**
```json
{
  "url": "https://discord.com/api/webhooks/..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Test message sent"
}
```

---

## 🔄 WebSocket API

Real-time updates via WebSocket connection.

### Connection

```javascript
const ws = new WebSocket('ws://localhost:1985/ws');

ws.onopen = () => {
  // Authenticate
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'Bearer eyJ...'
  }));
};
```

### Message Types

#### Server → Client

```json
// Webhook received
{
  "type": "webhook_received",
  "data": {
    "item_id": "abc123",
    "item_name": "Movie Title",
    "event": "ItemAdded"
  }
}

// Notification sent
{
  "type": "notification_sent",
  "data": {
    "webhook": "movies",
    "items_count": 1
  }
}

// Sync progress
{
  "type": "sync_progress",
  "data": {
    "progress": 50,
    "total": 100,
    "current_item": "Movie Title"
  }
}

// Config updated
{
  "type": "config_updated",
  "data": {
    "section": "discord",
    "key": "webhooks"
  }
}
```

#### Client → Server

```json
// Subscribe to events
{
  "type": "subscribe",
  "events": ["webhook_received", "notification_sent"]
}

// Request sync
{
  "type": "request_sync",
  "library_id": "optional_library_id"
}

// Ping/keepalive
{
  "type": "ping"
}
```

---

## 📊 Response Formats

### Success Response

```json
{
  "status": "success",
  "data": { /* Response data */ },
  "message": "Operation completed"
}
```

### Error Response

```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      {
        "field": "server_url",
        "message": "Must be a valid URL"
      }
    ]
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Pagination

```json
{
  "data": [ /* Items */ ],
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 500,
    "total_pages": 10
  }
}
```

---

## 🔧 Integration Guides

### Python Client Example

```python
import requests
import json

class JellynouncerClient:
    def __init__(self, base_url="http://localhost:1985", username=None, password=None):
        self.base_url = base_url
        self.token = None
        if username and password:
            self.login(username, password)
    
    def login(self, username, password):
        """Authenticate and store token"""
        response = requests.post(
            f"{self.base_url}/api/auth/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            self.token = data["access_token"]
            return True
        return False
    
    def get_config(self):
        """Get current configuration"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        response = requests.get(f"{self.base_url}/api/config", headers=headers)
        return response.json()
    
    def send_test_webhook(self, webhook_name="default"):
        """Send test notification"""
        response = requests.post(
            f"http://localhost:1984/test-webhook",
            params={"webhook_name": webhook_name}
        )
        return response.json()

# Usage
client = JellynouncerClient(username="admin", password="password")
config = client.get_config()
print(config)
```

### JavaScript/Node.js Client

```javascript
class JellynouncerClient {
  constructor(baseUrl = 'http://localhost:1985') {
    this.baseUrl = baseUrl;
    this.token = null;
  }

  async login(username, password) {
    const response = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (response.ok) {
      const data = await response.json();
      this.token = data.access_token;
      return true;
    }
    return false;
  }

  async getConfig() {
    const headers = {};
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    
    const response = await fetch(`${this.baseUrl}/api/config`, { headers });
    return response.json();
  }

  async sendTestWebhook(webhookName = 'default') {
    const response = await fetch(
      `http://localhost:1984/test-webhook?webhook_name=${webhookName}`,
      { method: 'POST' }
    );
    return response.json();
  }
}

// Usage
const client = new JellynouncerClient();
await client.login('admin', 'password');
const config = await client.getConfig();
console.log(config);
```

### cURL Examples

```bash
# Login
TOKEN=$(curl -s -X POST http://localhost:1985/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"password"}' \
  | jq -r '.access_token')

# Get config with auth
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:1985/api/config

# Send webhook (with optional auth)
curl -X POST http://localhost:1984/webhook \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "Event": "ItemAdded",
    "Item": {
      "Id": "123",
      "Name": "Test Movie",
      "Type": "Movie"
    }
  }'

# Test Discord webhook
curl -X POST "http://localhost:1984/test-webhook?webhook_name=movies"

# Get logs
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:1985/api/logs?lines=100&level=ERROR"
```

---

## 📝 Examples

### Complete Webhook Payload

<details>
<summary><b>View Full ItemAdded Webhook Payload</b></summary>

```json
{
  "Event": "ItemAdded",
  "Timestamp": "2024-01-01T12:00:00Z",
  "Server": {
    "Id": "server123",
    "Name": "My Jellyfin Server",
    "Version": "10.8.0"
  },
  "User": {
    "Id": "user123",
    "Name": "admin",
    "IsAdministrator": true
  },
  "Item": {
    "Id": "abc123def456",
    "Name": "The Matrix",
    "OriginalTitle": "The Matrix",
    "ServerId": "server123",
    "Type": "Movie",
    "RunTimeTicks": 136000000000,
    "ProductionYear": 1999,
    "IndexNumber": null,
    "ParentIndexNumber": null,
    "PremiereDate": "1999-03-31T00:00:00Z",
    "CriticRating": 87,
    "CommunityRating": 8.7,
    "Overview": "A computer hacker learns about the true nature of reality...",
    "Taglines": ["Welcome to the Real World"],
    "Genres": ["Action", "Science Fiction"],
    "Studios": [
      {
        "Name": "Warner Bros.",
        "Id": "studio123"
      }
    ],
    "ProviderIds": {
      "Tmdb": "603",
      "Imdb": "tt0133093"
    },
    "Path": "/media/movies/The Matrix (1999)/The Matrix.mkv",
    "OfficialRating": "R",
    "Width": 1920,
    "Height": 1080,
    "Video3DFormat": null,
    "MediaStreams": [
      {
        "Codec": "h264",
        "Language": "eng",
        "Type": "Video",
        "Height": 1080,
        "Width": 1920,
        "BitRate": 10000000,
        "FrameRate": 23.976
      },
      {
        "Codec": "ac3",
        "Language": "eng",
        "Type": "Audio",
        "Channels": 6,
        "SampleRate": 48000,
        "BitRate": 640000
      },
      {
        "Codec": "subrip",
        "Language": "eng",
        "Type": "Subtitle",
        "IsDefault": false,
        "IsForced": false
      }
    ],
    "ImageTags": {
      "Primary": "abc123",
      "Backdrop": "def456",
      "Logo": "ghi789"
    }
  }
}
```

</details>

### Multi-Channel Discord Setup

<details>
<summary><b>View Multi-Channel Configuration Example</b></summary>

```json
{
  "discord": {
    "webhooks": {
      "default": {
        "url": "https://discord.com/api/webhooks/123/default",
        "name": "📢 General",
        "enabled": true
      },
      "movies": {
        "url": "https://discord.com/api/webhooks/123/movies",
        "name": "🎬 Movies",
        "enabled": true,
        "grouping": {
          "mode": "event_type",
          "delay_minutes": 5,
          "max_items": 10
        }
      },
      "tv": {
        "url": "https://discord.com/api/webhooks/123/tv",
        "name": "📺 TV Shows",
        "enabled": true,
        "grouping": {
          "mode": "both",
          "delay_minutes": 3,
          "max_items": 15
        }
      },
      "music": {
        "url": "https://discord.com/api/webhooks/123/music",
        "name": "🎵 Music",
        "enabled": true
      }
    },
    "routing": {
      "enabled": true,
      "movie_types": ["Movie"],
      "tv_types": ["Episode", "Season", "Series"],
      "music_types": ["Audio", "MusicAlbum", "MusicArtist"],
      "fallback_webhook": "default"
    }
  }
}
```

</details>

---

## ⚠️ Error Handling

### HTTP Status Codes

| Code | Meaning | Common Cause |
|------|---------|--------------|
| 200 | Success | Request completed successfully |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid input or malformed request |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Valid auth but insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |
| 503 | Service Unavailable | Service temporarily down |

### Error Response Format

```json
{
  "detail": "Error message",
  "status_code": 400,
  "errors": [
    {
      "field": "server_url",
      "message": "Invalid URL format",
      "type": "validation_error"
    }
  ]
}
```

### Common Errors

#### Authentication Errors
```json
{
  "detail": "Token has expired",
  "status_code": 401,
  "error_code": "TOKEN_EXPIRED"
}
```

#### Validation Errors
```json
{
  "detail": "Validation failed",
  "status_code": 422,
  "errors": [
    {
      "loc": ["body", "server_url"],
      "msg": "invalid or missing URL scheme",
      "type": "value_error.url.scheme"
    }
  ]
}
```

#### Rate Limit Errors
```json
{
  "detail": "Rate limit exceeded",
  "status_code": 429,
  "retry_after": 60
}
```

---

## 📈 Rate Limiting

### Discord Webhook Rate Limits

| Limit Type | Value | Description |
|------------|-------|-------------|
| Requests per period | 5 | Maximum requests in period |
| Period | 2 seconds | Rate limit window |
| Channel limit | 30/minute | Per-channel message limit |
| Queue size | 100 | Maximum queued notifications |

### API Rate Limits

| Endpoint | Limit | Window |
|----------|-------|---------|
| `/api/auth/login` | 5 | 1 minute |
| `/api/auth/refresh` | 10 | 1 minute |
| `/api/config` (PUT) | 10 | 1 minute |
| `/webhook` | 100 | 1 minute |
| Other endpoints | 60 | 1 minute |

### Rate Limit Headers

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704110400
Retry-After: 30
```

### Handling Rate Limits

```python
import time
import requests

def make_request_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue
            
        return response
    
    raise Exception("Max retries exceeded")
```

---

## 🔗 Related Documentation

- [Configuration Guide](../config/README.md)
- [Template Documentation](../templates/README.md)
- [Main README](../README.md)

---

<div align="center">

**Need Help?**

[Open an Issue](https://github.com/jellynouncer/jellynouncer/issues) • [Discord Support](https://discord.gg/jellynouncer)

</div>