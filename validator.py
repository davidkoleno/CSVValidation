import csv
from collections import Counter
from pathlib import Path

from config import ValidatorConfig
from models import FileValidationResult


def discover_files(config: ValidatorConfig) -> list[Path]:
    if config.recursive:
        files = config.input_folder.rglob(config.file_pattern)
    else:
        files = config.input_folder.glob(config.file_pattern)

    return sorted(files)


def clean_line_generator(infile, result: FileValidationResult):
    """
    Counts NUL characters and removes them only from the stream
    being passed to csv.reader.

    This DOES NOT modify the source file.
    """

    for line in infile:
        nul_count = line.count("\x00")

        if nul_count:
            result.nul_count += nul_count
            line = line.replace("\x00", "")

        yield line


def validate_header(
    header: list[str],
    result: FileValidationResult,
    config: ValidatorConfig,
):
    result.header = header
    result.header_columns = len(header)

    # Blank headers
    blank_positions = [
        index + 1
        for index, column in enumerate(header)
        if not column.strip()
    ]

    result.blank_header_count = len(blank_positions)

    if blank_positions:
        result.add_error(
            issue_type="BLANK_HEADER",
            details=(
                "Blank column names found at positions: "
                + ", ".join(map(str, blank_positions))
            ),
        )

    # Duplicate headers
    counts = Counter(header)

    duplicates = {
        name: count
        for name, count in counts.items()
        if count > 1
    }

    result.duplicate_header_count = len(duplicates)

    for name, count in duplicates.items():
        positions = [
            index + 1
            for index, value in enumerate(header)
            if value == name
        ]

        result.add_error(
            issue_type="DUPLICATE_HEADER",
            actual_value=name,
            details=(
                f"Header appears {count} times at positions "
                f"{positions}"
            ),
        )

    # SQL Server width
    if result.header_columns > config.safe_source_column_limit:
        result.sql_column_limit_exceeded = True

        result.add_error(
            issue_type="SQL_COLUMN_LIMIT",
            expected_value=(
                f"<= {config.safe_source_column_limit}"
            ),
            actual_value=str(result.header_columns),
            details=(
                f"SQL maximum is {config.sql_max_columns}. "
                f"Loader adds {config.loader_added_columns} columns "
                f"and safety buffer is {config.sql_safety_buffer}."
            ),
        )


def validate_with_encoding(
    file_path: Path,
    encoding: str,
    config: ValidatorConfig,
) -> FileValidationResult:

    result = FileValidationResult(
        file_path=file_path,
        file_name=file_path.name,
        encoding=encoding,
        delimiter=config.delimiter,
    )

    with file_path.open(
        "r",
        encoding=encoding,
        newline="",
    ) as infile:

        cleaned_lines = clean_line_generator(
            infile,
            result,
        )

        reader = csv.reader(
            cleaned_lines,
            delimiter=config.delimiter,
            quotechar=config.quotechar,
            strict=True,
        )

        try:
            header = next(reader)
        except StopIteration:
            result.add_error(
                issue_type="EMPTY_FILE",
                details="File contains no records.",
            )

            return result

        # csv.reader.line_num is the number of physical
        # lines consumed to create the logical record.
        if reader.line_num > 1:
            result.multiline_header = True

            result.add_error(
                issue_type="MULTILINE_HEADER",
                actual_value=str(reader.line_num),
                details=(
                    "Header spans multiple physical lines."
                ),
                severity="WARNING",
            )

        validate_header(
            header,
            result,
            config,
        )

        expected_columns = len(header)

        logical_row_number = 1

        try:
            for row in reader:
                logical_row_number += 1
                result.rows_checked += 1

                actual_columns = len(row)

                if actual_columns != expected_columns:
                    result.bad_row_count += 1

                    # Keep counting every problem but limit
                    # detailed report size.
                    if (
                        len(result.errors)
                        < config.max_detailed_errors_per_file
                    ):
                        result.add_error(
                            issue_type="COLUMN_COUNT_MISMATCH",
                            row_number=logical_row_number,
                            expected_value=str(expected_columns),
                            actual_value=str(actual_columns),
                            details=(
                                "Logical CSV record contains a "
                                "different number of columns "
                                "than the header."
                            ),
                        )

        except csv.Error as exc:
            result.parse_error = True

            result.add_error(
                issue_type="CSV_PARSE_ERROR",
                row_number=logical_row_number + 1,
                details=str(exc),
            )

    if result.nul_count:
        result.add_error(
            issue_type="NUL_CHARACTERS",
            actual_value=str(result.nul_count),
            details=(
                f"Detected {result.nul_count:,} NUL characters."
            ),
            severity="WARNING",
        )

    return result


def validate_file(
    file_path: Path,
    config: ValidatorConfig,
) -> FileValidationResult:

    last_decode_error = None

    for encoding in config.encodings:
        try:
            return validate_with_encoding(
                file_path,
                encoding,
                config,
            )

        except UnicodeDecodeError as exc:
            last_decode_error = exc

    result = FileValidationResult(
        file_path=file_path,
        file_name=file_path.name,
        delimiter=config.delimiter,
    )

    result.add_error(
        issue_type="ENCODING_ERROR",
        details=str(last_decode_error),
    )

    return result
