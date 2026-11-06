"""Folder-based Dataset for segmented dental patches."""

from __future__ import annotations

from pathlib import Path

from densnet.constants import CLASS_NAMES, IMAGE_EXTENSIONS
from PIL import Image
from torch.utils.data import Dataset


class DentalRadiographyDataset(Dataset):
    """Load ``{data_dir}/{class_name}/*`` images with class labels."""

    def __init__(self, data_dir: str | Path, transform=None) -> None:
        self.data_dir = Path(data_dir)
        self.transform = transform
        self.images: list[Path] = []
        self.labels: list[int] = []
        self.classes = list(CLASS_NAMES)
        self.class_to_idx = {name: idx for idx, name in enumerate(self.classes)}
        self.idx_to_class = {idx: name for name, idx in self.class_to_idx.items()}

        for class_name in self.classes:
            class_dir = self.data_dir / class_name
            if not class_dir.is_dir():
                continue
            for img_path in sorted(class_dir.iterdir()):
                if img_path.suffix.lower() in IMAGE_EXTENSIONS:
                    self.images.append(img_path)
                    self.labels.append(self.class_to_idx[class_name])

    def __len__(self) -> int:
        return len(self.images)

    def __getitem__(self, idx: int):
        img_path = self.images[idx]
        label = self.labels[idx]
        try:
            image = Image.open(img_path).convert("RGB")
        except OSError as exc:
            print(f"Error loading {img_path}: {exc}")
            image = Image.new("RGB", (224, 224), color="black")

        if self.transform is not None:
            image = self.transform(image)
        return image, label
