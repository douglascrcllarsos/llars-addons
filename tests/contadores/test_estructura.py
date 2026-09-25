from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2] / "contadores"


def test_config_yaml_valido():
    cfg = yaml.safe_load((RAIZ / "config.yaml").read_text(encoding="utf-8"))
    assert cfg["slug"] == "contadores"
    assert cfg["services"] == ["mqtt:need"]
    assert "image" not in cfg, "build local: sin imagen prefabricada"
    assert "ingress" not in cfg
    # el schema exige lista de módulos con canales declarados
    assert "modulos" in cfg["schema"]


def test_ficheros_arranque():
    assert (RAIZ / "Dockerfile").is_file()
    assert (RAIZ / "rootfs" / "run.sh").is_file()
    assert (RAIZ / "rootfs" / "app").is_dir()
