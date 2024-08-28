import qrcode

# Replace with your actual IP address on your local network and the port you're using
ip_address = '10.0.0.172'  # Example IP address
port = '5000'
url = f'http://{ip_address}:{port}/'

# Generate the QR code
qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=10,
    border=4,
)
qr.add_data(url)
qr.make(fit=True)

# Create an image from the QR code
img = qr.make_image(fill='black', back_color='white')

# Save the image in the 'static' directory so it's accessible via Flask
img.save('static/check_in_qr.png')

print("QR code generated and saved as static/check_in_qr.png")
