#!/usr/bin/env python3
"""
Manage 4D base catalog files (.4DCatalog).

The <project> argument is the 4D project root — the script resolves to
<project>/Project/Sources/catalog.4DCatalog. Pass a direct path ending in
.4DCatalog to override.

Usage:
    catalog.py create <project> <base_name>
    catalog.py info <project>
    catalog.py add-table <project> <table> [field_spec ...] [--no-id]
    catalog.py remove-table <project> <table>
    catalog.py add-field <project> <table> <field_spec> [field_spec ...]
    catalog.py remove-field <project> <table> <field>

Field spec:  name:type[:flag,flag,...]

    Types: bool, int, long, int64, real, date, time, alpha, text,
           picture, blob, object, vector
    Flags: unique, not-null, autosequence, pk, length=N

Examples:
    catalog.py add-table . People Name:alpha:length=128 Age:int Vec:vector
    catalog.py add-field . Order total:real note:text tag:alpha:length=32
"""

import sys
import uuid
from pathlib import Path
from xml.etree import ElementTree as ET

FIELD_TYPES = {
    "bool": 1, "boolean": 1,
    "int": 3, "integer": 3,
    "long": 4, "longint": 4,
    "int64": 5,
    "real": 6, "float": 6,
    "date": 8,
    "time": 9,
    "alpha": 10, "text": 10,
    "picture": 12,
    "blob": 18,
    "object": 21, "vector": 21,
}

TYPE_NAMES = {
    1: "Boolean", 3: "Integer", 4: "Long Integer", 5: "Integer 64",
    6: "Real", 8: "Date", 9: "Time", 10: "Alpha/Text",
    12: "Picture", 18: "BLOB", 21: "Object",
}


def gen_uuid():
    return uuid.uuid4().hex.upper()


def resolve_catalog(project):
    """Project root → <project>/Project/Sources/catalog.4DCatalog.
    Pass a path ending in .4DCatalog to override."""
    p = Path(project)
    if p.suffix == ".4DCatalog":
        return p
    return p / "Project" / "Sources" / "catalog.4DCatalog"


def indent_xml(elem, level=0):
    indent = "\n" + "\t" * level
    child_indent = "\n" + "\t" * (level + 1)
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = child_indent
        for child in elem:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
    else:
        if level > 0 and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent


def write_catalog(root, path):
    import copy
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    root_copy = copy.deepcopy(root)
    # DTD requires base_extra to be the last child of base
    base_extra = root_copy.find("base_extra")
    if base_extra is not None:
        root_copy.remove(base_extra)
        root_copy.append(base_extra)
    indent_xml(root_copy)
    body = ET.tostring(root_copy, encoding="unicode", xml_declaration=False)
    header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    header += '<!DOCTYPE base SYSTEM "http://www.4d.com/dtd/2007/base.dtd" >\n'
    path.write_text(header + body + "\n", encoding="utf-8")


def load_catalog(path):
    path = Path(path)
    if not path.exists():
        sys.exit(f"Error: catalog not found: {path}")
    return ET.parse(str(path)).getroot()


def find_table(root, name):
    for t in root.findall("table"):
        if t.get("name") == name:
            return t
    return None


def next_table_id(root):
    return max((int(t.get("id", 0)) for t in root.findall("table")), default=0) + 1


def next_field_id(table):
    return max((int(f.get("id", 0)) for f in table.findall("field")), default=0) + 1


def parse_spec(spec):
    """Parse 'name:type[:flag,flag,length=N]' → dict."""
    parts = spec.split(":", 2)
    if len(parts) < 2:
        sys.exit(f"Error: bad field spec '{spec}' — expected name:type[:flags]")
    name, type_str = parts[0], parts[1].lower()
    if type_str not in FIELD_TYPES:
        sys.exit(f"Error: unknown type '{type_str}' in spec '{spec}'")
    out = {"name": name, "type": type_str, "unique": False, "not_null": False,
           "autosequence": False, "pk": False, "length": 255}
    if len(parts) == 3:
        for flag in parts[2].split(","):
            flag = flag.strip()
            if flag == "unique":
                out["unique"] = True
            elif flag == "not-null":
                out["not_null"] = True
            elif flag == "autosequence":
                out["autosequence"] = True
            elif flag == "pk":
                out["pk"] = True
            elif flag.startswith("length="):
                out["length"] = int(flag.split("=", 1)[1])
            elif flag:
                sys.exit(f"Error: unknown flag '{flag}' in spec '{spec}'")
    return out


