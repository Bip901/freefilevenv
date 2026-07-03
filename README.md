# FreeFileVenv

FreeFileSync wrapper to derive a FreeFileSync configuration file from another one.
Supports both Windows and Linux.

This is useful, for example, if you want your Google Drive backup rules to be the same
as your USB backup, except for some slight modifications - e.g. you don't want to back up heavy videos to Google Drive.

## Installation

```shell
uv sync
```

## Usage

```
freefilevenv --help
```

## Example Config File

```xml
<!-- Put this file at %appdata%\freefilevenv\config.xml or another location of your choice -->
<config>
  <default_venv>google-drive</default_venv>
  <freefilesync_path>C:\Program Files\FreeFileSync\FreeFileSync.exe</freefilesync_path>

  <venv name="google-drive">
    <global_settings_patches>
      <set_value xpath="/FreeFileSync/FailSafeFileCopy/@Enabled" new_value="false" />
      <set_value xpath="/FreeFileSync/LockDirectoriesDuringSync/@Enabled" new_value="false" />
    </global_settings_patches>
    <patch_file path="Backup to USB.ffs_gui" new_path="Backup to Google Drive.ffs_gui"
      delete_on_shutdown="true">
      <add_child xpath="/FreeFileSync/FolderPairs/Pair[1]/Filter/Exclude" child_name="Item"
        child_value="/Videos/" />
    </patch_file>
  </venv>

</config>
```

Then, running `freefilevenv` simply launches the executable defined in `freefilesync_path` while modifying its internal files according to the defined rules.

Changes you make in the GUI will be saved separately from your main FreeFileSync instance, in `%appdata%\freefilevenv` (or `~/.config/freefilevenv` for Linux).

For a list of possible rules, see [config.py](./src/freefilevenv/config.py).
