from collections import defaultdict
import openparse
import argparse

def is_all_caps(text):
    return text.isupper()

def findNormalCharacteristics(pdf_path, n):
    parser = openparse.DocumentParser()
    parsed_doc = parser.parse(pdf_path)

    style_counts = defaultdict(int)

    for node in parsed_doc.nodes:
        for element in node.elements:
            if isinstance(element, openparse.TextElement):
                for line in element.lines:
                    for span in line.spans:
                        style = (span.is_bold, span.is_italic, is_all_caps(span.text), span.size, line.style)
                        style_counts[style] += 1

    top_styles = sorted(style_counts.items(), key=lambda x: x[1], reverse=True)[:n]

    return top_styles

def findCommonStyles(styles):
    commonStyles = []
    lastStyleFreq = float("inf")
    for style in styles:
        if style[1] < lastStyleFreq * .4:
            commonStyles.append(style[0])
            lastStyleFreq = style[1]
        else:
            break
    return commonStyles

def custom_round(x, base=5):
    return base * round(x/base)

def group_lines(lines, tolerance=3, max_space=40):
    grouped_lines = []
    lines.sort(key=lambda x: (-int(custom_round(x.bbox[1], tolerance * 2)), x.bbox[0]))
    for line in lines:
        last_line_last_word = grouped_lines[-1][-1] if grouped_lines else None
        if not last_line_last_word:
            grouped_lines.append([line])
        elif abs(line.bbox[1] - last_line_last_word.bbox[1]) < tolerance:
            # it is within tolerance of the last line
            if line.bbox[0]  <= (last_line_last_word.bbox[2] + max_space):
                grouped_lines[-1].append(line)
        else:
            grouped_lines.append([line])
    return grouped_lines





def classify_line(line_group, common_styles, median_length):
    print(line_group)
    style_counts = defaultdict(int)
    for line in line_group:
        for span in line.spans:  
            style = (span.is_bold, span.is_italic, is_all_caps(span.text), span.size, line.style)
            style_counts[style] += 1

    most_frequent_style = max(style_counts, key=style_counts.get)
    line_length = sum(len(line.text) for line in line_group)

    if most_frequent_style in common_styles:
        return 'paragraph'
    elif line_length < median_length * 0.6:
        return 'header'
    elif len(style_counts) > 2:
        return 'paragraph'
    else:
        return 'header'
    

def merge_lines(lines):
    merged_text = ' '.join(line.text.strip() for line in lines)
    merged_text = merged_text.replace('- ', '')
    return merged_text

def parse_pdf(pdf_path, output_path, max_pages=100, merge_headers=True):
    parser = openparse.DocumentParser()
    parsed_doc = parser.parse(pdf_path)

    top_styles = findNormalCharacteristics(pdf_path, 20)
    common_styles = findCommonStyles(top_styles)

    page_lines = defaultdict(list)
    line_lengths = []
    for node in parsed_doc.nodes:
        if node.bbox[0].page >= max_pages:
            break
        lines = []
        for element in node.elements:
            if isinstance(element, openparse.TextElement):
                lines.extend(element.lines)

        grouped_lines = group_lines(lines)
        page_lines[node.bbox[0].page].extend(grouped_lines)
        line_lengths.extend(sum(len(line.text) for line in group) for group in grouped_lines)

    if len(line_lengths) == 0:
        exit("The parser was unable to extract any text from the PDF. This is usually the fault of the parser, not the PDF itself.")
    median_length = sorted(line_lengths)[len(line_lengths) // 2]

    with open(output_path, 'w') as output_file:
        for page, lines in page_lines.items():
            output_file.write(f"Page {page + 1}:\n")
            merged_lines = []
            prev_line_type = None
            start_line_num = 1

            for i, line_group in enumerate(lines, start=1):
                line_type = classify_line(line_group, common_styles, median_length)

                if line_type == prev_line_type:
                    merged_lines[-1][1].extend(line_group)
                else:
                    if prev_line_type is not None:
                        end_line_num = i - 1
                        line_range = f"{start_line_num}-{end_line_num}" if start_line_num != end_line_num else str(start_line_num)
                        merged_text = merge_lines(merged_lines[-1][1])
                        output_file.write(f"{line_range} [{prev_line_type[0].upper()}]: {merged_text}\n")

                    if line_type == 'header' and not merge_headers:
                        line_text = merge_lines(line_group)
                        output_file.write(f"{i} [{line_type[0].upper()}]: {line_text}\n")
                    else:
                        merged_lines.append((line_type, line_group))
                        start_line_num = i

                prev_line_type = line_type

            if merged_lines:
                end_line_num = len(lines)
                line_range = f"{start_line_num}-{end_line_num}" if start_line_num != end_line_num else str(start_line_num)
                merged_text = merge_lines(merged_lines[-1][1])
                output_file.write(f"{line_range} [{prev_line_type[0].upper()}]: {merged_text}\n")

            output_file.write("\n")

def main():
    parser = argparse.ArgumentParser(description="Parse PDF and classify lines.")
    parser.add_argument("pdf_path", type=str, help="Path to the input PDF file.")
    parser.add_argument("output_path", type=str, help="Path to the output text file.", nargs='?', default="output.txt")
    parser.add_argument("--max_pages", type=int, help="Maximum number of pages to process.", default=100)
    parser.add_argument("--merge_headers", type=bool, help="Whether to merge headers.", default=True)
    
    args = parser.parse_args()
    
    parse_pdf(args.pdf_path, args.output_path, args.max_pages, args.merge_headers)

if __name__ == "__main__":
    main()