def add_index_for_field(root, table, field_uuid, field_name, unique=True):
    idx = ET.SubElement(root, "index")
    idx.set("kind", "regular")
    if unique:
        idx.set("unique_keys", "true")
    idx.set("uuid", gen_uuid())
    idx.set("type", "7")
    fref = ET.SubElement(idx, "field_ref")
    fref.set("uuid", field_uuid)
    fref.set("name", field_name)
    tref = ET.SubElement(fref, "table_ref")
    tref.set("uuid", table.get("uuid"))
    tref.set("name", table.get("name"))


def add_field_to_table(root, table, spec):
    for f in table.findall("field"):
        if f.get("name") == spec["name"]:
            sys.exit(f"Error: field '{spec['name']}' already in '{table.get('name')}'")

    type_num = FIELD_TYPES[spec["type"]]
    field_uuid = gen_uuid()

    pk_elem = table.find("primary_key")
    insert_pos = list(table).index(pk_elem) if pk_elem is not None else len(list(table))

    field = ET.Element("field")
    field.set("name", spec["name"])
    field.set("uuid", field_uuid)
    field.set("type", str(type_num))
    if spec["type"] == "alpha":
        field.set("limiting_length", str(spec["length"]))
    if spec["type"] in ("object", "vector"):
        field.set("blob_switch_size", "2147483647")
    if spec["unique"]:
        field.set("unique", "true")
    if spec["autosequence"]:
        field.set("autosequence", "true")
    if spec["not_null"]:
        field.set("not_null", "true")
    field.set("id", str(next_field_id(table)))
    if spec["type"] == "vector":
        ET.SubElement(field, "field_extra").set("class_id", "4D.Vector")
    table.insert(insert_pos, field)

    if spec["pk"]:
        existing_pk = table.find("primary_key")
        if existing_pk is not None:
            table.remove(existing_pk)
        pk = ET.SubElement(table, "primary_key")
        pk.set("field_name", spec["name"])
        pk.set("field_uuid", field_uuid)
        add_index_for_field(root, table, field_uuid, spec["name"], unique=True)

    return field_uuid


# ─── Commands ─────────────────────────────────────────────────────────

def cmd_create(args):
    if len(args) < 2:
        sys.exit("Usage: catalog.py create <project> <base_name>")
    catalog_path = resolve_catalog(args[0])
    if catalog_path.exists():
        sys.exit(f"Error: catalog already exists: {catalog_path}")
    template = Path(__file__).parent.parent / "resources" / "empty_catalog.xml"
    content = template.read_text(encoding="utf-8")
    content = content.replace("{{basename}}", args[1]).replace("{{uuid}}", gen_uuid())
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(content, encoding="utf-8")
    print(f"Created {catalog_path} (base: {args[1]})")


def cmd_info(args):
    if len(args) < 1:
        sys.exit("Usage: catalog.py info <project>")
    root = load_catalog(resolve_catalog(args[0]))
    tables = root.findall("table")
    print(f"Base: {root.get('name')} — {len(tables)} tables, "
          f"{len(root.findall('relation'))} relations, "
          f"{len(root.findall('index'))} indexes")
    for t in tables:
        fields = t.findall("field")
        pk = t.find("primary_key")
        pk_name = pk.get("field_name") if pk is not None else "—"
        print(f"  [{t.get('id'):>2}] {t.get('name')} (pk: {pk_name})")
        for f in fields:
            ftype = int(f.get("type", 0))
            name = TYPE_NAMES.get(ftype, f"type {ftype}")
            fe = f.find("field_extra")
            if fe is not None and fe.get("class_id") == "4D.Vector":
                name = "Vector"
            flags = [k for k, v in [("unique", f.get("unique")),
                                    ("not-null", f.get("not_null")),
                                    ("autosequence", f.get("autosequence"))]
                     if v == "true"]
            extra = f" [{','.join(flags)}]" if flags else ""
            print(f"       [{f.get('id'):>2}] {f.get('name')}: {name}{extra}")


