import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import platformdirs
from xmlpatcher import Transformation, XMLDocument

from .config import Config, VenvConfig

config_dir = Path(platformdirs.user_config_dir("freefilevenv", appauthor=False, roaming=True))

VENV_NAME_REGEX = re.compile(r"^[a-zA-Z-_0-9]+$")


def _run_shell_command(command: str) -> None:
    if sys.platform == "win32":
        subprocess.run(["pwsh", "-Command", command], check=True)
    else:
        subprocess.run(["bash", "-c", command], check=True)


def launch_freefilesync(config: Config, venv_config: VenvConfig) -> None:
    freefilesync_path = shutil.which(config.freefilesync_path)
    if freefilesync_path is None:
        raise ValueError(f"Executable not found: {freefilesync_path}")
    freefilesync_appdata_dir = config.freefilesync_appdata_path or Path(
        platformdirs.user_config_dir("FreeFileSync", appauthor=False, roaming=True)
    )
    global_settings = XMLDocument(freefilesync_appdata_dir / "GlobalSettings.xml")
    global_settings.patch(*venv_config.global_settings_patches.to_xml_patches())

    venv_dir = config_dir / "venvs" / venv_config.name
    venv_dir.mkdir(parents=True, exist_ok=True)
    config_panel_path = venv_dir / "ConfigPanel.xml"
    print(f"Loading ConfigPanel element from {config_panel_path}")
    global_settings.load_element("/FreeFileSync/MainDialog/ConfigPanel", config_panel_path)

    for file_patch in venv_config.file_patches:
        original_path = freefilesync_appdata_dir / file_patch.path
        if not original_path.is_file():
            raise ValueError(f"Can't patch non-existent file at {file_patch.path}")
        new_path = venv_dir / file_patch.new_path
        print(f"Patching {original_path} -> {new_path}")
        Transformation(original_path, new_path, *file_patch.to_xml_patches()).apply()

    if venv_config.run_before:
        _run_shell_command(venv_config.run_before)

    with global_settings.save_to_temp_file() as modified_global_settings_path:
        print(f"Launching FreeFileSync with global settings from {modified_global_settings_path}")
        subprocess.run([freefilesync_path, modified_global_settings_path])
        modified_global_settings = XMLDocument(modified_global_settings_path)
        modified_global_settings.save_element("/FreeFileSync/MainDialog/ConfigPanel", config_panel_path)
        for file_patch in venv_config.file_patches:
            if file_patch.delete_on_shutdown:
                (venv_dir / file_patch.new_path).unlink()

    if venv_config.run_after:
        _run_shell_command(venv_config.run_after)


def main() -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.xml"

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, help=f"Optionally, path to config file. Defaults to {config_path}")
    parser.add_argument(
        "--venv",
        type=str,
        help="The name of the FreeFileSync venv to use. Defaults to the venv specified in config.xml.",
    )
    args = parser.parse_args()

    if args.config:
        config_path = Path(args.config)

    if not config_path.exists():
        print("Config file does not exist yet (is this your first run?)")
        xml_bytes: bytes = Config.get_default().to_xml(
            pretty_print=True, exclude_none=True, encoding="UTF-8", standalone=True
        )  # type: ignore[assignment]
        config_path.write_bytes(xml_bytes)
        print(f"Created config file {config_path}")
        print("Please edit it and run again.")
        exit(1)

    config = Config.from_xml(config_path.read_bytes())
    venv_name = args.venv or config.default_venv
    if venv_name is None:
        print("No --venv specified and no default_venv was given in the configuration file.")
        exit(2)
    if not VENV_NAME_REGEX.fullmatch(venv_name):
        print(f"venv name '{venv_name}' must match regex ${VENV_NAME_REGEX.pattern}")
        exit(3)
    try:
        venv_config = next(venv_config for venv_config in config.venv_configs if venv_config.name == venv_name)
    except StopIteration:
        print(f"venv '{venv_name}' is not defined in configuration file.")
        exit(4)
    launch_freefilesync(config, venv_config)
