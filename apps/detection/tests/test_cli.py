"""Unified CLI dispatch on ``main.py``."""

from __future__ import annotations

import pytest
from densnet.constants import CLASS_NAMES
from main import build_parser, main


def test_parser_requires_an_action() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_parser_predict_choices() -> None:
    parser = build_parser()
    args = parser.parse_args(["--predict", "enamel"])
    assert args.predict == "enamel"
    for name in [*CLASS_NAMES, "all"]:
        assert parser.parse_args(["--predict", name]).predict == name


def test_image_requires_detect(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--train", "--image", "x.png"])
    assert exc.value.code == 2
    assert "--image can only be used with --detect" in capsys.readouterr().err


def test_train_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []
    monkeypatch.setattr("main._cmd_train", lambda: called.append(True))
    main(["--train"])
    assert called == [True]


def test_evaluate_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []
    monkeypatch.setattr("main._cmd_evaluate", lambda: called.append(True))
    main(["--evaluate"])
    assert called == [True]


def test_roc_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []
    monkeypatch.setattr("main._cmd_roc", lambda: called.append(True))
    main(["--roc"])
    assert called == [True]


def test_predict_all_runs_each_class(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(
        "densnet.predict_batch.run_folder_predictions",
        lambda name: seen.append(name),
    )
    main(["--predict", "all"])
    assert seen == CLASS_NAMES


def test_detect_passes_image_path(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str | None] = []
    monkeypatch.setattr(
        "densnet.detect.run_detect_cli",
        lambda image: seen.append(image),
    )
    main(["--detect", "--image", "radiograph.png"])
    assert seen == ["radiograph.png"]


def test_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0
