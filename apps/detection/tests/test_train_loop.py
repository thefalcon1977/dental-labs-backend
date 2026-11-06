"""Training / validation epoch helpers on a tiny model."""

from __future__ import annotations

import torch
from densnet.train_loop import train_epoch, validate
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


class TinyClassifier(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.fc = nn.Linear(8, 3)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.fc(x.view(x.size(0), -1))


def _loader() -> DataLoader:
    images = torch.randn(8, 8)
    labels = torch.tensor([0, 1, 2, 0, 1, 2, 0, 1])
    return DataLoader(TensorDataset(images, labels), batch_size=4)


def test_train_epoch_returns_finite_metrics() -> None:
    device = torch.device("cpu")
    model = TinyClassifier()
    loader = _loader()
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)

    loss, acc, preds, labels = train_epoch(model, loader, criterion, optimizer, device)
    assert model.training is True
    assert loss == loss  # not NaN
    assert 0.0 <= acc <= 100.0
    assert len(preds) == len(labels) == 8


def test_validate_does_not_update_weights() -> None:
    device = torch.device("cpu")
    model = TinyClassifier()
    loader = _loader()
    criterion = nn.CrossEntropyLoss()
    before = {name: param.detach().clone() for name, param in model.named_parameters()}

    loss, acc, preds, labels = validate(model, loader, criterion, device)
    assert model.training is False
    assert loss == loss
    assert 0.0 <= acc <= 100.0
    assert len(preds) == len(labels) == 8
    for name, param in model.named_parameters():
        assert torch.equal(param, before[name])
