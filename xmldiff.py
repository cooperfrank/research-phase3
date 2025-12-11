#!/usr/bin/env python3
"""
android_xml_diff.py

Compare two Android UI XML dumps and report non-cosmetic differences.
Usage:
    python android_xml_diff.py base.xml input.xml
"""

import xml.etree.ElementTree as ET
import sys
import difflib
import json

# Configuration: adjust to tune sensitivity
KEY_ATTRS = ("resource-id", "content-desc", "class", "checked", "enabled",
             "clickable", "focusable", "selected", "index", "package")
IGNORE_PREFIXES = ("textSize", "textStyle", "textColor", "background", "alpha", "font")
TEXT_SIMILARITY_THRESHOLD = 0.9


def normalize_text(s):
    """
    Normalize text by removing extra whitespace and stripping leading/trailing spaces.

    Args:
        s: Input string to normalize

    Returns:
        Normalized string with single spaces between words, or empty string if input is None/empty
    """
    if not s:
        return ""
    return " ".join(s.split()).strip()


def strip_ns(tag):
    """
    Strip XML namespace from tag name.

    Args:
        tag: XML tag name that may contain namespace prefix

    Returns:
        Tag name without namespace prefix
    """
    if tag and tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def parse_xml(path):
    """
    Parse an XML file and return its root element.

    Args:
        path: File path to the XML file

    Returns:
        Root element of the parsed XML tree
    """
    return ET.parse(path).getroot()


def parse_bounds(bounds_str):
    """
    Parse Android UI bounds string into coordinate tuple.

    Args:
        bounds_str: Bounds string in format "[x1,y1][x2,y2]"

    Returns:
        Tuple of (x1, y1, x2, y2) coordinates, or None if parsing fails
    """
    if not bounds_str:
        return None
    try:
        p = bounds_str.replace("][", " ").replace("[", "").replace("]", "").split()
        x1, y1 = map(int, p[0].split(","))
        x2, y2 = map(int, p[1].split(","))
        return (x1, y1, x2, y2)
    except Exception:
        return None


def node_info(elem, path):
    """
    Extract relevant information from an XML element node.

    Args:
        elem: XML element to extract information from
        path: XPath-like string representing the element's position in the tree

    Returns:
        Dictionary containing id, class, content, text, bounds, filtered attributes, path, and element reference
    """
    attrib = dict(elem.attrib)
    rid = attrib.get("resource-id") or attrib.get("resource_id") or attrib.get("id")
    content = normalize_text(attrib.get("content-desc") or attrib.get("content_desc") or attrib.get("contentDescription"))
    text = normalize_text(attrib.get("text"))
    cls = attrib.get("class") or attrib.get("className") or strip_ns(elem.tag)
    bounds = parse_bounds(attrib.get("bounds"))

    filtered = {}
    for k, v in attrib.items():
        if k in KEY_ATTRS:
            filtered[k] = v
        elif not any(k.startswith(pref) for pref in IGNORE_PREFIXES):
            # keep other small state-like attributes if present
            if k in ("checked", "enabled", "clickable", "selected", "focusable"):
                filtered[k] = v

    return {
        "id": rid,
        "class": cls,
        "content": content,
        "text": text,
        "bounds": bounds,
        "attrib": filtered,
        "path": path,
        "elem": elem
    }


def collect_nodes(root):
    """
    Recursively collect all nodes from an XML tree with path information.

    Args:
        root: Root element of the XML tree

    Returns:
        List of node information dictionaries for all nodes in the tree
    """
    nodes = []
    stack = [(root, "/" + strip_ns(root.tag) + "[0]")]
    while stack:
        elem, path = stack.pop()
        nodes.append(node_info(elem, path))
        children = list(elem)
        for i, child in enumerate(reversed(children)):
            idx = len(children) - 1 - i
            child_path = f"{path}/{strip_ns(child.tag)}[{idx}]"
            stack.append((child, child_path))
    return nodes


def str_similarity(a, b):
    """
    Calculate similarity ratio between two strings.

    Args:
        a: First string to compare
        b: Second string to compare

    Returns:
        Float between 0 and 1 representing similarity ratio (1.0 = identical)
    """
    return difflib.SequenceMatcher(None, a or "", b or "").ratio()


def match_by_resource_id(base_nodes, input_nodes, used_input):
    """
    Match nodes between base and input trees by their resource IDs.

    Args:
        base_nodes: List of node information dictionaries from base XML
        input_nodes: List of node information dictionaries from input XML
        used_input: Set to track which input nodes have been matched

    Returns:
        List of (base_node, input_node) tuples representing matches
    """
    matches = []
    base_by_id = {}
    input_by_id = {}
    for n in base_nodes:
        if n["id"]:
            base_by_id.setdefault(n["id"], []).append(n)
    for n in input_nodes:
        if n["id"]:
            input_by_id.setdefault(n["id"], []).append(n)

    for rid, base_group in base_by_id.items():
        input_group = input_by_id.get(rid, [])
        maxlen = max(len(base_group), len(input_group))
        for i in range(maxlen):
            a = base_group[i] if i < len(base_group) else None
            b = input_group[i] if i < len(input_group) else None
            if b:
                used_input.add(id(b["elem"]))
            matches.append((a, b))
    return matches


