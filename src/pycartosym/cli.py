"""Command-line interface for CartoSym Transcoder."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from jsonschema import ValidationError
from jsonschema import validate as jsonschema_validate

from . import __version__
from .cli_style import (
    ExitCode,
    error,
    format_syntax_errors,
    hint,
    info,
    set_quiet,
    success,
)
from .converter import Converter
from .exceptions import CartoSymSyntaxError
from .parser import CartoSymParser

# When no target is given, --print picks the "other" text encoding.
_PRINT_DEFAULT_TARGET = {"cscss": "csjson", "csjson": "cscss"}

# Subcommands that are dispatched explicitly (not the default conversion path)
_SUBCOMMANDS = frozenset({"parse", "validate"})

# Common flags that consume a following token as their value — needed so the
# subcommand pre-detection below (which runs before argparse parses anything)
# doesn't mistake a flag's value for the subcommand name or the input file.
_VALUE_FLAGS = frozenset(
    {"--log-level", "-o", "--output", "--from-format", "--to-format"}
)

_SLD_FORMATS = ["sld", "sld:1.0.0", "sld:1.1.0", "sld:geoserver"]
_ALL_FORMATS = ["cscss", "csjson", *_SLD_FORMATS, "maplibre"]


def _leading_positionals(argv: list[str]) -> list[str]:
    """Return *argv* tokens that aren't flags or a flag's value.

    A value-taking flag (e.g. ``--log-level DEBUG``) consumes the token
    right after it, which would otherwise be mistaken for a positional.
    """
    positionals = []
    skip_next = False
    for token in argv:
        if skip_next:
            skip_next = False
            continue
        if token.startswith("-"):
            skip_next = token in _VALUE_FLAGS
            continue
        positionals.append(token)
    return positionals


def main() -> int:
    """Run the CLI entry point."""
    # Pre-detect whether a named subcommand is being used so that argparse
    # doesn't confuse a file path for a subcommand name (or vice-versa).
    positionals = _leading_positionals(sys.argv[1:])
    is_subcommand = bool(positionals) and positionals[0] in _SUBCOMMANDS

    parser = _create_subcommand_parser() if is_subcommand else _create_convert_parser()
    args = parser.parse_args()
    quiet = getattr(args, "quiet", False)
    set_quiet(quiet)
    # The CLI owns the process's logging: library modules call basicConfig
    # at INFO, which is noise here. force=True so this wins regardless of
    # import order. Default WARNING; `parse --log-level` can lower it,
    # `--quiet` always pins it back up.
    log_level = "WARNING" if quiet else (getattr(args, "log_level", None) or "WARNING")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(levelname)s: %(message)s",
        force=True,
    )

    try:
        if is_subcommand:
            if args.command == "parse":
                return parse_command(args)
            if args.command == "validate":
                return validate_command(args)
            parser.print_help()
            return ExitCode.USAGE
        if getattr(args, "input_file", None) is None:
            parser.print_help()
            return ExitCode.USAGE
        return convert_command(args)
    except FileNotFoundError as e:
        error(f"file not found: {e.filename or e}")
        return ExitCode.NOT_FOUND
    except Exception as e:  # noqa: BLE001 - top-level guard, reported to the user
        error(str(e))
        return ExitCode.USAGE


def create_argument_parser() -> argparse.ArgumentParser:
    """Return the default (conversion) argument parser."""
    return _create_convert_parser()


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--version", action="version", version=f"pycartosym {__version__}"
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress progress output; only warnings and errors are shown",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=None,
        help="Set the logging level (default: WARNING; overridden to WARNING "
        "by --quiet)",
    )


def _create_convert_parser() -> argparse.ArgumentParser:
    """Parser for the default conversion mode: cartosym <input> -o <output>."""
    parser = argparse.ArgumentParser(
        prog="cartosym",
        description="CartoSym transcoder: convert between .cscss, .cs.json, SLD/SE "
        "and MapLibre",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  cartosym examples/0-basic.cscss -o output/0-basic.cs.json\n"
            "  cartosym output/0-basic.cs.json -o output/0-basic.cscss\n"
            "  cartosym examples/0-basic.cscss --print\n"
            "\n"
            "Other commands:\n"
            "  cartosym parse <input>     Parse a CSCSS file\n"
            "  cartosym validate <input>  Validate a .cscss or .cs.json file\n"
        ),
    )
    _add_common_flags(parser)
    parser.add_argument(
        "input_file",
        nargs="?",
        type=Path,
        default=None,
        help="Input file to convert (.cscss, .cs.json, .sld)",
    )
    parser.add_argument(
        "-o", "--output", type=Path, help="Output file (if omitted, use --print)"
    )
    parser.add_argument(
        "--validate", action="store_true", help="Validate the output after conversion"
    )
    parser.add_argument(
        "--print", action="store_true", help="Print the result to stdout"
    )
    parser.add_argument(
        "--force", action="store_true", help="Overwrite the output file if it exists"
    )
    parser.add_argument(
        "--from-format",
        choices=_ALL_FORMATS,
        help="Source format (auto-detected from the file extension if omitted; "
        "a plain '.sld' auto-detects SLD 1.0.0 vs 1.1.0)",
    )
    parser.add_argument(
        "--to-format",
        choices=_ALL_FORMATS,
        help="Target format (auto-detected from the file extension if omitted; "
        "'sld' writes 1.1.0/SE, 'sld:1.0.0' pure OGC SLD 1.0.0, "
        "'sld:geoserver' SLD 1.0.0 with GeoServer <VendorOption>s)",
    )
    return parser


def _create_subcommand_parser() -> argparse.ArgumentParser:
    """Parser for named subcommands: cartosym parse|validate <input>."""
    parser = argparse.ArgumentParser(prog="cartosym", description="CartoSym transcoder")
    _add_common_flags(parser)

    subparsers = parser.add_subparsers(dest="command")

    parse_parser = subparsers.add_parser(
        "parse", help="Parse a CSCSS file and display info"
    )
    parse_parser.add_argument(
        "input_file", type=Path, help="Input CartoSym CSS (.cscss) file to parse"
    )
    parse_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    parse_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )

    validate_parser = subparsers.add_parser(
        "validate", help="Validate a .cscss or .cs.json file"
    )
    validate_parser.add_argument(
        "input_file", type=Path, help="File to validate (.cscss or .cs.json)"
    )
    validate_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    validate_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    validate_parser.add_argument(
        "--json",
        action="store_true",
        help="Print the result as a single machine-readable JSON object",
    )

    return parser


def _check_cscss_syntax(path: Path) -> list[tuple[int, int, str]]:
    """Return the syntax errors in the CSCSS file at *path* (empty if valid).

    Used by ``validate`` only — ``convert`` no longer pre-checks with a
    throwaway parse of its own; it lets its one real parse raise
    :class:`CartoSymSyntaxError` and reports that instead (a second full
    lex+parse of the same file used to run unconditionally before it).
    """
    try:
        CartoSymParser().parse_file(path)
    except CartoSymSyntaxError as e:
        return e.error_tuples or []
    return []


def _report_syntax_errors(path: Path, errors: list[tuple[int, int, str]]) -> None:
    error(f"{path}: {len(errors)} syntax error(s)")
    source_lines = path.read_text(encoding="utf-8").splitlines()
    sys.stderr.write(format_syntax_errors(errors, source_lines, str(path)) + "\n")


def _validate_csjson_instance(path: Path) -> str | None:
    """Return an error message if the CS-JSON file at *path* is invalid, else None."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return f"not valid JSON: {e}"
    schema_path = Path(__file__).parent / "schemas" / "CartoSym-JSON.schema.json"
    with open(schema_path, encoding="utf-8") as sf:
        schema = json.load(sf)
    try:
        jsonschema_validate(instance=data, schema=schema)
    except ValidationError as e:
        return f"does not match the CartoSym-JSON schema: {e.message}"
    return None


