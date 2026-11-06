"""Train / eval ImageNet transforms."""

from __future__ import annotations

import torch
from densnet import transforms as tf
from densnet.transforms import eval_transform, train_transform
from PIL import Image


def test_eval_transform_output_shape() -> None:
    image = Image.new("RGB", (300, 280), color="gray")
    tensor = eval_transform()(image)
    assert tuple(tensor.shape) == (3, 224, 224)


def test_eval_transform_is_deterministic() -> None:
    image = Image.new("RGB", (256, 256), color=(10, 20, 30))
    transform = eval_transform()
    assert torch.equal(transform(image), transform(image))


def test_train_transform_output_shape() -> None:
    image = Image.new("RGB", (300, 300), color="gray")
    tensor = train_transform()(image)
    assert tuple(tensor.shape) == (3, 224, 224)


def test_val_and_test_aliases_are_eval() -> None:
    assert tf.val_transform is tf.eval_transform
    assert tf.test_transform is tf.eval_transform
