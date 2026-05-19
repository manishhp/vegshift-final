from pathlib import Path

from tools.frontend_payload import PayloadPaths, build_payload


def test_frontend_payload_builds():
    repo_root = Path(__file__).resolve().parents[1]
    paths = PayloadPaths(
        data_dir=repo_root / "data" / "output",
        evidence_path=repo_root / "docs" / "evidence_sources.json",
        output_path=repo_root / "data" / "output" / "frontend_payload.json",
    )
    payload = build_payload(paths, strict=False)

    assert "summary" in payload
    assert "city_detail" in payload

    summary = payload["summary"]
    assert len(summary) > 0

    first = summary[0]
    assert first["risk_level"] in {"low", "medium", "high"}
    assert "top_crops" in first
