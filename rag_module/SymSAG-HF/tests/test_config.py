from __future__ import annotations

from symsag_hf import SymSAGConfig


def test_config_yaml_roundtrip(tmp_path):
    config = SymSAGConfig(text_encoder={"model_name": "custom-model"})
    path = tmp_path / "config.yaml"
    config.to_yaml(path)

    loaded = SymSAGConfig.from_yaml(path)
    assert loaded.text_encoder["model_name"] == "custom-model"
