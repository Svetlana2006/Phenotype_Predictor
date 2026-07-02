"""Check sizes of 1000G chromosome VCF files before streaming."""
import requests, urllib3
urllib3.disable_warnings()

BASE = "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/ALL.chr{}.phase3_shapeit2_mvncall_integrated_v5b.20130502.genotypes.vcf.gz"
chroms = ["4","5","6","8","9","11","12","14","15","16","17","20"]
total = 0
for c in chroms:
    url = BASE.format(c)
    try:
        r = requests.head(url, timeout=15, verify=False)
        size = int(r.headers.get("Content-Length", 0))
        total += size
        print("chr" + c.ljust(3) + "  " + str(round(size/1e9, 2)) + " GB")
    except Exception as e:
        print("chr" + c + "  ERROR: " + str(e)[:80])
print("Total: " + str(round(total/1e9, 2)) + " GB")
