# PDF Line Classifier

This script parses a PDF file and classifies its lines into paragraphs or headers. The classified lines are then written to an output text file.

## Requirements

- Python 3.x
- `openparse` library
- `argparse` library


## Usage
The script can be executed from the command line. You need to provide the path to the input PDF file and optionally the output file name.

```sh
python pdf2text.py /path/to/input.pdf /path/to/output.txt
```

### Optional Arguments
--max_pages: Maximum number of pages to process (default: 100).

--merge_headers: Whether to merge headers (default: True).

```sh
python pdf2text.py /path/to/input.pdf /path/to/output.txt --max_pages 50 --merge_headers False
```
