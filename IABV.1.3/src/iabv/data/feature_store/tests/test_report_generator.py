# src/iabv/data/feature_store/tests/test_report_generator.py
from pathlib import Path
from iabv.data.feature_store.report_generator import save_json, save_markdown, save_html, save_index
import json

def test_save_json_md_html(tmp_path):
    r = {"valid": False, "critical_errors": ["err1"], "info": ["i"], "sha1": "deadbeef", "raw": {"a":1}}
    p_json = tmp_path / "reports" / "r.json"
    p_md = tmp_path / "reports" / "r.md"
    p_html = tmp_path / "reports" / "r.html"
    save_json(r, p_json)
    save_markdown(r, p_md)
    save_html(r, p_html)
    assert p_json.exists()
    assert p_md.exists()
    assert p_html.exists()
    # basic content check
    j = json.loads(p_json.read_text(encoding="utf8"))
    assert j["valid"] is False
    assert "err1" in p_md.read_text(encoding="utf8")
    assert "<html" in p_html.read_text(encoding="utf8")

def test_save_index(tmp_path):
    d = tmp_path / "reports"
    d.mkdir()
    (d / "a.json").write_text("{}", encoding="utf8")
    (d / "b.md").write_text("#x", encoding="utf8")
    save_index(d)
    assert (d / "index.html").exists()
