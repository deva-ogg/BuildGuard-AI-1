
import pymupdf
import pytesseract
from PIL import Image
from io import BytesIO

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

# Create a sample PDF page with blueprint-style labels
doc = pymupdf.open()
page = doc.new_page(width=595, height=842)
page.insert_text((60, 100), "BUILDING PLAN - OCR TEST", fontsize=20)
page.insert_text((60, 150), "ROOM A: 4000 mm x 3000 mm", fontsize=14)
page.insert_text((60, 190), "WALL THICKNESS: 230 mm", fontsize=14)

# Render the PDF page into an image
pix = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False)
image = Image.open(BytesIO(pix.tobytes("png")))

# OCR reads the rendered page, not the PDF's selectable text
result = pytesseract.image_to_string(image)

print("OCR RESULT:")
print(result)

if "BUILDING PLAN" in result and "4000" in result and "230" in result:
    print("SUCCESS: PDF page OCR is working!")
else:
    print("OCR ran, but some sample text was not recognized.")

doc.close()
