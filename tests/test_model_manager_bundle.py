import zipfile

from caiengine.core import model_manager


def _write_bundle(path, version="1.2.3"):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("model.onnx", b"dummy")
        archive.writestr("manifest.yaml", f"model_name: tiny\nversion: '{version}'\n")


def test_transport_bundle_copies_local_archive(tmp_path):
    src = tmp_path / "source_bundle.zip"
    dest = tmp_path / "nested" / "dest_bundle.zip"
    _write_bundle(src)

    result = model_manager.transport_bundle(str(src), str(dest))

    assert result == str(dest)
    assert dest.exists()
    assert dest.read_bytes() == src.read_bytes()


def test_check_bundle_version_reads_manifest_from_archive(tmp_path):
    bundle = tmp_path / "bundle.zip"
    _write_bundle(bundle, version="3.0")

    assert model_manager.check_bundle_version(str(bundle), "3.0") is True
    assert model_manager.check_bundle_version(str(bundle), "2.0") is False
