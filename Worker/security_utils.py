import os
try:
    from cryptography.fernet import Fernet
except ImportError:
    print("!!! ERROR: cryptography not found")
    Fernet = None

def get_fernet():
    print("DEBUG: get_fernet called")
    key = os.environ.get("FERNET_SECRET")
    if not key:
        print("DEBUG: FERNET_SECRET is missing")
        raise ValueError("FERNET_SECRET not set in environment")
    
    print(f"DEBUG: FERNET_SECRET found, lens: {len(key.strip())}")
    
    if Fernet is None:
        raise ImportError("Fernet class is None, check cryptography installation")
    
    f = Fernet(key.strip().encode())
    print(f"DEBUG: Created Fernet instance: {f}")
    return f

def encrypt_password(password: str) -> str:
    print(f"DEBUG: encrypt_password called for secret of length {len(password)}")
    f = get_fernet()
    if f is None:
        print("DEBUG: f is None inside encrypt_password!")
        raise ValueError("Fernet instance is None")
    
    token = f.encrypt(password.encode())
    print(f"DEBUG: Encryption done, token length: {len(token)}")
    return token.decode()

def decrypt_password(encrypted_password: str) -> str:
    f = get_fernet()
    return f.decrypt(encrypted_password.encode()).decode()

def generate_key():
    return Fernet.generate_key().decode()

if __name__ == "__main__":
    print("Generated Key:", generate_key())
