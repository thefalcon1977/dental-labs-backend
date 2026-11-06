"""Folder dataset for segmented patches."""

from __future__ import annotations

from pathlib import Path

from densnet.constants import CLASS_NAMES
from densnet.dataset import DentalRadiographyDataset
from densnet.transforms import eval_transform
from PIL import Image


def test_dataset_labels_follow_class_order(class_folders: Path) -> None:
    dataset = DentalRadiographyDataset(class_folders)
    assert len(dataset) == 3
    assert dataset.class_to_idx == {name: idx for idx, name in enumerate(CLASS_NAMES)}
    labels = [dataset[i][1] for i in range(len(dataset))]
    assert sorted(labels) == [0, 1, 2]


def test_dataset_skips_non_images_and_missing_class_dirs(tmp_path: Path) -> None:
    dentin = tmp_path / "dentin"
    dentin.mkdir()
    Image.new("RGB", (16, 16), color="red").save(dentin / "ok.png")
    (dentin / "skip.txt").write_text("x", encoding="utf-8")
    # enamel / pulp dirs omitted on purpose
    dataset = DentalRadiographyDataset(tmp_path)
    assert len(dataset) == 1
    _image, label = dataset[0]
    assert label == 0


def test_dataset_applies_transform(class_folders: Path) -> None:
    dataset = DentalRadiographyDataset(class_folders, transform=eval_transform())
    image, label = dataset[0]
    assert tuple(image.shape) == (3, 224, 224)
    assert label in {0, 1, 2}


def test_dataset_corrupt_image_falls_back_to_black(tmp_path: Path) -> None:
    dentin = tmp_path / "dentin"
    dentin.mkdir()
    (dentin / "bad.png").write_bytes(b"not a png")
    dataset = DentalRadiographyDataset(tmp_path)
    image, label = dataset[0]
    assert label == 0
    assert image.size == (224, 224)
    assert image.getpixel((0, 0)) == (0, 0, 0)


def test_empty_dataset(tmp_path: Path) -> None:
    assert len(DentalRadiographyDataset(tmp_path)) == 0
