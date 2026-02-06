#!/usr/bin/env python3
"""Look up 4D documentation by command, class, or topic name.

Generates the correct developer.4d.com URL and optionally fetches content.
"""

import json
import re
import sys
import urllib.request
import urllib.error
from html.parser import HTMLParser


# URL patterns for developer.4d.com
BASE_URL = "https://developer.4d.com/docs"

# Known class name mappings to API doc page names
CLASS_MAP = {
    "blob": "BlobClass",
    "collection": "CollectionClass",
    "cryptokey": "CryptoKeyClass",
    "dataclass": "DataClassClass",
    "datastore": "DataStoreClass",
    "email": "EmailObjectClass",
    "entity": "EntityClass",
    "entityselection": "EntitySelectionClass",
    "file": "FileClass",
    "folder": "FolderClass",
    "formdata": "FormDataClass",
    "httpagent": "HTTPAgentClass",
    "httprequest": "HTTPRequestClass",
    "imap transporter": "IMAPTransporterClass",
    "mailbox": "MailboxClass",
    "object": "ObjectClass",
    "outgoingmessage": "OutGoingMessageClass",
    "pop3 transporter": "POP3TransporterClass",
    "session": "SessionClass",
    "sessionsstorage": "SessionsStorageClass",
    "signal": "SignalClass",
    "smtp transporter": "SMTPTransporterClass",
    "systemworker": "SystemWorkerClass",
    "webform": "WebFormClass",
    "webformitem": "WebFormItemClass",
    "webserver": "WebServerClass",
    "websocket": "WebSocketClass",
    "websocketconnection": "WebSocketConnectionClass",
    "websocketserver": "WebSocketServerClass",
    "ziparchive": "ZipArchiveClass",
    "zipfile": "ZipFileClass",
    "zipfolder": "ZipFolderClass",
}

# Topic categories
TOPIC_MAP = {
    "orda": "ORDA/overview",
    "variables": "Concepts/variables",
    "methods": "Concepts/methods",
    "classes": "Concepts/classes",
    "parameters": "Concepts/parameters",
    "shared": "Concepts/shared",
    "error handling": "Concepts/error-handling",
    "data types": "Concepts/data-types",
    "collections": "Concepts/collections",
    "objects": "Concepts/objects",
    "forms": "FormEditor/forms",
    "listbox": "FormObjects/listbox_overview",
    "web server": "WebServer/webServer",
    "rest": "REST/gettingStarted",
    "preferences": "Preferences/overview",
    "users": "Users/overview",
    "backup": "Backup/overview",
    "compiler": "Project/compiler",
    "components": "Project/components",
    "architecture": "Project/architecture",
}


class TextExtractor(HTMLParser):
    """Extract text from HTML, focusing on article content."""

    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_article = False
        self.skip = False
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")
        if tag == "article" or "markdown" in cls or "theme-doc-markdown" in cls:
            self.in_article = True
        if tag in ("nav", "footer", "script", "style", "header"):
            self.skip = True
            self.depth += 1
        if tag in ("h1", "h2", "h3", "h4"):
            self.text_parts.append("\n## ")
        if tag == "p":
            self.text_parts.append("\n")
        if tag == "code":
            self.text_parts.append("`")
        if tag == "pre":
            self.text_parts.append("\n```\n")

    def handle_endtag(self, tag):
        if tag in ("nav", "footer", "script", "style", "header"):
            self.depth -= 1
            if self.depth <= 0:
                self.skip = False
                self.depth = 0
        if tag == "code":
            self.text_parts.append("`")
        if tag == "pre":
            self.text_parts.append("\n```\n")

    def handle_data(self, data):
        if not self.skip:
            self.text_parts.append(data)

    def get_text(self) -> str:
        return "".join(self.text_parts).strip()


def command_to_slug(command: str) -> str:
    """Convert a 4D command name to URL slug."""
    slug = command.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug


def resolve_url(query: str) -> tuple[str, str]:
    """Resolve a query to a doc URL and type."""
    q = query.strip()
    ql = q.lower().replace("4d.", "").replace("cs.", "")

    # Check topic map
    for key, path in TOPIC_MAP.items():
        if ql == key or ql.startswith(key):
            return f"{BASE_URL}/{path}", "topic"

    # Check class map
    if ql in CLASS_MAP:
        return f"{BASE_URL}/API/{CLASS_MAP[ql]}", "class"

    # Try as class with "Class" suffix
    for class_key, class_page in CLASS_MAP.items():
        if ql.replace(" ", "") == class_key:
            return f"{BASE_URL}/API/{class_page}", "class"

    # Default: treat as command
    slug = command_to_slug(q)
    return f"{BASE_URL}/commands/{slug}", "command"


def fetch_doc(url: str, max_chars: int = 4000) -> str | None:
    """Fetch and extract text from a doc page."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "4D-Doc-Lookup/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            parser = TextExtractor()
            parser.feed(html)
            text = parser.get_text()
            if len(text) > max_chars:
                text = text[:max_chars] + "\n\n[... truncated]"
            return text
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}: Page not found at {url}"
    except Exception as e:
        return f"Error fetching: {e}"


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: doc_lookup.py <command|class|topic> [--fetch] [--max-chars N]"}))
        sys.exit(1)

    # Parse args
    query_parts = []
    fetch = "--fetch" in sys.argv
    max_chars = 4000
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--fetch":
            fetch = True
        elif sys.argv[i] == "--max-chars" and i + 1 < len(sys.argv):
            max_chars = int(sys.argv[i + 1])
            i += 1
        elif not sys.argv[i].startswith("--"):
            query_parts.append(sys.argv[i])
        i += 1

    query = " ".join(query_parts)
    url, doc_type = resolve_url(query)

    result = {
        "query": query,
        "type": doc_type,
        "url": url,
    }

    if fetch:
        content = fetch_doc(url, max_chars)
        result["content"] = content

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
