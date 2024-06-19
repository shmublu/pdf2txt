import fitz  # PyMuPDF
import asyncio
import statistics
import re

def fix_spacing(text):
    """Fix issues with spacing and hyphenation in the text."""
    # Replace hyphenation at the end of lines and correct multiple spaces
    text = re.sub(r'-\s+\n', '', text)  # Remove hyphen followed by newline
    text = re.sub(r'\s{2,}', ' ', text)  # Replace multiple spaces with a single space
    return text.strip()

def is_page_number(text):
    """Determine if a text block is likely a page number."""
    return text.strip().isdigit()  # Simple check if the text is just a number

def get_median_font_size(line):
    # Create a list to store the font sizes weighted by the length of the text
    weighted_font_sizes = []

    for span in line:
        font_size = span['size']
        text_length = len(span['text'])
        
        # Add the font size and its weight to the list
        weighted_font_sizes.append((font_size, text_length))
    
    # Sort the list of weighted font sizes based on font size
    weighted_font_sizes.sort()
    
    # Calculate the total length of all text spans
    total_length = sum(text_length for _, text_length in weighted_font_sizes)
    
    # Find the median position
    median_pos = total_length / 2

    cumulative_length = 0
    for font_size, text_length in weighted_font_sizes:
        cumulative_length += text_length
        if cumulative_length >= median_pos:
            return font_size


def is_heading(span, average_size, next_line):
    """Determine if a text span is likely a heading based on its formatting and relative size."""
    median_next_size = get_median_font_size(next_line) if not next_line else average_size
    if median_next_size is None:
        return False

    text = span['text']
    size = span['size']
    font_style = span['font'].lower()
    is_bold = "bold" in font_style
    is_all_caps = text.isupper()

    if is_page_number(text):
        return False
    if size > median_next_size * 1.15:
        return True
    if is_all_caps and size > median_next_size:
        return True
    if is_bold and size > median_next_size:
        return True
    return False
async def extract_text_by_section(doc):
    """Extract text from the PDF, identifying section headers to separate text by sections."""
    full_text = []
    current_section = []
    font_sizes = []

    # First pass to gather average font size and filter out page numbers
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b['type'] == 0:  # Text block
                for line in b["lines"]:
                    for span in line["spans"]:
                        if not is_page_number(span['text']):
                            font_sizes.append(span['size'])

    average_size = statistics.mean(font_sizes) if font_sizes else 12  # Default to 12 if no sizes found

    # Second pass to extract text with section detection, excluding page numbers
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if b['type'] == 0:  # Text block
                for i,line in enumerate(b["lines"]):
                    text_span = " ".join([fix_spacing(span['text']) for span in line["spans"] if not is_page_number(span['text'])])
                    if is_heading(line["spans"][0],average_size, (line["spans"])):
                        if current_section:
                            full_text.append(" ".join(current_section))
                            full_text.append("\n")  # Add extra newline to separate sections
                            current_section = []
                        full_text.append(text_span.upper() + "\n")  # Append the heading
                    else:
                        current_section.append(text_span)
    if current_section:
        full_text.append(" ".join(current_section))
    return full_text

async def process_pdf(pdf_path, output_text_path):
    """Asynchronous PDF processing to extract and categorize text by sections, excluding page numbers."""
    doc = fitz.open(pdf_path)
    extracted_text = await extract_text_by_section(doc)
    
    # Save the categorized text
    with open(output_text_path, 'w') as text_file:
        text_file.write("".join(extracted_text))
    print('Processing complete.')

# Usage
pdf_path = './winata.pdf'
output_text_path = './outputtext.txt'
asyncio.run(process_pdf(pdf_path, output_text_path))
