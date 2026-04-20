#!/usr/bin/env python3
"""Lightweight KML automation toolkit."""

from __future__ import annotations

import argparse
import json
import os
import random
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any
from xml.dom import minidom
from xml.etree import ElementTree as ET

KML_NS = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", KML_NS)
NS = {"kml": KML_NS}


@dataclass(frozen=True)
class OverlayTheme:
    identifier: str
    label: str
    line_color: str
    poly_color: str
    icon_href: str
    tags: tuple[str, ...]
    description: str


OVERLAYS = (
    OverlayTheme(
        identifier="sunrise",
        label="Sunrise Pulse",
        line_color="ff42a5f5",
        poly_color="7f5ec8ff",
        icon_href="http://maps.google.com/mapfiles/kml/shapes/sun.png",
        tags=("warm", "soft", "optimistic"),
        description="Warm amber/blue tones for friendly map storytelling.",
    ),
    OverlayTheme(
        identifier="neon-night",
        label="Neon Night",
        line_color="ffff00ff",
        poly_color="7f1a1a1a",
        icon_href="http://maps.google.com/mapfiles/kml/shapes/target.png",
        tags=("contrast", "bold", "dark"),
        description="High-contrast neon style for dramatic overlays.",
    ),
    OverlayTheme(
        identifier="earth-tone",
        label="Earth Tone",
        line_color="ff3f7045",
        poly_color="7f89b38f",
        icon_href="http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png",
        tags=("natural", "calm", "terrain"),
        description="Muted terrain-inspired styling for geographic analysis.",
    ),
    OverlayTheme(
        identifier="signal",
        label="Signal Grid",
        line_color="ff2ad7ff",
        poly_color="7f14676f",
        icon_href="http://maps.google.com/mapfiles/kml/shapes/triangle.png",
        tags=("technical", "modern", "clean"),
        description="Cyan signal tones for technical and utility overlays.",
    ),
)


def _kml(tag: str) -> str:
    return f"{{{KML_NS}}}{tag}"


def _parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def _normalize_whitespace(node: ET.Element) -> None:
    if node.text:
        node.text = " ".join(node.text.split())
    if node.tail:
        node.tail = " ".join(node.tail.split())
    for child in list(node):
        _normalize_whitespace(child)


def _pretty_write(root: ET.Element, output_path: Path) -> None:
    xml_bytes = ET.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(xml_bytes).toprettyxml(indent="  ", encoding="utf-8")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pretty)


def create_basic_kml(output_path: Path, name: str, latitude: float, longitude: float, description: str) -> None:
    root = ET.Element(_kml("kml"))
    document = ET.SubElement(root, _kml("Document"))
    ET.SubElement(document, _kml("name")).text = f"{name} Document"
    placemark = ET.SubElement(document, _kml("Placemark"))
    ET.SubElement(placemark, _kml("name")).text = name
    ET.SubElement(placemark, _kml("description")).text = description
    point = ET.SubElement(placemark, _kml("Point"))
    ET.SubElement(point, _kml("coordinates")).text = f"{longitude},{latitude},0"
    _pretty_write(root, output_path)


def clean_kml(input_path: Path, output_path: Path) -> None:
    tree = ET.parse(input_path)
    root = tree.getroot()
    _normalize_whitespace(root)

    for coordinates in root.findall(".//kml:coordinates", NS):
        if not coordinates.text:
            continue
        points = [p.strip() for p in coordinates.text.replace("\n", " ").split() if p.strip()]
        deduped: list[str] = []
        for point in points:
            if not deduped or deduped[-1] != point:
                deduped.append(point)
        coordinates.text = " ".join(deduped)

    for document in root.findall(".//kml:Document", NS):
        placemarks = [el for el in list(document) if el.tag == _kml("Placemark")]
        for placemark in placemarks:
            document.remove(placemark)
        placemarks.sort(
            key=lambda item: (item.findtext(_kml("name")) or "").strip().lower()
        )
        for placemark in placemarks:
            document.append(placemark)

    _pretty_write(root, output_path)


def _load_feedback(feedback_file: Path | None) -> dict[str, Any]:
    if not feedback_file or not feedback_file.exists():
        return {}
    with feedback_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data if isinstance(data, dict) else {}


