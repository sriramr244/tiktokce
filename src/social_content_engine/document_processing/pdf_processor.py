import logging
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


class PDFProcessor:
    def extract_text(self, pdf_path: str) -> str:
        """
        Extract text from a PDF file given its file path.
        """
        try:
            logger.info(f"Starting text extraction from PDF: {pdf_path}")

            # Open the PDF file
            with open(pdf_path, "rb") as pdf_file:
                reader = PdfReader(pdf_file)
                text = ""
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    text += page.extract_text()

            logger.info(f"Text extraction completed from PDF: {pdf_path}")
            return text

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            raise RuntimeError(f"Error extracting text from PDF: {e}")
