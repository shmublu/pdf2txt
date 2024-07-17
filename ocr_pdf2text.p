import argparse
import base64
import os
from pdf2image import convert_from_path
from openai import OpenAI
from PIL import Image

client = OpenAI(api_key=os.environ["SHAPIRO_TOK"])

def process_markdown_into_txt(markdown):
    markdown = markdown.replace("```markdown\n", "")
    markdown = markdown.replace("```", "")
    return markdown

def save_output_to_file(filename, output, mode='a'):
    with open(filename, mode) as file:
        file.write(output)

def compress_image(image_path):
    with Image.open(image_path) as image:
        # Check if the image size exceeds 20MB
        if os.path.getsize(image_path) > 20 * 1024 * 1024:
            # Compress the image
            image.save(image_path, "JPEG", optimize=True, quality=85)

def convert_pdf_to_markdown(pdf_path, give_next_page=False, max_pages=100):
    pages = convert_from_path(pdf_path)
    prev_text = ""
    model_role = """
        You are an intelligent, consistent AI assistant that converts images of PDF pages to Markdown format.
        You only convert the current page, but use the previous page text for context on how this page should be formatted.
        Begin with a new line if the starting text should be on a new line from the previous output, but not otherwise.
        Use markdown for ALL headers and stylization (and make sure the hierarchy is correct). Preserve italics, bold, new lines, and bullet points.
        Your output should be polished and ready for publication--- do not include any fragmented sentences, and ensure that the text is coherent and well-structured.
        Merge all partial words and sentences into the correct format, including if the last word of the previous page is a partial word (ending with a "-").
        A reader who directly appends your output to the previous page text should not be able to tell where you started writing.
        Add a new line after EVERY header.
        Do NOT repeat anything from the previous page.
        """
    for i in range(min(len(pages), max_pages)):
        if not give_next_page or i == len(pages) - 1:
            page_image_path = f"page_{i+1}.jpg"
            pages[i].save(page_image_path, "JPEG")
            compress_image(page_image_path)  # Compress the image if it exceeds 20MB
            with open(page_image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": model_role},
                    {"role": "user", "content": f"Here is the text from the previous page:\n\n{prev_text}\n\nPlease transcribe only the current page, and continue on from the previous text. Output your text so it can be seamlessly appended to the previous text."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Current page image:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]}
                ]
            )
            prev_text = process_markdown_into_txt(response.choices[0].message.content)
            save_output_to_file("output_ocr_text.md", prev_text, mode='a')
            os.remove(page_image_path)
        else:
            next_page_path = f"page_{i+2}.jpg" if i < len(pages) - 1 else None
            page_image_path = f"page_{i+1}.jpg"
            pages[i].save(page_image_path, "JPEG")
            compress_image(page_image_path)  # Compress the image if it exceeds 20MB
            pages[i+1].save(next_page_path, "JPEG")
            compress_image(next_page_path)  # Compress the next page image if it exceeds 20MB
            with open(page_image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            with open(next_page_path, "rb") as image_file:
                base64_next_page = base64.b64encode(image_file.read()).decode('utf-8')
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": model_role + "\n You are also given the next page image to provide context for the current page, but do not transcribe it. Use it for heading hierarchy, formatting, and context."},
                    {"role": "user", "content": f"Here is the text from the previous page:\n\n{prev_text}\n\nPlease transcribe only the current page, and continue on from the previous text. Do not include content from the next page. Output your text so it can be seamlessly appended to the previous text."},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Current page image:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]},
                    {"role": "user", "content": [
                        {"type": "text", "text": "Next page image(do not convert this to text):"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_next_page}"}}
                    ]}
                ]
            )
            prev_text = process_markdown_into_txt(response.choices[0].message.content)
            save_output_to_file("output_ocr_text.md", prev_text, mode='a')
            os.remove(page_image_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PDF to Markdown")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--max-pages", type=int, default=100, help="Maximum number of pages to process (default: 100)")
    parser.add_argument("--has-next-page-context", action="store_true", help="Use next page context for formatting")
    args = parser.parse_args()
    convert_pdf_to_markdown(args.pdf_path, give_next_page=args.has_next_page_context, max_pages=args.max_pages)