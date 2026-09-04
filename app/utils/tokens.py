import re
import time
from typing import Tuple, Optional, Dict, Any
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature, BadSignature
import jwt


GHANA_PHONE_REGEX = re.compile(r'^(?:\+233|233|0)(20|23|24|25|26|27|28|50|53|54|55|56|57|59)\d{7}$')


def validate_and_normalize_ghana_phone(phone: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validates Ghanaian mobile phone numbers (MTN, Telecel/Vodafone, AT/AirtelTigo)
    and normalizes them to E.164 format (+233...).
    Returns (is_valid, normalized_phone_or_none, error_message_or_none).
    """
    if not phone:
        return False, None, "Phone number is required."

    cleaned = re.sub(r'[\s\-()]', '', phone.strip())
    if not GHANA_PHONE_REGEX.match(cleaned):
        return False, None, (
            "Invalid Ghanaian mobile number. Please enter a valid number "
            "beginning with 020, 023, 024, 025, 026, 027, 028, 050, 053, 054, 055, 056, 057, or 059."
        )

    if cleaned.startswith('+233'):
        normalized = cleaned
    elif cleaned.startswith('233'):
        normalized = '+' + cleaned
    elif cleaned.startswith('0'):
        normalized = '+233' + cleaned[1:]
    else:
        normalized = cleaned

    return True, normalized, None


def generate_qr_token(index_number: str, secret_key: str, attachment_id: Optional[int] = None) -> str:
    """
    Generates a secure timed signed token for physical-to-digital QR onboarding gateway.
    Embeds student index number and attachment ID.
    """
    serializer = URLSafeTimedSerializer(secret_key, salt='qr-onboarding')
    payload = {'index_number': index_number}
    if attachment_id is not None:
        payload['attachment_id'] = attachment_id
    return serializer.dumps(payload)


def decode_qr_onboard_token(token: str, secret_key: str, max_age: int = 604800) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Decodes and validates a secure QR onboarding token.
    Default max_age is 7 days (604800 seconds) to accommodate physical delivery/intake.
    Returns (is_valid, payload_dict_or_none, error_message_or_none).
    """
    serializer = URLSafeTimedSerializer(secret_key, salt='qr-onboarding')
    try:
        data = serializer.loads(token, max_age=max_age)
        if not isinstance(data, dict) or not data.get('index_number'):
            return False, None, "Invalid token structure."
        return True, data, None
    except SignatureExpired:
        return False, None, "This onboarding QR code has expired. Please visit the Industrial Liaison Office for a re-issuance."
    except (BadTimeSignature, BadSignature):
        return False, None, "Invalid or altered onboarding QR token."
    except Exception as e:
        return False, None, f"Token validation error: {str(e)}"


def verify_qr_token(token: str, expected_index_number: str, secret_key: str, max_age: int = 604800) -> Tuple[bool, Optional[str]]:
    """
    Validates a timed QR token against an expected student index number.
    Returns (is_valid, error_reason).
    """
    is_valid, data, err = decode_qr_onboard_token(token, secret_key, max_age=max_age)
    if not is_valid:
        return False, err
    if data.get('index_number') != expected_index_number:
        return False, "Token index number does not match this student record."
    return True, None


def generate_elogbook_sso_jwt(student, attachment, secret_key: str, expires_in: int = 120) -> str:
    """
    Generates a cryptographically signed HMAC-SHA256 JWT with a 120-second expiration window
    for seamless SSO hand-off to the decoupled external eLogBook application.
    """
    now = int(time.time())
    payload = {
        'iss': 'usted-u-iap-portal',
        'sub': student.index_number,
        'index_number': student.index_number,
        'full_name': student.full_name,
        'programme': student.programme,
        'department': student.department,
        'current_level': student.current_level,
        'attachment_id': attachment.id,
        'academic_year': attachment.academic_year,
        'duration_weeks': attachment.duration_weeks,
        'target_organization': attachment.target_organization or 'To be confirmed',
        'iat': now,
        'exp': now + expires_in
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')
