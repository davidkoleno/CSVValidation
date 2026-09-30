from pathlib import Path

from config import ValidatorConfig
from reporting import write_reports
from schema_validator import compare_schemas
from validator import discover_files, validate_file
from repair import repair_files

INPUT_FOLDER = Path(
    r"C:\Path\To\Input"
)

REPORT_FOLDER = Path(
    r"C:\Path\To\ValidationReports"
)

REPAIR_FOLDER = Path(
    r"C:\Path\To\Repaired"
)

def main():
    config = ValidatorConfig(
        input_folder=INPUT_FOLDER,
        report_folder=REPORT_FOLDER,

        delimiter="^",
        quotechar='"',

        loader_added_columns=2,
        sql_safety_buffer=10,
    )

    files = discover_files(config)

    print()
    print("CSV Validation Tool")
    print("=" * 60)

    print(f"Input: {config.input_folder}")
    print(f"Files found: {len(files):,}")
    print(
        "Safe SQL source column limit: "
        f"{config.safe_source_column_limit:,}"
    )

    print()

    results = []

    for file_number, file_path in enumerate(
        files,
        start=1,
    ):
        relative_path = file_path.relative_to(
            config.input_folder
        )

        print(
            f"[{file_number:,}/{len(files):,}] "
            f"{relative_path}"
        )

        result = validate_file(
            file_path,
            config,
        )

        results.append(result)

        print(
            f"    {result.status} | "
            f"{result.header_columns:,} columns | "
            f"{result.rows_checked:,} rows | "
            f"{result.bad_row_count:,} bad rows"
        )

        if result.nul_count:
            print(
                f"    NUL characters: "
                f"{result.nul_count:,}"
            )

    print()
    print("Comparing schemas...")

    compare_schemas(results)

    print("Writing validation reports...")

    write_reports(
        results,
        config.report_folder,
    )

    print()
    print("Repairing files...")

    repair_files(
        results,
        config,
        REPAIR_FOLDER,
    )

    print()
    print("Repair complete.")

    passed = sum(
        1
        for result in results
        if result.status == "PASS"
    )

    warnings = sum(
        1
        for result in results
        if result.status == "WARNING"
    )

    failed = sum(
        1
        for result in results
        if result.status == "FAIL"
    )

    print()
    print("=" * 60)
    print("Validation Complete")
    print("=" * 60)

    print(f"PASS:    {passed:,}")
    print(f"WARNING: {warnings:,}")
    print(f"FAIL:    {failed:,}")

    print()
    print(
        f"Summary: "
        f"{config.report_folder / 'validation_summary.csv'}"
    )

    print(
        f"Errors:  "
        f"{config.report_folder / 'validation_errors.csv'}"
    )


if __name__ == "__main__":
    main()
