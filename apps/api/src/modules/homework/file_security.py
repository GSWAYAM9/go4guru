"""Upload security, magic-byte sniffing, EXIF stripping, and PDF inspection for Homework AI."""

from __future__ import annotations

import hashlib
import re
import zlib
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

SupportedFormat = Literal["jpeg", "png", "webp", "pdf"]

ALLOWED_MIME_BY_FORMAT: dict[SupportedFormat, str] = {
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "pdf": "application/pdf",
}

ALLOWED_EXT_BY_FORMAT: dict[SupportedFormat, str] = {
    "jpeg": "jpg",
    "png": "png",
    "webp": "webp",
    "pdf": "pdf",
}

# Dangerous PDF active-content tokens rejected before storage/OCR
_PDF_DANGEROUS_PATTERNS: tuple[tuple[bytes, str], ...] = (
    (b"/JavaScript", "Embedded PDF JavaScript is not permitted."),
    (b"/JS", "Embedded PDF JS action is not permitted."),
    (b"/OpenAction", "PDF OpenAction auto-execution triggers are not permitted."),
    (b"/Launch", "PDF Launch actions are not permitted."),
    (b"/EmbeddedFile", "PDF embedded file attachments are not permitted."),
    (b"/RichMedia", "PDF RichMedia payloads are not permitted."),
)

_FILENAME_SAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")
_PDF_PAGE_RE = re.compile(rb"/Type\s*/Page(?![A-Za-z])")
_PDF_LITERAL_STR_RE = re.compile(rb"\(([^()\\]*(?:\\.[^()\\]*)*)\)")


