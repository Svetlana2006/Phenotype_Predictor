from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Marker:
    gene: str
    rsid: str
    allele: str

    @property
    def feature_name(self) -> str:
        return f"{self.rsid}_{self.allele}"


HIRISPLEX_S_MARKERS = [
    Marker("MC1R", "rs312262906", "A"),
    Marker("MC1R", "rs11547464", "A"),
    Marker("MC1R", "rs885479", "T"),
    Marker("MC1R", "rs1805008", "T"),
    Marker("MC1R", "rs1805005", "T"),
    Marker("MC1R", "rs1805006", "A"),
    Marker("MC1R", "rs1805007", "T"),
    Marker("TUBB3", "rs1805009", "C"),
    Marker("MC1R", "rs201326893", "A"),
    Marker("MC1R", "rs2228479", "A"),
    Marker("MC1R", "rs1110400", "C"),
    Marker("SLC45A2", "rs28777", "C"),
    Marker("SLC45A2", "rs16891982", "C"),
    Marker("KITLG", "rs12821256", "G"),
    Marker("LOC105374875", "rs4959270", "A"),
    Marker("IRF4", "rs12203592", "T"),
    Marker("TYR", "rs1042602", "T"),
    Marker("OCA2", "rs1800407", "A"),
    Marker("SLC24A4", "rs2402130", "G"),
    Marker("HERC2", "rs12913832", "T"),
    Marker("PIGU", "rs2378249", "C"),
    Marker("LOC105370627", "rs12896399", "T"),
    Marker("TYR", "rs1393350", "T"),
    Marker("TYRP1", "rs683", "G"),
    Marker("ANKRD11", "rs3114908", "T"),
    Marker("OCA2", "rs1800414", "C"),
    Marker("BNC2", "rs10756819", "G"),
    Marker("HERC2", "rs2238289", "C"),
    Marker("SLC24A4", "rs17128291", "C"),
    Marker("HERC2", "rs6497292", "C"),
    Marker("HERC2", "rs1129038", "G"),
    Marker("HERC2", "rs1667394", "C"),
    Marker("TYR", "rs1126809", "A"),
    Marker("OCA2", "rs1470608", "A"),
    Marker("SLC24A5", "rs1426654", "G"),
    Marker("ASIP", "rs6119471", "C"),
    Marker("OCA2", "rs1545397", "T"),
    Marker("RALY", "rs6059655", "T"),
    Marker("OCA2", "rs12441727", "A"),
    Marker("MC1R", "rs3212355", "A"),
    Marker("DEF8", "rs8051733", "C"),
]


def marker_manifest() -> pd.DataFrame:
    return pd.DataFrame(
        [{"gene": m.gene, "rsid": m.rsid, "allele": m.allele, "feature": m.feature_name} for m in HIRISPLEX_S_MARKERS]
    )


def extract_hirisplex_counts(genotypes: pd.DataFrame) -> pd.DataFrame:
    """Convert long-form genotypes to HIrisPlex-S allele-count features.

    Expected columns: sample_id, rsid, allele_1, allele_2.
    Output values are 0, 1, 2, or NA when a marker is missing.
    """
    required = {"sample_id", "rsid", "allele_1", "allele_2"}
    missing = required.difference(genotypes.columns)
    if missing:
        raise ValueError(f"Missing required genotype columns: {sorted(missing)}")

    rows = []
    grouped = genotypes.groupby("sample_id")
    for sample_id, group in grouped:
        by_rsid = group.set_index("rsid")
        row = {"sample_id": sample_id}
        for marker in HIRISPLEX_S_MARKERS:
            if marker.rsid not in by_rsid.index:
                row[marker.feature_name] = pd.NA
                continue
            record = by_rsid.loc[marker.rsid]
            if isinstance(record, pd.DataFrame):
                record = record.iloc[0]
            row[marker.feature_name] = int(record["allele_1"] == marker.allele) + int(record["allele_2"] == marker.allele)
        rows.append(row)
    return pd.DataFrame(rows)
