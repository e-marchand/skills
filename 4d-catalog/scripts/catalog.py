#!/usr/bin/env python3
"""
Manage 4D base catalog files (.4DCatalog).

Usage:
    catalog.py create <catalog_path> <base_name>
    catalog.py info <catalog_path>
    catalog.py list-tables <catalog_path>
    catalog.py add-table <catalog_path> <table_name> [--no-id]
    catalog.py remove-table <catalog_path> <table_name>
    catalog.py add-field <catalog_path> <table_name> <field_name> <type> [options]
    catalog.py remove-field <catalog_path> <table_name> <field_name>

Field types:
    bool / boolean      Boolean (type 1)
    int / integer       Integer (type 3)
    long / longint      Long Integer (type 4) — default for IDs
    int64               Integer 64 (type 5)
    real / float        Real (type 6)
    date                Date (type 8)
    time                Time (type 9)
    alpha               Alpha text (type 10, limiting_length=255)
    text                Long text (type 10, no length limit)
    picture             Picture (type 12)
    blob                BLOB (type 18)
    object              Object (type 21)
    vector              Vector — Object with 4D.Vector class (type 21)

add-field options:
    --unique            Mark field as unique
    --not-null          Mark field as not null
    --autosequence      Mark field as autosequence
    --length N          Alpha limiting length (default 255)
    --primary-key       Set as table primary key
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


def resolve_catalog(path_input):
    """Resolve catalog path from various inputs."""
    p = Path(path_input)
    if p.suffix == ".4DCatalog":
        return p
    # Directory: look for catalog inside
    for candidate in [p / "Project" / "Sources" / "catalog.4DCatalog",
                      p / "catalog.4DCatalog"]:
        if candidate.exists():
            return candidate
    # Also try as-is if it exists
    if p.exists():
        return p
    # Default: treat as directory and return expected path
    return p / "Project" / "Sources" / "catalog.4DCatalog"


def indent_xml(elem, level=0):
    """Add pretty-print indentation in-place (tab-based, no trailing blank lines)."""
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
    indent_xml(root_copy)
    body = ET.tostring(root_copy, encoding="unicode", xml_declaration=False)
    header = '<?xml version="1.0" encoding="UTF-8"?>\n'
    header += '<!DOCTYPE base SYSTEM "http://www.4d.com/dtd/2007/base.dtd" >\n'
    path.write_text(header + body + "\n", encoding="utf-8")


def load_catalog(path):
    path = Path(path)
    if not path.exists():
        print(f"Error: catalog not found: {path}")
        sys.exit(1)
    ET.register_namespace("", "")
    return ET.parse(str(path)).getroot()


def next_table_id(root):
    ids = [int(t.get("id", 0)) for t in root.findall("table")]
    return max(ids, default=0) + 1


def next_field_id(table):
    ids = [int(f.get("id", 0)) for f in table.findall("field")]
    return max(ids, default=0) + 1


def find_table(root, name):
    for t in root.findall("table"):
        if t.get("name") == name:
            return t
    return None


def cmd_create(args):
    if len(args) < 2:
        print("Usage: catalog.py create <catalog_path> <base_name>")
        sys.exit(1)
    path, base_name = args[0], args[1]
    catalog_path = resolve_catalog(path)
    if catalog_path.exists():
        print(f"Error: catalog already exists: {catalog_path}")
        sys.exit(1)

    template_path = Path(__file__).parent.parent / "resources" / "empty_catalog.xml"
    content = template_path.read_text(encoding="utf-8")
    content = content.replace("{{basename}}", base_name).replace("{{uuid}}", gen_uuid())

    catalog_path = Path(catalog_path)
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(content, encoding="utf-8")
    print(f"Created catalog: {catalog_path}")
    print(f"  Base name: {base_name}")


def cmd_info(args):
    if len(args) < 1:
        print("Usage: catalog.py info <catalog_path>")
        sys.exit(1)
    root = load_catalog(resolve_catalog(args[0]))
    tables = root.findall("table")
    relations = root.findall("relation")
    indexes = root.findall("index")
    print(f"Base: {root.get('name')} (uuid: {root.get('uuid')})")
    print(f"  Tables:    {len(tables)}")
    print(f"  Relations: {len(relations)}")
    print(f"  Indexes:   {len(indexes)}")
    for t in tables:
        fields = t.findall("field")
        pk = t.find("primary_key")
        pk_name = pk.get("field_name") if pk is not None else "(none)"
        print(f"  [{t.get('id'):>2}] {t.get('name')} — {len(fields)} field(s), pk: {pk_name}")


def cmd_list_tables(args):
    if len(args) < 1:
        print("Usage: catalog.py list-tables <catalog_path>")
        sys.exit(1)
    root = load_catalog(resolve_catalog(args[0]))
    tables = root.findall("table")
    if not tables:
        print("No tables.")
        return
    for t in tables:
        fields = t.findall("field")
        print(f"  [{t.get('id'):>2}] {t.get('name')} ({len(fields)} fields)")
        for f in fields:
            ftype = int(f.get("type", 0))
            type_name = TYPE_NAMES.get(ftype, f"type {ftype}")
            extras = []
            if f.get("autosequence") == "true":
                extras.append("autosequence")
            if f.get("unique") == "true":
                extras.append("unique")
            if f.get("not_null") == "true":
                extras.append("not null")
            fe = f.find("field_extra")
            if fe is not None and fe.get("class_id") == "4D.Vector":
                type_name = "Vector"
            extra_str = f"  [{', '.join(extras)}]" if extras else ""
            print(f"       [{f.get('id'):>2}] {f.get('name')} : {type_name}{extra_str}")


def cmd_add_table(args):
    no_id = "--no-id" in args
    args = [a for a in args if not a.startswith("--")]
    if len(args) < 2:
        print("Usage: catalog.py add-table <catalog_path> <table_name> [--no-id]")
        sys.exit(1)
    catalog_path = resolve_catalog(args[0])
    table_name = args[1]
    root = load_catalog(catalog_path)

    if find_table(root, table_name):
        print(f"Error: table '{table_name}' already exists")
        sys.exit(1)

    table = ET.SubElement(root, "table")
    table.set("name", table_name)
    table.set("uuid", gen_uuid())
    table.set("id", str(next_table_id(root)))

    if not no_id:
        field = ET.SubElement(table, "field")
        field_uuid = gen_uuid()
        field.set("name", "ID")
        field.set("uuid", field_uuid)
        field.set("type", "4")
        field.set("unique", "true")
        field.set("autosequence", "true")
        field.set("not_null", "true")
        field.set("id", "1")

        pk = ET.SubElement(table, "primary_key")
        pk.set("field_name", "ID")
        pk.set("field_uuid", field_uuid)

        index = ET.SubElement(root, "index")
        index.set("kind", "regular")
        index.set("unique_keys", "true")
        index.set("uuid", gen_uuid())
        index.set("type", "7")
        fref = ET.SubElement(index, "field_ref")
        fref.set("uuid", field_uuid)
        fref.set("name", "ID")
        tref = ET.SubElement(fref, "table_ref")
        tref.set("uuid", table.get("uuid"))
        tref.set("name", table_name)

    write_catalog(root, catalog_path)
    id_note = " (with ID field + primary key + index)" if not no_id else ""
    print(f"Added table '{table_name}'{id_note}")


def cmd_remove_table(args):
    if len(args) < 2:
        print("Usage: catalog.py remove-table <catalog_path> <table_name>")
        sys.exit(1)
    catalog_path = resolve_catalog(args[0])
    table_name = args[1]
    root = load_catalog(catalog_path)

    table = find_table(root, table_name)
    if table is None:
        print(f"Error: table '{table_name}' not found")
        sys.exit(1)

    table_uuid = table.get("uuid")
    field_uuids = {f.get("uuid") for f in table.findall("field")}

    # Remove table
    root.remove(table)

    # Remove relations referencing this table
    for rel in root.findall("relation"):
        for rf in rel.findall("related_field"):
            fr = rf.find("field_ref")
            if fr is not None:
                tr = fr.find("table_ref")
                if tr is not None and tr.get("uuid") == table_uuid:
                    root.remove(rel)
                    break

    # Remove indexes referencing this table's fields
    for idx in root.findall("index"):
        for fr in idx.findall("field_ref"):
            if fr.get("uuid") in field_uuids:
                root.remove(idx)
                break

    write_catalog(root, catalog_path)
    print(f"Removed table '{table_name}' (and its relations/indexes)")


def cmd_add_field(args):
    # Parse flags
    unique = "--unique" in args
    not_null = "--not-null" in args
    autosequence = "--autosequence" in args
    primary_key = "--primary-key" in args
    length = 255
    if "--length" in args:
        idx = args.index("--length")
        length = int(args[idx + 1])
        args = args[:idx] + args[idx + 2:]
    args = [a for a in args if not a.startswith("--")]

    if len(args) < 4:
        print("Usage: catalog.py add-field <catalog_path> <table_name> <field_name> <type> [options]")
        sys.exit(1)

    catalog_path = resolve_catalog(args[0])
    table_name, field_name, type_str = args[1], args[2], args[3].lower()

    if type_str not in FIELD_TYPES:
        print(f"Error: unknown type '{type_str}'. Valid: {', '.join(sorted(set(FIELD_TYPES.keys())))}")
        sys.exit(1)

    root = load_catalog(catalog_path)
    table = find_table(root, table_name)
    if table is None:
        print(f"Error: table '{table_name}' not found")
        sys.exit(1)

    # Check field doesn't exist
    for f in table.findall("field"):
        if f.get("name") == field_name:
            print(f"Error: field '{field_name}' already exists in table '{table_name}'")
            sys.exit(1)

    type_num = FIELD_TYPES[type_str]
    field_uuid = gen_uuid()

    # Insert before primary_key and table_extra
    pk_elem = table.find("primary_key")
    insert_pos = list(table).index(pk_elem) if pk_elem is not None else len(list(table))

    field = ET.Element("field")
    field.set("name", field_name)
    field.set("uuid", field_uuid)
    field.set("type", str(type_num))

    if type_str == "alpha":
        field.set("limiting_length", str(length))
    if type_str in ("object", "vector"):
        field.set("blob_switch_size", "2147483647")
    if unique:
        field.set("unique", "true")
    if autosequence:
        field.set("autosequence", "true")
    if not_null:
        field.set("not_null", "true")

    field.set("id", str(next_field_id(table)))

    if type_str == "vector":
        fe = ET.SubElement(field, "field_extra")
        fe.set("class_id", "4D.Vector")

    table.insert(insert_pos, field)

    if primary_key:
        # Replace or add primary_key element
        existing_pk = table.find("primary_key")
        if existing_pk is not None:
            table.remove(existing_pk)
        pk = ET.SubElement(table, "primary_key")
        pk.set("field_name", field_name)
        pk.set("field_uuid", field_uuid)

    write_catalog(root, catalog_path)
    print(f"Added field '{field_name}' ({type_str}) to table '{table_name}'")


def cmd_remove_field(args):
    if len(args) < 3:
        print("Usage: catalog.py remove-field <catalog_path> <table_name> <field_name>")
        sys.exit(1)
    catalog_path = resolve_catalog(args[0])
    table_name, field_name = args[1], args[2]
    root = load_catalog(catalog_path)

    table = find_table(root, table_name)
    if table is None:
        print(f"Error: table '{table_name}' not found")
        sys.exit(1)

    field = None
    for f in table.findall("field"):
        if f.get("name") == field_name:
            field = f
            break
    if field is None:
        print(f"Error: field '{field_name}' not found in table '{table_name}'")
        sys.exit(1)

    field_uuid = field.get("uuid")
    table.remove(field)

    # Remove primary_key if it references this field
    pk = table.find("primary_key")
    if pk is not None and pk.get("field_uuid") == field_uuid:
        table.remove(pk)
        print(f"  Note: removed primary key referencing '{field_name}'")

    # Remove indexes referencing this field
    for idx in root.findall("index"):
        for fr in idx.findall("field_ref"):
            if fr.get("uuid") == field_uuid:
                root.remove(idx)
                print(f"  Note: removed index referencing '{field_name}'")
                break

    write_catalog(root, catalog_path)
    print(f"Removed field '{field_name}' from table '{table_name}'")


COMMANDS = {
    "create": cmd_create,
    "info": cmd_info,
    "list-tables": cmd_list_tables,
    "add-table": cmd_add_table,
    "remove-table": cmd_remove_table,
    "add-field": cmd_add_field,
    "remove-field": cmd_remove_field,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: catalog.py <command> [args]")
        print("Commands:", ", ".join(COMMANDS.keys()))
        sys.exit(1)
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
