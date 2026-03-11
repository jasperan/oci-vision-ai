"""OCI Vision AI — Web dashboard package."""

from oci_vision.web.app import create_app

# Default app instance for uvicorn (used by CLI ``web`` command).
app = create_app(demo=True)
