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


def is_heading(span, average_size, next_span):
    """Determine if a text span is likely a heading based on its formatting and relative size."""
    median_next_size = next_span['size'] if next_span else average_size

    text = span['text']
    size = span['size']
    font_style = span['font'].lower()
    is_bold = "bold" in font_style
    is_all_caps = text.isupper()

    if is_page_number(text):
        return False
    if size > median_next_size * 1.15:
        return True
    if is_all_caps and size >= median_next_size * 1.025:
        return True
    if is_bold and size >= median_next_size* 1.025:
        return True
    return False

def is_sentence_end(text):
    """Check if the last non-whitespace character of the text is a sentence-ending punctuation mark."""
    sentence_end_chars = ['.', '?', '!']
    text = text.strip()
    if text and text[-1] in sentence_end_chars:
        return True
    return False

async def extract_text_by_section(doc):
    """Extract text from the PDF, identifying section headers to separate text by sections."""
    full_text = []
    current_section = []
    font_sizes = []
    prev_formatting = None

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
                for i, line in enumerate(b["lines"]):
                    for j, span in enumerate(line["spans"]):
                        if is_page_number(span['text']):
                            continue
                        text_span = fix_spacing(span['text'])
                        formatting = {
                            'bold': 'bold' in span['font'].lower(),
                            'size': span['size']
                        }
                        next_span = line["spans"][j + 1] if j < len(line["spans"]) - 1 else None
                        if is_heading(span, average_size, next_span):
                            if current_section:
                                full_text.append(" ".join(current_section))
                                full_text.append("\n")  # Add extra newline to separate sections
                                current_section = []
                            full_text.append(text_span.upper() + "\n")  # Append the heading
                            prev_formatting = formatting
                        else:
                            if prev_formatting and formatting == prev_formatting:
                                if current_section and not is_sentence_end(current_section[-1]):
                                    current_section[-1] += " " + text_span
                                else:
                                    current_section.append(text_span)
                            else:
                                if current_section:
                                    full_text.append(" ".join(current_section))
                                    full_text.append("\n")  # Add extra newline to separate sections
                                    current_section = []
                                current_section.append(text_span)
                                prev_formatting = formatting
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

pdf_path = './historypdf.pdf'
output_text_path = './outputtext.txt'
asyncio.run(process_pdf(pdf_path, output_text_path))