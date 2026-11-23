#!/usr/bin/env python3
"""Look up parts on the South African supplier sites for the Vemef Parts sheet.

    python supplier.py sites                      the sites and how each is searched
    python supplier.py search <site> <query>      candidate products on one site
    python supplier.py product <url>              name, SKU, price, stock from a product page

Prints JSON. Standard library only. Sites that sit behind a bot check
(Cloudflare and the like) are reported as "blocked": look those up with web
search instead and record their prices as unconfirmed.
"""
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# name used in the sheet's Supplier column -> how to search it
SITES = {
    # method: woo / shopify = the store's product API (prices included);
    # html = the site's search page (names and links; read prices with `product`);
    # websearch = its search runs in the browser: find the page with web search,
    #   then read it with `product`;
    # blocked = a bot check stops every fetch: web search only, prices unconfirmed
#   (any site can answer `product` with "blocked" on a bad day: treat it the same);
    # gone = no longer sells parts.
    # vat: what a price read from the site includes, where checked.
    "make.net.za": {"supplier": "Make", "method": "woo", "base": "https://make.net.za"},
    "stelltron.co.za": {"supplier": "Stelltron", "method": "woo", "base": "https://stelltron.co.za"},
    "communica.co.za": {"supplier": "Communica", "method": "shopify", "base": "https://www.communica.co.za",
                        "vat": "the API and structured price are ex VAT; the page shows both"},
    "electromannsa.co.za": {"supplier": "Electromann", "method": "shopify", "base": "https://electromannsa.co.za",
                            "vat": "incl VAT ('Tax included'); rate-limits quickly"},
    "netram.co.za": {"supplier": "Netram", "method": "html", "search": "https://www.netram.co.za/search?s={q}",
                     "vat": "structured price incl VAT; the page also shows ex VAT"},
    "rabtron.co.za": {"supplier": "Rabtron", "method": "html", "search": "https://www.rabtron.co.za/search?s={q}"},
    "hobbytronics.co.za": {"supplier": "Hobbytronics", "method": "html",
                           "search": "https://hobbytronics.co.za/search?q={q}"},
    "mantech.co.za": {"supplier": "Mantech", "method": "websearch",
                      "vat": "quantity breaks (1 to 10, 11 to 20, ...): use the 1-off price"},
    "progenix.co.za": {"supplier": "Progenix", "method": "websearch"},
    "em.co.za": {"supplier": "ElectroMechanica", "method": "websearch"},
    "evetech.co.za": {"supplier": "Evetech", "method": "websearch"},
    "pishop.co.za": {"supplier": "Pishop", "method": "websearch", "vat": "shows 'Inc VAT'"},
    "robotics.org.za": {"supplier": "Micro Robotics", "method": "websearch",
                        "vat": "leads with the ex-VAT price, then 'Inc Tax'; its search and home "
                               "pages sit behind a bot check, its product pages usually do not"},
    "diyelectronics.co.za": {"supplier": "DIYElectronics", "method": "blocked"},
    "robofactory.co.za": {"supplier": "RoboFactory", "method": "html",
                          "search": "https://www.robofactory.co.za/search?s={q}",
                          "vat": "its bot check comes and goes"},
    "digikey.co.za": {"supplier": "DigiKey", "method": "blocked"},
    "botshop.co.za": {"supplier": "Botshop", "method": "gone"},
}

BOT_MARKERS = ("Just a moment...", "cf_chl_opt", "Verifying your connection", "Attention Required!")


class Blocked(Exception):
    pass


def fetch(url, accept="text/html,application/xhtml+xml"):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept,
                                               "Accept-Language": "en-ZA,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
            final = r.geturl()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        if e.code in (403, 429, 503) and any(m in body for m in BOT_MARKERS):
            raise Blocked(f"{url}: bot check (HTTP {e.code})")
        if e.code == 429:
            raise Blocked(f"{url}: rate limited (HTTP 429)")
        raise
    if any(m in body[:20000] for m in BOT_MARKERS):
        raise Blocked(f"{url}: bot check")
    return body, final


def site_of(url_or_name):
    host = urllib.parse.urlparse(url_or_name).hostname or url_or_name
    host = host.lower().removeprefix("www.")
    if host not in SITES:
        raise SystemExit(f"unknown site {url_or_name!r}; known: {', '.join(SITES)}")
    return host


