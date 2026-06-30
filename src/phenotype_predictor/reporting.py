from __future__ import annotations

from datetime import datetime
from pathlib import Path


def write_model_card(
    path: str | Path,
    title: str,
    training_data: str,
    target: str,
    metrics: dict[str, float],
    limitations: list[str],
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    metric_lines = "\n".join(f"- {key}: {value:.4f}" for key, value in metrics.items())
    limitation_lines = "\n".join(f"- {item}" for item in limitations)
    path.write_text(
        f"""# {title}

Generated: {datetime.utcnow().isoformat()}Z

## Training Data

{training_data}

## Target

{target}

## Metrics

{metric_lines}

## Limitations

{limitation_lines}
""",
        encoding="utf-8",
    )
