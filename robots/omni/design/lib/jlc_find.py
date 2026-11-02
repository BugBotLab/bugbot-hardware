# JLC parts lookup (jlcpcb.com's own component search): stock, Basic/Extended, price.
#   C:/Python312/python.exe design/lib/jlc_find.py "keyword" ["keyword" ...]  [--n 6]
import sys, json, urllib.request

def find(keyword, n=6):
    req = urllib.request.Request(
        "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList",
        data=json.dumps({"keyword": keyword, "currentPage": 1, "pageSize": 30, "searchSource": "search"}).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/141.0"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    lst = (((d.get("data") or {}).get("componentPageInfo") or {}).get("list")) or []
    out = []
    for c in lst:
        pr = c.get("componentPrices") or [{}]
        out.append({"C": c.get("componentCode"), "mpn": c.get("componentModelEn"), "pkg": c.get("componentSpecificationEn"),
                    "stock": c.get("stockCount") or 0, "lib": c.get("componentLibraryType"), "price": pr[0].get("productPrice"),
                    "desc": (c.get("describe") or "")[:90]})
    out.sort(key=lambda r: (r["lib"] != "base", -(r["stock"] or 0)))
    return out[:n]

if __name__ == "__main__":
    n = 6
    args = sys.argv[1:]
    if "--n" in args:
        i = args.index("--n"); n = int(args[i + 1]); del args[i:i + 2]
    for k in args:
        print(f"== {k}")
        for r in find(k, n):
            print(f"   {r['C']:>10s}  {('BASIC' if r['lib'] == 'base' else 'ext'):5s} stock {r['stock']:>8}  ${r['price']}  {r['mpn']}  [{r['pkg']}]  {r['desc']}")
