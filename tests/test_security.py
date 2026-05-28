import time
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)

def test_password_hashing():
    password = "SuperSecretPassword123"
    
    # Hash password
    hashed = hash_password(password)
    assert hashed != password
    assert "$" in hashed
    
    # Verify correct password
    assert verify_password(password, hashed) is True
    
    # Verify incorrect password
    assert verify_password("WrongPassword123", hashed) is False
    assert verify_password("", hashed) is False

def test_password_salting_is_unique():
    password = "same_password"
    
    # Generate two hashes for the exact same password
    hash_1 = hash_password(password)
    hash_2 = hash_password(password)
    
    # They must have different salts and thus completely different hashes
    assert hash_1 != hash_2
    
    # But both must verify successfully
    assert verify_password(password, hash_1) is True
    assert verify_password(password, hash_2) is True

def test_jwt_token_creation_and_decoding():
    data = {"sub": "alice_test", "role": "admin"}
    
    # Create token
    token = create_access_token(data, expires_in_minutes=5)
    assert len(token.split(".")) == 3
    
    # Decode token
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "alice_test"
    assert decoded["role"] == "admin"
    assert "exp" in decoded

def test_jwt_token_tampering_fails():
    data = {"sub": "bob_test"}
    token = create_access_token(data, expires_in_minutes=5)
    
    # Split token and tamper with the payload part
    parts = token.split(".")
    # Encode a fake payload e.g. {"sub": "admin_bob"}
    # {"sub": "admin_bob"} in base64url is eyJzdWIiOiAiYWRtaW5fYm9iIn0
    tampered_parts = [parts[0], "eyJzdWIiOiAiYWRtaW5fYm9iIn0", parts[2]]
    tampered_token = ".".join(tampered_parts)
    
    # Decoding should fail because signature won't match the new payload
    assert decode_access_token(tampered_token) is None

def test_jwt_token_expiration():
    data = {"sub": "charlie_test"}
    
    # Create an instantly expiring token (expires in -1 minutes, i.e. in the past)
    token = create_access_token(data, expires_in_minutes=-1)
    
    # Decoding should fail because the expiration time has already passed
    assert decode_access_token(token) is None