def parse_command(args) -> int:
    """Handle the ``parse`` command."""
    parser = CartoSymParser(log_level=args.log_level or "WARNING")
    if not args.input_file.exists():
        error(f"file not found: {args.input_file}")
        return ExitCode.NOT_FOUND
    stylesheet = parser.parse_file(args.input_file)
    n_rules = len(stylesheet.styling_rules.rules) if stylesheet.styling_rules else 0
    n_meta = len(stylesheet.metadata)
    success(f"parsed {args.input_file}")
    info(f"  {n_meta} metadata entr(y/ies), {n_rules} styling rule(s)")
    return ExitCode.OK


def detect_format(path: Path) -> str | None:
    """Detect the format of a file from its extension."""
    name = path.name.lower()
    if name.endswith(".cscss"):
        return "cscss"
    if name.endswith(".cs.json"):
        return "csjson"
    if name.endswith(".sld") or name.endswith(".se"):
        return "sld"
    if name.endswith(".maplibre.json"):
        return "maplibre"
    return None


def _write_output(output: Path, text: str) -> None:
    output.write_text(text, encoding="utf-8")


def convert_command(args) -> int:
    """Handle the default conversion path, with format auto-detection."""
    converter = Converter()
    input_path: Path = args.input_file

    if not input_path.exists():
        error(f"file not found: {input_path}")
        return ExitCode.NOT_FOUND

    if not args.output and not args.print:
        error("no destination: pass -o/--output or --print")
        return ExitCode.USAGE

    from_format = args.from_format or detect_format(input_path)
    to_format = args.to_format or (detect_format(args.output) if args.output else None)
    if from_format and not to_format and args.print and not args.output:
        # `cartosym foo.cscss --print` — round-trip to the other text encoding.
        to_format = _PRINT_DEFAULT_TARGET.get(from_format)
    if not from_format or not to_format:
        error("could not determine the conversion")
        hint(
            f"from={from_format or '?'} to={to_format or '?'} — "
            "pass --from-format / --to-format or use recognised extensions"
        )
        return ExitCode.UNSUPPORTED

    # CSCSS syntax is validated by the real parse inside _run_conversion
    # itself (caught below) rather than a separate throwaway parse here —
    # a cscss source used to get lexed and parsed twice unconditionally.
    if from_format == "csjson":
        problem = _validate_csjson_instance(input_path)
        if problem is not None:
            error(f"{input_path}: {problem}")
            return ExitCode.INPUT_INVALID

    try:
        output_str = _run_conversion(converter, args, from_format, to_format)
    except CartoSymSyntaxError as e:
        _report_syntax_errors(input_path, e.error_tuples or [])
        return ExitCode.INPUT_INVALID
    except NotImplementedError as e:
        error(f"{from_format} → {to_format}: {e}")
        return ExitCode.TRANSCODE_GAP
    except _UnsupportedConversion:
        error(f"conversion from {from_format} to {to_format} is not supported yet")
        return ExitCode.UNSUPPORTED
    except FileNotFoundError as e:
        error(f"file not found: {e.filename or e}")
        return ExitCode.NOT_FOUND
    except Exception as e:  # noqa: BLE001 - reported to the user
        error(f"conversion failed: {e}")
        return ExitCode.INPUT_INVALID

    if args.print:
        sys.stdout.write(output_str if output_str.endswith("\n") else output_str + "\n")
    if args.output:
        if args.output.exists() and not args.force:
            error(f"{args.output} exists (use --force to overwrite)")
            return ExitCode.USAGE
        _write_output(args.output, output_str)
        if args.validate and to_format == "csjson":
            problem = _validate_csjson_instance(args.output)
            if problem is not None:
                error(f"output {args.output}: {problem}")
                return ExitCode.INPUT_INVALID
        success(f"{input_path} → {args.output}")
    return ExitCode.OK


