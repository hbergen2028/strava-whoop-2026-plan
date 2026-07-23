"""Minimal ClickUp v2 client for posting the weekly grade task (idempotent)."""

import json
import requests

API = "https://api.clickup.com/api/v2"


def _week_prefix(name):
    """'Week of Jun 01' — used to match an existing task for the same week.

    Cuts before the end date so tasks written under the older
    'Week of Jun 01 — …' naming still match 'Week of Jun 01 to 07 — …'
    and get updated rather than duplicated.
    """
    return name.split("—")[0].split(" to ")[0].strip()


def current_user_id(token):
    """The user ID behind this API token, or None if it can't be resolved."""
    if not token:
        return None
    r = requests.get(f"{API}/user", headers={"Authorization": token})
    return r.json().get("user", {}).get("id") if r.ok else None


def post_or_update_week_task(token, list_id, name, description,
                             assignee_id=None, due_date=None):
    """Create the weekly grade task, or update it if one for the same week exists.

    assignee_id puts the task in your queue; due_date (epoch ms) is what actually
    surfaces it on ClickUp Home, whose widgets are all date-driven. A dateless
    task is invisible there however it is assigned.
    """
    if not token or not list_id:
        return {"skipped": True, "reason": "missing CLICKUP_API_TOKEN or CLICKUP_LIST_ID"}

    headers = {"Authorization": token, "Content-Type": "application/json"}
    prefix = _week_prefix(name)

    existing = requests.get(f"{API}/list/{list_id}/task", headers=headers,
                            params={"archived": "false"})
    if existing.ok:
        for t in existing.json().get("tasks", []):
            if t.get("name", "").startswith(prefix):
                body = {"name": name, "description": description}
                if assignee_id:
                    # PUT wants add/rem, not the plain list POST takes.
                    body["assignees"] = {"add": [assignee_id]}
                if due_date:
                    body["due_date"] = due_date
                    body["due_date_time"] = False
                put = requests.put(f"{API}/task/{t['id']}", headers=headers,
                                   data=json.dumps(body))
                if put.ok:
                    return {"skipped": False, "updated": True, **put.json()}
                return {"skipped": False, "error": put.text}

    body = {"name": name, "description": description}
    if assignee_id:
        body["assignees"] = [assignee_id]
    if due_date:
        body["due_date"] = due_date
        body["due_date_time"] = False
    post = requests.post(f"{API}/list/{list_id}/task", headers=headers,
                         data=json.dumps(body))
    if post.ok:
        return {"skipped": False, "updated": False, **post.json()}
    return {"skipped": False, "error": post.text}