def money(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return round(float(v), 2)
    s = re.sub(r"[^\d.,]", "", str(v))
    if "," in s and "." in s:
        s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if re.search(r",\d{2}$", s) else s.replace(",", "")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


# ---------------------------------------------------------------- search

def search_woo(base, q):
    url = f"{base}/wp-json/wc/store/v1/products?search={urllib.parse.quote(q)}&per_page=10"
    body, _ = fetch(url, "application/json")
    out = []
    for p in json.loads(body):
        prices = p.get("prices", {})
        minor = int(prices.get("currency_minor_unit", 2))
        price = prices.get("price")
        out.append({
            "name": clean(p.get("name")),
            "url": p.get("permalink"),
            "sku": p.get("sku") or None,
            "price": round(int(price) / 10 ** minor, 2) if price not in (None, "") else None,
            "currency": prices.get("currency_code"),
            "in_stock": p.get("is_in_stock"),
        })
    return out


def search_shopify(base, q):
    url = (f"{base}/search/suggest.json?q={urllib.parse.quote(q)}"
           "&resources%5Btype%5D=product&resources%5Blimit%5D=10")
    body, _ = fetch(url, "application/json")
    out = []
    for p in json.loads(body)["resources"]["results"].get("products", []):
        link = p.get("url", "").split("?")[0]
        out.append({
            "name": clean(p.get("title")),
            "url": urllib.parse.urljoin(base, link),
            "sku": None,
            "price": money(p.get("price")),
            "currency": "ZAR",
            "in_stock": p.get("available"),
        })
    return out


def search_html(template, q):
    url = template.format(q=urllib.parse.quote_plus(q))
    body, final = fetch(url)
    host = urllib.parse.urlparse(final).hostname
    tokens = [t.lower() for t in re.split(r"\W+", q) if len(t) >= 2]
    seen, out = set(), []
    for attrs, inner in re.findall(r'<a\b([^>]*)>(.*?)</a>', body, re.S | re.I):
        href = re.search(r'href="([^"#]+)"', attrs)
        if not href:
            continue
        link = urllib.parse.urljoin(final, html.unescape(href.group(1)))
        # the name: the link text, else a title or image alt, else the URL slug
        text = clean(inner)
        if not text:
            alt = re.search(r'(?:title|alt)="([^"]+)"', attrs + inner)
            text = html.unescape(alt.group(1)) if alt else \
                urllib.parse.urlparse(link).path.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
        if urllib.parse.urlparse(link).hostname != host or not text or len(text) > 200:
            continue
        hay = (text + " " + link).lower()
        if not all(t in hay for t in tokens):
            continue
        if re.search(r"[?&](s|q|query|search|Query)=|/search|/cart|/login|/account", link):
            continue
        if link in seen:
            continue
        seen.add(link)
        out.append({"name": text, "url": link})
    return {"search_url": final, "candidates": out[:15],
            "note": "names and links only; run `product <url>` on the right one for its price"}


def cmd_search(site, q):
    host = site_of(site)
    s = SITES[host]
    try:
        if s["method"] == "woo":
            return {"site": host, "supplier": s["supplier"], "results": search_woo(s["base"], q)}
        if s["method"] == "shopify":
            return {"site": host, "supplier": s["supplier"], "results": search_shopify(s["base"], q)}
        if s["method"] == "html":
            return {"site": host, "supplier": s["supplier"], **search_html(s["search"], q)}
    except Blocked as e:
        return {"site": host, "supplier": s["supplier"], "blocked": str(e)}
    if s["method"] == "websearch":
        return {"site": host, "supplier": s["supplier"],
                "note": f"site search runs in the browser: web search `{q} site:{host}`, "
                        "then run `product <url>` on the result"}
    if s["method"] == "gone":
        return {"site": host, "supplier": s["supplier"], "gone": "no longer sells parts: skip it"}
    return {"site": host, "supplier": s["supplier"], "blocked": "bot check: use web search; "
            "prices from it are unconfirmed"}


# ---------------------------------------------------------------- product page

def _ld_products(body):
    found = []
    for raw in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', body, re.S | re.I):
        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            continue
        stack = [data]
        while stack:
            d = stack.pop()
            if isinstance(d, list):
                stack.extend(d)
            elif isinstance(d, dict):
                t = d.get("@type")
                if t == "Product" or (isinstance(t, list) and "Product" in t):
                    found.append(d)
                stack.extend(v for k, v in d.items() if k in ("@graph", "mainEntity", "itemListElement", "item"))
    return found


def _offer(offers):
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if not isinstance(offers, dict):
        return None, None, None
    if offers.get("@type") == "AggregateOffer":
        price = offers.get("lowPrice") or offers.get("price")
    else:
        price = offers.get("price")
        spec = offers.get("priceSpecification")
        if price is None and isinstance(spec, (dict, list)):
            spec = spec[0] if isinstance(spec, list) else spec
            price = spec.get("price")
    avail = str(offers.get("availability") or "")
    stock = None
    if avail:
        stock = "InStock" in avail or "LimitedAvailability" in avail
    return money(price), offers.get("priceCurrency"), stock


def _meta(body, *names):
    for n in names:
        m = re.search(r'<meta[^>]+(?:property|name|itemprop)="%s"[^>]+content="([^"]*)"' % re.escape(n), body, re.I) \
            or re.search(r'<meta[^>]+content="([^"]*)"[^>]+(?:property|name|itemprop)="%s"' % re.escape(n), body, re.I)
        if m:
            return html.unescape(m.group(1))
    return None


def cmd_product(url):
    host = site_of(url)
    try:
        body, final = fetch(url)
    except Blocked as e:
        return {"url": url, "supplier": SITES[host]["supplier"], "blocked": str(e)}
    except urllib.error.HTTPError as e:
        return {"url": url, "supplier": SITES[host]["supplier"],
                "error": f"HTTP {e.code}: the page has gone; search for the part again"}
    res = {"url": final, "supplier": SITES[host]["supplier"], "name": None, "sku": None,
           "price": None, "currency": None, "in_stock": None, "found_by": None}
    for p in _ld_products(body):
        price, cur, stock = _offer(p.get("offers"))
        res.update(name=clean(p.get("name")), sku=p.get("sku") or p.get("mpn"),
                   price=price, currency=cur, in_stock=stock, found_by="json-ld")
        if price is not None:
            break
    if res["price"] is None:
        price = money(_meta(body, "product:price:amount", "og:price:amount", "price"))
        if price is not None:
            res.update(price=price, currency=_meta(body, "product:price:currency", "og:price:currency",
                                                   "priceCurrency"), found_by="meta")
    if res["price"] is None:
        m = re.search(r'itemprop="price"[^>]*content="([^"]+)"', body) or \
            re.search(r'content="([^"]+)"[^>]*itemprop="price"', body)
        if m:
            res.update(price=money(m.group(1)), found_by="microdata")
    if not res["name"]:
        res["name"] = clean(_meta(body, "og:title") or (re.search(r"<title>(.*?)</title>", body, re.S) or [None, ""])[1])
    # what the page says about VAT next to its prices, so the caller can tell
    # an ex-VAT price from an incl-VAT one; and, with no structured price, the
    # amounts the page shows, in context
    text = clean(re.sub(r"<(script|style)\b.*?</\1>", " ", body, flags=re.S | re.I))
    shown = []
    for m in re.finditer(r"R\s?\d{1,3}(?:[ ,]\d{3})*[.,]\d{2}\b", text):
        ctx = text[max(0, m.start() - 60):m.end() + 60]
        if money(m.group(0)) and ctx not in shown:
            shown.append(ctx)
        if len(shown) == 6:
            break
    res["page_prices"] = shown
    if res["price"] is None:
        res["note"] = ("no structured price: take it from page_prices (the product's own, "
                       "not a cart total or a related item) or treat it as not found")
    if urllib.parse.urlparse(final).path.strip("/") in ("", "index.php", "store") and \
            urllib.parse.urlparse(url).path.strip("/") not in ("", "index.php", "store"):
        res["error"] = "redirected to the home page: the product has gone; search for it again"
    return res


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd = argv[1]
    if cmd == "sites":
        out = {h: {k: v for k, v in s.items() if k in ("supplier", "method", "vat")}
               for h, s in SITES.items()}
    elif cmd == "search" and len(argv) >= 4:
        out = cmd_search(argv[2], " ".join(argv[3:]))
    elif cmd == "product" and len(argv) == 3:
        out = cmd_product(argv[2])
    else:
        print(__doc__, file=sys.stderr)
        return 2
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
