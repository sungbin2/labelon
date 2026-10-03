from pathlib import Path

import pytest

from labelon_reviewer import config as cfgmod
from labelon_reviewer.domain import ConfigError


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "config.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_example_config():
    example = Path(__file__).resolve().parents[1] / "config.example.yaml"
    cfg = cfgmod.load(example)
    assert cfg.dataset_id == 688
    assert cfg.persona == "장난기가 많은 어린아이"
    assert set(cfg.archetype_templates) == {"일상지원", "보행안전", "쇼핑", "음식", "실내탐색", "가전조작"}
    assert cfg.models.judge == "claude-sonnet-5"
    assert cfg.base_dir == example.parent


def test_missing_required_field_names_field(tmp_path):
    p = write(tmp_path, "persona: x\n")
    with pytest.raises(ConfigError) as ei:
        cfgmod.load(p)
    assert ei.value.field == "dataset_id"


def test_threshold_out_of_range(tmp_path):
    p = write(tmp_path, "dataset_id: 1\npersona: x\nthreshold: 150\n")
    with pytest.raises(ConfigError) as ei:
        cfgmod.load(p)
    assert ei.value.field == "threshold"


def test_template_without_placeholder(tmp_path):
    p = write(tmp_path, "dataset_id: 1\npersona: x\narchetype_templates:\n  음식: '자리표시자 없음'\n")
    with pytest.raises(ConfigError) as ei:
        cfgmod.load(p)
    assert "archetype_templates" in ei.value.field


def test_chrome_window_format(tmp_path):
    """사이클 9: chrome.window 는 maximized 또는 가로x세로."""
    cfg = cfgmod.load(write(tmp_path, "dataset_id: 1\npersona: x\nchrome:\n  window: 1600x1000\n"))
    assert cfg.chrome.window_size() == (1600, 1000) and cfg.chrome.image_tab is True
    assert cfgmod.AppConfig(dataset_id=1).chrome.window_size() is None
    with pytest.raises(ConfigError) as ei:
        cfgmod.load(write(tmp_path, "dataset_id: 1\npersona: x\nchrome:\n  window: big\n"))
    assert "window" in ei.value.field


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError) as ei:
        cfgmod.load(tmp_path / "nope.yaml")
    assert ei.value.field == "file"


def test_yaml_syntax_error(tmp_path):
    p = write(tmp_path, "dataset_id: [1\n")
    with pytest.raises(ConfigError) as ei:
        cfgmod.load(p)
    assert ei.value.field == "yaml"
