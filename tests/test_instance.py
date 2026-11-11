# tests/test_instance.py
import os
import instance


def test_instance_driver_keeps_exe_extension(tmp_path, monkeypatch):
    base = tmp_path / "undetected_chromedriver.exe"
    base.write_bytes(b"x")
    monkeypatch.setattr(instance, "_BASE_DRIVER", str(base))
    monkeypatch.setattr(instance, "_SCRIPT_DIR", str(tmp_path))
    path = instance._instance_driver(0)
    assert path.endswith("chromedriver-0.exe") and os.path.exists(path)
    assert instance._instance_driver(1) != path


def test_instance_driver_no_extension_on_linux(tmp_path, monkeypatch):
    base = tmp_path / "undetected_chromedriver"
    base.write_bytes(b"x")
    monkeypatch.setattr(instance, "_BASE_DRIVER", str(base))
    monkeypatch.setattr(instance, "_SCRIPT_DIR", str(tmp_path))
    assert instance._instance_driver(0).endswith("chromedriver-0")
