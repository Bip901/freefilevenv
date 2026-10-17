import shutil
import sys
from abc import ABC, abstractmethod
from collections.abc import Iterable
from os.path import expandvars
from pathlib import Path
from typing import Self, override

from pydantic_xml import BaseXmlModel, attr, element
from xmlpatcher import patches as xmlpatches


class BaseXmlPatch(BaseXmlModel, ABC):
    xpath: str = attr()

    @abstractmethod
    def to_xml_patch(self) -> xmlpatches.Patch:
        raise NotImplementedError


class SetValueXmlPatch(BaseXmlPatch, tag="set_value"):
    new_value: str | None = attr()

    @override
    def to_xml_patch(self) -> xmlpatches.Patch:
        return xmlpatches.SetValue(self.xpath, self.new_value)


class AddChildXmlPatch(BaseXmlPatch, tag="add_child"):
    child_name: str = attr()
    child_value: str = attr()

    @override
    def to_xml_patch(self) -> xmlpatches.Patch:
        return xmlpatches.AddChild(self.xpath, self.child_name, self.child_value)


class RemoveXmlPatch(BaseXmlPatch, tag="remove"):
    @override
    def to_xml_patch(self) -> xmlpatches.Patch:
        return xmlpatches.Remove(self.xpath)


class PatchList(BaseXmlModel):
    patches: list[SetValueXmlPatch | AddChildXmlPatch | RemoveXmlPatch] = element()

    def to_xml_patches(self) -> Iterable[xmlpatches.Patch]:
        yield from (patch.to_xml_patch() for patch in self.patches)


class FilePatch(PatchList, tag="patch_file"):
    path: Path = attr()
    """The new file path, either absolute or relative to the FreeFileSync app data directory."""
    new_path: Path = attr()
    """The new file path, either absolute or relative to the venv directory."""
    delete_on_shutdown: bool = attr(default=True)


class RunBeforeCommand(BaseXmlModel):
    command: str
    keep_alive: bool = attr(default=False)
    """If true, doesn't wait for the shell process to finish, and kills it when FreeFileSync is closed."""
    wait_for_stderr: bool = attr(default=False)
    """
    If true, waits for the shell process to write anything to stderr before starting FreeFileSync,
    and closes the processe's stdin to signal it to stop.
    This only has an effect if keep_alive is true, because otherwise we wait for the process to exit entirely.
    """


class VenvConfig(BaseXmlModel, tag="venv"):
    name: str = attr()
    run_before: RunBeforeCommand | None = element(default=None)
    """A shell command (pwsh for Windows, bash for Linux) to run prior to running FreeFileSync."""
    run_after: str | None = element(default=None)
    """A shell command (pwsh for Windows, bash for Linux) to run after running FreeFileSync."""
    global_settings_patches: PatchList | None = element(default=None)
    file_patches: list[FilePatch] = element(default_factory=list)


class Config(BaseXmlModel, tag="config"):
    default_venv: str | None = element(default=None)
    """The venv to be used when no --venv is specified."""
    freefilesync_path: str = element()
    freefilesync_appdata_path: Path | None = element(default=None)
    venv_configs: list[VenvConfig] = element()

    @classmethod
    def get_default(cls) -> Self:
        if shutil.which("FreeFileSync") is not None:
            freefilesync_path = "FreeFileSync"
        else:
            match os_platform := sys.platform:
                case "linux":
                    freefilesync_path = "/opt/FreeFileSync/FreeFileSync"
                case "win32":
                    freefilesync_path = expandvars(R"$programfiles\FreeFileSync\FreeFileSync.exe")
                case _:
                    raise RuntimeError(f"Unsupported OS: {os_platform}")
        return cls(
            default_venv="example-venv",
            freefilesync_path=freefilesync_path,
            venv_configs=[
                VenvConfig(
                    name="example-venv",
                    global_settings_patches=PatchList(
                        patches=[
                            SetValueXmlPatch(xpath="/FreeFileSync/FailSafeFileCopy/@Enabled", new_value="false"),
                            SetValueXmlPatch(
                                xpath="/FreeFileSync/LockDirectoriesDuringSync/@Enabled", new_value="false"
                            ),
                        ]
                    ),
                    file_patches=[],
                )
            ],
        )

    def resolve_freefilesync_path(self) -> Path:
        freefilesync_path = shutil.which(self.freefilesync_path)
        if freefilesync_path is None:
            raise ValueError(f"Executable not found: {freefilesync_path}")
        return Path(freefilesync_path)
