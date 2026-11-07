
from io import BytesIO
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from pypdf import PdfReader
from pypdf.errors import PdfReadError

import pymupdf
import pytesseract
from PIL import Image


# --------------------------------------------------
# 1. PROJECT SETTINGS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_PDF_PAGES = 50
MAX_EXTRACTED_CHARS = 100_000
MAX_OCR_PAGES = 10

OCR_DPI = 200

TESSERACT_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Configure Tesseract once when the application starts.
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# --------------------------------------------------
# 2. CREATE FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="BuildGuard AI",
    description="Preliminary construction blueprint text extraction",
    version="0.3.0",
)

# Serve CSS and JavaScript files.
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static",
)


# --------------------------------------------------
# 3. HOME PAGE
# --------------------------------------------------

@app.get("/")
async def home():
    index_file = STATIC_DIR / "index.html"

    if not index_file.is_file():
        raise HTTPException(
            status_code=500,
            detail="Website file static/index.html was not found.",
        )

    return FileResponse(str(index_file))


# --------------------------------------------------
# 4. HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "application": "BuildGuard AI",
        "version": "0.3.0",
    }


# --------------------------------------------------
# 5. API INFORMATION
# --------------------------------------------------

@app.get("/api")
async def api_info():
    return {
        "application": "BuildGuard AI",
        "version": "0.3.0",
        "upload_endpoint": "/api/upload",
        "supported_file": "PDF",
        "max_file_size_mb": 10,
        "ocr_enabled": True,
    }


# --------------------------------------------------
# 6. OCR HELPER FUNCTION
# --------------------------------------------------

def extract_scanned_page_text(
    pdf_bytes: bytes,
    page_number: int,
) -> str:
    """Render one PDF page and extract text using local OCR."""

    # Set the path again to avoid configuration issues.
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

    with pymupdf.open(
        stream=pdf_bytes,
        filetype="pdf",
    ) as document:

        page = document[page_number]

        scale = OCR_DPI / 72

        pixmap = page.get_pixmap(
            matrix=pymupdf.Matrix(scale, scale),
            alpha=False,
        )

        image_bytes = pixmap.tobytes("png")

    with Image.open(BytesIO(image_bytes)) as image:
        text = pytesseract.image_to_string(
            image,
            lang="eng",
            config="--psm 3",
        )

    return text.strip()


# --------------------------------------------------
# 7. PDF UPLOAD AND TEXT EXTRACTION
# --------------------------------------------------

@app.post("/api/upload")
async def upload_blueprint(
    file: UploadFile = File(...),
):
    try:
        # Check the uploaded filename.
        filename = file.filename or ""

        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported.",
            )

        # Read one extra byte to detect oversized files.
        contents = await file.read(MAX_FILE_SIZE + 1)

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="File exceeds the 10 MB size limit.",
            )

        # Basic PDF signature check.
        if not contents.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=400,
                detail="Invalid PDF file. Please upload a valid PDF.",
            )

        # Read PDF metadata and validate the document.
        try:
            reader = PdfReader(
                BytesIO(contents),
                strict=False,
            )

            if reader.is_encrypted:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Password-protected PDFs are not supported."
                    ),
                )

            page_count = len(reader.pages)

        except HTTPException:
            raise

        except (PdfReadError, ValueError, OSError):
            raise HTTPException(
                status_code=400,
                detail="The PDF could not be read. Check the file.",
            ) from None

        except Exception as exc:
            print(
                f"PDF reading error: {type(exc).__name__}: {exc}"
            )

            raise HTTPException(
                status_code=400,
                detail="The PDF is damaged or cannot be read.",
            ) from None

        if page_count == 0:
            raise HTTPException(
                status_code=400,
                detail="The PDF contains no pages.",
            )

        if page_count > MAX_PDF_PAGES:
            raise HTTPException(
                status_code=413,
                detail="PDF exceeds the 50-page limit.",
            )

        # Prepare extraction results.
        extracted_parts = []
        characters_extracted = 0

        ocr_pages_processed = 0
        ocr_pages_skipped = 0
        ocr_attempted = False
        ocr_failures = 0

        # Process each page.
        for page_index in range(page_count):
            page_number = page_index + 1

            try:
                page = reader.pages[page_index]
                page_text = page.extract_text() or ""

            except Exception as exc:
                print(
                    f"Text extraction error on page {page_number}: "
                    f"{type(exc).__name__}: {exc}"
                )
                page_text = ""

            page_text = page_text.strip()

            # Use OCR if embedded text is missing.
            if not page_text:
                ocr_attempted = True

                if ocr_pages_processed >= MAX_OCR_PAGES:
                    ocr_pages_skipped += 1
                    continue

                try:
                    page_text = extract_scanned_page_text(
                        contents,
                        page_index,
                    )

                    ocr_pages_processed += 1

                except Exception as exc:
                    ocr_failures += 1
                    ocr_pages_skipped += 1

                    print(
                        f"OCR error on page {page_number}: "
                        f"{type(exc).__name__}: {exc}"
                    )

                    # Continue processing other pages.
                    continue

            if not page_text:
                continue

            # Keep the response within the text limit.
            remaining_chars = (
                MAX_EXTRACTED_CHARS - characters_extracted
            )

            if remaining_chars <= 0:
                break

            page_text = page_text[:remaining_chars]

            extracted_parts.append(
                f"--- Page {page_number} ---\n{page_text}"
            )

            characters_extracted += len(page_text)

        extracted_text = "\n\n".join(extracted_parts)

        # Determine the extraction status.
        if ocr_pages_skipped > 0:
            extraction_status = "partial_ocr"

            message = (
                "Extraction completed with some pages skipped. "
                "Review the results manually."
            )

        elif ocr_pages_processed > 0 and extracted_text:
            extraction_status = "ocr_extracted"

            message = (
                "Text extraction completed using embedded text "
                "and/or OCR."
            )

        elif ocr_attempted and not extracted_text:
            extraction_status = "no_text_found"

            message = (
                "No readable text was extracted. The PDF may be "
                "blank, unclear, or require better image quality."
            )

        elif extracted_text:
            extraction_status = "text_extracted"

            message = "Embedded PDF text extracted successfully."

        else:
            extraction_status = "no_text_found"

            message = "No readable text was found in the PDF."

        if ocr_failures > 0:
            message += (
                f" OCR failed on {ocr_failures} page(s). "
                "Check the server terminal for details."
            )

        return {
            "filename": filename,
            "page_count": page_count,
            "characters_extracted": len(extracted_text),
            "extraction_status": extraction_status,
            "ocr_pages_processed": ocr_pages_processed,
            "ocr_pages_skipped": ocr_pages_skipped,
            "message": message,
            "extracted_text": extracted_text,
        }

    finally:
        await file.close()
