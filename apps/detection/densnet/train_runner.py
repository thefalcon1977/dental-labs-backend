"""Full training pipeline: data → train → test → plots."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns
import torch
import torch.nn as nn
import torch.optim as optim
from densnet.constants import CLASS_NAMES
from densnet.dataset import DentalRadiographyDataset
from densnet.device import describe_device, get_device
from densnet.model import create_densenet121
from densnet.train_loop import train_epoch, validate
from densnet.transforms import eval_transform, train_transform
from sklearn.metrics import classification_report, confusion_matrix
from torch.utils.data import DataLoader, WeightedRandomSampler


def run_training(
    *,
    train_dir: str | Path = "segmented_dental_adiography/train",
    val_dir: str | Path = "segmented_dental_adiography/valid",
    test_dir: str | Path = "segmented_dental_adiography/test",
    best_model_path: str | Path = "best_densenet_model.pth",
    num_epochs: int = 30,
    batch_size: int = 16,
    patience: int = 7,
) -> None:
    """Train DenseNet121, evaluate on the test set, and write plots.

    Final recipe (defaults in this function):

    * Optimizer: AdamW, ``weight_decay=1e-4``
    * Learning rate: ``1e-4`` (backbone), ``1e-3`` (classifier head)
    * Batch size: 16
    * Epochs: 30 maximum; early stopping after 7 epochs with no gain in
      validation accuracy
    * LR scheduler: ``ReduceLROnPlateau`` on validation loss (factor 0.5,
      patience 3)

    Images are loaded from **pre-split** ``train`` / ``valid`` / ``test``
    folders. This function does not randomly split a single pool of images.
    Augmentation is applied on train only via :func:`train_transform`.

    Args:
        train_dir: ``{class_name}/*`` training patches.
        val_dir: Validation patches (no augmentation).
        test_dir: Held-out test patches (no augmentation).
        best_model_path: Where to save the best validation-accuracy checkpoint.
        num_epochs: Maximum epochs (early stopping may stop sooner).
        batch_size: Mini-batch size for train, val, and test loaders.
        patience: Epochs without validation-accuracy improvement before stop.
    """
    device = get_device()
    print(f"Using device: {describe_device(device)}")

    print("\n" + "=" * 60)
    print("Loading Datasets...")
    print("=" * 60)

    train_dataset = DentalRadiographyDataset(train_dir, transform=train_transform())
    val_dataset = DentalRadiographyDataset(val_dir, transform=eval_transform())
    test_dataset = DentalRadiographyDataset(test_dir, transform=eval_transform())

    print(f"Train samples: {len(train_dataset)}")
    print(f"Validation samples: {len(val_dataset)}")
    print(f"Test samples: {len(test_dataset)}")

    train_labels = [train_dataset.labels[i] for i in range(len(train_dataset))]
    class_counts = Counter(train_labels)
    print("\nClass distribution in training set:")
    for idx, count in sorted(class_counts.items()):
        print(f"  {train_dataset.idx_to_class[idx]}: {count} samples")

    total_samples = len(train_labels)
    class_weights = [total_samples / (3 * class_counts.get(idx, 1)) for idx in range(3)]
    sample_weights = [class_weights[label] for label in train_labels]
    weighted_sampler = WeightedRandomSampler(
        weights=sample_weights,
        num_samples=len(sample_weights),
        replacement=True,
    )

    use_cuda = device.type == "cuda"
    pin_memory = use_cuda
    num_workers = 2 if use_cuda else 0
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        sampler=weighted_sampler,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=pin_memory,
    )

    print("\n" + "=" * 60)
    print("Creating Model...")
    print("=" * 60)
    model = create_densenet121(pretrained=True).to(device)
    print("Model: DenseNet121")
    print(f"Total parameters: {sum(p.numel() for p in model.parameters()):,}")
    print(
        "Trainable parameters: "
        f"{sum(p.numel() for p in model.parameters() if p.requires_grad):,}"
    )

    criterion = nn.CrossEntropyLoss(weight=torch.FloatTensor(class_weights).to(device))
    optimizer = optim.AdamW(
        [
            {
                "params": [
                    p for n, p in model.named_parameters() if "classifier" not in n
                ],
                "lr": 1e-4,
            },
            {
                "params": [p for n, p in model.named_parameters() if "classifier" in n],
                "lr": 1e-3,
            },
        ],
        weight_decay=1e-4,
    )
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=3
    )

    train_losses: list[float] = []
    train_accs: list[float] = []
    val_losses: list[float] = []
    val_accs: list[float] = []
    best_val_acc = 0.0
    patience_counter = 0
    best_path = Path(best_model_path)

    print("\n" + "=" * 60)
    print("Starting Training...")
    print("=" * 60)

    for epoch in range(num_epochs):
        print(f"\nEpoch {epoch + 1}/{num_epochs}")
        print("-" * 60)

        train_loss, train_acc, _, _ = train_epoch(
            model, train_loader, criterion, optimizer, device
        )
        val_loss, val_acc, _, _ = validate(model, val_loader, criterion, device)

        old_lr = optimizer.param_groups[0]["lr"]
        scheduler.step(val_loss)
        new_lr = optimizer.param_groups[0]["lr"]

        train_losses.append(train_loss)
        train_accs.append(train_acc)
        val_losses.append(val_loss)
        val_accs.append(val_acc)

        print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")
        print(f"Learning Rate: {new_lr:.6f}", end="")
        if new_lr < old_lr:
            print(f" (reduced from {old_lr:.6f})")
        else:
            print()

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_acc": val_acc,
                    "val_loss": val_loss,
                },
                best_path,
            )
            print(f"✅ Saved best model with validation accuracy: {val_acc:.2f}%")
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping triggered after {epoch + 1} epochs")
                break

    print("\n" + "=" * 60)
    print("Testing on Test Set...")
    print("=" * 60)

    checkpoint = torch.load(best_path, map_location=device, weights_only=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    print(
        f"Loaded model from epoch {checkpoint['epoch'] + 1} "
        f"with val_acc: {checkpoint['val_acc']:.2f}%"
    )

    test_loss, test_acc, test_preds, test_labels = validate(
        model, test_loader, criterion, device
    )
    print(f"\nTest Loss: {test_loss:.4f}")
    print(f"Test Accuracy: {test_acc:.2f}%")

    print("\n" + "=" * 60)
    print("Detailed Classification Report")
    print("=" * 60)
    print("\nTest Set Classification Report:")
    print(
        classification_report(
            test_labels,
            test_preds,
            target_names=CLASS_NAMES,
            digits=4,
        )
    )

    cm = confusion_matrix(test_labels, test_preds)
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=CLASS_NAMES,
        yticklabels=CLASS_NAMES,
    )
    plt.title("Confusion Matrix - Test Set")
    plt.ylabel("True Label")
    plt.xlabel("Predicted Label")
    plt.tight_layout()
    plt.savefig("confusion_matrix.png", dpi=300)
    print("\nConfusion matrix saved to confusion_matrix.png")

    _fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    axes[0].plot(train_losses, label="Train Loss", linewidth=2)
    axes[0].plot(val_losses, label="Val Loss", linewidth=2)
    axes[0].set_xlabel("Epoch", fontsize=12)
    axes[0].set_ylabel("Loss", fontsize=12)
    axes[0].set_title("Training and Validation Loss", fontsize=14)
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(train_accs, label="Train Acc", linewidth=2)
    axes[1].plot(val_accs, label="Val Acc", linewidth=2)
    axes[1].set_xlabel("Epoch", fontsize=12)
    axes[1].set_ylabel("Accuracy (%)", fontsize=12)
    axes[1].set_title("Training and Validation Accuracy", fontsize=14)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("training_history.png", dpi=300)
    print("Training history saved to training_history.png")

    print("\n" + "=" * 60)
    print("Training Summary")
    print("=" * 60)
    print(f"Best Validation Accuracy: {best_val_acc:.2f}%")
    print(f"Test Accuracy: {test_acc:.2f}%")
    print(f"Total Epochs Trained: {len(train_losses)}")
    print(f"Best Model Saved: {best_path}")
    print("=" * 60)
