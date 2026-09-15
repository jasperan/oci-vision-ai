"""Tests for the upload size guard.

The endpoint's 20 MB check used to run after the whole body had been read into memory, so the guard
bounded what was processed rather than what was buffered. These tests pin the bound itself, then the
endpoint's contract on top of it.
"""

import asyncio

from oci_vision.web.app import _MAX_UPLOAD_BYTES, _UPLOAD_CHUNK_BYTES, _read_capped


class _StreamingUpload:
    """An upload that hands over everything it has when asked without a size.

    The distinction matters: an unbounded ``read()`` on a real upload returns the whole remaining
    body, which is exactly what the cap exists to avoid. When the caller passes a size - which is
    what ``_read_capped`` does - this behaves like a normal stream.
    """

    content_type = "image/png"
    filename = "endless.png"

    def __init__(self, unbounded_chunk: int | None = None) -> None:
        self.delivered = 0
        self._unbounded_chunk = unbounded_chunk or (_MAX_UPLOAD_BYTES * 2)

    async def read(self, size: int = -1) -> bytes:
        if size is None or size < 0:
            amount = self._unbounded_chunk
        else:
            amount = size
        self.delivered += amount
        if self.delivered > _MAX_UPLOAD_BYTES * 8:
            # Endless stream: stop rather than let a broken caller loop forever.
            return b""
        return b"0" * amount


class _ShortUpload:
    content_type = "image/png"
    filename = "small.png"

    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self._sent = False

    async def read(self, size: int = -1) -> bytes:
        if self._sent:
            return b""
        self._sent = True
        return self._payload


def test_read_capped_stops_near_the_limit():
    upload = _StreamingUpload()

    contents, oversize = asyncio.run(_read_capped(upload, _MAX_UPLOAD_BYTES))

    assert oversize is True
    # At most one chunk beyond the limit is read, instead of the whole stream. This is the
    # assertion that fails if the read ever goes back to being unbounded, because such a read
    # hands over _MAX_UPLOAD_BYTES * 2 in one call.
    assert upload.delivered <= _MAX_UPLOAD_BYTES + _UPLOAD_CHUNK_BYTES
    assert len(contents) == upload.delivered


def test_read_capped_returns_smaller_uploads_intact():
    payload = b"x" * 1024

    contents, oversize = asyncio.run(_read_capped(_ShortUpload(payload), _MAX_UPLOAD_BYTES))

    assert contents == payload
    assert oversize is False
