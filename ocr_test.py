
from PIL import Image, ImageDraw, ImageFont
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

image = Image.new("RGB", (1200, 250), "white")
draw = ImageDraw.Draw(image)

font = ImageFont.truetype("arial.ttf", 48)
draw.text(
    (30, 70),
    "BUILDGUARD AI - OCR TEST 12345",
    font=font,
    fill="black"
)

result = pytesseract.image_to_string(
    image,
    config="--psm 7"
)

print("OCR RESULT:")
print(repr(result))

if "BUILDGUARD" in result and "12345" in result:
    print("SUCCESS: OCR is working!")
else:
    print("OCR ran, but recognition needs improvement.")
