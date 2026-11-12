"""Test penerimaan foto struk sebagai foto biasa maupun dokumen (UX-054)."""

from types import SimpleNamespace

from bot.handlers.transaction import _image_source


def test_foto_biasa_dipakai_sebagai_jpg():
    message = SimpleNamespace(
        photo=[SimpleNamespace(file_id="small"), SimpleNamespace(file_id="large")],
        document=None,
    )
    file_id, extension, error = _image_source(message)

    assert file_id == "large"
    assert extension == ".jpg"
    assert error is None


def test_dokumen_jpeg_diterima():
    message = SimpleNamespace(
        photo=None,
        document=SimpleNamespace(
            file_id="doc-1", mime_type="image/jpeg", file_size=1024
        ),
    )
    file_id, extension, error = _image_source(message)

    assert file_id == "doc-1"
    assert extension == ".jpg"
    assert error is None


def test_dokumen_pdf_ditolak_dengan_pesan_ramah():
    message = SimpleNamespace(
        photo=None,
        document=SimpleNamespace(
            file_id="doc-2", mime_type="application/pdf", file_size=1024
        ),
    )
    file_id, extension, error = _image_source(message)

    assert file_id is None
    assert extension is None
    assert "JPG atau PNG" in error


def test_gambar_terlalu_besar_ditolak():
    message = SimpleNamespace(
        photo=None,
        document=SimpleNamespace(
            file_id="doc-3",
            mime_type="image/png",
            file_size=11 * 1024 * 1024,
        ),
    )
    _, _, error = _image_source(message)

    assert "terlalu besar" in error
