import json

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app import config

router = APIRouter(include_in_schema=False)

_PAGE = """<!doctype html>
<meta charset="utf-8"><title>Google login test</title>
<body style="font-family:sans-serif;max-width:640px;margin:40px auto">
<h2>Google login test</h2>
<label>Role for a NEW account:
  <select id="role"><option>student</option><option>teacher</option></select></label>
<div id="button" style="margin:16px 0"></div>
<pre id="out" style="white-space:pre-wrap;word-break:break-all;background:#f3f4f6;padding:12px">Waiting...</pre>
<script src="https://accounts.google.com/gsi/client" async defer></script>
<script>
const CLIENT_ID = __CLIENT_ID__;
const out = document.getElementById("out");

async function start() {
  const { nonce } = await (await fetch("/api/v1/auth/google/nonce", { method: "POST" })).json();
  google.accounts.id.initialize({ client_id: CLIENT_ID, nonce, callback: onCredential });
  google.accounts.id.renderButton(document.getElementById("button"), { theme: "outline", size: "large" });
}

async function onCredential(response) {
  const res = await fetch("/api/v1/auth/google", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential: response.credential, role: document.getElementById("role").value }),
  });
  out.textContent = res.status + "\\n" + JSON.stringify(await res.json(), null, 2);
  await start();
}

window.onGoogleLibraryLoad = start;
</script>
"""


@router.get("/dev/google", response_class=HTMLResponse)
def google_test_page():
    if not config.GOOGLE_CLIENT_ID:
        return HTMLResponse("<p>Set GOOGLE_CLIENT_ID in the .env file and restart the backend.</p>")
    return HTMLResponse(
        _PAGE.replace("__CLIENT_ID__", json.dumps(config.GOOGLE_CLIENT_ID)),
        headers={"Referrer-Policy": "no-referrer-when-downgrade"},
    )
