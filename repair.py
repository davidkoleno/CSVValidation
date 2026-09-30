# repair.py

import csv
from pathlib import Path

from config import ValidatorConfig
from models import FileValidationResult


def clean_stream(infile):
    """
    Removes NUL characters from the parsing stream.
    Source file is not modified.
    """
    for line in infile:
        yield line.replace("\x00", "")


def clean_header(header: list[str]) -> list[str]:
    """
    Removes embedded CR/LF characters from header values.
    """

    return [
        column.replace("\r", " ").replace("\n", " ").strip()
        for column in header
    ]


def get_output_path(
    input_file: Path,
    input_root: Path,
    output_root: Path,
) -> Path:
    """
    Preserves the original folder structure.
    """

    relative_path = input_file.relative_to(input_root)

    return output_root / relative_path


def repair_normal_file(
    input_file: Path,
    output_file: Path,
    encoding: str,
    config: ValidatorConfig,
):
    """
    Repairs a normal-width file.

    Repairs:
    - NUL characters
    - multiline headers
    - normalized quoting
    """

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with input_file.open(
        "r",
        encoding=encoding,
        newline="",
    ) as infile:

        reader = csv.reader(
            clean_stream(infile),
            delimiter=config.delimiter,
            quotechar=config.quotechar,
            strict=True,
        )

        try:
            header = next(reader)
        except StopIteration:
            print(f"Skipped empty file: {input_file}")
            return

        fixed_header = clean_header(header)

        with output_file.open(
            "w",
            encoding=encoding,
            newline="",
        ) as outfile:

            writer = csv.writer(
                outfile,
                delimiter=config.delimiter,
                quotechar=config.quotechar,
                quoting=csv.QUOTE_ALL,
                lineterminator="\n",
            )

            writer.writerow(fixed_header)

            for row in reader:
                writer.writerow(row)


def split_wide_file(
    input_file: Path,
    output_file: Path,
    encoding: str,
    config: ValidatorConfig,
):
    """
    Splits files that exceed the safe SQL column limit.

    ROW_ID is added to every split file.
    """

    # Reserve one column for ROW_ID
    source_columns_per_part = (
        config.safe_source_column_limit - 1
    )

    with input_file.open(
        "r",
        encoding=encoding,
        newline="",
    ) as infile:

        reader = csv.reader(
            clean_stream(infile),
            delimiter=config.delimiter,
            quotechar=config.quotechar,
            strict=True,
        )

        try:
            header = next(reader)
        except StopIteration:
            print(f"Skipped empty file: {input_file}")
            return

        header = clean_header(header)

        header_chunks = [
            header[i:i + source_columns_per_part]
            for i in range(
                0,
                len(header),
                source_columns_per_part,
            )
        ]

        print(
            f"    Splitting into "
            f"{len(header_chunks)} files"
        )

        output_handles = []
        writers = []

        try:
            for part_number, header_chunk in enumerate(
                header_chunks,
                start=1,
            ):
                part_file = (
                    output_file.parent
                    / (
                        f"{output_file.stem}"
                        f"_part{part_number}"
                        f"{output_file.suffix}"
                    )
                )

                part_file.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                handle = part_file.open(
                    "w",
                    encoding=encoding,
                    newline="",
                )

                writer = csv.writer(
                    handle,
                    delimiter=config.delimiter,
                    quotechar=config.quotechar,
                    quoting=csv.QUOTE_ALL,
                    lineterminator="\n",
                )

                writer.writerow(
                    ["ROW_ID"] + header_chunk
                )

                output_handles.append(handle)
                writers.append(writer)

            for row_id, row in enumerate(
                reader,
                start=1,
            ):
                for index, writer in enumerate(writers):

                    start = (
                        index
                        * source_columns_per_part
                    )

                    end = (
                        start
                        + source_columns_per_part
                    )

                    writer.writerow(
                        [row_id]
                        + row[start:end]
                    )

                if row_id % 100000 == 0:
                    print(
                        f"        "
                        f"{row_id:,} rows processed"
                    )

        finally:
            for handle in output_handles:
                handle.close()


def repair_file(
    result: FileValidationResult,
    config: ValidatorConfig,
    output_folder: Path,
):
    """
    Repairs one validated file.
    """

    input_file = result.file_path

    output_file = get_output_path(
        input_file,
        config.input_folder,
        output_folder,
    )

    if not result.encoding:
        print(
            f"Skipping: {input_file} "
            f"(encoding could not be determined)"
        )
        return

    print(f"Repairing: {input_file}")

    if result.sql_column_limit_exceeded:
        split_wide_file(
            input_file=input_file,
            output_file=output_file,
            encoding=result.encoding,
            config=config,
        )

    else:
        repair_normal_file(
            input_file=input_file,
            output_file=output_file,
            encoding=result.encoding,
            config=config,
        )


def repair_files(
    results: list[FileValidationResult],
    config: ValidatorConfig,
    output_folder: Path,
):
    """
    Repairs all files that were successfully parsed.

    Schema mismatches are reported but not automatically repaired.
    """

    output_folder.mkdir(
        parents=True,
        exist_ok=True,
    )

    for result in results:

        if result.parse_error:
            print(
                f"Skipping parse error: "
                f"{result.file_path}"
            )
            continue

        if not result.header:
            print(
                f"Skipping invalid/empty file: "
                f"{result.file_path}"
            )
            continue

        repair_file(
            result,
            config,
            output_folder,
        )
