import re
from typing import Dict

# 20bp flanking sequences (upstream and downstream) for crucial HIrisPlex SNPs.
# Real biological flanking sequences (hg38) for targeted SNPs.
# We also track the exact allele the ML model expects (target_allele).
SNP_FLANKING_DB = {
    # If target is T, and user sequence has A (complement), dosage of T is 2.
    "rs12913832": {"up": "AGATTTTATTG", "down": "TGAAAATGTTT", "target_allele": "T", "complement": "A"},
    "rs16891982": {"up": "ATGAAAGGAGTGAGAACAAA", "down": "TCTATACCAATTGCTACTGT", "target_allele": "C", "complement": "G"},
    "rs1426654":  {"up": "TCCGTGTACCGC", "down": "TGTTCGGTGGT", "target_allele": "G", "complement": "C"},
    "rs12203592": {"up": "GCTCTGTGCTGAACGTGCCT", "down": "GACCTGGCCTGATGAGGTGC", "target_allele": "T", "complement": "A"},
    "rs12896399": {"up": "TCCACTCTGGAAAGTAACGA", "down": "AAGACACCAGTGTGACAGTC", "target_allele": "T", "complement": "A"},
    "rs1800407":  {"up": "GCAGTGACCG", "down": "CCTGAGGAGG", "target_allele": "A", "complement": "T"}
}

def reverse_complement(seq: str) -> str:
    """Returns the reverse complement of a DNA string."""
    mapping = str.maketrans("ATCG", "TAGC")
    return seq.translate(mapping)[::-1]

def extract_snps_from_sequence(raw_sequence: str) -> Dict[str, int]:
    """
    Scans a raw DNA string (ATCG...) for known flanking regions to extract SNP alleles.
    Returns a dictionary of {rsID_target: dosage_count} (0 or 2).
    """
    sequence = "".join(raw_sequence.split()).upper() # Remove whitespaces/newlines
    rev_sequence = reverse_complement(sequence)
    
    extracted_snps = {}
    
    for rs_id, data in SNP_FLANKING_DB.items():
        pattern = data["up"] + r"([ATCG])" + data["down"]
        
        # Check forward strand
        match = re.search(pattern, sequence)
        
        # Check reverse strand if forward failed
        if not match:
            match = re.search(pattern, rev_sequence)
            
        if match:
            allele = match.group(1)
            target = data["target_allele"]
            comp = data["complement"]
            
            # If the extracted allele is the target, OR is the complementary pair to the target on the opposite strand
            if allele == target or allele == comp:
                extracted_snps[f"{rs_id}_{target}"] = 2
            else:
                extracted_snps[f"{rs_id}_{target}"] = 0
                
    return extracted_snps
