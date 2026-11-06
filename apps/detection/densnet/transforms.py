"""Image transforms shared by train / val / inference."""

from __future__ import annotations

from densnet.constants import IMAGENET_MEAN, IMAGENET_STD
from torchvision import transforms


def eval_transform() -> transforms.Compose:
    """Center-crop ImageNet-normalized transform for val/test/inference."""
    return transforms.Compose(
        [
            transforms.Resize((256, 256)),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )


def train_transform() -> transforms.Compose:
    """Augmented transform used only during training.

    After a 256x256 resize: random resized crop to 224 (scale 0.8-1.0, a
    zoom/crop), horizontal flip (p=0.5), vertical flip (p=0.3), rotation
    +/-15 degrees, color jitter, affine translate (10%) and scale (0.9-1.1),
    ImageNet normalize, then random erasing (p=0.2).
    """
    return transforms.Compose(
        [
            transforms.Resize((256, 256)),
            transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.3),
            transforms.RandomRotation(15),
            transforms.ColorJitter(
                brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1
            ),
            transforms.RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1)),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            transforms.RandomErasing(p=0.2, scale=(0.02, 0.33)),
        ]
    )


# Alias for clarity at call sites
val_transform = eval_transform
test_transform = eval_transform
