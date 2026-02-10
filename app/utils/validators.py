import re
from ..core.config import settings


def validate_company_email(email: str) -> bool:
    """Validate email matches company format."""
    pattern = rf"^[a-z]+\.[a-z]+@{re.escape(settings.COMPANY_DOMAIN)}$"
    return bool(re.match(pattern, email.lower()))


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets requirements."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    
    return True, ""