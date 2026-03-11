from oci_vision.gallery import get_gallery_path, load_manifest, get_cached_response


def test_gallery_path_exists():
    path = get_gallery_path()
    assert path.exists()
    assert (path / "manifest.json").exists()


def test_load_manifest():
    manifest = load_manifest()
    assert len(manifest["images"]) >= 1
    entry = manifest["images"][0]
    assert "id" in entry
    assert "filename" in entry
    assert "features" in entry


def test_gallery_images_exist():
    manifest = load_manifest()
    gallery = get_gallery_path()
    for entry in manifest["images"]:
        img_path = gallery / "images" / entry["filename"]
        assert img_path.exists(), f"Missing gallery image: {entry['filename']}"


def test_gallery_responses_exist():
    manifest = load_manifest()
    gallery = get_gallery_path()
    for entry in manifest["images"]:
        for feature in entry["features"]:
            resp_path = gallery / "responses" / f"{entry['id']}_{feature}.json"
            assert resp_path.exists(), f"Missing cached response: {entry['id']}_{feature}.json"


def test_get_cached_response():
    resp = get_cached_response("dog_closeup", "classification")
    assert resp is not None
    assert "labels" in resp


def test_get_cached_response_missing():
    resp = get_cached_response("nonexistent", "classification")
    assert resp is None
