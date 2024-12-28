import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import qrcode
from PIL import Image
import io
import tempfile
import os

def create_qr_code(uuid):
    """Create a QR code for the given UUID"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(uuid)
    qr.make(fit=True)
    
    # Create PIL image
    qr_image = qr.make_image(fill_color="black", back_color="white")
    return qr_image

def create_id_cards_pdf(json_data, output_filename, columns=3):
    """Create a PDF with QR codes, UUIDs, and names"""
    # Initialize PDF
    c = canvas.Canvas(output_filename, pagesize=letter)
    width, height = letter
    
    # Calculate layout
    margin = 0.5 * inch
    usable_width = width - (2 * margin)
    column_width = usable_width / columns
    qr_size = column_width * 0.8  # QR code takes 80% of column width
    
    # Start positions
    x = margin
    y = height - margin - qr_size
    
    # Create temporary directory for QR codes
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Load JSON data
        with open(json_data, 'r') as f:
            data = json.load(f)


        # Sort the entries in 'data' by each user's display name
        data = dict(sorted(data.items(), key=lambda x: x[1]['display_name']))
        
        for i, (uuid, info) in enumerate(data.items()):
            # If we need to start a new page
            if y < margin:
                c.showPage()
                y = height - margin - qr_size
                x = margin
            
            # Create QR code and save it to a temporary file
            qr_image = create_qr_code(uuid)
            temp_path = os.path.join(temp_dir, f'qr_{i}.png')
            qr_image.save(temp_path, format='PNG')
            
            # Draw the image
            c.drawImage(temp_path, x + (column_width - qr_size)/2, y, width=qr_size, height=qr_size)
            
            # Add UUID text
            c.setFont("Helvetica", 8)
            text_width = c.stringWidth(uuid, "Helvetica", 8)
            c.drawString(x + (column_width - text_width)/2, y - 15, uuid)
            
            # Add name
            c.setFont("Helvetica", 12)
            name_width = c.stringWidth(info['display_name'], "Helvetica", 12)
            c.drawString(x + (column_width - name_width)/2, y - 30, info['display_name'])
            
            # Move to next position
            x += column_width
            
            # If we've reached the end of the row, move to next row
            if (i + 1) % columns == 0:
                x = margin
                y -= (qr_size + 50)  # 50 points for text and spacing
            
            # Clean up temporary file
            os.remove(temp_path)
        
        # Save the PDF
        c.save()
    
    finally:
        # Clean up temporary directory
        try:
            os.rmdir(temp_dir)
        except:
            pass

if __name__ == "__main__":
    # Usage
    input_file = "badges.json"
    output_file = "id_cards.pdf"
    create_id_cards_pdf(input_file, output_file, columns=3)
