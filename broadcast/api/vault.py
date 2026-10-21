"""Load secret keys from Key Vault with the container's managed identity.

SPEECH_REGION, CONTENT_SAFETY_ENDPOINT, FOUNDRY_ENDPOINT, and KEY_VAULT_URI
stay in the environment. The keys themselves do not.
"""

from __future__ import annotations

import json
import os
import urllib.request

SECRETS = {
    "speech-key": "SPEECH_KEY",
    "content-safety-key": "CONTENT_SAFETY_KEY",
}


def load_key_vault() -> None:
    vault = os.environ.get("KEY_VAULT_URI", "").strip().rstrip("/")
    if not vault:
        return
    if not vault.startswith("https://"):
        raise RuntimeError("KEY_VAULT_URI must be an https URL")
    token = _token()
    for name, env in SECRETS.items():
        if os.environ.get(env, "").strip():
            continue
        os.environ[env] = _secret(vault, name, token)


def _token() -> str:
    url = (
        "http://169.254.169.254/metadata/identity/oauth2/token"
        "?api-version=2018-02-01&resource=https://vault.azure.net"
    )
    request = urllib.request.Request(url, headers={"Metadata": "true"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))["access_token"]


def _secret(vault: str, name: str, token: str) -> str:
    request = urllib.request.Request(
        f"{vault}/secrets/{name}?api-version=7.4",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))["value"]
