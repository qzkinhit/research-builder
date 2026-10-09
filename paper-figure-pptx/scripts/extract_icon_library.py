#!/usr/bin/env python3
"""Archive original SVGs and their relationship-linked PNG fallbacks from PPTX.

Requires Pillow. Usage:
  python3 extract_icon_library.py SOURCE.pptx OUTPUT_DIR --selection choices.json

The output directory must not exist. The original PPTX is never modified or
copied. A selection JSON may contain source_pptx_sha256, exclude_svg_files,
prior_selection_svg_files, icon_metadata (keyed by SVG basename), and arbitrary
descriptive metadata. Exclusions refer
to exact media basenames. Prior selection does not imply layout approval.
"""

import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

from PIL import Image, ImageDraw


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "asvg": "http://schemas.microsoft.com/office/drawing/2016/SVG/main",
}
EMBED = "{" + NS["r"] + "}embed"
RID = "{" + NS["r"] + "}id"
SHAPES = {"pic", "sp", "graphicFrame", "cxnSp"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def natural_key(value):
    return [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", value)]


def relationships(archive, part):
    p = PurePosixPath(part)
    relfile = str(p.parent / "_rels" / (p.name + ".rels"))
    if relfile not in archive.namelist():
        return {}
    result = {}
    for rel in ET.fromstring(archive.read(relfile)):
        if rel.get("TargetMode") == "External":
            continue
        target = rel.attrib["Target"]
        result[rel.attrib["Id"]] = posixpath.normpath(
            target.lstrip("/") if target.startswith("/") else str(p.parent / target)
        )
    return result


def slide_parts(archive):
    rels = relationships(archive, "ppt/presentation.xml")
    root = ET.fromstring(archive.read("ppt/presentation.xml"))
    return [rels[node.attrib[RID]] for node in root.findall("p:sldIdLst/p:sldId", NS)]


def source_occurrences(archive):
    """Map each SVG through asvg:svgBlip and its containing a:blip, not names."""
    occurrences = {}
    for slide, part in enumerate(slide_parts(archive), 1):
        rels = relationships(archive, part)
        root = ET.fromstring(archive.read(part))
        parents = {child: parent for parent in root.iter() for child in parent}
        for svg_blip in root.findall(".//asvg:svgBlip", NS):
            svg_rid = svg_blip.get(EMBED)
            svg_member = rels.get(svg_rid)
            if not svg_member or not svg_member.lower().endswith(".svg"):
                raise ValueError(f"Unresolved SVG relationship in {part}: {svg_rid}")
            node = svg_blip
            while node is not None and node.tag != "{" + NS["a"] + "}blip":
                node = parents.get(node)
            if node is None:
                raise ValueError(f"SVG has no containing a:blip: {part}/{svg_rid}")
            png_rid = node.get(EMBED)
            png_member = rels.get(png_rid)
            if not png_member or not png_member.lower().endswith(".png"):
                raise ValueError(f"SVG has no linked PNG fallback: {part}/{svg_rid}")
            shape = node
            while shape is not None and shape.tag.split("}")[-1] not in SHAPES:
                shape = parents.get(shape)
            identity = shape.find(".//p:cNvPr", NS) if shape is not None else None
            if identity is None:
                raise ValueError(f"SVG has no identifiable shape: {part}/{svg_rid}")
            occurrences.setdefault(svg_member, []).append({
                "slide": slide,
                "slide_member": part,
                "shape_id": int(identity.attrib["id"]),
                "shape_name": identity.get("name", ""),
                "svg_relationship_id": svg_rid,
                "png_relationship_id": png_rid,
                "source_png_member": png_member,
                "png_path": "fallback/" + PurePosixPath(png_member).name,
            })
    return occurrences


def svg_audit(data):
    root = ET.fromstring(data)
    tags = Counter(node.tag.split("}")[-1] for node in root.iter())
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("Media with SVG extension does not have an SVG root")
    raster = tags["image"] + tags["foreignObject"]
    raster_data_uri = bool(re.search(rb"data:image/(?:png|jpe?g|gif|webp|bmp)", data, re.I))
    events, resources = [], []
    for node in root.iter():
        for key, value in node.attrib.items():
            local = key.split("}")[-1]
            if local.lower().startswith("on"):
                events.append(local)
            if local in {"href", "src"} and value:
                resources.append(value.strip())
    source_text = data.decode("utf-8")
    resources.extend(v.strip().strip("\"'") for v in re.findall(r"url\(([^)]+)\)", source_text, re.I))
    external = [value for value in resources if not value.startswith("#")]
    ids = {node.get("id") for node in root.iter() if node.get("id")}
    missing = [value for value in resources if value.startswith("#") and value[1:] not in ids]
    active = tags["script"] or events or re.search(r"javascript\s*:|@import\b", source_text, re.I)
    vector_count = sum(tags[k] for k in ("path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "text"))
    if raster or raster_data_uri or not vector_count:
        raise ValueError("SVG contains raster/foreign content or has no vector primitives")
    if active or external or missing:
        raise ValueError("SVG contains active content, external resources, or unresolved local references")
    return {"vector_primitive_count": vector_count, "image_element_count": tags["image"],
            "foreign_object_count": tags["foreignObject"], "raster_data_uri": raster_data_uri,
            "script_element_count": tags["script"], "event_handler_attribute_count": len(events),
            "external_resource_reference_count": len(external),
            "unresolved_local_reference_count": len(missing), "self_contained": True}


def png_metadata(data):
    with Image.open(io.BytesIO(data)) as im:
        if im.format != "PNG":
            raise ValueError("Linked PNG fallback is not a PNG file")
        rgba = im.convert("RGBA")
        width, height = rgba.size
        bbox = rgba.getchannel("A").getbbox()
        return {
            "width_px": width, "height_px": height,
            "visible_alpha_bbox_px": list(bbox) if bbox else None,
            "visible_alpha_bbox_normalized": [bbox[0] / width, bbox[1] / height,
                                               bbox[2] / width, bbox[3] / height] if bbox else None,
            "visible_alpha_bbox_rule": "alpha > 0; [left, top, right, bottom), right/bottom exclusive",
            "sizing_note": "Use visible alpha bounds for icon sizing. Transparent canvas padding is not icon size. Opaque whitespace cannot be detected by alpha.",
        }


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_contact_sheet(output, icons, columns):
    width, height = 200, 175
    rows = (len(icons) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * width, rows * height), "white")
    draw = ImageDraw.Draw(sheet)
    for index, icon in enumerate(icons):
        x, y = index % columns * width, index // columns * height
        fallback = icon["png_fallbacks"][0]
        with Image.open(output / fallback["path"]) as im:
            im = im.convert("RGBA")
            bbox = fallback["visible_alpha_bbox_px"]
            if bbox:
                im = im.crop(tuple(bbox))
                im.thumbnail((140, 128), Image.Resampling.LANCZOS)
                sheet.paste(im, (x + (width - im.width) // 2, y + (128 - im.height) // 2), im)
        draw.text((x + 6, y + 139), icon["id"], fill="black")
        first = icon["occurrences"][0]
        draw.text((x + 6, y + 154), f"P{first['slide']} ID{first['shape_id']}", fill="black")
    sheet.save(output / "contact-sheet.png")
    return {"path": "contact-sheet.png", "sha256": digest((output / "contact-sheet.png").read_bytes()),
            "columns": columns, "rows": rows, "ordered_svg_files": [icon["id"] for icon in icons],
            "preview_note": "Preview generated from original PNG fallbacks cropped to visible alpha bounds. Archived SVG and PNG files are unchanged."}


def extract(source, output, selection, columns):
    if output.exists():
        raise ValueError(f"Output directory already exists; refusing to overwrite: {output}")
    source_data = source.read_bytes()
    source_sha = digest(source_data)
    expected = selection.get("source_pptx_sha256")
    if expected and expected != source_sha:
        raise ValueError("Selection source SHA256 does not match the PPTX")
    excluded_list = selection.get("exclude_svg_files", [])
    prior_list = selection.get("prior_selection_svg_files", [])
    for values in (excluded_list, prior_list):
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise ValueError("Selection lists must contain media basename strings")
        if len(values) != len(set(values)):
            raise ValueError("Selection lists contain duplicate media names")
    excluded, prior = set(excluded_list), set(prior_list)
    if excluded & prior:
        raise ValueError("Excluded icons cannot also be prior selections")
    with zipfile.ZipFile(io.BytesIO(source_data)) as archive:
        members = sorted((n for n in archive.namelist() if n.startswith("ppt/media/") and n.lower().endswith(".svg")), key=natural_key)
        by_name = {PurePosixPath(n).name: n for n in members}
        if len(by_name) != len(members):
            raise ValueError("Duplicate SVG basenames")
        if (excluded | prior) - by_name.keys():
            raise ValueError(f"Unknown selection media: {sorted((excluded | prior) - by_name.keys())}")
        metadata = selection.get("icon_metadata", {})
        if not isinstance(metadata, dict) or set(metadata) - by_name.keys():
            raise ValueError("icon_metadata must be an object keyed by known media basenames")
        occurrences = source_occurrences(archive)
        icons, retained_data, fallback_data = [], {}, {}
        for member in members:
            name = PurePosixPath(member).name
            if name in excluded:
                continue
            data = archive.read(member)
            audit = svg_audit(data)
            matches = occurrences.get(member, [])
            if not matches:
                raise ValueError(f"Retained SVG has no slide occurrence: {member}")
            pngs = []
            for png_member in sorted({m["source_png_member"] for m in matches}, key=natural_key):
                png_data = archive.read(png_member)
                png_path = "fallback/" + PurePosixPath(png_member).name
                if png_path in fallback_data and fallback_data[png_path] != png_data:
                    raise ValueError(f"Conflicting fallback basenames: {png_path}")
                fallback_data[png_path] = png_data
                pngs.append({"path": png_path, "source_member": png_member,
                             "sha256": digest(png_data), **png_metadata(png_data)})
            relative = "svg/" + name
            retained_data[relative] = data
            icons.append({"id": name, "path": relative, "source_member": member,
                          "sha256": digest(data), "svg_audit": audit,
                          "metadata": metadata.get(name, {}),
                          "selection_state": "prior_selection" if name in prior else "candidate",
                          "final_layout_approved": False, "png_fallbacks": pngs,
                          "occurrences": matches})
        if not icons:
            raise ValueError("No SVG icons remain after applying exclusions")
        output.mkdir(parents=True, exist_ok=False)
        (output / "svg").mkdir()
        (output / "fallback").mkdir()
        for relative, data in {**retained_data, **fallback_data}.items():
            (output / relative).write_bytes(data)
        selection = {**selection, "source_pptx_sha256": source_sha}
        write_json(output / "selection.json", selection)
        contact = make_contact_sheet(output, icons, columns)
        manifest = {
            "schema_version": 1,
            "source_pptx": {"filename": source.name, "sha256": source_sha,
                            "copied_into_library": False},
            "selection_path": "selection.json",
            "source_svg_count": len(members), "retained_svg_count": len(icons),
            "excluded_svg_count": len(excluded), "png_fallback_count": len(fallback_data),
            "note": "Only retained SVG and linked PNG bytes are archived. Excluded SVG and exclusive fallbacks are not copied. Slide numbers are 1-based presentation order. SVG preservation does not imply native PowerPoint path editability. Prior selection does not mean final layout approval.",
            "contact_sheet": contact, "icons": icons,
        }
        write_json(output / "manifest.json", manifest)
        errors = []
        links_verified = 0
        for icon in icons:
            if (output / icon["path"]).read_bytes() != archive.read(icon["source_member"]):
                errors.append(f"SVG bytes differ: {icon['id']}")
            for png in icon["png_fallbacks"]:
                if (output / png["path"]).read_bytes() != archive.read(png["source_member"]):
                    errors.append(f"PNG bytes differ: {png['path']}")
            for occurrence in icon["occurrences"]:
                part = occurrence["slide_member"]
                rels = relationships(archive, part)
                root = ET.fromstring(archive.read(part))
                matched = False
                for shape in root.iter():
                    if shape.tag.split("}")[-1] not in SHAPES:
                        continue
                    identity = shape.find(".//p:cNvPr", NS)
                    if identity is None or identity.get("id") != str(occurrence["shape_id"]):
                        continue
                    for blip in shape.findall(".//a:blip", NS):
                        for svg in blip.findall(".//asvg:svgBlip", NS):
                            if (rels.get(svg.get(EMBED)) == icon["source_member"] and
                                    rels.get(blip.get(EMBED)) == occurrence["source_png_member"]):
                                matched = True
                if matched:
                    links_verified += 1
                else:
                    errors.append(f"Unverified relationship: {icon['id']}/{occurrence['slide']}/{occurrence['shape_id']}")
        excluded_pngs = {m["source_png_member"] for name in excluded for m in occurrences.get(by_name[name], [])}
        exclusive_pngs = {"fallback/" + PurePosixPath(n).name for n in excluded_pngs} - fallback_data.keys()
        for relative in ["svg/" + n for n in excluded] + sorted(exclusive_pngs):
            if (output / relative).exists():
                errors.append(f"Excluded media unexpectedly saved: {relative}")
        if source.read_bytes() != source_data:
            errors.append("Source PPTX changed during extraction")
        validation = {
            "status": "passed" if not errors else "failed", "source_pptx_sha256": source_sha,
            "source_unchanged": source.read_bytes() == source_data,
            "source_svg_count": len(members), "retained_svg_bytes_verified": len(icons),
            "retained_png_bytes_verified": len(fallback_data),
            "relationship_occurrences_verified": links_verified,
            "excluded_svg_files_not_saved": len(excluded),
            "exclusive_excluded_png_files_not_saved": len(exclusive_pngs),
            "source_pptx_not_copied": not (output / "source.pptx").exists(),
            "svg_xml_roots_verified": len(icons), "svg_raster_image_elements": 0,
            "svg_foreign_objects": 0, "svg_raster_data_uris": 0,
            "svg_script_elements": 0, "svg_event_handler_attributes": 0,
            "svg_external_resource_references": 0, "svg_unresolved_local_references": 0,
            "self_contained_svg_count": len(icons),
            "contact_sheet_retained_icons_only": contact["ordered_svg_files"] == [i["id"] for i in icons],
            "validation_scope": "Byte identity with source ZIP; independent shape/relationship association check; SVG XML and vector-content checks; PNG visible alpha bounds; exclusion absence. No visual correctness or final layout approval is claimed.",
            "errors": errors,
        }
        write_json(output / "validation.json", validation)
        if errors:
            raise ValueError("Archive validation failed; see validation.json")
    return validation


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--selection", type=Path, help="Selection JSON with exclusions and prior selections")
    parser.add_argument("--columns", type=int, default=6, help="Contact-sheet column count (default: 6)")
    args = parser.parse_args()
    if args.columns < 1:
        parser.error("--columns must be positive")
    try:
        selection = json.loads(args.selection.read_text(encoding="utf-8")) if args.selection else {}
        if not isinstance(selection, dict):
            raise ValueError("Selection JSON must be an object")
        result = extract(args.source, args.output, selection, args.columns)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, ET.ParseError, zipfile.BadZipFile) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