class _UnsupportedConversion(Exception):
    """No codec path exists for the requested (from, to) formats."""


def _run_conversion(
    converter: Converter, args, from_format: str, to_format: str
) -> str:
    """Run the conversion and return the serialised output as a string."""
    if from_format == "cscss" and to_format == "csjson":
        result = converter.cscss_to_csjson(args.input_file)
        return json.dumps(result, indent=2, ensure_ascii=False)
    if from_format == "csjson" and to_format == "cscss":
        return converter.csjson_to_cscss(args.input_file)
    if from_format == "csjson" and to_format == "csjson":
        style = converter.csjson_to_style(args.input_file)
        return json.dumps(style.to_dict(), indent=2, ensure_ascii=False)

    from .codecs import get_codec

    src_codec = get_codec(from_format)
    dst_codec = get_codec(to_format)
    if not (src_codec and dst_codec and src_codec.reader and dst_codec.writer):
        raise _UnsupportedConversion
    style = src_codec.read(args.input_file)
    result = dst_codec.write(style)
    if isinstance(result, dict):
        return json.dumps(result, indent=2, ensure_ascii=False)
    return str(result)


def _print_json(data: dict) -> None:
    sys.stdout.write(json.dumps(data) + "\n")


def validate_command(args) -> int:
    """Validate a CSCSS or CS-JSON file."""
    input_path: Path = args.input_file
    as_json: bool = args.json
    path_str = str(input_path)

    if not input_path.exists():
        if as_json:
            _print_json({"valid": False, "file": path_str, "error": "file not found"})
        else:
            error(f"file not found: {input_path}")
        return ExitCode.NOT_FOUND

    name = input_path.name.lower()
    if name.endswith(".cscss"):
        errors = _check_cscss_syntax(input_path)
        if errors:
            if as_json:
                _print_json(
                    {
                        "valid": False,
                        "file": path_str,
                        "format": "cscss",
                        "errors": [
                            {"line": line, "column": col + 1, "message": msg}
                            for line, col, msg in errors
                        ],
                    }
                )
            else:
                _report_syntax_errors(input_path, errors)
            return ExitCode.INPUT_INVALID
        if as_json:
            _print_json({"valid": True, "file": path_str, "format": "cscss"})
        else:
            success(f"valid CSCSS: {input_path}")
        return ExitCode.OK
    if name.endswith(".cs.json"):
        problem = _validate_csjson_instance(input_path)
        if problem is not None:
            if as_json:
                _print_json(
                    {
                        "valid": False,
                        "file": path_str,
                        "format": "csjson",
                        "errors": [{"message": problem}],
                    }
                )
            else:
                error(f"{input_path}: {problem}")
            return ExitCode.INPUT_INVALID
        if as_json:
            _print_json({"valid": True, "file": path_str, "format": "csjson"})
        else:
            success(f"valid CartoSym-JSON: {input_path}")
        return ExitCode.OK

    if as_json:
        _print_json(
            {
                "valid": False,
                "file": path_str,
                "error": "unrecognised extension for validation",
            }
        )
    else:
        error(f"unrecognised extension for validation: {input_path}")
        hint("expected a .cscss or .cs.json file")
    return ExitCode.USAGE


if __name__ == "__main__":
    sys.exit(main())
