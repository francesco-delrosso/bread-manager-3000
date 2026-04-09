"""
Genera il QR code per la pagina ordini.
Uso: python generate_qr.py  [URL opzionale]
Default URL: http://ordini.piccolocamping.com
"""
import sys, qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer

URL = sys.argv[1] if len(sys.argv) > 1 else "http://ordini.piccolocamping.com"

qr = qrcode.QRCode(
    version=None,
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=12,
    border=2,
)
qr.add_data(URL)
qr.make(fit=True)

img = qr.make_image(
    image_factory=StyledPilImage,
    module_drawer=RoundedModuleDrawer(),
    fill_color="#1B5E3B",
    back_color="white"
)
img.save("qrcode_ordini.png")
print(f"QR code salvato: qrcode_ordini.png  →  {URL}")