def cmd_add_table(args):
    no_id = "--no-id" in args
    args = [a for a in args if a != "--no-id"]
    if len(args) < 2:
        sys.exit("Usage: catalog.py add-table <project> <table> [field_spec ...] [--no-id]")
    catalog_path = resolve_catalog(args[0])
    table_name = args[1]
    specs = [parse_spec(s) for s in args[2:]]
    root = load_catalog(catalog_path)
    if find_table(root, table_name):
        sys.exit(f"Error: table '{table_name}' already exists")

    table = ET.SubElement(root, "table")
    table.set("name", table_name)
    table.set("uuid", gen_uuid())
    table.set("id", str(next_table_id(root)))

    if not no_id:
        add_field_to_table(root, table, parse_spec("ID:long:unique,autosequence,not-null,pk"))

    for spec in specs:
        add_field_to_table(root, table, spec)

    write_catalog(root, catalog_path)
    note = f" with ID + {len(specs)} field(s)" if specs or not no_id else ""
    print(f"Added table '{table_name}'{note}")


def cmd_remove_table(args):
    if len(args) < 2:
        sys.exit("Usage: catalog.py remove-table <project> <table>")
    catalog_path = resolve_catalog(args[0])
    root = load_catalog(catalog_path)
    table = find_table(root, args[1])
    if table is None:
        sys.exit(f"Error: table '{args[1]}' not found")

    table_uuid = table.get("uuid")
    field_uuids = {f.get("uuid") for f in table.findall("field")}
    root.remove(table)

    for rel in list(root.findall("relation")):
        for rf in rel.findall("related_field"):
            fr = rf.find("field_ref")
            if fr is not None:
                tr = fr.find("table_ref")
                if tr is not None and tr.get("uuid") == table_uuid:
                    root.remove(rel)
                    break

    for idx in list(root.findall("index")):
        for fr in idx.findall("field_ref"):
            if fr.get("uuid") in field_uuids:
                root.remove(idx)
                break

    write_catalog(root, catalog_path)
    print(f"Removed table '{args[1]}'")


def cmd_add_field(args):
    if len(args) < 3:
        sys.exit("Usage: catalog.py add-field <project> <table> <field_spec> [field_spec ...]")
    catalog_path = resolve_catalog(args[0])
    root = load_catalog(catalog_path)
    table = find_table(root, args[1])
    if table is None:
        sys.exit(f"Error: table '{args[1]}' not found")
    specs = [parse_spec(s) for s in args[2:]]
    for spec in specs:
        add_field_to_table(root, table, spec)
    write_catalog(root, catalog_path)
    names = ", ".join(s["name"] for s in specs)
    print(f"Added {len(specs)} field(s) to '{args[1]}': {names}")


def cmd_remove_field(args):
    if len(args) < 3:
        sys.exit("Usage: catalog.py remove-field <project> <table> <field>")
    catalog_path = resolve_catalog(args[0])
    root = load_catalog(catalog_path)
    table = find_table(root, args[1])
    if table is None:
        sys.exit(f"Error: table '{args[1]}' not found")
    field = next((f for f in table.findall("field") if f.get("name") == args[2]), None)
    if field is None:
        sys.exit(f"Error: field '{args[2]}' not found in '{args[1]}'")

    field_uuid = field.get("uuid")
    table.remove(field)

    pk = table.find("primary_key")
    if pk is not None and pk.get("field_uuid") == field_uuid:
        table.remove(pk)

    for idx in list(root.findall("index")):
        for fr in idx.findall("field_ref"):
            if fr.get("uuid") == field_uuid:
                root.remove(idx)
                break

    write_catalog(root, catalog_path)
    print(f"Removed field '{args[2]}' from '{args[1]}'")


COMMANDS = {
    "create": cmd_create,
    "info": cmd_info,
    "add-table": cmd_add_table,
    "remove-table": cmd_remove_table,
    "add-field": cmd_add_field,
    "remove-field": cmd_remove_field,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
