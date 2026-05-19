from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class PayloadPaths:
    data_dir: Path
    evidence_path: Path
    output_path: Path


ALLOWED_RISK_LEVELS = {"low", "medium", "high"}


class PayloadError(RuntimeError):
    pass


def _load_json(path: Path) -> Any:
    if not path.exists():
        raise PayloadError(f"Missing required file: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _max_mtime(paths: Iterable[Path]) -> str:
    latest = max(path.stat().st_mtime for path in paths)
    return datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()


def _ensure_city_list(*dicts: Dict[str, Any]) -> List[str]:
    city_sets = [set(d.keys()) for d in dicts]
    if not city_sets:
        raise PayloadError("No city data found.")
    common = set.intersection(*city_sets)
    if not common:
        raise PayloadError("No overlapping cities across datasets.")
    missing_sets = [sorted(list(s - common)) for s in city_sets]
    if any(missing_sets):
        raise PayloadError("City mismatch across datasets.")
    return sorted(common)


def _compute_recent_cvle(events: List[Dict[str, Any]], window_years: int = 5) -> Dict[str, int]:
    if not events:
        return {}
    years = [int(e["year"]) for e in events if "year" in e]
    if not years:
        return {}
    max_year = max(years)
    cutoff = max_year - (window_years - 1)
    counts: Dict[str, int] = {}
    for row in events:
        try:
            city = row["city"]
            year = int(row["year"])
        except (KeyError, ValueError, TypeError):
            continue
        if year >= cutoff:
            counts[city] = counts.get(city, 0) + 1
    return counts


def _compute_risk_level(eri_score: float, eri_alert: bool, trend_label: str, recent_cvle: int) -> str:
    if eri_alert or (trend_label == "deteriorating" and recent_cvle >= 1):
        return "high"
    if trend_label == "deteriorating" or eri_score >= 0.5:
        return "medium"
    return "low"


def _top_features(feature_map: Dict[str, float], count: int = 5) -> List[Dict[str, Any]]:
    items = sorted(feature_map.items(), key=lambda x: x[1], reverse=True)
    return [{"feature": name, "score": round(value, 6)} for name, value in items[:count]]


def build_payload(paths: PayloadPaths, strict: bool = False) -> Dict[str, Any]:
    data_dir = paths.data_dir

    advisory = _load_json(data_dir / "crop_advisory.json")
    irrigation = _load_json(data_dir / "irrigation_strategy.json")
    eri_report = _load_json(data_dir / "exploitation_risk_report.json")
    transitions = _load_json(data_dir / "transition_report.json")
    linkage = _load_json(data_dir / "transition_cvle_linkage.json")
    trend_report = _load_json(data_dir / "viability_trend_report.json")
    cvle_events = _load_json(data_dir / "crop_viability_events.json")
    shap_out = _load_json(data_dir / "shap_explanation.json")
    recharge = _load_json(data_dir / "groundwater_recharge_grid.json")

    evidence = _load_json(paths.evidence_path)

    trend_by_city = {row["city"]: row for row in trend_report}
    recent_cvle = _compute_recent_cvle(cvle_events)

    cities = _ensure_city_list(advisory, irrigation, eri_report, trend_by_city, recharge)

    missing_evidence = [city for city in cities if not evidence.get(city)]
    if missing_evidence and strict:
        raise PayloadError(f"Missing evidence entries for: {', '.join(missing_evidence)}")

    summary: List[Dict[str, Any]] = []
    city_detail: Dict[str, Any] = {}

    for city in cities:
        adv = advisory[city]
        irr = irrigation[city]
        eri = eri_report[city]
        trend = trend_by_city[city]

        recent_count = recent_cvle.get(city, 0)
        risk_level = _compute_risk_level(float(eri["eri"]), bool(eri["alert"]), trend["trend"], recent_count)

        top_crops = [
            {"crop": c["crop"], "score": c["score"], "season": c["season"], "zone_match": c["zone_match"]}
            for c in adv.get("ranked_crops", [])[:3]
        ]

        summary.append({
            "city": city,
            "risk_level": risk_level,
            "top_crops": top_crops,
            "irrigation": {"rsi_level": irr["rsi_level"], "method": irr["irrigation_method"]},
            "eri": {"score": eri["eri"], "alert": eri["alert"]},
            "trend": {"slope": trend["slope"], "trend": trend["trend"]},
            "recent_cvle_count": recent_count,
            "current_zone": adv.get("current_zone"),
            "evidence_missing": city in missing_evidence,
        })

        city_transitions = [t for t in transitions if t["city"] == city]
        city_linkage = [t for t in linkage if t["city"] == city]
        city_cvle = [e for e in cvle_events if e["city"] == city]
        shap_city = shap_out.get("city_importance", {}).get(city, {})
        shap_global = {row["feature"]: row["mean_abs_shap"] for row in shap_out.get("global_importance", [])}

        city_detail[city] = {
            "advisory": adv,
            "irrigation": irr,
            "eri": eri,
            "transitions": city_transitions,
            "transition_linkage": city_linkage,
            "cvle_events": city_cvle,
            "trend": trend,
            "recharge": recharge.get(city, {}),
            "shap": {
                "city_top": _top_features(shap_city, count=5),
                "global_top": _top_features(shap_global, count=5),
            },
            "evidence": evidence.get(city, []),
        }

    for item in summary:
        if item["risk_level"] not in ALLOWED_RISK_LEVELS:
            raise PayloadError(f"Invalid risk level for {item['city']}: {item['risk_level']}")

    meta = {
        "version": "1.0",
        "last_updated": _max_mtime([
            data_dir / "crop_advisory.json",
            data_dir / "irrigation_strategy.json",
            data_dir / "exploitation_risk_report.json",
            data_dir / "transition_report.json",
            data_dir / "transition_cvle_linkage.json",
            data_dir / "viability_trend_report.json",
            data_dir / "crop_viability_events.json",
            data_dir / "shap_explanation.json",
            data_dir / "groundwater_recharge_grid.json",
            paths.evidence_path,
        ]),
    }

    return {
        "meta": meta,
        "summary": summary,
        "city_detail": city_detail,
    }


def write_payload(payload: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
