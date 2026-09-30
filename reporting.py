import csv
from pathlib import Path

from models import FileValidationResult


SUMMARY_HEADERS = [
    "FilePath",
    "FileName",
    "Status",
    "Encoding",
    "Delimiter",
    "HeaderColumns",
    "RowsChecked",
    "BadRowCount",
    "NULCount",
    "MultilineHeader",
    "BlankHeaderCount",
    "DuplicateHeaderCount",
    "SchemaMatch",
    "ReferenceSchema",
    "SQLColumnLimitExceeded",
    "ErrorCount",
]


ERROR_HEADERS = [
    "FilePath",
    "FileName",
    "RowNumber",
    "IssueType",
    "ExpectedValue",
    "ActualValue",
    "Details",
]


def write_reports(
    results: list[FileValidationResult],
    report_folder: Path,
):
    report_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_summary_report(
        results,
        report_folder / "validation_summary.csv",
    )

    write_error_report(
        results,
        report_folder / "validation_errors.csv",
    )


def write_summary_report(
    results: list[FileValidationResult],
    output_file: Path,
):
    with output_file.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as outfile:

        writer = csv.DictWriter(
            outfile,
            fieldnames=SUMMARY_HEADERS,
        )

        writer.writeheader()

        for result in results:
            writer.writerow({
                "FilePath": result.file_path,
                "FileName": result.file_name,
                "Status": result.status,
                "Encoding": result.encoding,
                "Delimiter": result.delimiter,
                "HeaderColumns": result.header_columns,
                "RowsChecked": result.rows_checked,
                "BadRowCount": result.bad_row_count,
                "NULCount": result.nul_count,
                "MultilineHeader": result.multiline_header,
                "BlankHeaderCount": result.blank_header_count,
                "DuplicateHeaderCount":
                    result.duplicate_header_count,
                "SchemaMatch": result.schema_match,
                "ReferenceSchema": result.reference_schema,
                "SQLColumnLimitExceeded":
                    result.sql_column_limit_exceeded,
                "ErrorCount": len(result.errors),
            })


def write_error_report(
    results: list[FileValidationResult],
    output_file: Path,
):
    with output_file.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as outfile:

        writer = csv.DictWriter(
            outfile,
            fieldnames=ERROR_HEADERS,
        )

        writer.writeheader()

        for result in results:
            for error in result.errors:
                writer.writerow({
                    "FilePath": result.file_path,
                    "FileName": result.file_name,
                    "RowNumber": error.row_number,
                    "IssueType": error.issue_type,
                    "ExpectedValue":
                        error.expected_value,
                    "ActualValue":
                        error.actual_value,
                    "Details": error.details,
                })
