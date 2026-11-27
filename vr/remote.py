"""Paneldeki girdileri depoya 'gelen kutusu' dosyası olarak yazar ve isteğe bağlı olarak işi başlatır.
GitHub REST API kullanır; jeton yalnızca bu depoya sınırlı fine-grained token olmalıdır
(Contents: read/write, Actions: read/write). Jeton loglanmaz."""
import base64
import json
import urllib.error
import urllib.request
import uuid
from datetime import datetime

API = "https://api.github.com"


def _req(method: str, url: str, token: str, body: dict | None = None) -> int:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "viral-radar-ai"})
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def push_inbox(repo: str, token: str, kind: str, payload: dict, branch: str = "main") -> bool:
    name = f"data/inbox/{datetime.now().strftime('%Y%m%dT%H%M%S')}_{kind}_{uuid.uuid4().hex[:8]}.json"
    content = base64.b64encode(json.dumps({"tur": kind, "veri": payload}, ensure_ascii=False).encode()).decode()
    code = _req("PUT", f"{API}/repos/{repo}/contents/{name}", token,
                {"message": f"inbox: {kind}", "content": content, "branch": branch})
    return code in (200, 201)


def dispatch_job(repo: str, token: str, workflow: str = "research.yml", branch: str = "main") -> bool:
    return _req("POST", f"{API}/repos/{repo}/actions/workflows/{workflow}/dispatches", token, {"ref": branch}) == 204
