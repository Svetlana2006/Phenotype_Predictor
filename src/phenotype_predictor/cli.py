from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from phenotype_predictor.config import OUTPUT_DIR
from phenotype_predictor.data_io import read_table, split_features_target, write_table
from phenotype_predictor.datasets.gse40279 import prepare_age_table
from phenotype_predictor.datasets.igsr import prepare_ancestry_table
from phenotype_predictor.markers.hirisplex import extract_hirisplex_counts, marker_manifest
from phenotype_predictor.models.baselines import train_classifiers, train_regressors
from phenotype_predictor.models.multitask_train import train_multitask_table
from phenotype_predictor.reporting import write_model_card


def _cmd_markers(args: argparse.Namespace) -> None:
    manifest = marker_manifest()
    write_table(manifest, args.output)
    print(f"Wrote {len(manifest)} HIrisPlex-S markers to {args.output}")


def _cmd_extract_hirisplex(args: argparse.Namespace) -> None:
    genotypes = read_table(args.input)
    features = extract_hirisplex_counts(genotypes)
    write_table(features, args.output)
    print(f"Wrote marker-count matrix for {len(features)} samples to {args.output}")


def _cmd_train_age(args: argparse.Namespace) -> None:
    df = read_table(args.input)
    x, y = split_features_target(df, args.target)
    results = train_regressors(x, y, args.output_dir)
    for result in results:
        write_model_card(
            Path(args.output_dir) / f"{result.model_name}_model_card.md",
            f"Age model: {result.model_name}",
            args.input,
            args.target,
            result.metrics,
            [
                "Chronological age prediction is dependent on tissue type and training population.",
                "External validation is required before any forensic interpretation.",
            ],
        )
        print(result.model_name, result.metrics, result.model_path)


def _cmd_prepare_gse40279(args: argparse.Namespace) -> None:
    df = prepare_age_table(args.beta, args.sample_key, args.output, max_cpgs=args.max_cpgs)
    print(f"Wrote GSE40279 age table with {len(df)} samples and {len(df.columns) - 2} CpG features to {args.output}")


def _cmd_prepare_igsr(args: argparse.Namespace) -> None:
    df = prepare_ancestry_table(args.features, args.sample_panel, args.output, target=args.target)
    print(f"Wrote IGSR ancestry table with {len(df)} samples and {len(df.columns) - 2} SNP features to {args.output}")


def _cmd_train_multitask(args: argparse.Namespace) -> None:
    df = read_table(args.input)
    targets = {}
    for item in args.target:
        name, kind = item.split(":", 1)
        if kind not in {"regression", "classification"}:
            raise ValueError("Targets must be formatted as column:regression or column:classification")
        targets[name] = kind
    metadata = train_multitask_table(
        df,
        targets,
        args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        hidden_dim=args.hidden_dim,
    )
    print(f"Wrote multi-task model to {args.output_dir}")
    print(f"Targets: {metadata['targets']}")


def _cmd_train_ancestry(args: argparse.Namespace) -> None:
    df = read_table(args.input)
    x, y = split_features_target(df, args.target)
    results = train_classifiers(x, y, args.output_dir)
    for result in results:
        write_model_card(
            Path(args.output_dir) / f"{result.model_name}_model_card.md",
            f"Ancestry model: {result.model_name}",
            args.input,
            args.target,
            result.metrics,
            [
                "Population labels are proxies for reference-panel structure, not identity.",
                "Confidence should be reduced for samples far from the training distribution.",
            ],
        )
        print(result.model_name, result.metrics, result.model_path)


