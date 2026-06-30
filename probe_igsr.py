"""Probe 1000G FTP for accessible ancestry / PCA files."""
import urllib.request

urls = [
    "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/working/20130606_sample_info/20130606_g1k.ped",
    "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/release/20130502/supporting/hg38_liftover/20130502_phase3_liftover_nygc.hg38.pca.evec",
    "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/working/20131122_sample_lists_for_phase3/20131122_phase3_selection.txt",
    "https://ftp.1000genomes.ebi.ac.uk/vol1/ftp/technical/working/20120131_omni_genotypes_and_intensities/Omni25_genotypes_2141_samples.b37.vcf.gz",
    # IGSR data portal direct download (GRCh38 SNP allele freq table - small)
    "https://www.internationalgenome.org/data-portal/sample",
]

for url in urls:
    fname = url.split("/")[-1]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read(600)
        print(f"OK  {fname}")
        print("    ", data[:200])
        print()
    except Exception as e:
        print(f"FAIL {fname}: {e}")
