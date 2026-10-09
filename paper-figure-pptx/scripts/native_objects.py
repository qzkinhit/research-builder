#!/usr/bin/env python3
"""Safely package editable PPTX groups, SVG images, and native elbow connectors.

Only Python's standard library is required. ``group::member`` names form a
native group with an identity coordinate transform. Existing text, child IDs,
coordinates, PNG fallback bytes, and connector semantics are preserved.
Interleaved members are rejected unless --allow-interleaved-groups is explicit.

Examples::

    python3 native_objects.py source.pptx result.pptx --svg-map svg-map.json
    python3 native_objects.py source.pptx result.pptx --route-map routes.json
    python3 native_objects.py result.pptx --audit-only --strict

SVG map object: {"heatmap": "../assets/heatmap.svg"}. A list also supports
match, path, slide (one based), field (name/descr/title/auto), contains, or
picture_index with slide. Relative paths resolve against the map file. Every
selector must match, and mapped pictures must already have a PNG fallback.

Route map object: {"feedback": {"points": [[10,20],[40,20],[40,60]]}}.
Lists also support name and slide. Orthogonal routes contain 3 to 6 vertices;
units are px at 96 dpi by default, or emu. Optional start_idx/end_idx refer to
native connection sites. Optional start_anchor: {"side":"bottom","size_px":4}
creates a transparent native anchor. Optional detach preserves preset routing
while removing shape attachment references. Use these only for verified viewer
compatibility needs. A route remains a single p:cxnSp, never line fragments.

Subscript map object: {"Qbest": {"base":"Q","subscript":"best"}}. Base plus
subscript must equal the token, so formatting cannot change source characters.
Matching applies to whole tokens within a single native text run; tokens already
split across runs need authoring-time formatting. All selectors must match.

Packaging rejects audit errors before writing and publishes a verified ZIP
atomically. Existing output and in-place writes require --overwrite. A canvas
ratio is checked only with --expected-ratio. Arrowless native connectors are
valid and produce warnings, unless --require-end-arrows requests arrows on every
connector. Native block-arrow shapes are allowed. Geometry audits cannot detect
all text overflow or visual alignment defects; always render and inspect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import posixpath
import re
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.dom import Node, minidom
from xml.parsers.expat import ExpatError


NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "asvg": "http://schemas.microsoft.com/office/drawing/2016/SVG/main",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
}
SVG_EXT_URI = "{96DAC541-7B7A-43D3-8B79-37D633B846F1}"
XMLNS = "http://www.w3.org/2000/xmlns/"
IMAGE_REL = NS["r"] + "/image"
DRAWABLES = {"sp", "pic", "cxnSp", "graphicFrame", "grpSp"}


def children(node, namespace=None, local=None):
    return [child for child in node.childNodes
            if child.nodeType == Node.ELEMENT_NODE
            and (namespace is None or child.namespaceURI == namespace)
            and (local is None or child.localName == local)]


def direct(node, prefix, local):
    matches = children(node, NS[prefix], local)
    return matches[0] if matches else None


def descendants(node, prefix, local):
    return list(node.getElementsByTagNameNS(NS[prefix], local))


def make(doc, prefix, local, **attrs):
    node = doc.createElementNS(NS[prefix], f"{prefix}:{local}")
    for key, value in attrs.items():
        node.setAttribute(key, str(value))
    return node


def ensure_ns(doc, prefix):
    doc.documentElement.setAttributeNS(XMLNS, f"xmlns:{prefix}", NS[prefix])


def cnvpr(shape):
    """Only the object's own nonvisual properties, never a nested child's."""
    containers = {
        "sp": "nvSpPr", "pic": "nvPicPr", "cxnSp": "nvCxnSpPr",
        "graphicFrame": "nvGraphicFramePr", "grpSp": "nvGrpSpPr",
    }
    container = direct(shape, "p", containers.get(shape.localName, ""))
    return direct(container, "p", "cNvPr") if container is not None else None


def object_name(shape):
    nv = cnvpr(shape)
    return nv.getAttribute("name") if nv is not None else ""


def object_bounds(shape):
    if shape.localName == "graphicFrame":
        xfrm = direct(shape, "p", "xfrm")
    else:
        props = direct(shape, "p", "grpSpPr" if shape.localName == "grpSp" else "spPr")
        xfrm = direct(props, "a", "xfrm") if props is not None else None
    if xfrm is None:
        raise ValueError(f"Object {object_name(shape)!r} has no explicit transform")
    off, ext = direct(xfrm, "a", "off"), direct(xfrm, "a", "ext")
    if off is None or ext is None:
        raise ValueError(f"Object {object_name(shape)!r} lacks offset or extent")
    x, y = int(off.getAttribute("x")), int(off.getAttribute("y"))
    w, h = int(ext.getAttribute("cx")), int(ext.getAttribute("cy"))
    if w < 0 or h < 0:
        raise ValueError(f"Object {object_name(shape)!r} has negative extent")
    angle = math.radians(int(xfrm.getAttribute("rot") or "0") / 60000)
    rw = abs(w * math.cos(angle)) + abs(h * math.sin(angle))
    rh = abs(w * math.sin(angle)) + abs(h * math.cos(angle))
    return (math.floor(x + (w - rw) / 2), math.floor(y + (h - rh) / 2),
            math.ceil(x + (w + rw) / 2), math.ceil(y + (h + rh) / 2))


def group_slide(doc, slide_number, allow_interleaved=False):
    ensure_ns(doc, "p")
    ensure_ns(doc, "a")
    used_ids = [int(n.getAttribute("id")) for n in descendants(doc, "p", "cNvPr")
                if n.getAttribute("id").isdigit()]
    next_id = max(used_ids, default=0) + 1
    events, warnings = [], []
    # Work from inner containers out, without interpreting '::' recursively.
    containers = descendants(doc, "p", "spTree") + descendants(doc, "p", "grpSp")
    for container in reversed(containers):
        objects = [n for n in children(container, NS["p"]) if n.localName in DRAWABLES]
        # Compatibility wrappers and unknown drawing children still occupy a
        # z-order position. Only known nonvisual group metadata can be skipped.
        stacking_nodes = [n for n in children(container)
                          if not (n.namespaceURI == NS["p"] and n.localName in
                                  {"nvGrpSpPr", "grpSpPr", "extLst"})]
        candidates = defaultdict(list)
        for shape in objects:
            name = object_name(shape)
            if "::" in name:
                key, suffix = name.split("::", 1)
                if not key.strip() or not suffix.strip():
                    raise ValueError(f"Malformed group prefix in slide {slide_number}: {name!r}")
                # Re-running a packaged file does not wrap every existing group.
                if container.localName == "grpSp" and object_name(container) == key:
                    continue
                candidates[key].append(shape)
        for key, members in candidates.items():
            indices = [stacking_nodes.index(member) for member in members]
            if max(indices) - min(indices) + 1 != len(indices):
                message = (f"Slide {slide_number}: {key!r} members are interleaved; "
                           "grouping changes their z-order relative to other objects")
                if not allow_interleaved:
                    raise ValueError(message + "; use --allow-interleaved-groups only after review")
                warnings.append(message)
            bounds = [object_bounds(member) for member in members]
            left, top = min(b[0] for b in bounds), min(b[1] for b in bounds)
            right, bottom = max(b[2] for b in bounds), max(b[3] for b in bounds)
            width, height = max(1, right - left), max(1, bottom - top)
            group = make(doc, "p", "grpSp")
            nonvisual = make(doc, "p", "nvGrpSpPr")
            nonvisual.appendChild(make(doc, "p", "cNvPr", id=next_id, name=key))
            next_id += 1
            nonvisual.appendChild(make(doc, "p", "cNvGrpSpPr"))
            nonvisual.appendChild(make(doc, "p", "nvPr"))
            group.appendChild(nonvisual)
            props, transform = make(doc, "p", "grpSpPr"), make(doc, "a", "xfrm")
            # Identity group mapping: off == chOff and ext == chExt.
            for local, attrs in (("off", {"x": left, "y": top}),
                                 ("ext", {"cx": width, "cy": height}),
                                 ("chOff", {"x": left, "y": top}),
                                 ("chExt", {"cx": width, "cy": height})):
                transform.appendChild(make(doc, "a", local, **attrs))
            props.appendChild(transform)
            group.appendChild(props)
            container.insertBefore(group, members[0])
            for member in members:
                group.appendChild(member)
            events.append({"slide": slide_number, "name": key, "members": len(members),
                           "bbox_emu": [left, top, width, height]})
    return events, warnings


def read_svg_map(map_path):
    if map_path is None:
        return []
    source = json.loads(map_path.read_text(encoding="utf-8"))
    records = ([{"match": k, "path": v} for k, v in source.items()]
               if isinstance(source, dict) else source)
    if not isinstance(records, list):
        raise ValueError("SVG map must be a JSON object or list")
    result = []
    for record in records:
        if (not isinstance(record, dict) or not record.get("path")
                or not (record.get("match") or record.get("picture_index"))):
            raise ValueError("Each SVG mapping needs 'path' and 'match' or 'picture_index'")
        if record.get("picture_index") is not None and (int(record["picture_index"]) < 1 or record.get("slide") is None):
            raise ValueError("A picture_index selector requires a slide and one-based positive index")
        field = record.get("field", "auto")
        if field not in {"auto", "name", "descr", "title"}:
            raise ValueError(f"Invalid SVG selector field {field!r}")
        path = Path(record["path"]).expanduser()
        if not path.is_absolute():
            path = map_path.parent / path
        payload = path.read_bytes()
        svg_doc = minidom.parseString(payload)
        if svg_doc.documentElement.localName != "svg":
            raise ValueError(f"Not an SVG document: {path}")
        result.append({**record, "field": field, "payload": payload,
                       "source": str(path.resolve()), "hits": 0})
    return result


def read_route_map(map_path):
    if map_path is None:
        return []
    source = json.loads(map_path.read_text(encoding="utf-8"))
    if isinstance(source, dict):
        source = [{"name": key, **(value if isinstance(value, dict) else {"points": value})}
                  for key, value in source.items()]
    if not isinstance(source, list):
        raise ValueError("Route map must be a JSON object or list")
    records = []
    for record in source:
        if not isinstance(record, dict) or not record.get("name"):
            raise ValueError("Each route needs a nonempty connector name")
        if record.get("units", "px") not in {"px", "emu"}:
            raise ValueError("Route units must be px or emu")
        records.append({**record, "hits": 0})
    return records


def require_identity_ancestor_groups(connector, slide_number):
    """Route coordinates are slide coordinates; transformed parents need authoring-time routing."""
    parent = connector.parentNode
    while parent is not None:
        if parent.namespaceURI == NS["p"] and parent.localName == "grpSp":
            props = direct(parent, "p", "grpSpPr")
            transform = direct(props, "a", "xfrm") if props is not None else None
            identity = transform is not None
            if identity:
                identity = (int(transform.getAttribute("rot") or "0") == 0
                            and all(transform.getAttribute(flag) in {"", "0", "false"}
                                    for flag in ("flipH", "flipV")))
                for outer, inner, keys in (("off", "chOff", ("x", "y")),
                                           ("ext", "chExt", ("cx", "cy"))):
                    a, b = direct(transform, "a", outer), direct(transform, "a", inner)
                    if a is None or b is None:
                        identity = False
                        continue
                    values = [(int(a.getAttribute(key)), int(b.getAttribute(key))) for key in keys]
                    identity = identity and all(left == right for left, right in values)
                    if outer == "ext":
                        identity = identity and all(left > 0 and right > 0 for left, right in values)
            if not identity:
                raise ValueError(f"Slide {slide_number}: connector {object_name(connector)!r} "
                                 f"has a non-identity or unverified ancestor group transform "
                                 f"in {object_name(parent)!r}; route it in the authoring source")
        parent = parent.parentNode


def route_connectors(doc, slide_number, records):
    """Set editable preset geometry; a connector remains exactly one p:cxnSp.

    DrawingML presets, including unconstrained adjustment ranges, are defined in
    Apache POI's primary implementation resource:
    https://github.com/apache/poi/blob/trunk/poi/src/main/resources/org/apache/poi/sl/draw/geom/presetShapeDefinitions.xml
    """
    events = []
    for connector in descendants(doc, "p", "cxnSp"):
        matches = [record for record in records if object_name(connector) == record["name"]
                   and (record.get("slide") is None or int(record["slide"]) == slide_number)]
        if len(matches) > 1:
            raise ValueError(f"Multiple routes match slide {slide_number}, {object_name(connector)!r}")
        if not matches:
            continue
        record = matches[0]
        require_identity_ancestor_groups(connector, slide_number)
        source_points = record.get("points")
        if not isinstance(source_points, list) or len(source_points) not in {3, 4, 5, 6}:
            raise ValueError("Native elbow routing needs three through six vertices")
        scale = 9525 if record.get("units", "px") == "px" else 1
        points = []
        for point in source_points:
            if not isinstance(point, list) or len(point) != 2:
                raise ValueError("Each route vertex must be [x, y]")
            points.append(tuple(round(float(value) * scale) for value in point))
        vertical_first = points[0][0] == points[1][0]
        virtual = [(y, -x) for x, y in points] if vertical_first else points
        for index, (first, second) in enumerate(zip(virtual, virtual[1:])):
            if first == second:
                raise ValueError("Native elbow routes may not contain zero-length segments")
            # Preset bent connectors begin horizontally and alternate H, V.
            if first[1 if index % 2 == 0 else 0] != second[1 if index % 2 == 0 else 0]:
                raise ValueError("Route must alternate horizontal and vertical segments")
        sx, sy = virtual[0]
        ex, ey = virtual[-1]
        # A zero preset extent prevents any offset on that axis. Give it the
        # smallest positive extent that keeps adjustments in signed 32-bit range.
        if sx == ex:
            ex += max(1, math.ceil(max(abs(x - sx) for x, y in virtual) * 100000 / 2147483647))
        if sy == ey:
            ey += max(1, math.ceil(max(abs(y - sy) for x, y in virtual) * 100000 / 2147483647))
        width, height = abs(ex - sx), abs(ey - sy)
        sign_x, sign_y = (1 if ex > sx else -1), (1 if ey > sy else -1)
        local = [((x - sx) * sign_x, (y - sy) * sign_y) for x, y in virtual]
        adjustments = [round(local[1][0] / width * 100000)] if len(points) >= 4 else []
        if len(points) >= 5:
            adjustments.append(round(local[2][1] / height * 100000))
        if len(points) == 6:
            adjustments.append(round(local[3][0] / width * 100000))
        props = direct(connector, "p", "spPr")
        if props is None:
            raise ValueError(f"Connector {object_name(connector)!r} lacks p:spPr")
        old_xfrm = direct(props, "a", "xfrm")
        transform = make(doc, "a", "xfrm")
        if sign_x < 0:
            transform.setAttribute("flipH", "1")
        if sign_y < 0:
            transform.setAttribute("flipV", "1")
        if vertical_first:
            transform.setAttribute("rot", "5400000")
            # Actual-coordinate center is the inverse rotation of virtual center.
            cx, cy = -(sy + ey) / 2, (sx + ex) / 2
            ox, oy = round(cx - width / 2), round(cy - height / 2)
            center_error = (ox + width / 2 - cx, oy + height / 2 - cy)
        else:
            ox, oy = min(sx, ex), min(sy, ey)
            center_error = (0, 0)
        transform.appendChild(make(doc, "a", "off", x=ox, y=oy))
        transform.appendChild(make(doc, "a", "ext", cx=width, cy=height))
        if old_xfrm is not None:
            props.replaceChild(transform, old_xfrm)
        else:
            props.insertBefore(transform, props.firstChild)
        geometry = make(doc, "a", "prstGeom", prst=f"bentConnector{len(points) - 1}")
        adjustment_list = make(doc, "a", "avLst")
        for index, value in enumerate(adjustments, 1):
            adjustment_list.appendChild(make(doc, "a", "gd", name=f"adj{index}", fmla=f"val {value}"))
        geometry.appendChild(adjustment_list)
        old_geometry = direct(props, "a", "prstGeom") or direct(props, "a", "custGeom")
        if old_geometry is not None:
            props.replaceChild(geometry, old_geometry)
        else:
            props.insertBefore(geometry, transform.nextSibling)
        anchor_name = None
        if record.get("start_anchor"):
            # Old Impress versions may discard a route if their inferred bend
            # count differs from the preset's count. A small transparent anchor
            # supplies an explicit departure side without drawing extra lines.
            spec = record["start_anchor"]
            side = spec.get("side", "bottom")
            if side not in {"top", "left", "bottom", "right"}:
                raise ValueError("start_anchor side must be top, left, bottom, or right")
            anchor_size = max(9525, round(float(spec.get("size_px", 4)) * 9525))
            px, py = points[0]
            anchor_x = px - (anchor_size if side == "right" else 0 if side == "left" else anchor_size / 2)
            anchor_y = py - (anchor_size if side == "bottom" else 0 if side == "top" else anchor_size / 2)
            anchor_name = object_name(connector) + "__route_start_anchor"
            old_anchors = [shape for shape in descendants(doc, "p", "sp") if object_name(shape) == anchor_name]
            if old_anchors:
                anchor = old_anchors[0]
                anchor_id = cnvpr(anchor).getAttribute("id")
                for old in old_anchors:
                    old.parentNode.removeChild(old)
            else:
                anchor_id = str(max(int(n.getAttribute("id")) for n in descendants(doc, "p", "cNvPr")) + 1)
            anchor = make(doc, "p", "sp")
            nonvisual = make(doc, "p", "nvSpPr")
            nonvisual.appendChild(make(doc, "p", "cNvPr", id=anchor_id, name=anchor_name,
                                       descr="Transparent routing anchor for native elbow connector"))
            nonvisual.appendChild(make(doc, "p", "cNvSpPr"))
            nonvisual.appendChild(make(doc, "p", "nvPr"))
            anchor.appendChild(nonvisual)
            anchor_props = make(doc, "p", "spPr")
            anchor_transform = make(doc, "a", "xfrm")
            anchor_transform.appendChild(make(doc, "a", "off", x=round(anchor_x), y=round(anchor_y)))
            anchor_transform.appendChild(make(doc, "a", "ext", cx=anchor_size, cy=anchor_size))
            anchor_props.appendChild(anchor_transform)
            anchor_geom = make(doc, "a", "prstGeom", prst="rect")
            anchor_geom.appendChild(make(doc, "a", "avLst"))
            anchor_props.appendChild(anchor_geom)
            anchor_props.appendChild(make(doc, "a", "noFill"))
            anchor_line = make(doc, "a", "ln")
            anchor_line.appendChild(make(doc, "a", "noFill"))
            anchor_props.appendChild(anchor_line)
            anchor.appendChild(anchor_props)
            connector.parentNode.insertBefore(anchor, connector)
            conn_props = direct(direct(connector, "p", "nvCxnSpPr"), "p", "cNvCxnSpPr")
            starts = descendants(connector, "a", "stCxn")
            start = starts[0] if starts else make(doc, "a", "stCxn")
            if not starts:
                conn_props.insertBefore(start, conn_props.firstChild)
            start.setAttribute("id", anchor_id)
            start.setAttribute("idx", str({"top": 0, "left": 1, "bottom": 2, "right": 3}[side]))
        for field, local_name in (("start_idx", "stCxn"), ("end_idx", "endCxn")):
            if field == "start_idx" and anchor_name:
                continue
            if field in record:
                connection = descendants(connector, "a", local_name)
                if not connection and record.get("detach"):
                    continue
                if len(connection) != 1:
                    raise ValueError(f"Connector {object_name(connector)!r} lacks one {local_name} reference")
                connection[0].setAttribute("idx", str(int(record[field])))
        if record.get("detach"):
            # Some consumers reroute an attached rotated connector on import.
            # Detaching preserves editable preset geometry and its arrow while
            # making the supplied route authoritative in those consumers.
            for local_name in ("stCxn", "endCxn"):
                for connection in descendants(connector, "a", local_name):
                    connection.parentNode.removeChild(connection)
        x1 = width * adjustments[0] / 100000 if adjustments else width
        y2 = height * adjustments[1] / 100000 if len(points) >= 5 else height
        actual_local = [(0, 0), (x1, 0), (x1, y2)]
        if len(points) == 6:
            x3 = width * adjustments[2] / 100000
            actual_local += [(x3, y2), (x3, height), (width, height)]
        elif len(points) == 5:
            actual_local += [(width, y2), (width, height)]
        elif len(points) == 4:
            actual_local += [(width, height)]
        actual = [(sx + x * sign_x, sy + y * sign_y) for x, y in actual_local]
        if vertical_first:
            actual = [(-y + center_error[0], x + center_error[1]) for x, y in actual]
        error = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(points, actual)) / 9525
        record["hits"] += 1
        events.append({"slide": slide_number, "name": object_name(connector),
                       "geometry": geometry.getAttribute("prst"), "adjustments": adjustments,
                       "rotation_degrees": 90 if vertical_first else 0,
                       "detached": bool(record.get("detach")),
                       "start_anchor": anchor_name,
                       "requested_points_px": [[x / 9525, y / 9525] for x, y in points],
                       "rendered_points_px": [[x / 9525, y / 9525] for x, y in actual],
                       "max_vertex_error_px": error})
    return events


def read_subscript_map(map_path):
    if map_path is None:
        return []
    source = json.loads(map_path.read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        raise ValueError("Subscript map must be a JSON object")
    records = []
    for token, spec in source.items():
        if (not token or not isinstance(spec, dict)
                or not isinstance(spec.get("base"), str) or not spec["base"]
                or not isinstance(spec.get("subscript"), str) or not spec["subscript"]
                or spec["base"] + spec["subscript"] != token):
            raise ValueError("Every subscript token must equal its nonempty base + subscript")
        records.append({"token": token, **spec, "hits": 0})
    return records


def format_subscripts(doc, slide_number, records):
    """Split native text runs, retaining characters and unrelated properties."""
    if not records:
        return []
    by_token = {record["token"]: record for record in records}
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(
        re.escape(token) for token in sorted(by_token, key=len, reverse=True)) + r")(?!\w)")
    events = []
    for run in list(descendants(doc, "a", "r")):
        text_node = direct(run, "a", "t")
        if text_node is None:
            continue
        source = "".join(n.data for n in text_node.childNodes
                         if n.nodeType in {Node.TEXT_NODE, Node.CDATA_SECTION_NODE})
        matches = list(pattern.finditer(source))
        if not matches:
            continue
        rpr = direct(run, "a", "rPr")
        size = rpr.getAttribute("sz") if rpr is not None else ""
        if not size:
            ppr = direct(run.parentNode, "a", "pPr")
            default = direct(ppr, "a", "defRPr") if ppr is not None else None
            size = default.getAttribute("sz") if default is not None else ""
        if not size or int(size) <= 0:
            raise ValueError(f"Subscript run needs an explicit positive font size: {source!r}")
        pieces, cursor = [], 0
        for match in matches:
            record = by_token[match.group()]
            pieces.append((source[cursor:match.start()] + record["base"], False))
            pieces.append((record["subscript"], True))
            cursor = match.end()
            record["hits"] += 1
            events.append({"slide": slide_number, "token": match.group(),
                           "base_font_size": int(size), "subscript_font_size": round(int(size) * .7),
                           "baseline": -25000})
        pieces.append((source[cursor:], False))
        assert "".join(value for value, _ in pieces) == source
        for value, subscript in pieces:
            if not value:
                continue
            new_run = run.cloneNode(deep=True)
            new_text = direct(new_run, "a", "t")
            while new_text.firstChild is not None:
                new_text.removeChild(new_text.firstChild)
            new_text.appendChild(doc.createTextNode(value))
            if value[0].isspace() or value[-1].isspace():
                new_text.setAttributeNS("http://www.w3.org/XML/1998/namespace", "xml:space", "preserve")
            if subscript:
                new_rpr = direct(new_run, "a", "rPr")
                if new_rpr is None:
                    new_rpr = make(doc, "a", "rPr")
                    new_run.insertBefore(new_rpr, new_run.firstChild)
                new_rpr.setAttribute("baseline", "-25000")
                new_rpr.setAttribute("sz", str(round(int(size) * .7)))
            run.parentNode.insertBefore(new_run, run)
        run.parentNode.removeChild(run)
    return events


def map_matches(nv, record, slide_number, picture_index):
    if record.get("slide") is not None and int(record["slide"]) != slide_number:
        return False
    if record.get("picture_index") is not None:
        return int(record["picture_index"]) == picture_index
    fields = ["name", "descr", "title"] if record["field"] == "auto" else [record["field"]]
    values = [nv.getAttribute(field) for field in fields]
    return (any(record["match"] in value for value in values) if record.get("contains")
            else record["match"] in values)


def rels_path(slide_path):
    return posixpath.join(posixpath.dirname(slide_path), "_rels", posixpath.basename(slide_path) + ".rels")


def ensure_svg_content_type(files):
    path = "[Content_Types].xml"
    doc = minidom.parseString(files[path])
    defaults = descendants(doc, "ct", "Default")
    entry = next((n for n in defaults if n.getAttribute("Extension").lower() == "svg"), None)
    if entry is None:
        entry = doc.createElementNS(NS["ct"], "Default")
        entry.setAttributeNS(XMLNS, "xmlns", NS["ct"])
        entry.setAttribute("Extension", "svg")
        doc.documentElement.appendChild(entry)
    entry.setAttribute("ContentType", "image/svg+xml")
    files[path] = doc.toxml(encoding="UTF-8")


def embed_svgs(doc, slide_path, slide_number, records, files):
    if not records:
        return []
    relation_path = rels_path(slide_path)
    if relation_path not in files:
        rel_doc = minidom.parseString(f'<Relationships xmlns="{NS["rel"]}"/>')
    else:
        rel_doc = minidom.parseString(files[relation_path])
    relations = {r.getAttribute("Id"): r for r in descendants(rel_doc, "rel", "Relationship")}
    events = []
    for picture_index, picture in enumerate(descendants(doc, "p", "pic"), 1):
        nv = cnvpr(picture)
        matches = [r for r in records if nv is not None and map_matches(nv, r, slide_number, picture_index)]
        if len(matches) > 1:
            raise ValueError(f"Multiple SVG mappings match slide {slide_number}, {object_name(picture)!r}")
        if not matches:
            continue
        record = matches[0]
        if record.get("name"):
            nv.setAttribute("name", record["name"])
            nv.setAttribute("descr", record.get("descr", record["name"]))
        blips = descendants(picture, "a", "blip")
        if len(blips) != 1:
            raise ValueError(f"Expected one raster blip in {object_name(picture)!r}")
        blip = blips[0]
        fallback_id = blip.getAttributeNS(NS["r"], "embed")
        fallback_rel = relations.get(fallback_id)
        if fallback_rel is None:
            raise ValueError(f"Picture {object_name(picture)!r} has no embedded fallback relation")
        fallback_path = posixpath.normpath(posixpath.join(posixpath.dirname(slide_path),
                                                        fallback_rel.getAttribute("Target"))).lstrip("/")
        fallback = files.get(fallback_path, b"")
        if not fallback.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError(f"Picture {object_name(picture)!r} must already have a PNG fallback")
        digest = hashlib.sha256(record["payload"]).hexdigest()[:20]
        media_path = f"ppt/media/native_{digest}.svg"
        files[media_path] = record["payload"]
        target = posixpath.relpath(media_path, posixpath.dirname(slide_path))
        existing = next((rid for rid, relation in relations.items()
                         if relation.getAttribute("Type") == IMAGE_REL
                         and relation.getAttribute("Target") == target), None)
        if existing is None:
            next_id = max([int(m.group(1)) for rid in relations
                           if (m := re.fullmatch(r"rId(\d+)", rid))], default=0) + 1
            existing = f"rId{next_id}"
            relation = rel_doc.createElementNS(NS["rel"], "Relationship")
            relation.setAttributeNS(XMLNS, "xmlns", NS["rel"])
            for attr, value in {"Id": existing, "Type": IMAGE_REL, "Target": target}.items():
                relation.setAttribute(attr, value)
            rel_doc.documentElement.appendChild(relation)
            relations[existing] = relation
        ext_list = direct(blip, "a", "extLst")
        if ext_list is None:
            ext_list = make(doc, "a", "extLst")
            blip.appendChild(ext_list)
        # Replace an existing SVG extension, retaining all unrelated extensions.
        for extension in list(children(ext_list, NS["a"], "ext")):
            if extension.getAttribute("uri").upper() == SVG_EXT_URI:
                ext_list.removeChild(extension)
        extension = make(doc, "a", "ext", uri=SVG_EXT_URI)
        svg_blip = make(doc, "asvg", "svgBlip")
        svg_blip.setAttributeNS(XMLNS, "xmlns:asvg", NS["asvg"])
        svg_blip.setAttributeNS(XMLNS, "xmlns:r", NS["r"])
        svg_blip.setAttributeNS(NS["r"], "r:embed", existing)
        extension.appendChild(svg_blip)
        ext_list.appendChild(extension)
        record["hits"] += 1
        events.append({"slide": slide_number, "name": object_name(picture),
                       "svg": record["source"], "fallback": fallback_path,
                       "media": media_path})
    if events:
        files[relation_path] = rel_doc.toxml(encoding="UTF-8")
        ensure_svg_content_type(files)
    return events


def slide_paths(files):
    """Return display order, which need not match slide part numbers."""
    presentation = minidom.parseString(files["ppt/presentation.xml"])
    rel_path = "ppt/_rels/presentation.xml.rels"
    if rel_path not in files:
        raise ValueError("Presentation lacks its relationships part")
    rel_doc = minidom.parseString(files[rel_path])
    relations = {r.getAttribute("Id"): r for r in descendants(rel_doc, "rel", "Relationship")}
    paths = []
    for slide in descendants(presentation, "p", "sldId"):
        rid = slide.getAttributeNS(NS["r"], "id")
        rel = relations.get(rid)
        if rel is None or rel.getAttribute("TargetMode") == "External":
            raise ValueError(f"Slide relationship {rid!r} is absent or external")
        if rel.getAttribute("Type") != NS["r"] + "/slide":
            raise ValueError(f"Relationship {rid!r} does not target a slide")
        path = posixpath.normpath(posixpath.join("ppt", rel.getAttribute("Target"))).lstrip("/")
        if path not in files:
            raise ValueError(f"Presentation references missing slide {path!r}")
        paths.append(path)
    if len(paths) != len(set(paths)):
        raise ValueError("Presentation repeats a slide part")
    if not paths:
        raise ValueError("Presentation contains no slides")
    return paths


def mutually_exclusive_compatibility_nodes(first, second):
    """Two XML objects cannot coexist if any shared AlternateContent chooses different branches."""
    def branches(node):
        result = {}
        while node.parentNode is not None:
            parent = node.parentNode
            if (node.namespaceURI == NS["mc"] and node.localName in {"Choice", "Fallback"}
                    and parent.namespaceURI == NS["mc"] and parent.localName == "AlternateContent"):
                result[parent] = node
            node = parent
        return result
    first_branches, second_branches = branches(first), branches(second)
    return any(container in second_branches and branch is not second_branches[container]
               for container, branch in first_branches.items())


def audit(files, expected_ratio=None, require_end_arrows=False):
    presentation = minidom.parseString(files["ppt/presentation.xml"])
    sizes = descendants(presentation, "p", "sldSz")
    errors, warnings = [], []
    if not sizes:
        raise ValueError("Presentation has no p:sldSz")
    width, height = int(sizes[0].getAttribute("cx")), int(sizes[0].getAttribute("cy"))
    if width <= 0 or height <= 0:
        errors.append("Canvas dimensions must be positive")
    elif expected_ratio is not None and not math.isclose(width / height, expected_ratio, abs_tol=1e-6):
        errors.append(f"Canvas width:height does not equal expected ratio {expected_ratio}")
    pages = []
    for page_number, path in enumerate(slide_paths(files), 1):
        doc = minidom.parseString(files[path])
        nodes_by_id = defaultdict(list)
        for node in descendants(doc, "p", "cNvPr"):
            nodes_by_id[node.getAttribute("id")].append(node)
        ids = list(nodes_by_id)
        duplicates = [value for value, nodes in nodes_by_id.items()
                      if any(not mutually_exclusive_compatibility_nodes(first, second)
                             for index, first in enumerate(nodes) for second in nodes[index + 1:])]
        if duplicates:
            errors.append(f"Slide {page_number}: duplicate object IDs {duplicates}")
        refs, connections = [], []
        for connector in descendants(doc, "p", "cxnSp"):
            props = direct(connector, "p", "spPr")
            line = direct(props, "a", "ln") if props is not None else None
            tail = direct(line, "a", "tailEnd") if line is not None else None
            head = direct(line, "a", "headEnd") if line is not None else None
            arrow = tail.getAttribute("type") if tail is not None else "none"
            geometry = direct(props, "a", "prstGeom") if props is not None else None
            targets = []
            for local in ("stCxn", "endCxn"):
                for ref in descendants(connector, "a", local):
                    target = ref.getAttribute("id")
                    targets.append({"end": local, "id": target, "idx": ref.getAttribute("idx")})
                    if target not in ids:
                        refs.append(target)
            info = {"id": cnvpr(connector).getAttribute("id"), "name": object_name(connector),
                    "geometry": geometry.getAttribute("prst") if geometry is not None else None,
                    "tail_arrow": arrow,
                    "head_arrow": head.getAttribute("type") if head is not None else "none",
                    "connections": targets}
            connections.append(info)
            if arrow in {"", "none"} and info["head_arrow"] in {"", "none"}:
                message = f"Slide {page_number}: connector {info['name']!r} has no explicit arrow"
                (errors if require_end_arrows else warnings).append(message)
        if refs:
            errors.append(f"Slide {page_number}: unresolved connector target IDs {sorted(set(refs))}")
        suspect_shapes, block_arrows = [], []
        for shape in descendants(doc, "p", "sp"):
            for geom in descendants(shape, "a", "prstGeom"):
                kind = geom.getAttribute("prst")
                if kind in {"triangle", "rtTriangle"}:
                    suspect_shapes.append({"name": object_name(shape), "geometry": kind})
                elif "arrow" in kind.lower():
                    block_arrows.append({"name": object_name(shape), "geometry": kind})
        if suspect_shapes:
            warnings.append(f"Slide {page_number}: inspect {len(suspect_shapes)} triangle "
                            "shapes; their geometry alone cannot prove they are detached arrowheads")
        groups = [{"id": cnvpr(g).getAttribute("id"), "name": object_name(g),
                   "direct_objects": sum(c.localName in DRAWABLES for c in children(g, NS["p"]))}
                  for g in descendants(doc, "p", "grpSp")]
        pages.append({"slide": page_number, "part": path,
                      "shapes": len(descendants(doc, "p", "sp")),
                      "groups": len(groups), "connectors": len(connections),
                      "tables": len(descendants(doc, "a", "tbl")),
                      "images": len(descendants(doc, "p", "pic")),
                      "svg_images": len(descendants(doc, "asvg", "svgBlip")),
                      "top_level_objects": sum(c.localName in DRAWABLES
                                               for c in children(descendants(doc, "p", "spTree")[0], NS["p"])),
                      "group_details": groups, "connector_details": connections,
                      "triangle_or_arrow_shapes": suspect_shapes,
                      "native_block_arrows": block_arrows})
    return {"canvas_emu": [width, height], "width_height_ratio": width / height if height else None,
            "slide_count": len(pages), "slides": pages, "errors": errors, "warnings": warnings,
            "passed": not errors}


def validate_output(input_path, output_path, overwrite):
    if output_path.resolve() == input_path.resolve() and not overwrite:
        raise ValueError("In-place modification requires --overwrite")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"Output exists; use --overwrite explicitly: {output_path}")


def atomic_zip_write(output_path, files, infos, overwrite):
    """Publish only a verified archive; link() also prevents overwrite races."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix="." + output_path.name + ".", suffix=".tmp",
                                    dir=output_path.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, payload in files.items():
                archive.writestr(infos.get(name, name), payload)
        with zipfile.ZipFile(tmp_path) as archive:
            if archive.testzip() is not None:
                raise ValueError("Output ZIP archive verification failed")
            if set(archive.namelist()) != set(files):
                raise ValueError("Output ZIP entry verification failed")
            for name, payload in files.items():
                if archive.read(name) != payload:
                    raise ValueError(f"Output entry bytes differ: {name}")
        with tmp_path.open("rb") as stream:
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(tmp_path, output_path)
        else:
            os.link(tmp_path, output_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def read_pptx(input_path):
    with zipfile.ZipFile(input_path) as archive:
        if archive.testzip() is not None:
            raise ValueError("Input ZIP archive has a corrupt entry")
        infos = {item.filename: item for item in archive.infolist()}
        if len(infos) != len(archive.infolist()):
            raise ValueError("Input ZIP archive has duplicate entry names")
        files = {name: archive.read(name) for name in infos}
    if "ppt/presentation.xml" not in files or "[Content_Types].xml" not in files:
        raise ValueError("Input lacks required PPTX presentation parts")
    return infos, files


def package(input_path, output_path, svg_map_path=None, route_map_path=None, expected_ratio=None,
            subscript_map_path=None, overwrite=False, allow_interleaved_groups=False,
            require_end_arrows=False):
    input_path, output_path = Path(input_path), Path(output_path)
    validate_output(input_path, output_path, overwrite)
    infos, files = read_pptx(input_path)
    records = read_svg_map(svg_map_path)
    routes = read_route_map(route_map_path)
    subscripts = read_subscript_map(subscript_map_path)
    grouped, embedded, warnings, routed, formatted = [], [], [], [], []
    for page_number, path in enumerate(slide_paths(files), 1):
        doc = minidom.parseString(files[path])
        formatted.extend(format_subscripts(doc, page_number, subscripts))
        group_events, group_warnings = group_slide(doc, page_number, allow_interleaved_groups)
        grouped.extend(group_events)
        warnings.extend(group_warnings)
        routed.extend(route_connectors(doc, page_number, routes))
        embedded.extend(embed_svgs(doc, path, page_number, records, files))
        files[path] = doc.toxml(encoding="UTF-8")
    unmatched = [record.get("match", f"slide={record.get('slide')},picture={record.get('picture_index')}")
                 for record in records if not record["hits"]]
    if unmatched:
        raise ValueError(f"SVG selectors did not match any picture: {unmatched}")
    unmatched_routes = [record["name"] for record in routes if not record["hits"]]
    if unmatched_routes:
        raise ValueError(f"Route selectors did not match any connector: {unmatched_routes}")
    unmatched_subscripts = [record["token"] for record in subscripts if not record["hits"]]
    if unmatched_subscripts:
        raise ValueError(f"Subscript tokens did not match a text run: {unmatched_subscripts}")
    result = audit(files, expected_ratio, require_end_arrows)
    result.update({"input": str(input_path.resolve()), "output": str(output_path.resolve()),
                   "created_groups": grouped, "embedded_svgs": embedded, "routed_connectors": routed,
                   "formatted_subscripts": formatted})
    result["warnings"].extend(warnings)
    if result["errors"]:
        raise ValueError("Audit failed; no PPTX written: " + "; ".join(result["errors"]))
    atomic_zip_write(output_path, files, infos, overwrite)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--svg-map", type=Path)
    parser.add_argument("--route-map", type=Path)
    parser.add_argument("--subscript-map", type=Path)
    parser.add_argument("--expected-ratio", type=float, help="Optional canvas width/height check")
    parser.add_argument("--allow-interleaved-groups", action="store_true")
    parser.add_argument("--require-end-arrows", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--audit-json", type=Path)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Audit-only exits 2 on errors; packaging always rejects errors")
    args = parser.parse_args(argv)
    if not args.audit_only and args.output is None:
        parser.error("output is required unless --audit-only is specified")
    if args.audit_only and (args.output or args.svg_map or args.route_map or args.subscript_map
                            or args.allow_interleaved_groups):
        parser.error("--audit-only cannot be combined with output or mutation options")
    if args.expected_ratio is not None and (not math.isfinite(args.expected_ratio) or args.expected_ratio <= 0):
        parser.error("--expected-ratio must be positive and finite")
    try:
        if args.audit_json is not None:
            if args.audit_json.resolve() in {args.input.resolve(), args.output.resolve() if args.output else None}:
                raise ValueError("Audit JSON cannot overwrite a PPTX input or output")
            if args.audit_json.exists() and not args.overwrite:
                raise FileExistsError("Audit JSON exists; use --overwrite explicitly")
        if args.audit_only:
            _, files = read_pptx(args.input)
            result = audit(files, args.expected_ratio, args.require_end_arrows)
        else:
            result = package(args.input, args.output, args.svg_map, args.route_map, args.expected_ratio,
                             args.subscript_map, args.overwrite, args.allow_interleaved_groups,
                             args.require_end_arrows)
        payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.audit_json is not None:
            args.audit_json.parent.mkdir(parents=True, exist_ok=True)
            mode = "w" if args.overwrite else "x"
            with args.audit_json.open(mode, encoding="utf-8") as stream:
                stream.write(payload)
        print(payload, end="")
        return 2 if args.strict and result["errors"] else 0
    except (OSError, ValueError, zipfile.BadZipFile, KeyError, ExpatError) as exc:
        print(f"native_objects.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
