from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ValidationError:
    file_path: Path
    issue_type: str

    row_number: int | None = None
    expected_value: str | None = None
    actual_value: str | None = None
    details: str = ""


@dataclass
class FileValidationResult:
    file_path: Path
    file_name: str

    status: str = "PASS"

    encoding: str = ""
    delimiter: str = ""

    header: list[str] = field(default_factory=list)
    header_columns: int = 0

    rows_checked: int = 0
    bad_row_count: int = 0

    nul_count: int = 0

    multiline_header: bool = False
    blank_header_count: int = 0
    duplicate_header_count: int = 0

    sql_column_limit_exceeded: bool = False

    schema_match: bool | None = None
    reference_schema: str = ""

    parse_error: bool = False

    errors: list[ValidationError] = field(default_factory=list)

    def add_error(
        self,
        issue_type: str,
        row_number: int | None = None,
        expected_value: str | None = None,
        actual_value: str | None = None,
        details: str = "",
        severity: str = "FAIL",
    ):
        self.errors.append(
            ValidationError(
                file_path=self.file_path,
                issue_type=issue_type,
                row_number=row_number,
                expected_value=expected_value,
                actual_value=actual_value,
                details=details,
            )
        )

        if severity == "FAIL":
            self.status = "FAIL"
        elif severity == "WARNING" and self.status == "PASS":
            self.status = "WARNING"
