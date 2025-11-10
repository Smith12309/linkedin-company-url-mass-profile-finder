import logging
from datetime import datetime
from typing import Any, Dict

import requests
from bs4 import BeautifulSoup

from utils.url_parser import is_valid_linkedin_company_url, normalize_linkedin_url

logger = logging.getLogger(__name__)

class SearchHandler:
    """
    Encapsulates logic for searching LinkedIn company URLs
    via a public search engine (DuckDuckGo HTML endpoint by default).
    """

    def __init__(self, base_url: str, timeout_seconds: int = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def build_query(self, company_name: str) -> str:
        return f"linkedin company {company_name}"

    def _perform_search(self, query: str) -> str:
        """
        Perform a search request and return the HTML response text.

        Uses DuckDuckGo's HTML interface by default; this may change over time.
        """
        params = {"q": query}
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
        }
        logger.debug("Requesting search for query: %s", query)

        resp = requests.get(
            self.base_url,
            params=params,
            headers=headers,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        return resp.text

    def _extract_linkedin_url_from_html(self, html: str) -> str:
        """
        Parse HTML and find the first LinkedIn company URL.
        """
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "linkedin.com/company" in href:
                if is_valid_linkedin_company_url(href):
                    return normalize_linkedin_url(href)
        return ""

    def search_company(self, company_name: str) -> Dict[str, Any]:
        """
        High-level method to search for a single company and return
        a structured result object as described in the README.
        """
        query = self.build_query(company_name)
        timestamp = datetime.utcnow().isoformat() + "Z"

        try:
            html = self._perform_search(query)
            linkedin_url = self._extract_linkedin_url_from_html(html)

            if linkedin_url:
                info = "LinkedIn page successfully found"
            else:
                info = "No LinkedIn company page found in search results"

            logger.debug(
                "Search result for '%s': url=%s info=%s", company_name, linkedin_url, info
            )

            return {
                "companyName": company_name,
                "searchQuery": query,
                "linkedinUrl": linkedin_url,
                "info": info,
                "timestamp": timestamp,
            }

        except requests.RequestException as exc:
            logger.warning(
                "Network/search error while processing '%s': %s", company_name, exc
            )
            return {
                "companyName": company_name,
                "searchQuery": query,
                "linkedinUrl": "",
                "info": f"Search error: {exc}",
                "timestamp": timestamp,
            }
        except Exception as exc:
            logger.exception("Unexpected error while searching for '%s': %s", company_name, exc)
            return {
                "companyName": company_name,
                "searchQuery": query,
                "linkedinUrl": "",
                "info": f"Unexpected error: {exc}",
                "timestamp": timestamp,
            }