"""One-off probe: run the real Cineco Qatar/Bahrain scrapers from
moviegoersme/showtimes, and inspect q-tickets.com's 403."""

import re
import sys
import traceback
from collections import Counter

sys.path.insert(0, "showtimes")


def section(t):
    print(f"\n{'=' * 20} {t} {'=' * 20}", flush=True)


def run_real_scrapers():
    from scrapers.schema import ScraperCinema  # noqa
    from scrapers.qatar import cineco as qa
    from scrapers.bahrain import cineco as bh
    import inspect
    print("ScraperCinema fields:", inspect.signature(ScraperCinema))
    cases = [
        (qa, ["Cineco Alkhor", "Cineco Asian Town", "Cineco City Centre", "Cineco Gulf Mall", "Cineco Villagio"]),
        (bh, ["Cineco Seef", "Cineco Juffair", "Cineco Wadi Al Sail", "Cineco Al Hamra"]),
    ]
    for mod, names in cases:
        for name in names:
            section(f"REAL SCRAPER {mod.__name__} / {name}")
            try:
                cinema = ScraperCinema(id="probe", name=name, url="", site_label=name)
                rows = mod.scrape(cinema)
                print("showtimes:", len(rows))
                days = Counter(r.showtime_datetime.date().isoformat() for r in rows)
                print("by date:", dict(days))
                for r in rows[:3]:
                    print("  ", r)
            except Exception:
                traceback.print_exc()
            if mod is qa:
                break  # one Qatar cinema is enough to see if fetch works; all share pages


def probe_qtickets():
    from scrapling.fetchers import Fetcher
    import httpx
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    urls = [
        "https://q-tickets.com/Movie/BookTickets",
        "https://www.q-tickets.com/",
        "https://q-tickets.com/MovieDetailsList/46194/aaram-malayalam",
        "https://www.q-tickets.com/MovieDetailsList/46194/aaram-malayalam",
    ]
    for u in urls:
        section(f"Q-TICKETS {u}")
        try:
            r = httpx.get(u, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                                      "Accept": "text/html,application/xhtml+xml"}, follow_redirects=True, timeout=30)
            print("httpx:", r.status_code, r.url, len(r.text))
            print("headers:", {k: v for k, v in r.headers.items() if k.lower() in ("server", "via", "x-cache", "cf-ray", "x-amz-cf-id", "x-azure-ref", "x-iinfo", "x-sucuri-id", "set-cookie", "content-type", "x-powered-by", "x-aspnet-version")})
            print("body head:", re.sub(r"\s+", " ", r.text[:600]))
        except Exception as e:
            print("httpx ERR", repr(e))
        try:
            p = Fetcher.get(u, impersonate="chrome", stealthy_headers=True, timeout=30)
            body = p.body.decode("utf-8", "ignore") if isinstance(p.body, bytes) else str(p.body)
            print("curl_cffi chrome:", p.status, len(body))
            print("body head:", re.sub(r"\s+", " ", body[:400]))
            if p.status == 200:
                for kw in ("Cineco", "cineco", "ShowTime", "showtime", "/Movie/", "ajax", "$.post", "$.get", "fetch("):
                    idx = [m.start() for m in re.finditer(re.escape(kw), body)][:3]
                    for i in idx:
                        print(f"  [{kw}]", re.sub(r"\s+", " ", body[max(i - 150, 0): i + 250]))
                print("scripts:", sorted(set(re.findall(r'<script[^>]+src="([^"]+)"', body)))[:30])
        except Exception as e:
            print("curl_cffi ERR", repr(e))
    import urllib.request, json
    section("runner egress IP")
    try:
        print(urllib.request.urlopen("https://ipinfo.io/json", timeout=10).read().decode()[:400])
    except Exception as e:
        print("ipinfo ERR", e)


if __name__ == "__main__":
    run_real_scrapers()
    probe_qtickets()
