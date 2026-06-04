import base64

from app.services.whapi_cloud import (
    _looks_like_image_bytes,
    decode_whapi_data_uri_image,
)


def test_decode_whapi_data_uri_minimal_png():
    # 1x1 PNG
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    uri = f"data:image/png;base64,{png_b64}"
    out = decode_whapi_data_uri_image(uri)
    assert out is not None
    assert _looks_like_image_bytes(out, "image/png")


def test_decode_rejects_short_payload():
    uri = "data:image/png;base64,AA=="
    assert decode_whapi_data_uri_image(uri) is None


def test_looks_like_jpeg_magic():
    assert _looks_like_image_bytes(b"\xff\xd8\xff" + b"x" * 100)
