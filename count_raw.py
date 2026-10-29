import csv, glob, os
from collections import Counter

files = sorted(glob.glob(r"D:\Desktop\work\raw_*.csv"))
rows = []
per_file = {}
for f in files:
    with open(f, encoding="utf-8-sig", newline="") as fh:
        r = csv.DictReader(fh)
        cnt = 0
        for row in r:
            # require essential fields
            name = (row.get("岗位名称") or "").strip()
            comp = (row.get("企业") or "").strip()
            city = (row.get("城市") or "").strip()
            if not name or not comp:
                continue
            rows.append(row)
            cnt += 1
        per_file[os.path.basename(f)] = cnt

print("=== per-file raw row counts (excl header) ===")
for k in sorted(per_file):
    print(f"  {k}: {per_file[k]}")
print(f"  TOTAL raw rows: {sum(per_file.values())}")

# dedupe by (岗位名称, 企业, 城市, 区域)
seen = set()
uniq = []
for row in rows:
    key = (row.get("岗位名称","").strip(), row.get("企业","").strip(),
           row.get("城市","").strip(), row.get("区域","").strip())
    if key in seen:
        continue
    seen.add(key)
    uniq.append(row)

print(f"\n=== DEDUPED unique rows: {len(uniq)} ===")
city_c = Counter(r["城市"] for r in uniq)
print("  by city:", dict(city_c))
kw_c = Counter(r.get("关键词","") for r in uniq)
print("  by keyword:")
for k,v in sorted(kw_c.items(), key=lambda x:-x[1]):
    print(f"    {k}: {v}")

# salary parse sanity
bad_sal = [r for r in uniq if not (r.get("薪资") or "").strip()]
print(f"\n  rows missing salary: {len(bad_sal)}")
