from pdfminer.high_level import extract_text
from pdf2image import convert_from_path
import zxing


def extract_pdf_content(file_path):
    """extract content from the PDF using pdfminer"""
    return extract_text(file_path)


def content_to_dict(content):
    """transform the extracted content into a dictionary"""
    lines = content.split('\n')
    info_dict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" in line:
            key, value = line.split(":", 1)
            if not value.strip() and i + 1 < len(lines) and not lines[i + 1].strip() and i + 2 < len(lines):
                # if the current value is empty, and the next line is also empty,
                # then we consider the value to be in the line after that
                value = lines[i + 2]
                i += 2
            info_dict[key.strip()] = value.strip()
        i += 1
    return info_dict


def extract_keys_from_reference(reference_path):
    """extract keys from a reference PDF"""
    content = extract_pdf_content(reference_path)
    reference_dict = content_to_dict(content)
    return list(reference_dict.keys())


def extract_barcodes(pdf_path):
    """find barcodes and extract them from pdf files"""
    # Convert the PDF into a list of images with higher DPI
    images = convert_from_path(pdf_path, dpi=300)

    # Initialize ZXing barcode reader
    reader = zxing.BarCodeReader()

    all_barcodes = []
    barcode_positions = []

    for image in images:
        # Convert image to grayscale
        image_gray = image.convert("L")
        width, height = image.size
        whitespace_bands = []

        # Find bands of whitespace
        for y in range(height):
            if sum(image_gray.getpixel((x, y)) for x in range(width)) / width > 250:  # Threshold for whitespace
                whitespace_bands.append(y)

        # Extract potential barcode regions
        potential_barcodes = []
        for i in range(len(whitespace_bands) - 1):
            if whitespace_bands[i + 1] - whitespace_bands[i] > 30:  # Height threshold for barcode area
                top = whitespace_bands[i]
                bottom = whitespace_bands[i + 1]
                potential_barcodes.append(image.crop((0, top, width, bottom)))
                barcode_positions.append((0, top, width, bottom))

        # Decode barcodes from each potential region
        for region in potential_barcodes:
            barcode = reader.decode(region)
            if barcode:
                all_barcodes.append(barcode.parsed)

    return all_barcodes, barcode_positions


def validate_pdf_structure(info_dict, expected_keys, barcode_positions, ref_barcode_positions):
    """validate the content against the expected structure"""
    missing_keys = [key for key in expected_keys if key not in info_dict]
    if missing_keys:
        return False, f"Missing keys: {', '.join(missing_keys)}"
    if list(info_dict.keys()) != expected_keys:
        return False, "Key ordering is wrong"

    # Check the number of barcodes in the new file against the reference
    barcode_count = len(barcode_positions)
    ref_barcode_count = len(ref_barcode_positions)
    if barcode_count != ref_barcode_count:
        return False, f"Expected {ref_barcode_count} barcodes, found {barcode_count}"

    # Check if barcodes are in the same position
    barcode_data_ref, barcode_positions_ref = ref_barcode_positions
    barcode_data, barcode_positions = barcode_positions
    # Threshold can be adjusted on how precise you need this to be
    threshold = 10
    for index in range(ref_barcode_count):
        ref_pos = barcode_positions_ref[index]
        new_pos = barcode_positions[index]

        if abs(ref_pos[0] - new_pos[0]) > threshold or abs(ref_pos[1] - new_pos[1]) > threshold:
            return False, f"Barcode at position {index + 1} has moved"

    return True, "PDF structure is valid"


def main(file_path, reference_path):
    expected_keys = extract_keys_from_reference(reference_path)
    expected_barcodes = extract_barcodes(reference_path)
    barcodes = extract_barcodes(file_path)
    content = extract_pdf_content(file_path)
    info_dict = content_to_dict(content)
    is_valid, message = validate_pdf_structure(info_dict, expected_keys, barcodes, expected_barcodes)

    if is_valid:
        print("The PDF structure is valid.")
    else:
        print(message)
    return info_dict, barcodes


file = "path_to_file"
reference = "path_to_file"
result = main(file, reference)

keys, barcodes = result

print("Keys:", keys)
print("Barcodes:", barcodes[0])
