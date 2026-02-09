import uuid
from datetime import datetime


def generate_employee_id(prefix: str = "EMP") -> str:
    """Generate a unique employee ID."""
    timestamp = datetime.now().strftime("%Y%m%d")
    random_part = str(uuid.uuid4())[:6].upper()
    return f"{prefix}-{timestamp}-{random_part}"


def generate_unique_code(prefix: str = "") -> str:
    """Generate a unique code."""
    random_part = str(uuid.uuid4())[:8].upper()
    if prefix:
        return f"{prefix}-{random_part}"
    return random_part