class FileValidationError(ValueError):
    """Structured file validation error raised before persisting untrusted uploads."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class ValidatedHomeworkFile:
    """Sanitized, verified upload ready for private immutable storage and OCR."""

    original_filename: str
    sanitized_bytes: bytes
    detected_format: SupportedFormat
    mime_type: str
    size_bytes: int
    sha256: str
    exif_stripped: bool
    pdf_page_count: int | None
    scan_status: Literal["clean"]
    warnings: tuple[str, ...]


def sanitize_display_filename(filename: str | None, *, fallback_index: int) -> str:
    """Strip path segments and unsafe characters from user-supplied filenames."""
    if not filename:
        return f"page_{fallback_index}.bin"
    base = filename.replace("\\", "/").split("/")[-1].strip()
    cleaned = _FILENAME_SAFE_RE.sub("_", base).strip("._")
    if not cleaned:
        return f"page_{fallback_index}.bin"
    return cleaned[:180]


def detect_magic_format(data: bytes) -> SupportedFormat | None:
    """Detect real binary format purely from magic-byte headers (never trust extensions)."""
    if len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:5] == b"%PDF-":
        return "pdf"
    return None


def strip_jpeg_metadata(data: bytes) -> tuple[bytes, bool]:
    """Remove EXIF (APP1), IPTC (APP13), and COM segments from JPEG without external native libs."""
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return data, False

    out = bytearray(b"\xff\xd8")
    i = 2
    stripped = False
    n = len(data)

    while i < n:
        if data[i] != 0xFF:
            # Unexpected non-marker data: append remainder intact
            out.extend(data[i:])
            break
        while i < n and data[i] == 0xFF:
            i += 1
        if i >= n:
            break
        marker = data[i]
        i += 1

        # Start of Scan (SOS) or End of Image (EOI): copy rest verbatim
        if marker == 0xDA:  # SOS
            out.extend(b"\xff\xda")
            out.extend(data[i:])
            break
        if marker == 0xD9:  # EOI
            out.extend(b"\xff\xd9")
            break
        # Standalone restart/TEM markers have no length field
        if 0xD0 <= marker <= 0xD8 or marker == 0x01:
            out.extend(bytes((0xFF, marker)))
            continue

        if i + 2 > n:
            break
        seg_len = int.from_bytes(data[i : i + 2], "big")
        if seg_len < 2 or i + seg_len > n:
            raise FileValidationError(
                "MALFORMED_JPEG",
                "Uploaded JPEG image has a corrupted segment structure.",
            )

        # Strip APP1 (0xE1 EXIF/XMP), APP13 (0xED IPTC/Photoshop), COM (0xFE comments)
        if marker in (0xE1, 0xED, 0xFE):
            stripped = True
        else:
            out.extend(bytes((0xFF, marker)))
            out.extend(data[i : i + seg_len])
        i += seg_len

    return bytes(out), stripped


def strip_png_metadata(data: bytes) -> tuple[bytes, bool]:
    """Remove ancillary PNG text and EXIF chunks (eXIf, tEXt, zTXt, iTXt, tIME)."""
    if len(data) < 16 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return data, False

    out = bytearray(data[:8])
    i = 8
    n = len(data)
    stripped = False
    disallowed_chunks = {b"eXIf", b"tEXt", b"zTXt", b"iTXt", b"tIME"}

    while i + 12 <= n:
        chunk_len = int.from_bytes(data[i : i + 4], "big")
        chunk_type = data[i + 4 : i + 8]
        total_chunk = 12 + chunk_len
        if i + total_chunk > n:
            raise FileValidationError(
                "MALFORMED_PNG",
                "Uploaded PNG image has a truncated or corrupted chunk.",
            )
        if chunk_type in disallowed_chunks:
            stripped = True
        else:
            out.extend(data[i : i + total_chunk])
        i += total_chunk
        if chunk_type == b"IEND":
            break

    return bytes(out), stripped


def strip_webp_metadata(data: bytes) -> tuple[bytes, bool]:
    """Strip EXIF and XMP RIFF subchunks from extended WebP containers when present."""
    if len(data) < 16 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return data, False

    i = 12
    n = len(data)
    kept_chunks = bytearray()
    stripped = False

    while i + 8 <= n:
        fourcc = data[i : i + 4]
        chunk_size = int.from_bytes(data[i + 4 : i + 8], "little")
        padded = chunk_size + (chunk_size % 2)
        if i + 8 + padded > n:
            raise FileValidationError(
                "MALFORMED_WEBP",
                "Uploaded WebP image has a corrupted RIFF chunk.",
            )
        if fourcc in (b"EXIF", b"XMP "):
            stripped = True
        else:
            kept_chunks.extend(data[i : i + 8 + padded])
        i += 8 + padded

    if not stripped:
        return data, False

    riff_size = 4 + len(kept_chunks)
    return b"RIFF" + riff_size.to_bytes(4, "little") + b"WEBP" + bytes(kept_chunks), True


def inspect_pdf_security_and_pages(data: bytes, *, max_pages: int) -> int:
    """Inspect PDF binary for active-script exploits and count pages safely."""
    if b"%%EOF" not in data[-2048:] and b"endobj" not in data:
        raise FileValidationError(
            "MALFORMED_PDF",
            "Uploaded PDF appears truncated or corrupted.",
        )

    for pattern, err_msg in _PDF_DANGEROUS_PATTERNS:
        if re.search(re.escape(pattern) + rb"(?![A-Za-z0-9])", data):
            raise FileValidationError("UNSAFE_PDF_PAYLOAD", err_msg)

    pages = len(_PDF_PAGE_RE.findall(data))
    page_count = max(1, pages)
    if page_count > max_pages:
        raise FileValidationError(
            "PDF_PAGE_LIMIT_EXCEEDED",
            f"PDF contains {page_count} pages, exceeding the maximum allowed {max_pages} pages.",
        )
    return page_count


def _unescape_pdf_literal(raw: bytes) -> str:
    text = raw.decode("latin-1", errors="ignore")
    text = (
        text.replace(r"\(", "(")
        .replace(r"\)", ")")
        .replace(r"\\", "\\")
        .replace(r"\n", "\n")
        .replace(r"\r", "\r")
        .replace(r"\t", "\t")
    )
    return text


def extract_pdf_embedded_text(data: bytes) -> str:
    """Extract readable text from uncompressed or FlateDecode PDF content streams safely."""
    extracted_parts: list[str] = []

    def _collect_from_chunk(chunk: bytes) -> None:
        for bt_match in re.finditer(rb"BT(.*?)ET", chunk, flags=re.DOTALL):
            block = bt_match.group(1)
            for lit in _PDF_LITERAL_STR_RE.findall(block):
                decoded = _unescape_pdf_literal(lit).strip()
                if decoded:
                    extracted_parts.append(decoded)

    _collect_from_chunk(data)

    # Also attempt safe FlateDecode stream decompression (bounded to avoid zip-bomb expansion)
    max_decompressed_total = 2 * 1024 * 1024
    decompressed_total = 0
    for stream_match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, flags=re.DOTALL):
        raw_stream = stream_match.group(1)
        if not raw_stream or decompressed_total >= max_decompressed_total:
            continue
        try:
            decomp = zlib.decompressobj()
            out = decomp.decompress(raw_stream, 256 * 1024)
            decompressed_total += len(out)
            _collect_from_chunk(out)
        except zlib.error:
            continue

    lines = [line.strip() for line in extracted_parts if line.strip()]
    return "\n".join(lines)


def validate_and_sanitize_upload(
    *,
    filename: str | None,
    raw_bytes: bytes,
    declared_content_type: str | None,
    max_file_bytes: int,
    max_pdf_pages: int,
    page_index: int,
) -> ValidatedHomeworkFile:
    """Validate magic bytes, enforce caps, block active payloads, and strip image EXIF."""
    safe_name = sanitize_display_filename(filename, fallback_index=page_index)
    if not raw_bytes:
        raise FileValidationError(
            "EMPTY_FILE",
            f"File '{safe_name}' is empty (0 bytes).",
        )
    if len(raw_bytes) > max_file_bytes:
        limit_mb = round(max_file_bytes / (1024 * 1024), 1)
        raise FileValidationError(
            "FILE_TOO_LARGE",
            f"File '{safe_name}' exceeds the {limit_mb} MB per-file size limit.",
        )

    # Block SVG/HTML disguised as images early
    head_lower = raw_bytes[:512].lstrip().lower()
    if head_lower.startswith((b"<svg", b"<?xml", b"<!doctype", b"<html", b"<script")):
        raise FileValidationError(
            "UNSAFE_FILE_TYPE",
            f"File '{safe_name}' contains active markup/SVG and is rejected for security.",
        )

    detected = detect_magic_format(raw_bytes)
    if detected is None:
        raise FileValidationError(
            "UNSUPPORTED_FILE_FORMAT",
            f"File '{safe_name}' is not a valid JPEG, PNG, WebP image, or PDF document.",
        )

    warnings: list[str] = []
    canonical_mime = ALLOWED_MIME_BY_FORMAT[detected]
    if declared_content_type:
        norm_decl = declared_content_type.split(";")[0].strip().lower()
        if norm_decl and norm_decl != canonical_mime and norm_decl != "application/octet-stream":
            warnings.append(
                f"Declared MIME '{norm_decl}' differed from verified header '{canonical_mime}'."
            )

    exif_stripped = False
    pdf_pages: int | None = None
    sanitized = raw_bytes

    if detected == "jpeg":
        sanitized, exif_stripped = strip_jpeg_metadata(raw_bytes)
    elif detected == "png":
        sanitized, exif_stripped = strip_png_metadata(raw_bytes)
    elif detected == "webp":
        sanitized, exif_stripped = strip_webp_metadata(raw_bytes)
    elif detected == "pdf":
        pdf_pages = inspect_pdf_security_and_pages(raw_bytes, max_pages=max_pdf_pages)

    sha256 = hashlib.sha256(sanitized).hexdigest()
    return ValidatedHomeworkFile(
        original_filename=safe_name,
        sanitized_bytes=sanitized,
        detected_format=detected,
        mime_type=canonical_mime,
        size_bytes=len(sanitized),
        sha256=sha256,
        exif_stripped=exif_stripped,
        pdf_page_count=pdf_pages,
        scan_status="clean",
        warnings=tuple(warnings),
    )


def build_private_homework_storage_key(
    *,
    student_id: UUID,
    submission_id: UUID,
    page_no: int,
    sha256: str,
    detected_format: SupportedFormat,
) -> str:
    """Build deterministic server-only storage key (never incorporates user filenames)."""
    ext = ALLOWED_EXT_BY_FORMAT[detected_format]
    return f"homework/{student_id}/{submission_id}/p{page_no:02d}_{sha256[:16]}.{ext}"
