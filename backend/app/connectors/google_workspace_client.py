"""Mock Google Workspace API client — simulates Drive, Calendar, Chat, Meet integrations."""

import uuid
from datetime import datetime, timezone

# In-memory mock store keyed by workspace_id (demo / no real Google credentials)
_workspace_store: dict[uuid.UUID, dict] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_workspace(workspace_id: uuid.UUID, lab_id: uuid.UUID, lab_name: str) -> dict:
    """Seed mock workspace resources after provisioning completes."""
    data = {
        "lab_name": lab_name,
        "drive_files": [
            {"id": "f1", "name": f"{lab_name} — Shared Protocols", "type": "folder", "updated_at": _now_iso(), "url": f"/api/mock/drive/{lab_id}/protocols"},
            {"id": "f2", "name": "Dataset batch #42.csv", "type": "file", "updated_at": _now_iso(), "url": f"/api/mock/drive/{lab_id}/dataset-42"},
            {"id": "f3", "name": "Lab Safety Checklist.pdf", "type": "file", "updated_at": _now_iso(), "url": f"/api/mock/drive/{lab_id}/safety"},
        ],
        "calendar_events": [
            {"id": "e1", "title": "Weekly standup", "start": "Mon 10:00 AM", "attendees": 6},
            {"id": "e2", "title": "Dataset review", "start": "Wed 2:00 PM", "attendees": 4},
            {"id": "e3", "title": "Equipment maintenance", "start": "Fri 9:00 AM", "attendees": 2},
        ],
        "chat_messages": [
            {"id": "m1", "author": "Dave Okonkwo", "content": "Dataset upload complete — ready for annotation.", "created_at": "10:32 AM"},
            {"id": "m2", "author": "Eve Nguyen", "content": "Simulation run finished. Results in Drive.", "created_at": "11:15 AM"},
        ],
    }
    _workspace_store[workspace_id] = data
    return data


def get_workspace_data(workspace_id: uuid.UUID) -> dict | None:
    return _workspace_store.get(workspace_id)


def ensure_workspace_initialized(workspace_id: uuid.UUID, lab_id: uuid.UUID, lab_name: str) -> dict:
    """Re-hydrate mock store after server restart if workspace is ACTIVE in DB."""
    if workspace_id not in _workspace_store:
        return initialize_workspace(workspace_id, lab_id, lab_name)
    return _workspace_store[workspace_id]


def list_drive_files(workspace_id: uuid.UUID) -> list[dict]:
    ws = _workspace_store.get(workspace_id, {})
    return ws.get("drive_files", [])


def list_calendar_events(workspace_id: uuid.UUID) -> list[dict]:
    ws = _workspace_store.get(workspace_id, {})
    return ws.get("calendar_events", [])


def list_chat_messages(workspace_id: uuid.UUID) -> list[dict]:
    ws = _workspace_store.get(workspace_id, {})
    return ws.get("chat_messages", [])


def send_chat_message(workspace_id: uuid.UUID, author: str, content: str) -> dict:
    ws = _workspace_store.setdefault(workspace_id, {"chat_messages": []})
    msg = {
        "id": f"m{len(ws.get('chat_messages', [])) + 1}",
        "author": author,
        "content": content,
        "created_at": datetime.now(timezone.utc).strftime("%I:%M %p"),
    }
    ws.setdefault("chat_messages", []).append(msg)
    return msg


def start_meet_session(workspace_id: uuid.UUID, meet_url: str) -> dict:
    return {
        "meet_url": meet_url,
        "join_code": meet_url.split("-")[-1] if meet_url else "mock-0000",
        "status": "LIVE",
        "participants": 1,
    }
