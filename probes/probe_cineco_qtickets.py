"""One-off probe: run the real VOX scraper for one KSA and one UAE
cinema from moviegoersme/showtimes, counting requests and statuses."""

import sys
import time
import traceback
from collections import Counter

sys.path.insert(0, "showtimes")

from scrapers import fetch  # noqa: E402
from scrapers.platforms import vox  # noqa: E402
from scrapers.schema import ScraperCinema  # noqa: E402

statuses = Counter()
_orig = fetch.Fetcher.get


def counting_get(url, **kw):
    page = _orig(url, **kw)
    statuses[(url.split("?")[0], page.status)] += 1
    return page


fetch.Fetcher.get = counting_get

for cid, url, label in (
    ("vox-ksa-probe", "https://ksa.voxcinemas.com/showtimes", "Al Qasr Mall - Riyadh"),
    ("vox-uae-probe", "https://uae.voxcinemas.com/showtimes", None),
):
    print(f"\n===== {url} =====", flush=True)
    if label is None:
        page = fetch.fetch_page(url, retries=3)
        names = sorted({(t or "").strip() for t in page.css("article.movie-compare h3.highlight::text").getall()})
        print("cinema labels on UAE page:", names[:40])
        label = names[0] if names else "?"
    statuses.clear()
    t = time.time()
    try:
        rows = vox.scrape(ScraperCinema(id=cid, name=label, url=url, site_label=label))
        print(f"{label}: {len(rows)} showtimes in {time.time()-t:.0f}s")
        print("dates:", dict(Counter(r.showtime_datetime.date().isoformat() for r in rows)))
    except Exception:
        traceback.print_exc()
    print("requests by (url, status):", dict(statuses))
