import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.config import get_settings

def base64url_encode(data: bytes) -> str:
    """Encode bytes to a base64url string (RFC 4648), removing padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def base64url_decode(data: str) -> bytes:
    """Decode a base64url string to bytes, adding back correct padding if needed."""
    rem = len(data) % 4
    if rem > 0:
        data += "=" * (4 - rem)
    return base64.urlsafe_b64decode(data.encode("ascii"))

def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with a 16-byte random salt."""
    salt = secrets.token_bytes(16)
    # Stretch using 100,000 iterations of SHA-256
    hash_bytes = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    
    # Store as hex salt$hash
    return f"{salt.hex()}${hash_bytes.hex()}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify standard PBKDF2-HMAC-SHA256 password hash in constant time."""
    try:
        parts = hashed_password.split("$")
        if len(parts) != 2:
            return False
            
        salt_hex, hash_hex = parts
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        
        # Re-derive the hash using the same salt & iterations
        derived_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        
        # Prevent timing attacks by comparing digests in constant time
        return hmac.compare_digest(derived_hash, expected_hash)
    except Exception:
        return False

def create_access_token(data: dict, expires_in_minutes: Optional[int] = None) -> str:
    """Create a signed JWT access token in pure Python using Base64Url and HMAC-SHA256."""
    settings = get_settings()
    expire_minutes = expires_in_minutes or settings.access_token_expire_minutes
    
    # 1. Prepare claims
    claims = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    claims["exp"] = int(expire.timestamp())
    
    # 2. Base64Url encode Header & Payload
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    
    encoded_header = base64url_encode(json.dumps(header).encode("utf-8"))
    encoded_payload = base64url_encode(json.dumps(claims).encode("utf-8"))
    
    # 3. Compute HMAC Signature
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    secret_bytes = settings.jwt_secret_key.encode("utf-8")
    
    signature_bytes = hmac.new(secret_bytes, signing_input, hashlib.sha256).digest()
    encoded_signature = base64url_encode(signature_bytes)
    
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and cryptographically verify a JWT access token in pure Python."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
            
        encoded_header, encoded_payload, encoded_signature = parts
        
        settings = get_settings()
        secret_bytes = settings.jwt_secret_key.encode("utf-8")
        
        # 1. Verify Signature in constant time to prevent timing attacks
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
        computed_signature = hmac.new(secret_bytes, signing_input, hashlib.sha256).digest()
        
        provided_signature = base64url_decode(encoded_signature)
        
        if not hmac.compare_digest(computed_signature, provided_signature):
            return None
            
        # 2. Decode payload
        payload_bytes = base64url_decode(encoded_payload)
        payload = json.loads(payload_bytes.decode("utf-8"))
        
        # 3. Verify Expiration
        exp = payload.get("exp")
        if exp is None:
            return None
            
        now = datetime.now(timezone.utc).timestamp()
        if now > exp:
            return None
            
        return payload
    except Exception:
        return None
