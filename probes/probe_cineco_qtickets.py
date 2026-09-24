"""One-off probe: why do the Cineco Qatar/Bahrain scrapers return no
showtimes, and what does q-tickets.com (the booking site they link to)
expose? Prints findings to the job log."""

import json
import re

import httpx
from playwright.sync_api import sync_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"


def section(title):
    print(f"\n{'=' * 20} {title} {'=' * 20}", flush=True)


def probe_cineco(base, movie_path):
    section(f"CINECO {base}")
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=30) as c:
        r = c.get(f"{base}/now-showing/")
        print("now-showing:", r.status_code, r.url, len(r.text), "bytes")
        links = sorted(set(re.findall(r'href="([^"]*' + movie_path + r'[^"]*)"', r.text)))
        print(f"movie links ({movie_path}):", len(links), links[:5])
        qt = sorted(set(re.findall(r'href="([^"]*q-tickets[^"]*)"', r.text)))
        print("q-tickets links:", len(qt), qt[:10])
        if not links:
            print("--- now-showing head (3KB) ---")
            print(r.text[:3000])
            return
        m = c.get(links[0])
        print("movie page:", m.status_code, m.url, len(m.text))
        i = m.text.find("single-movie-showtimes")
        print("single-movie-showtimes present:", i >= 0)
        if i >= 0:
            print(m.text[i - 200 : i + 2500])
        else:
            for kw in ("showtime", "cinema_name", "q-tickets", "Book"):
                j = m.text.find(kw)
                print(f"-- first '{kw}' at {j}:", m.text[max(j - 300, 0) : j + 700] if j >= 0 else "")


def probe_qtickets():
    section("Q-TICKETS BookTickets (browser)")
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(user_agent=UA)
        page = ctx.new_page()
        reqs = []

        def on_response(resp):
            rt = resp.request.resource_type
            if rt in ("xhr", "fetch", "document"):
                try:
                    body = resp.text()
                except Exception as e:
                    body = f"<unreadable {e}>"
                reqs.append((resp.request.method, resp.url, resp.status, rt,
                             resp.headers.get("content-type", ""), resp.request.post_data, body))

        page.on("response", on_response)
        page.goto("https://q-tickets.com/Movie/BookTickets", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)
        print("final url:", page.url, "title:", page.title())
        html = page.content()
        print("html length:", len(html))
        print("mentions of Cineco:", len(re.findall(r"(?i)cineco", html)))
        for m in list(re.finditer(r"(?i)cineco", html))[:8]:
            print("  ...", re.sub(r"\s+", " ", html[max(m.start() - 200, 0) : m.end() + 200]))
        print("forms/selects:")
        for sel in page.query_selector_all("select"):
            opts = [o.inner_text().strip() for o in sel.query_selector_all("option")][:40]
            print("  select", sel.get_attribute("id"), sel.get_attribute("name"), opts)
        scripts = sorted(set(re.findall(r'<script[^>]+src="([^"]+)"', html)))
        print("script srcs:", scripts)
        inline_urls = sorted(set(re.findall(r"['\"](/[A-Za-z]+/[A-Za-z]+[^'\"\s]*)['\"]", html)))
        print("relative URL-ish strings in html:", inline_urls[:120])
        section("Q-TICKETS network (xhr/fetch/document)")
        for method, url, status, rt, ct, post, body in reqs:
            print(f"{method} {status} [{rt}] {ct} {url}")
            if post:
                print("   POST:", post[:500])
            if rt != "document":
                print("   BODY:", re.sub(r"\s+", " ", body[:1500]))
        # Fetch app JS bundles and grep for endpoints
        section("Q-TICKETS endpoints referenced in own JS")
        with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=30) as c:
            for s in scripts:
                if s.startswith("//"):
                    s = "https:" + s
                elif s.startswith("/"):
                    s = "https://q-tickets.com" + s
                if "q-tickets" not in s:
                    continue
                try:
                    js = c.get(s).text
                except Exception as e:
                    print(s, "ERR", e)
                    continue
                eps = sorted(set(re.findall(r"['\"]((?:https?://[^'\"]*q-?tickets[^'\"]*)|(?:/(?:Movie|Home|api|Api|Booking|Cinema|Theatre|Show)[A-Za-z0-9/_\-.?=&]*))['\"]", js)))
                print(s, len(js), "bytes ->", eps[:80])
        b.close()


if __name__ == "__main__":
    for base, path in (("https://qatar.cineco.net", "/movie/"), ("https://bahrain.cineco.net", "/amy_movie/")):
        try:
            probe_cineco(base, path)
        except Exception as e:
            print("CINECO PROBE ERROR", base, repr(e))
    try:
        probe_qtickets()
    except Exception as e:
        print("QTICKETS PROBE ERROR", repr(e))
