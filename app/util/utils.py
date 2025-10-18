import asyncio
import io

from pypdf import PdfReader


async def extract_pdf_text(pdf_bytes: bytes) -> str:
    return await asyncio.to_thread(_pdf_bytes_to_text, pdf_bytes)


@staticmethod
def _pdf_bytes_to_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join(
        filter(None, (page.extract_text() or "" for page in reader.pages))
    )
