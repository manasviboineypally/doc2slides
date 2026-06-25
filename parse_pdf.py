"""
Extract text from a PDF file.
This is the foundation of the Parser agent.
"""
import pdfplumber
import sys


def extract_text_from_pdf(pdf_path: str) -> None:
    """Open a PDF and print the text from each page."""
    
    print(f"Opening: {pdf_path}\n")
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}\n")
        print("=" * 60)
        
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            
            print(f"\n--- Page {page_num} ---\n")
            
            if text:
                print(text[:500])
                if len(text) > 500:
                    print(f"\n[... {len(text) - 500} more characters ...]")
            else:
                print("(No extractable text on this page — might be an image)")
            
            print("\n" + "=" * 60)


if __name__ == "__main__":
    pdf_file = sys.argv[1] if len(sys.argv) > 1 else "test.pdf"
    
    try:
        extract_text_from_pdf(pdf_file)
    except FileNotFoundError:
        print(f"ERROR: Could not find file '{pdf_file}'")
        print("Make sure the PDF is in your project folder.")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")