def choose_overlay(target_date: date, feedback_file: Path | None) -> OverlayTheme:
    feedback = _load_feedback(feedback_file)
    scores = {overlay.identifier: 1.0 for overlay in OVERLAYS}

    votes = feedback.get("votes", {})
    if isinstance(votes, dict):
        for key, value in votes.items():
            if key in scores:
                try:
                    scores[key] += float(value)
                except (TypeError, ValueError):
                    continue

    preferred_tags = feedback.get("preferred_tags", [])
    if isinstance(preferred_tags, list):
        preferred = {str(tag).strip().lower() for tag in preferred_tags}
        for overlay in OVERLAYS:
            if preferred.intersection(overlay.tags):
                scores[overlay.identifier] += 0.8

    avoid_tags = feedback.get("avoid_tags", [])
    if isinstance(avoid_tags, list):
        avoided = {str(tag).strip().lower() for tag in avoid_tags}
        for overlay in OVERLAYS:
            if avoided.intersection(overlay.tags):
                scores[overlay.identifier] -= 0.8

    weighted_scores = [max(0.1, scores[overlay.identifier]) for overlay in OVERLAYS]
    rng = random.Random(target_date.toordinal())
    return rng.choices(list(OVERLAYS), weights=weighted_scores, k=1)[0]


def apply_overlay(input_path: Path, output_path: Path, target_date: date, feedback_file: Path | None) -> OverlayTheme:
    tree = ET.parse(input_path)
    root = tree.getroot()
    overlay = choose_overlay(target_date, feedback_file)

    document = root.find(".//kml:Document", NS)
    if document is None:
        document = ET.SubElement(root, _kml("Document"))

    style_id = f"overlay-{overlay.identifier}"
    style = ET.SubElement(document, _kml("Style"), attrib={"id": style_id})

    line_style = ET.SubElement(style, _kml("LineStyle"))
    ET.SubElement(line_style, _kml("color")).text = overlay.line_color
    ET.SubElement(line_style, _kml("width")).text = "2.5"

    poly_style = ET.SubElement(style, _kml("PolyStyle"))
    ET.SubElement(poly_style, _kml("color")).text = overlay.poly_color
    ET.SubElement(poly_style, _kml("fill")).text = "1"
    ET.SubElement(poly_style, _kml("outline")).text = "1"

    icon_style = ET.SubElement(style, _kml("IconStyle"))
    icon = ET.SubElement(icon_style, _kml("Icon"))
    ET.SubElement(icon, _kml("href")).text = overlay.icon_href

    for placemark in root.findall(".//kml:Placemark", NS):
        style_url = placemark.find(_kml("styleUrl"))
        if style_url is None:
            style_url = ET.SubElement(placemark, _kml("styleUrl"))
        style_url.text = f"#{style_id}"

    _pretty_write(root, output_path)
    return overlay


def build_atomic_output(output_path: Path, name: str, latitude: float, longitude: float, description: str, target_date: date, feedback_file: Path | None) -> OverlayTheme:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kml-pipeline-") as tmpdir:
        tmp = Path(tmpdir)
        raw_file = tmp / "raw.kml"
        cleaned_file = tmp / "cleaned.kml"
        styled_file = tmp / "styled.kml"
        create_basic_kml(raw_file, name, latitude, longitude, description)
        clean_kml(raw_file, cleaned_file)
        overlay = apply_overlay(cleaned_file, styled_file, target_date, feedback_file)
        os.replace(styled_file, output_path)
        return overlay


