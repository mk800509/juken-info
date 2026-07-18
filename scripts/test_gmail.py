#!/usr/bin/env python3
"""Standalone one-off test for the Gmail send-only (gmail.send scope) notification
path. Does not touch state.json, the dashboard, or the Anthropic API. Run manually
via the 'Test Gmail Notification' workflow_dispatch, then check both inboxes and
this job's log output."""
import os, sys, json, base64, urllib.request, urllib.parse
from email.mime.text import MIMEText
from email.header import Header

GMAIL_SENDER = "kajiwara.makoto@gmail.com"
GMAIL_RECIPIENTS = ["kajiwara.makoto@gmail.com", "eriko.taoka06@gmail.com"]


def main():
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
    missing = [
        n
        for n, v in [
            ("GMAIL_CLIENT_ID", client_id),
            ("GMAIL_CLIENT_SECRET", client_secret),
            ("GMAIL_REFRESH_TOKEN", refresh_token),
        ]
        if not v
    ]
    if missing:
        print("FAIL: missing secrets:", ", ".join(missing))
        return 1

    print("Step 1: refreshing access token via oauth2.googleapis.com ...")
    token_body = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    token_req = urllib.request.Request(
        "https://oauth2.googleapis.com/token", data=token_body, method="POST"
    )
    try:
        with urllib.request.urlopen(token_req, timeout=30) as resp:
            token_data = json.loads(resp.read().decode("utf-8"))
        access_token = token_data["access_token"]
        print("  OK: got access token (scope:", token_data.get("scope"), ")")
    except urllib.error.HTTPError as e:
        print("FAIL: token refresh HTTPError", e.code, e.read().decode("utf-8", "replace"))
        return 1
    except Exception as e:
        print("FAIL: token refresh error:", e)
        return 1

    print("Step 2: sending test email via gmail.googleapis.com ...")
    msg = MIMEText(
        "これは志望校監視システムからのGmail送信テストです。\n"
        "このメールが届いていれば、gmail.send権限での自動通知は正常に動作しています。",
        "plain",
        "utf-8",
    )
    msg["To"] = ", ".join(GMAIL_RECIPIENTS)
    msg["From"] = GMAIL_SENDER
    msg["Subject"] = str(Header("【テスト】志望校監視システム Gmail通知テスト", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    send_body = json.dumps({"raw": raw}).encode("utf-8")
    send_req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        data=send_body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(send_req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        print("  OK: message id", result.get("id"))
        print("SUCCESS")
        return 0
    except urllib.error.HTTPError as e:
        print("FAIL: send HTTPError", e.code, e.read().decode("utf-8", "replace"))
        return 1
    except Exception as e:
        print("FAIL: send error:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
