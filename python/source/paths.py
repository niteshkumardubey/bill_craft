import os

# Base directory (this file's parent directory)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Font path
FONT_PATH = os.path.abspath(
    os.path.join(BASE_DIR, "..", "Fonts", "dejavu-fonts-ttf-2.37", "ttf", "DejaVuSans.ttf")
)

# Database path
DATABASE_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "Database"))

# Invoice folder path
INVOICE_PATH = os.path.abspath(os.path.join(DATABASE_PATH, "Sell Invoice"))

# Ensure all important directories exist
for path in [os.path.dirname(FONT_PATH), DATABASE_PATH, INVOICE_PATH]:
    if not os.path.exists(path):
        print(f"Making directory: {path}")
        os.makedirs(path, exist_ok=True)
