from urllib.parse import urlparse, urlunparse

LINKEDIN_COMPANY_HOST = "www.linkedin.com"
LINKEDIN_COMPANY_PREFIX = "/company/"

def is_valid_linkedin_company_url(url: str) -> bool:
    """
    Basic validation to check if the URL looks like a LinkedIn company profile.
    """
    if not url:
        return False

    try:
        parsed = urlparse(url)
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    host = (parsed.netloc or "").lower()
    if "linkedin.com" not in host:
        return False

    path = parsed.path or ""
    return "/company/" in path.lower()

def normalize_linkedin_url(url: str) -> str:
    """
    Normalize LinkedIn company URL:
    - force https
    - ensure 'www.linkedin.com'
    - strip query and fragment
    - trim trailing slash
    """
    parsed = urlparse(url)

    scheme = "https"
    netloc = parsed.netloc or LINKEDIN_COMPANY_HOST

    # Normalize host
    host = netloc.lower()
    if "linkedin.com" not in host:
        host = LINKEDIN_COMPANY_HOST

    # Remove query and fragment
    path = parsed.path or ""
    if path.endswith("/"):
        path = path[:-1]

    normalized = urlunparse((scheme, host, path, "", "", ""))
    return normalized