def match_remaining(base_nodes, input_nodes, used_input):
    """
    Match remaining nodes without resource IDs using heuristic similarity scoring.

    Args:
        base_nodes: List of node information dictionaries from base XML
        input_nodes: List of node information dictionaries from input XML
        used_input: Set of already matched input node element IDs

    Returns:
        List of (base_node, input_node) tuples representing best matches and unmatched nodes
    """
    base_noid = [n for n in base_nodes if not n["id"]]
    input_noid = [n for n in input_nodes if not n["id"] and id(n["elem"]) not in used_input]
    matches = []
    unmatched_input = list(input_noid)

    for a in base_noid:
        best = None
        best_score = 0.0
        for b in unmatched_input:
            if a["class"] != b["class"]:
                continue
            score = max(str_similarity(a["content"], b["content"]) * 1.2,
                        str_similarity(a["text"], b["text"]))
            if a["bounds"] and b["bounds"]:
                ax1, ay1, ax2, ay2 = a["bounds"]
                bx1, by1, bx2, by2 = b["bounds"]
                ix1, iy1 = max(ax1, bx1), max(ay1, by1)
                ix2, iy2 = min(ax2, bx2), min(ay2, by2)
                if ix2 > ix1 and iy2 > iy1:
                    score += 0.05
            if score > best_score:
                best_score = score
                best = b
        if best and best_score > 0.4:
            matches.append((a, best))
            unmatched_input.remove(best)
        else:
            matches.append((a, None))

    for b in unmatched_input:
        matches.append((None, b))

    return matches


def significant_text_change(a_text, b_text):
    """
    Determine if text change between two nodes is significant enough to report.

    Args:
        a_text: Text content from base node
        b_text: Text content from input node

    Returns:
        True if text change is significant (similarity below threshold), False otherwise
    """
    a_norm = normalize_text(a_text)
    b_norm = normalize_text(b_text)
    if a_norm == b_norm:
        return False
    return str_similarity(a_norm, b_norm) < TEXT_SIMILARITY_THRESHOLD


def compare_nodes(pairs):
    """
    Compare matched node pairs and identify significant differences.

    Args:
        pairs: List of (base_node, input_node) tuples to compare

    Returns:
        List of difference dictionaries describing added, removed, and changed nodes
    """
    diffs = []
    for a, b in pairs:
        if a is None and b is not None:
            diffs.append({"type": "added", "path": b["path"], "class": b["class"], "id": b["id"], "text": b["text"]})
            continue
        if b is None and a is not None:
            diffs.append({"type": "removed", "path": a["path"], "class": a["class"], "id": a["id"], "text": a["text"]})
            continue
        if a is None and b is None:
            continue

        # attribute differences
        keys = set(a["attrib"].keys()) | set(b["attrib"].keys())
        for k in sorted(keys):
            va = a["attrib"].get(k)
            vb = b["attrib"].get(k)
            if va != vb:
                diffs.append({"type": "attr_change", "path": a["path"], "class": a["class"], "attr": k, "from": va, "to": vb})

        # text
        if significant_text_change(a["text"], b["text"]):
            diffs.append({"type": "text_change", "path": a["path"], "class": a["class"], "from": a["text"], "to": b["text"]})

        # bounds
        if a["bounds"] and b["bounds"] and a["bounds"] != b["bounds"]:
            diffs.append({"type": "bounds_change", "path": a["path"], "class": a["class"], "from": a["bounds"], "to": b["bounds"]})

    return diffs


def calculate_difference_score(diffs, total_nodes):
    """
    Calculate a normalized difference score between 0 and 1.

    Args:
        diffs: List of difference dictionaries from compare_nodes
        total_nodes: Total number of nodes in the base XML

    Returns:
        Float between 0 (identical) and 1 (completely different)
    """
    if total_nodes == 0:
        return 0.0
    
    # Weight different types of changes
    weights = {
        "added": 1.0,
        "removed": 1.0,
        "attr_change": 0.5,
        "text_change": 0.7,
        "bounds_change": 0.3
    }
    
    weighted_diffs = sum(weights.get(d["type"], 0.5) for d in diffs)
    
    # Normalize by total nodes - cap at 1.0
    score = min(weighted_diffs / total_nodes, 1.0)
    
    return round(score, 4)


def main():
    """
    Main entry point for XML diff tool - compares two Android UI XML dumps.

    Args:
        None (uses command-line arguments sys.argv)

    Returns:
        None (prints differences to stdout as JSON or success message)
    """
    if len(sys.argv) != 3:
        print("usage: python xmldiff.py base.xml input.xml")
        return
    base_root = parse_xml(sys.argv[1])
    input_root = parse_xml(sys.argv[2])

    base_nodes = collect_nodes(base_root)
    input_nodes = collect_nodes(input_root)

    used_input = set()
    pairs = []
    pairs.extend(match_by_resource_id(base_nodes, input_nodes, used_input))
    pairs.extend(match_remaining(base_nodes, input_nodes, used_input))

    diffs = compare_nodes(pairs)
    diff_score = calculate_difference_score(diffs, len(base_nodes))

    if not diffs:
        print("no significant differences found")
    else:
        print(json.dumps(diffs, indent=2, ensure_ascii=False))
    
    print(f"Difference Score: {diff_score:.4f} (0=identical, 1=completely different)")
    print(f"Total Differences: {len(diffs)}")
    


if __name__ == "__main__":
    main()