def record_feedback(feedback_file: Path, overlay_id: str, vote: int, note: str | None) -> None:
    data = _load_feedback(feedback_file)
    votes = data.get("votes", {})
    if not isinstance(votes, dict):
        votes = {}
    votes[overlay_id] = int(votes.get(overlay_id, 0)) + vote
    data["votes"] = votes

    if note:
        notes = data.get("notes", [])
        if not isinstance(notes, list):
            notes = []
        notes.append({"overlay": overlay_id, "note": note, "timestamp": datetime.utcnow().isoformat()})
        data["notes"] = notes

    feedback_file.parent.mkdir(parents=True, exist_ok=True)
    with feedback_file.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def print_resources() -> None:
    print("KML Expert Resources")
    print("- OGC KML 2.2 Standard: https://www.ogc.org/standards/kml/")
    print("- Google KML Reference: https://developers.google.com/kml/documentation/kmlreference")
    print("- Google KML Tutorial: https://developers.google.com/kml/documentation/kml_tut")
    print("- KML Best Practices: https://developers.google.com/kml/documentation/kml_21tutorial")
    print("- XML Validation for KML: https://developers.google.com/kml/documentation/kmlreference#validation")
    print()
    print("Core development guidance:")
    print("1) Keep coordinates in KML order: longitude,latitude[,altitude].")
    print("2) Use explicit <Style> and <styleUrl> for predictable rendering.")
    print("3) Clean and normalize KML before sharing to reduce parser issues.")
    print("4) Keep overlays modular so style can change without altering geometry.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lightweight automated KML toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create a basic KML file")
    create.add_argument("--output", required=True, type=Path)
    create.add_argument("--name", required=True)
    create.add_argument("--latitude", required=True, type=float)
    create.add_argument("--longitude", required=True, type=float)
    create.add_argument("--description", default="Auto-generated KML placemark")

    clean = sub.add_parser("clean", help="Normalize and clean an existing KML file")
    clean.add_argument("--input", required=True, type=Path)
    clean.add_argument("--output", required=True, type=Path)

    overlay = sub.add_parser("overlay", help="Apply daily overlay style to a KML file")
    overlay.add_argument("--input", required=True, type=Path)
    overlay.add_argument("--output", required=True, type=Path)
    overlay.add_argument("--date", default=None, help="YYYY-MM-DD")
    overlay.add_argument("--feedback-file", type=Path, default=None)

    build = sub.add_parser("build", help="Atomically create, clean, and overlay a KML file")
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--name", required=True)
    build.add_argument("--latitude", required=True, type=float)
    build.add_argument("--longitude", required=True, type=float)
    build.add_argument("--description", default="Auto-generated KML placemark")
    build.add_argument("--date", default=None, help="YYYY-MM-DD")
    build.add_argument("--feedback-file", type=Path, default=None)

    suggest = sub.add_parser("suggest-overlay", help="Preview today's overlay style")
    suggest.add_argument("--date", default=None, help="YYYY-MM-DD")
    suggest.add_argument("--feedback-file", type=Path, default=None)

    feedback = sub.add_parser("record-feedback", help="Record overlay feedback for future daily iteration")
    feedback.add_argument("--feedback-file", required=True, type=Path)
    feedback.add_argument("--overlay-id", required=True, choices=[overlay.identifier for overlay in OVERLAYS])
    feedback.add_argument("--vote", required=True, type=int, choices=[-1, 1])
    feedback.add_argument("--note", default=None)

    sub.add_parser("resources", help="Show KML learning resources and development guidance")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "create":
        create_basic_kml(args.output, args.name, args.latitude, args.longitude, args.description)
        print(f"Created: {args.output}")
    elif args.command == "clean":
        clean_kml(args.input, args.output)
        print(f"Cleaned: {args.output}")
    elif args.command == "overlay":
        overlay = apply_overlay(args.input, args.output, _parse_date(args.date), args.feedback_file)
        print(f"Overlay '{overlay.identifier}' applied to: {args.output}")
    elif args.command == "build":
        overlay = build_atomic_output(
            args.output,
            args.name,
            args.latitude,
            args.longitude,
            args.description,
            _parse_date(args.date),
            args.feedback_file,
        )
        print(f"Built atomically with overlay '{overlay.identifier}': {args.output}")
    elif args.command == "suggest-overlay":
        overlay = choose_overlay(_parse_date(args.date), args.feedback_file)
        print(f"{overlay.identifier} | {overlay.label}")
        print(overlay.description)
        print(f"tags={', '.join(overlay.tags)}")
    elif args.command == "record-feedback":
        record_feedback(args.feedback_file, args.overlay_id, args.vote, args.note)
        print(f"Feedback saved: {args.feedback_file}")
    elif args.command == "resources":
        print_resources()


if __name__ == "__main__":
    main()
