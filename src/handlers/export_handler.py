import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

logger = logging.getLogger(__name__)

class ExportHandler:
    """
    Handle exporting data to various formats.
    For this project tree we guarantee JSON and CSV.
    """

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir

    def _ensure_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _export_json(self, records: Iterable[Mapping[str, Any]]) -> Path:
        self._ensure_output_dir()
        output_path = self.output_dir / "results.json"
        # Ensure list
        data = list(records)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Written JSON results to %s", output_path)
        return output_path

    def _export_csv(self, records: Iterable[Mapping[str, Any]]) -> Path:
        self._ensure_output_dir()
        output_path = self.output_dir / "results.csv"

        rows: List[Mapping[str, Any]] = list(records)
        if not rows:
            # still create an empty CSV with a standard header
            header = ["companyName", "searchQuery", "linkedinUrl", "info", "timestamp"]
            with output_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=header)
                writer.writeheader()
            logger.info("Written empty CSV results to %s", output_path)
            return output_path

        # Build header from keys union, but keep stable ordering for known keys
        default_order = ["companyName", "searchQuery", "linkedinUrl", "info", "timestamp"]
        extra_keys = set()
        for row in rows:
            extra_keys.update(row.keys())
        for known in default_order:
            extra_keys.discard(known)
        header = default_order + sorted(extra_keys)

        with output_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        logger.info("Written CSV results to %s", output_path)
        return output_path

    def export(self, records: Iterable[Mapping[str, Any]], formats: Iterable[str]) -> Dict[str, Path]:
        """
        Export records to the specified formats.

        Supported formats in this implementation:
          - json
          - csv
        """
        formats_set = {fmt.lower() for fmt in formats}
        paths: Dict[str, Path] = {}
        records_list = list(records)

        if "json" in formats_set:
            try:
                paths["json"] = self._export_json(records_list)
            except Exception as exc:
                logger.error("Failed to export JSON: %s", exc)

        if "csv" in formats_set:
            try:
                paths["csv"] = self._export_csv(records_list)
            except Exception as exc:
                logger.error("Failed to export CSV: %s", exc)

        unsupported = formats_set - {"json", "csv"}
        if unsupported:
            logger.warning("Requested unsupported formats (ignored): %s", ", ".join(sorted(unsupported)))

        return paths