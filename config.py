from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidatorConfig:
    input_folder: Path
    report_folder: Path

    file_pattern: str = "*.csv"
    recursive: bool = True

    delimiter: str = "^"
    quotechar: str = '"'

    # Try these in order
    encodings: list[str] = field(
        default_factory=lambda: [
            "utf-8-sig",
            "cp1252",
        ]
    )

    sql_max_columns: int = 1024

    # Columns your loader adds automatically
    loader_added_columns: int = 2

    # Extra breathing room
    sql_safety_buffer: int = 10

    max_detailed_errors_per_file: int = 1000

    @property
    def safe_source_column_limit(self) -> int:
        return (
            self.sql_max_columns
            - self.loader_added_columns
            - self.sql_safety_buffer
        )
