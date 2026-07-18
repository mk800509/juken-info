#!/usr/bin/env python3
import os, sys, json, re, hashlib, datetime, urllib.request

TARGETS = [
    ("suiran", "https://www.pen-kanagawa.ed.jp/yokohamasuiran-h/zennichi/nyugaku/r8_setsumeikai.html"),
    ("kawawa", "https://www.pen-kanagawa.ed.jp/kawawa-h/nyugaku/20260-kakkousetumeikai-itiran.html"),
    ("gakugei_info", "https://www.gakugei-hs.setagaya.tokyo.jp/exam/info/"),
    ("gakugei_session", "https://www.gakugei-hs.setagaya.tokyo.jp/exam/infosession2022s/"),
    ("chuo-yokohama", "https://www.yokohama-js.chuo-u.ac.jp/admission/senior/"),
    ("yamate", "https://www.yamate-gakuin.ac.jp/examinee/h_boshu/"),
]

SCHOOL_NAMES = {
    "suiran": "横浜翠嵐高校",
    "kawawa": "川和高校",
    "gakugei_info": "東京学芸大学附属高校（入試情報ページ）",
    "gakugei_session": "東京学芸大学附属高校（学校説明会ページ）",
    "chuo-yokohama": "中央大学附属横浜高校",
    "yamate": "山手学院高校",
}

STATE_PATH = "state.json"
DASHBOARD_PATH = "index.html"
EVENTS_PATH = "events.ics"
NOTIFY_PATH = "notify_message.txt"


def fetch_text(url):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; KanagawaKoukouMonitor/1.0)"}
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read()
        charset = resp.headers.get_content_charset() or "utf-8"
        html = raw.decode(charset, errors="replace")
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract(tag, s):
    m = re.search(rf"<{tag}>(.*?)</{tag}>", s, flags=re.S)
    return m.group(1).strip() if m else None


def main():
    old_state = {}
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            old_state = json.load(f)

    new_state = dict(old_state)
    changed = {}
    errors = []

    for key, url in TARGETS:
        try:
            text = fetch_text(url)
        except Exception as e:
            errors.append(f"{key} ({url}): {e}")
            continue
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        prev = old_state.get(key)
        if prev is None:
            new_state[key] = {"hash": h, "text": text}
        elif prev.get("hash") != h:
            changed[key] = (prev.get("text", ""), text)
            new_state[key] = {"hash": h, "text": text}

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(new_state, f, ensure_ascii=False, indent=2)

    if errors:
        print("ERRORS:")
        for e in errors:
            print(" -", e)

    if not changed:
        print("NO_CHANGES")
        return 0

    with open(DASHBOARD_PATH, "r", encoding="utf-8") as f:
        dashboard_html = f.read()
    with open(EVENTS_PATH, "r", encoding="utf-8") as f:
        events_ics = f.read()

    changed_desc = []
    for key, (old_t, new_t) in changed.items():
        name = SCHOOL_NAMES.get(key, key)
        changed_desc.append(
            f"### {name} (key: {key})\n[旧内容]\n{old_t[:3000]}\n\n[新内容]\n{new_t[:3000]}\n"
        )
    changed_block = "\n".join(changed_desc)
    changed_schools = "、".join(SCHOOL_NAMES.get(k, k) for k in changed.keys())

    now_utc = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    prompt = f"""あなたは神奈川県内在住の中学3年生（2027年度高校受験予定）の父親（Makoto）のために、志望校の入試・学校説明会情報ダッシュボードを保守しています。

以下は、監視対象ページのうち内容に変化があった学校と、その旧内容・新内容のテキスト（HTMLタグ除去済み、多少ノイズを含む）です。

{changed_block}

変化があった学校: {changed_schools}

現在のダッシュボードHTML全文:
---HTML START---
{dashboard_html}
---HTML END---

現在のiPhoneカレンダー購読用ICSファイル全文:
---ICS START---
{events_ics}
---ICS END---

実行時刻（UTC）: {now_utc}（日本時間はUTC+9で変換してください）

# あなたのタスク
1. ダッシュボードHTMLを更新してください。学校ごとに `<!-- SCHOOL:xxx --> ... <!-- /SCHOOL -->` で区切られたカードがあります。変化があった学校のカード内で新しい内容を反映するようテーブルの行やdivの文言を書き換え、変わった箇所には `updated`（divの場合 class="row updated"）または `updated-row`（trの場合 class="updated-row"）を追加してください。他の学校カードに残っている古いハイライトは通常のクラスに戻してください。該当する `<ul id="log-XXX">` の先頭に `<li>YYYY/MM/DD HH:MM 内容の要約</li>` を追加し最新5件までに保ってください。`<div id="last-checked">` も更新してください。
2. ICSファイルを更新してください。変化があった学校の接頭辞（suiran-, kawawa-, gakugei-, chuoyoko-, yamate-）を持つVEVENTのうち該当する行事のDTSTART/DTEND/SUMMARY/LOCATION/DESCRIPTIONを更新し、DTSTAMPを現在時刻に更新してください。新しい行事があれば命名規則に沿った新UIDで追加してください。共通選抜の公式日程（kanagawa2027-で始まるUID）は変更しないでください。
3. 短い日本語の通知メッセージを作成してください。学校ごとに「【更新あり】学校名 — 内容の要約」の形式で1〜2行、全体で5行以内にまとめてください。

# 出力形式（厳守。前置きや説明文は一切書かないこと）
<DASHBOARD_HTML>
（更新後のHTML全文）
</DASHBOARD_HTML>
<EVENTS_ICS>
（更新後のICS全文）
</EVENTS_ICS>
<SUMMARY>
（通知メッセージ）
</SUMMARY>
"""

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set; state.json updated but dashboard/ics left unchanged.")
        return 0

    body = json.dumps(
        {
            "model": "claude-sonnet-5",
            "max_tokens": 16000,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print("Anthropic API call failed:", e)
        return 0

    text_out = "".join(block.get("text", "") for block in result.get("content", []))

    new_dashboard = extract("DASHBOARD_HTML", text_out)
    new_events = extract("EVENTS_ICS", text_out)
    summary = extract("SUMMARY", text_out)

    if new_dashboard:
        with open(DASHBOARD_PATH, "w", encoding="utf-8") as f:
            f.write(new_dashboard)
    if new_events:
        with open(EVENTS_PATH, "w", encoding="utf-8") as f:
            f.write(new_events)
    if summary:
        with open(NOTIFY_PATH, "w", encoding="utf-8") as f:
            f.write(summary)

    print("UPDATED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
