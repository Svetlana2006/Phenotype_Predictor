from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


@dataclass(frozen=True)
class MultiTaskHead:
    name: str
    kind: str
    output_dim: int


class MultiTaskPhenotypeNet(nn.Module):
    def __init__(self, input_dim: int, heads: list[MultiTaskHead], hidden_dim: int = 128, dropout: float = 0.2):
        super().__init__()
        self.heads = heads
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.output_heads = nn.ModuleDict(
            {
                head.name: nn.Linear(hidden_dim, 1 if head.kind == "regression" else head.output_dim)
                for head in heads
            }
        )

    def forward(self, x: torch.Tensor) -> dict[str, torch.Tensor]:
        shared = self.encoder(x)
        return {name: head(shared) for name, head in self.output_heads.items()}


def masked_multitask_loss(
    outputs: dict[str, torch.Tensor],
    targets: dict[str, torch.Tensor],
    masks: dict[str, torch.Tensor],
    heads: list[MultiTaskHead],
) -> torch.Tensor:
    losses = []
    for head in heads:
        output = outputs[head.name]
        target = targets[head.name]
        mask = masks[head.name].bool()
        if mask.sum() == 0:
            continue
        if head.kind == "regression":
            loss = nn.functional.l1_loss(output[mask].squeeze(-1), target[mask].float())
        else:
            loss = nn.functional.cross_entropy(output[mask], target[mask].long())
        losses.append(loss)
    if not losses:
        return torch.tensor(0.0, requires_grad=True)
    return torch.stack(losses).mean()
