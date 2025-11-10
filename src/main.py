import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from handlers.search_handler import SearchHandler
from handlers.export_handler import ExportHandler
from utils.data_cleaner import load_companies_from_file, dedupe_companies
from utils.url_parser import is_valid_linkedin_company_url

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_FILE = ROOT_DIR / "data" / "inputs" / "companies_list.txt"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "outputs"
SETTINGS_FILE = ROOT_DIR / "src" / "config" / "settings.json"

def setup_logging(level: str = "INFO") -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

def load_settings() -> Dict[str, Any]:
    default_settings: Dict[str, Any] = {
        "search": {
            "base_url": "https://duckduckgo.com/html/",
            "timeout_seconds": 10,
            "max_workers": 8,
        }
    }

    if not SETTINGS_FILE.exists():
        logging.warning("settings.json not found, using default settings.")
        return default_settings

    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as f:
            raw = json.load(f)
            # Merge with defaults to avoid missing keys
            for section, values in default_settings.items():
                if section not in raw or not isinstance(raw[section], dict):
                    raw[section] = values
                else:
                    for k, v in values.items():
                        raw[section].setdefault(k, v)
            return raw
    except Exception as exc:
        logging.error("Failed to load settings.json: %s", exc)
        return default_settings

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LinkedIn Company URL - Mass Profile Finder"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=str(DEFAULT_INPUT_FILE),
        help="Path to input companies list (one company per line).",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where results will be written.",
    )
    parser.add_argument(
        "--formats",
        type=str,
        default="json,csv",
        help="Comma-separated list of export formats (json,csv).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of companies to process.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR).",
    )
    return parser.parse_args()

def validate_results(results: List[Dict[str, Any]]) -> None:
    """Log any results that don't contain a valid LinkedIn URL."""
    invalid = [
        r for r in results if r.get("linkedinUrl") and not is_valid_linkedin_company_url(r["linkedinUrl"])
    ]
    if invalid:
        logging.warning(
            "Found %d results with invalid LinkedIn URLs (they will still be exported).",
            len(invalid),
        )

def main() -> None:
    args = parse_args()
    setup_logging(args.log_level)

    settings = load_settings()
    search_settings = settings.get("search", {})
    logging.info("Loaded settings: %s", search_settings)

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    formats = [fmt.strip().lower() for fmt in args.formats.split(",") if fmt.strip()]

    if not input_path.exists():
        logging.error("Input file does not exist: %s", input_path)
        sys.exit(1)

    try:
        companies = load_companies_from_file(input_path)
    except Exception as exc:
        logging.error("Failed to read companies from %s: %s", input_path, exc)
        sys.exit(1)

    companies = dedupe_companies(companies)
    if args.limit is not None:
        companies = companies[: args.limit]

    if not companies:
        logging.warning("No companies found in input file.")
        sys.exit(0)

    logging.info("Processing %d companies...", len(companies))

    search_handler = SearchHandler(
        base_url=search_settings.get("base_url", "https://duckduckgo.com/html/"),
        timeout_seconds=search_settings.get("timeout_seconds", 10),
    )
    results: List[Dict[str, Any]] = []

    # Use a thread pool for concurrent search
    max_workers = int(search_settings.get("max_workers", 8))
    max_workers = max(1, max_workers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_company = {
            executor.submit(search_handler.search_company, company): company
            for company in companies
        }

        for future in as_completed(future_to_company):
            company_name = future_to_company[future]
            try:
                result = future.result()
                results.append(result)
                logging.info(
                    "Processed '%s' -> %s",
                    company_name,
                    result.get("linkedinUrl") or "NO RESULT",
                )
            except Exception as exc:
                logging.exception("Unexpected error while processing '%s': %s", company_name, exc)
                results.append(
                    {
                        "companyName": company_name,
                        "searchQuery": search_handler.build_query(company_name),
                        "linkedinUrl": "",
                        "info": f"Unexpected error: {exc}",
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    }
                )

    validate_results(results)

    exporter = ExportHandler(output_dir=output_dir)
    paths = exporter.export(results, formats=formats)

    if paths:
        logging.info("Export completed:")
        for fmt, path in paths.items():
            logging.info("  %s -> %s", fmt.upper(), path)
    else:
        logging.warning("No exports were generated. Check requested formats.")

if __name__ == "__main__":
    main()