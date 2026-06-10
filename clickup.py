"""Minimal ClickUp v2 client for posting the weekly grade task (idempotent)."""

import json
import requests

API = "https://api.clickup.com/api/v2"


def _week_prefix(name):
    """'Week of Jun 8' — used to match an existing task for the same week."""
    return name.split("—")[0].strip()


def post_or_update_week_task(token, list_id, name, description):
    """Create the weekly grade task, or update it if one for the same week exists."""
    if not token or not list_id:
        return {"skipped": True, "reason": "missing CLICKUP_API_TOKEN or CLICKUP_LIST_ID"}

    headers = {"Authorization": token, "Content-Type": "application/json"}
    prefix = _week_prefix(name)

    existing = requests.get(f"{API}/list/{list_id}/task", headers=headers,
                            params={"archived": "false"})
    if existing.ok:
        for t in existing.json().get("tasks", []):
            if t.get("name", "").startswith(prefix):
                put = requests.put(f"{API}/task/{t['id']}", headers=headers,
                                   data=json.dumps({"name": name, "description": description}))
                if put.ok:
                    return {"skipped": False, "updated": True, **put.json()}
                return {"skipped": False, "error": put.text}

    post = requests.post(f"{API}/list/{list_id}/task", headers=headers,
                         data=json.dumps({"name": name, "description": description}))
    if post.ok:
        return {"skipped": False, "updated": False, **post.json()}
    return {"skipped": False, "error": post.text}
