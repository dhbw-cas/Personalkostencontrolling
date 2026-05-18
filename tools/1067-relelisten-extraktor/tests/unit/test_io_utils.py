import io
import zipfile
from dataclasses import dataclass

from relelisten_extraktor.io_utils import collect_pdf_documents


@dataclass
class _FakeUpload:
    name: str
    payload: bytes

    def getvalue(self) -> bytes:
        return self.payload


def test_collect_pdf_documents_supports_zip_and_single_pdf() -> None:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w") as archive:
        archive.writestr("folder/file_a.pdf", b"A")
        archive.writestr("file_b.pdf", b"B")
        archive.writestr("ignore.txt", b"C")

    uploads = [
        _FakeUpload(name="sample.zip", payload=zip_buffer.getvalue()),
        _FakeUpload(name="single.pdf", payload=b"PDF"),
    ]

    documents = collect_pdf_documents(uploads)

    assert {document.name for document in documents} == {
        "file_a.pdf",
        "file_b.pdf",
        "single.pdf",
    }
    content_by_name = {document.name: document.content for document in documents}
    assert content_by_name == {
        "file_a.pdf": b"A",
        "file_b.pdf": b"B",
        "single.pdf": b"PDF",
    }
