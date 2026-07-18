#!/usr/bin/env python3
"""Sends one realistic SAMPLE of the actual update-notification email format
(same subject/body structure monitor.py uses when a real change is detected).
One-off use, not part of the regular monitoring flow."""
import os, sys, json, base64, urllib.request, urllib.parse
from email.mime.text import MIMEText
from email.header import Header

GMAIL_SENDER = "kajiwara.makoto@gmail.com"
GMAIL_RECIPIENTS = ["kajiwara.makoto@gmail.com", "eriko.taoka06@gmail.com"]
DASHBOARD_URL = "https://mk800509.github.io/juken-info/"

SAMPLE_CHANGED_SCHOOLS = "山手学院高校"
SAMPLE_SUMMARY = (
    "【更新あり】山手学院高校 — 11月開催の学校説明会（要予約）の申込開始が"
    "10/1(木) 10:00からに決定しました。ダッシュボードとカレンダーに反映済みです。"
)
SAMPLE_SOURCE_LINES = "・山手学院高校: https://www.yamate-gakuin.ac.jp/examinee/h_boshu/"


def main():
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN")
    if not (client_id and client_secret and refresh_token):
        print("FAIL: missing Gmail secrets")
        return 1

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
    with urllib.request.urlopen(token_req, timeout=30) as resp:
        access_token = json.loads(resp.read().decode("utf-8"))["access_token"]

    subject = f"【志望校情報 更新／サンプル】{SAMPLE_CHANGED_SCHOOLS}"
    body = (
        f"{SAMPLE_SUMMARY}\n\n"
        f"更新元ページ:\n{SAMPLE_SOURCE_LINES}\n\n"
        f"ダッシュボード: {DASHBOARD_URL}\n"
        f"カレンダー: {DASHBOARD_URL}events.ics\n\n"
        f"※これは実際の更新通知メールと同じ形式のサンプルです。実データではありません。"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["To"] = ", ".join(GMAIL_RECIPIENTS)
    msg["From"] = GMAIL_SENDER
    msg["Subject"] = str(Header(subject, "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    send_req = urllib.request.Request(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        data=json.dumps({"raw": raw}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(send_req, timeout=30) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    print("SUCCESS, message id", result.get("id"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
