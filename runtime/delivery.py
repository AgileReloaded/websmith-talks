"""Gmail connector arguments. This module never opens a network connection."""
import html
import json

GMAIL_TOOL = "mcp__codex_apps__gmail_send_email"


def gmail_arguments(recipient, attachment_path, filename, name, reply_to=""):
    arguments = {
        "to": recipient, "subject": "TRTalks — " + filename,
        "payload": {"mime_type": "text/html", "body": {"content":
            "<p>Resoconto TRTalks preparato da " + html.escape(name or "TRTalks")
            + ".</p><p>Il documento Markdown completo è allegato.</p>"}},
        "attachment_files": [str(attachment_path)],
    }
    if reply_to:
        arguments["reply_to"] = reply_to
    return arguments


def gmail_receipt(value):
    """Read the connector response, including the standard MCP wrappers."""
    if not isinstance(value, dict) or value.get("isError") or value.get("error"):
        raise ValueError("Gmail non ha confermato l'invio")
    if isinstance(value.get("structuredContent"), dict):
        return gmail_receipt(value["structuredContent"])
    if isinstance(value.get("content"), list):
        parts = [p for p in value["content"] if isinstance(p, dict) and p.get("type") == "text"]
        if len(parts) == 1:
            return gmail_receipt(json.loads(parts[0]["text"]))
    message_id = value.get("id")
    if not isinstance(message_id, str) or not message_id.strip() or any(c.isspace() for c in message_id):
        raise ValueError("Ricevuta Gmail priva dell'id del messaggio; verificare manualmente")
    return value
