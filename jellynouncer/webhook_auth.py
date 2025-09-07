#!/usr/bin/env python3
"""
Enhanced Webhook Authentication Module

Provides multiple authentication methods for webhook endpoints:
- API Key authentication (non-expiring)
- Basic Authentication
- JWT Bearer tokens (existing)
- IP-based trust with service tokens
- Long-lived service tokens

This allows flexible authentication options for different use cases,
particularly for Jellyfin webhook integration.
"""

import os
import base64
import hashlib
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext

from .utils import get_logger

logger = get_logger("webhook_auth")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class WebhookAuthenticator:
    """
    Handles multiple authentication methods for webhook endpoints.
    
    Supports:
    - API Keys (permanent, for services)
    - Basic Authentication
    - JWT Bearer tokens
    - Service tokens with IP validation
    """
    
    def __init__(self, web_db):
        self.web_db = web_db
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
        
    async def authenticate_request(self, request) -> Optional[Dict[str, Any]]:
        """
        Authenticate a webhook request using multiple methods.
        
        Returns:
            Dict with auth info if authenticated, None otherwise
        """
        auth_header = request.headers.get("authorization", "")
        client_ip = request.client.host if request.client else None
        
        # Try each authentication method in order
        
        # 1. API Key Authentication
        if auth_header.startswith("ApiKey "):
            result = await self._validate_api_key(auth_header)
            if result:
                return result
        
        # 2. Basic Authentication
        elif auth_header.startswith("Basic "):
            result = await self._validate_basic_auth(auth_header)
            if result:
                return result
        
        # 3. Service Token (with optional IP validation)
        elif auth_header.startswith("Service "):
            result = await self._validate_service_token(auth_header, client_ip)
            if result:
                return result
        
        # 4. JWT Bearer Token (existing method)
        elif auth_header.startswith("Bearer "):
            result = await self._validate_jwt_token(auth_header)
            if result:
                return result
        
        # 5. IP-based trust (for specific Jellyfin server)
        if client_ip:
            result = await self._validate_trusted_ip(client_ip, auth_header)
            if result:
                return result
        
        return None
    
    async def _validate_api_key(self, auth_header: str) -> Optional[Dict[str, Any]]:
        """Validate API key authentication"""
        try:
            api_key = auth_header.replace("ApiKey ", "").strip()
            
            # Get stored API keys from database
            stored_keys = await self.web_db.get_webhook_api_keys()
            
            for key_info in stored_keys:
                # Compare using constant-time comparison to prevent timing attacks
                if secrets.compare_digest(api_key, key_info["key"]):
                    logger.info(f"Webhook authenticated via API key: {key_info['name']}")
                    return {
                        "auth_type": "api_key",
                        "key_name": key_info["name"],
                        "key_id": key_info["id"],
                        "username": f"api-key-{key_info['name']}"
                    }
        except Exception as e:
            logger.error(f"API key validation error: {e}")
        
        return None
    
    async def _validate_basic_auth(self, auth_header: str) -> Optional[Dict[str, Any]]:
        """Validate Basic authentication"""
        try:
            # Decode Basic auth header
            encoded_credentials = auth_header.replace("Basic ", "").strip()
            decoded = base64.b64decode(encoded_credentials).decode('utf-8')
            username, password = decoded.split(":", 1)
            
            # Get webhook-specific credentials
            webhook_creds = await self.web_db.get_webhook_basic_auth()
            
            if webhook_creds and webhook_creds["username"] == username:
                # Verify password
                if pwd_context.verify(password, webhook_creds["password_hash"]):
                    logger.info(f"Webhook authenticated via Basic auth: {username}")
                    return {
                        "auth_type": "basic",
                        "username": username,
                        "user_id": webhook_creds.get("user_id", 0)
                    }
        except Exception as e:
            logger.error(f"Basic auth validation error: {e}")
        
        return None
    
    async def _validate_service_token(self, auth_header: str, client_ip: str = None) -> Optional[Dict[str, Any]]:
        """Validate service token (long-lived token for services)"""
        try:
            token = auth_header.replace("Service ", "").strip()
            
            # Decode without expiry validation first
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=["HS256"],
                options={"verify_exp": False}  # Check expiry manually
            )
            
            # Check if it's a service token
            if payload.get("type") != "service":
                return None
            
            # Check if token is registered and not revoked
            token_info = await self.web_db.get_service_token_info(payload.get("jti"))  # JWT ID
            if not token_info or token_info.get("revoked"):
                return None
            
            # Optional: Validate IP if configured
            if token_info.get("allowed_ips"):
                if client_ip not in token_info["allowed_ips"]:
                    logger.warning(f"Service token used from unauthorized IP: {client_ip}")
                    return None
            
            # Check custom expiry (could be very long or infinite)
            if token_info.get("expires_at"):
                if datetime.utcnow() > token_info["expires_at"]:
                    logger.warning("Service token has expired")
                    return None
            
            logger.info(f"Webhook authenticated via service token: {payload.get('service')}")
            return {
                "auth_type": "service_token",
                "service": payload.get("service"),
                "username": payload.get("username", "service"),
                "token_id": payload.get("jti")
            }
            
        except jwt.InvalidTokenError as e:
            logger.error(f"Service token validation error: {e}")
        except Exception as e:
            logger.error(f"Service token error: {e}")
        
        return None
    
    async def _validate_jwt_token(self, auth_header: str) -> Optional[Dict[str, Any]]:
        """Validate standard JWT Bearer token"""
        try:
            token = auth_header.replace("Bearer ", "").strip()
            
            # Decode and validate JWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            
            # Accept both access and refresh tokens for webhooks
            token_type = payload.get("type")
            if token_type not in ["access", "refresh"]:
                return None
            
            logger.info(f"Webhook authenticated via JWT: {payload.get('username')}")
            return {
                "auth_type": "jwt",
                "token_type": token_type,
                "username": payload.get("username"),
                "user_id": payload.get("user_id")
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
        
        return None
    
    async def _validate_trusted_ip(self, client_ip: str, auth_header: str = None) -> Optional[Dict[str, Any]]:
        """
        Validate request from trusted IP address.
        Can optionally require a simple shared secret.
        """
        try:
            # Get trusted IPs from configuration
            trusted_ips = await self.web_db.get_trusted_webhook_ips()
            
            if client_ip in trusted_ips:
                # Optional: Check for simple shared secret
                if auth_header and auth_header.startswith("SharedSecret "):
                    secret = auth_header.replace("SharedSecret ", "").strip()
                    stored_secret = await self.web_db.get_webhook_shared_secret()
                    
                    if stored_secret and secrets.compare_digest(secret, stored_secret):
                        logger.info(f"Webhook authenticated via trusted IP with secret: {client_ip}")
                        return {
                            "auth_type": "trusted_ip_secret",
                            "client_ip": client_ip,
                            "username": f"trusted-{client_ip}"
                        }
                else:
                    # Just IP validation (if configured to allow)
                    if await self.web_db.get_allow_ip_only_auth():
                        logger.info(f"Webhook authenticated via trusted IP only: {client_ip}")
                        return {
                            "auth_type": "trusted_ip",
                            "client_ip": client_ip,
                            "username": f"trusted-{client_ip}"
                        }
        except Exception as e:
            logger.error(f"IP validation error: {e}")
        
        return None


class WebhookAPIKeyManager:
    """
    Manages API keys for webhook authentication.
    """
    
    @staticmethod
    def generate_api_key(prefix: str = "wh") -> str:
        """
        Generate a secure API key.
        
        Format: prefix_randomstring
        Example: wh_a3b4c5d6e7f8g9h0i1j2k3l4m5n6o7p8
        """
        random_part = secrets.token_urlsafe(32)
        return f"{prefix}_{random_part}"
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """
        Hash an API key for secure storage.
        
        Uses SHA-256 for consistent hashing.
        """
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    async def create_api_key(web_db, name: str, description: str = None) -> Dict[str, str]:
        """
        Create a new API key for webhook authentication.
        
        Returns:
            Dict with 'key' (the actual key to give to user) and 'id'
        """
        api_key = WebhookAPIKeyManager.generate_api_key()
        key_hash = WebhookAPIKeyManager.hash_api_key(api_key)
        
        key_id = await web_db.save_webhook_api_key({
            "name": name,
            "key_hash": key_hash,
            "description": description,
            "created_at": datetime.utcnow(),
            "last_used": None,
            "active": True
        })
        
        return {
            "id": key_id,
            "key": api_key,  # Return the actual key only once
            "name": name
        }


class ServiceTokenManager:
    """
    Manages long-lived service tokens for webhook authentication.
    """
    
    @staticmethod
    def create_service_token(
        service_name: str,
        jwt_secret: str,
        expires_in_days: int = 3650,  # 10 years default
        allowed_ips: list = None
    ) -> Dict[str, Any]:
        """
        Create a long-lived service token.
        
        Args:
            service_name: Name of the service (e.g., "jellyfin")
            jwt_secret: JWT secret key
            expires_in_days: Token validity in days (0 for no expiry)
            allowed_ips: Optional list of allowed IP addresses
        
        Returns:
            Dict with token and metadata
        """
        # Generate unique token ID
        token_id = secrets.token_urlsafe(16)
        
        # Create payload
        payload = {
            "jti": token_id,  # JWT ID for tracking
            "type": "service",
            "service": service_name,
            "username": f"{service_name}-webhook",
            "iat": datetime.utcnow()
        }
        
        # Add expiry if specified
        if expires_in_days > 0:
            payload["exp"] = (datetime.utcnow() + timedelta(days=expires_in_days)).timestamp()
        
        # Generate token
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")
        
        return {
            "token": token,
            "token_id": token_id,
            "service": service_name,
            "expires_in_days": expires_in_days if expires_in_days > 0 else None,
            "allowed_ips": allowed_ips
        }