import uuid
import random
from datetime import datetime


def generate_user_code() -> str:
    """Generate a unique 4-digit user code (1000-9999)."""
    return str(random.randint(1000, 9999))


def generate_unique_code(prefix: str = "") -> str:
    """Generate a unique code."""
    random_part = str(uuid.uuid4())[:8].upper()
    if prefix:
        return f"{prefix}-{random_part}"
    return random_part