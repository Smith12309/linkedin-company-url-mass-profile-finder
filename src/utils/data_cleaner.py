from pathlib import Path
from typing import Iterable, List

def clean_company_name(name: str) -> str:
    """
    Clean up a raw company name string:
    - strip whitespace
    - collapse internal whitespace
    """
    name = (name or "").strip()
    if not name:
        return ""
    parts = name.split()
    return " ".join(parts)

def dedupe_companies(companies: Iterable[str]) -> List[str]:
    """
    Remove duplicates while preserving order and ignoring trivial differences.
    """
    seen = set()
    result: List[str] = []
    for raw in companies:
        cleaned = clean_company_name(raw)
        key = cleaned.lower()
        if not cleaned:
            continue
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result

def load_companies_from_file(path: Path) -> List[str]:
    """
    Load company names from a text file, one company per line.
    Blank lines are ignored.
    """
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    companies: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            companies.append(line)
    return companies