import qrcode

# Data to encode in the QR code
data = "https://www.example.com"

# Create a QRCode object with default settings
qr = qrcode.QRCode(
    version=1,  # controls the size of the QR code (1 is the smallest)
    error_correction=qrcode.constants.ERROR_CORRECT_L,  # error correction level (L, M, Q, H)
    box_size=10,  # size of each box in the QR code grid
    border=4,  # thickness of the border (in boxes)
)

# Add the data to the QRCode object
qr.add_data(data)
qr.make(fit=True)  # Fit the data within the QR code

# Create an image from the QR code
img = qr.make_image(fill='black', back_color='white')

# Save the image as a PNG file
img.save("qrcode.png")

# Optionally, display the image
img.show()
