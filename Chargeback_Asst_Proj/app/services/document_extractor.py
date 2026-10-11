from __future__ import annotations

from email import policy
from email.parser import BytesParser
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image

from app.schemas.evidence import SourceDocument

MAX_EXTRACTED_CHARACTERS = 12000
IMAGE_NOTICE = 'Image attached. Its contents were not OCR-read; describe relevant image facts in the case details.'


def extract_uploaded_document(name: str, content: bytes) -> SourceDocument:
    suffix = Path(name).suffix.lower()

    if suffix == '.pdf':
        try:
            with fitz.open(stream=content, filetype='pdf') as pdf:
                extracted_text = '\n'.join(page.get_text() for page in pdf)
        except Exception as exc:
            raise ValueError(f'Could not read PDF: {name}') from exc
        if not extracted_text.strip():
            extracted_text = 'No selectable text found. This may be a scanned PDF; analyst summary is needed.'
        kind = 'pdf'
    elif suffix == '.eml':
        try:
            message = BytesParser(policy=policy.default).parsebytes(content)
            body_part = message.get_body(preferencelist=('plain', 'html'))
            body = body_part.get_content() if body_part else ''
            extracted_text = '\n'.join(
                part for part in (
                    f"Subject: {message.get('subject', '')}",
                    f"From: {message.get('from', '')}",
                    f"Date: {message.get('date', '')}",
                    str(body),
                ) if part.strip()
            )
        except Exception as exc:
            raise ValueError(f'Could not read email: {name}') from exc
        kind = 'email'
    elif suffix == '.txt':
        extracted_text = content.decode('utf-8-sig', errors='replace')
        kind = 'email_text'
    elif suffix in {'.png', '.jpg', '.jpeg'}:
        try:
            with Image.open(BytesIO(content)) as image:
                image.verify()
        except Exception as exc:
            raise ValueError(f'Could not read image: {name}') from exc
        extracted_text = IMAGE_NOTICE
        kind = 'image'
    else:
        raise ValueError(f'Unsupported evidence file: {name}')

    return SourceDocument(
        name=name,
        kind=kind,
        source='analyst_upload',
        content=extracted_text[:MAX_EXTRACTED_CHARACTERS],
    )