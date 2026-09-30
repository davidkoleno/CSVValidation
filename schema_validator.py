from collections import defaultdict

from models import FileValidationResult


def compare_schemas(
    results: list[FileValidationResult],
):
    groups = defaultdict(list)

    for result in results:
        groups[result.file_name.lower()].append(result)

    for _, group in groups.items():

        # Nothing to compare
        if len(group) < 2:
            group[0].schema_match = True
            continue

        valid_headers = [
            result
            for result in group
            if result.header
        ]

        if not valid_headers:
            continue

        reference = valid_headers[0]
        reference_header = reference.header

        reference.schema_match = True
        reference.reference_schema = str(
            reference.file_path
        )

        for result in valid_headers[1:]:
            result.reference_schema = str(
                reference.file_path
            )

            if result.header == reference_header:
                result.schema_match = True
                continue

            result.schema_match = False

            compare_header_details(
                reference,
                result,
            )


def compare_header_details(
    reference: FileValidationResult,
    result: FileValidationResult,
):
    expected = reference.header
    actual = result.header

    if len(expected) != len(actual):
        result.add_error(
            issue_type="SCHEMA_COLUMN_COUNT",
            expected_value=str(len(expected)),
            actual_value=str(len(actual)),
            details=(
                f"Schema differs from "
                f"{reference.file_path}"
            ),
        )

    expected_set = set(expected)
    actual_set = set(actual)

    missing = [
        col
        for col in expected
        if col not in actual_set
    ]

    extra = [
        col
        for col in actual
        if col not in expected_set
    ]

    if missing:
        result.add_error(
            issue_type="SCHEMA_MISSING_COLUMNS",
            details=", ".join(missing),
        )

    if extra:
        result.add_error(
            issue_type="SCHEMA_EXTRA_COLUMNS",
            details=", ".join(extra),
        )

    # Same names but wrong positions
    max_length = min(
        len(expected),
        len(actual),
    )

    position_differences = []

    for index in range(max_length):
        if expected[index] != actual[index]:
            position_differences.append(
                (
                    index + 1,
                    expected[index],
                    actual[index],
                )
            )

    if position_differences:
        details = []

        for position, expected_name, actual_name in position_differences[:50]:
            details.append(
                f"Position {position}: "
                f"expected '{expected_name}', "
                f"found '{actual_name}'"
            )

        result.add_error(
            issue_type="SCHEMA_COLUMN_ORDER",
            details="; ".join(details),
        )