def _cmd_smoke(_: argparse.Namespace) -> None:
    out = OUTPUT_DIR / "smoke"
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)

    age_df = pd.DataFrame(rng.normal(size=(120, 12)), columns=[f"cpg_{i}" for i in range(12)])
    age_df.insert(0, "sample_id", [f"A{i:03d}" for i in range(len(age_df))])
    age_df["age"] = 45 + age_df["cpg_0"] * 9 - age_df["cpg_3"] * 4 + rng.normal(scale=3, size=len(age_df))
    age_path = out / "synthetic_age.csv"
    write_table(age_df, age_path)
    _cmd_train_age(argparse.Namespace(input=age_path, target="age", output_dir=out / "age_models"))

    ancestry_df = pd.DataFrame(rng.normal(size=(150, 16)), columns=[f"snp_{i}" for i in range(16)])
    labels = np.array(["SAS", "EUR", "AFR"])
    y = np.repeat(labels, 50)
    ancestry_df.loc[y == "SAS", ["snp_0", "snp_1"]] += 1.5
    ancestry_df.loc[y == "EUR", ["snp_2", "snp_3"]] += 1.5
    ancestry_df.loc[y == "AFR", ["snp_4", "snp_5"]] += 1.5
    ancestry_df.insert(0, "sample_id", [f"P{i:03d}" for i in range(len(ancestry_df))])
    ancestry_df["ancestry"] = y
    ancestry_path = out / "synthetic_ancestry.csv"
    write_table(ancestry_df, ancestry_path)
    _cmd_train_ancestry(argparse.Namespace(input=ancestry_path, target="ancestry", output_dir=out / "ancestry_models"))

    marker_path = out / "hirisplex_s_markers.csv"
    _cmd_markers(argparse.Namespace(output=marker_path))

    multitask_df = ancestry_df.drop(columns=["ancestry"]).merge(age_df[["sample_id", "age"]], on="sample_id", how="outer")
    multitask_df["ancestry"] = pd.Series(y).sample(len(multitask_df), replace=True, random_state=42).to_numpy()
    multitask_path = out / "synthetic_multitask.csv"
    write_table(multitask_df, multitask_path)
    _cmd_train_multitask(
        argparse.Namespace(
            input=multitask_path,
            target=["age:regression", "ancestry:classification"],
            output_dir=out / "multitask_model",
            epochs=5,
            batch_size=32,
            hidden_dim=32,
        )
    )
    print(f"Smoke test complete. Outputs: {out}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phenotype Predictor CLI")
    sub = parser.add_subparsers(required=True)

    markers = sub.add_parser("markers", help="Write HIrisPlex-S marker manifest")
    markers.add_argument("--output", default=OUTPUT_DIR / "hirisplex_s_markers.csv")
    markers.set_defaults(func=_cmd_markers)

    extract = sub.add_parser("extract-hirisplex", help="Extract HIrisPlex-S allele-count features from long genotypes")
    extract.add_argument("--input", required=True)
    extract.add_argument("--output", required=True)
    extract.set_defaults(func=_cmd_extract_hirisplex)

    train_age = sub.add_parser("train-age", help="Train baseline age regressors from a table")
    train_age.add_argument("--input", required=True)
    train_age.add_argument("--target", default="age")
    train_age.add_argument("--output-dir", default=OUTPUT_DIR / "age_models")
    train_age.set_defaults(func=_cmd_train_age)

    prep_gse = sub.add_parser("prepare-gse40279", help="Prepare GEO GSE40279 methylation age table")
    prep_gse.add_argument("--beta", required=True, help="GSE40279 average beta matrix file")
    prep_gse.add_argument("--sample-key", required=True, help="GSE40279 sample key file")
    prep_gse.add_argument("--output", required=True)
    prep_gse.add_argument("--max-cpgs", type=int, default=5000, help="Limit CpG rows for quick experiments")
    prep_gse.set_defaults(func=_cmd_prepare_gse40279)

    prep_igsr = sub.add_parser("prepare-igsr", help="Join IGSR genotype features to population labels")
    prep_igsr.add_argument("--features", required=True, help="sample_id + SNP dosage feature table")
    prep_igsr.add_argument("--sample-panel", required=True, help="IGSR sample panel")
    prep_igsr.add_argument("--target", default="super_population", choices=["population", "super_population"])
    prep_igsr.add_argument("--output", required=True)
    prep_igsr.set_defaults(func=_cmd_prepare_igsr)

    train_ancestry = sub.add_parser("train-ancestry", help="Train baseline ancestry classifiers from a table")
    train_ancestry.add_argument("--input", required=True)
    train_ancestry.add_argument("--target", default="ancestry")
    train_ancestry.add_argument("--output-dir", default=OUTPUT_DIR / "ancestry_models")
    train_ancestry.set_defaults(func=_cmd_train_ancestry)

    train_multi = sub.add_parser("train-multitask", help="Train shared neural net with multiple phenotype heads")
    train_multi.add_argument("--input", required=True)
    train_multi.add_argument(
        "--target",
        action="append",
        required=True,
        help="Target spec, e.g. age:regression or eye_color:classification. Repeat for each task.",
    )
    train_multi.add_argument("--output-dir", default=OUTPUT_DIR / "multitask_model")
    train_multi.add_argument("--epochs", type=int, default=40)
    train_multi.add_argument("--batch-size", type=int, default=32)
    train_multi.add_argument("--hidden-dim", type=int, default=128)
    train_multi.set_defaults(func=_cmd_train_multitask)

    smoke = sub.add_parser("smoke", help="Run a synthetic end-to-end smoke test")
    smoke.set_defaults(func=_cmd_smoke)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
