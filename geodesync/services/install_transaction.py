"""Transactional install helpers (moved verbatim from v2.8.0 main.py): atomic JSON writes, staged copy with journal, rollback and crash recovery."""

import os
import json
import shutil
import time
import tempfile


def _copy_directory_transactionally(source, destination, validator=None):
    """Stage a complete directory beside its destination, then swap with rollback."""
    source = os.path.abspath(source)
    destination = os.path.abspath(destination)
    parent = os.path.dirname(destination)
    if not os.path.isdir(source):
        raise FileNotFoundError(f"Source app bundle does not exist: {source}")
    os.makedirs(parent, exist_ok=True)
    stage_root = tempfile.mkdtemp(prefix=".geodesync-stage-", dir=parent)
    staged = os.path.join(stage_root, os.path.basename(destination))
    previous = os.path.join(stage_root, "previous")
    moved_previous = False
    try:
        shutil.copytree(source, staged, symlinks=True, copy_function=shutil.copy2)
        if validator:
            problem = validator(staged)
            if problem:
                raise OSError(f"The downloaded Geometry Dash app bundle is incomplete: {problem}")
        if os.path.lexists(destination):
            os.replace(destination, previous)
            moved_previous = True
        try:
            os.replace(staged, destination)
        except Exception:
            if moved_previous and os.path.lexists(previous):
                os.replace(previous, destination)
                moved_previous = False
            raise
    finally:
        # Keep the old app in place if stage creation or validation failed.
        if os.path.lexists(previous) and not os.path.lexists(destination):
            os.replace(previous, destination)
        shutil.rmtree(stage_root, ignore_errors=True)


def safe_copy_item(src, dst, max_retries=5):
    """Copy with bounded retries; file replacement is atomic and failures are never hidden."""
    last_error = None
    for i in range(max_retries):
        try:
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                parent = os.path.dirname(os.path.abspath(dst))
                os.makedirs(parent, exist_ok=True)
                fd, temporary = tempfile.mkstemp(prefix=".geodesync-copy-", dir=parent)
                os.close(fd)
                try:
                    shutil.copy2(src, temporary)
                    try:
                        with open(temporary, "ab") as copied:
                            copied.flush()
                            os.fsync(copied.fileno())
                    except OSError:
                        pass
                    os.replace(temporary, dst)
                except Exception:
                    # Fallback to direct copy if atomic replace fails
                    shutil.copy2(src, dst)
                finally:
                    try:
                        os.unlink(temporary)
                    except (FileNotFoundError, OSError):
                        pass
            return True
        except OSError as e:
            last_error = e
            if i == max_retries - 1:
                try:
                    shutil.copy2(src, dst)
                    return True
                except Exception:
                    raise
            time.sleep(0.2)
        except Exception as e:
            if i == max_retries - 1:
                try:
                    shutil.copy2(src, dst)
                    return True
                except Exception:
                    raise e
            time.sleep(0.2)
    raise last_error or OSError(f"Could not copy {src} to {dst}.")


def atomic_write_json(path, value):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".geodesync-write-", dir=parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.flush()
            try:
                os.fsync(stream.fileno())
            except OSError:
                pass
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except (FileNotFoundError, OSError):
            pass


def _remove_path(path):
    if os.path.islink(path) or (os.path.exists(path) and not os.path.isdir(path)):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def _tree_size(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for root, _dirs, files in os.walk(path, followlinks=False):
        for filename in files:
            try:
                total += os.path.getsize(os.path.join(root, filename))
            except OSError:
                pass
    return total


def _copy_file_with_retry(source, destination, retries=6, delay=0.4):
    for attempt in range(retries):
        try:
            shutil.copy2(source, destination)
            return
        except OSError as e:
            if getattr(e, "winerror", None) in (32, 33, 5) and attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            elif attempt < retries - 1:
                time.sleep(delay)
            else:
                raise


def _safe_replace(source, destination, retries=6, delay=0.4):
    for attempt in range(retries):
        try:
            os.replace(source, destination)
            return
        except OSError as e:
            if getattr(e, "winerror", None) in (32, 33, 5) and attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
            elif attempt < retries - 1:
                time.sleep(delay)
            else:
                raise


def _copy_entry(source, destination):
    if os.path.islink(source):
        os.symlink(os.readlink(source), destination)
    elif os.path.isdir(source):
        shutil.copytree(source, destination, symlinks=True, copy_function=_copy_file_with_retry)
    else:
        _copy_file_with_retry(source, destination)


def _rollback_install_transaction(stage_root, destination_root, journal):
    incoming = os.path.join(stage_root, "incoming")
    previous = os.path.join(stage_root, "previous")
    original_items = set(journal.get("original_items", []))
    for name in reversed(journal.get("items", [])):
        if not isinstance(name, str) or name in ("", ".", "..") or "/" in name or "\\" in name or os.path.basename(name) != name:
            continue
        installed_path = os.path.join(destination_root, name)
        staged_path = os.path.join(incoming, name)
        previous_path = os.path.join(previous, name)
        if os.path.lexists(previous_path):
            if os.path.lexists(installed_path):
                _remove_path(installed_path)
            _safe_replace(previous_path, installed_path)
        elif name not in original_items and not os.path.lexists(staged_path) and os.path.lexists(installed_path):
            _remove_path(installed_path)


def recover_pending_install_transactions(destination_root):
    """Roll back interrupted game swaps left by a crash or power loss."""
    destination_root = os.path.abspath(destination_root)
    recovered = []
    if not os.path.isdir(destination_root):
        return recovered
    for name in os.listdir(destination_root):
        if not name.startswith(".geodesync-transaction-"):
            continue
        stage_root = os.path.join(destination_root, name)
        if os.path.islink(stage_root):
            raise ValueError("An unfinished GeodeSync recovery folder is a symbolic link; it was left untouched.")
        journal_path = os.path.join(stage_root, "journal.json")
        if not os.path.isfile(journal_path):
            shutil.rmtree(stage_root, ignore_errors=True)
            continue
        with open(journal_path, "r", encoding="utf-8") as stream:
            journal = json.load(stream)
        if os.path.abspath(journal.get("destination", "")) != destination_root:
            raise ValueError("An unfinished GeodeSync transaction points to a different game folder.")
        if journal.get("state") != "committed":
            _rollback_install_transaction(stage_root, destination_root, journal)
        shutil.rmtree(stage_root)
        recovered.append(name)
    return recovered


def install_depot_transactionally(
    source_root, destination_root, validator=None, installed_validator=None,
    reserve_bytes=128 * 1024 * 1024,
):
    """Stage and validate every depot entry; rollback all changed entries on any interruption."""
    source_root = os.path.abspath(source_root)
    destination_root = os.path.abspath(destination_root)
    if not os.path.isdir(source_root) or not os.path.isdir(destination_root):
        raise FileNotFoundError("The Steam depot or Geometry Dash installation folder is missing.")
    items = sorted(os.listdir(source_root))
    if not items or any(
        item in ("", ".", "..") or "/" in item or "\\" in item or os.path.basename(item) != item
        for item in items
    ):
        raise ValueError("The downloaded game depot has no safe top-level files to install.")

    required_bytes = sum(_tree_size(os.path.join(source_root, item)) for item in items) + reserve_bytes
    available_bytes = shutil.disk_usage(destination_root).free
    if available_bytes < required_bytes:
        raise OSError(
            f"Not enough free space to safely stage this game update. "
            f"Need about {required_bytes // (1024 * 1024)} MB; "
            f"{available_bytes // (1024 * 1024)} MB is available."
        )

    stage_root = tempfile.mkdtemp(prefix=".geodesync-transaction-", dir=destination_root)
    incoming = os.path.join(stage_root, "incoming")
    previous = os.path.join(stage_root, "previous")
    os.makedirs(incoming)
    os.makedirs(previous)
    try:
        for item in items:
            _copy_entry(os.path.join(source_root, item), os.path.join(incoming, item))
        if validator:
            problem = validator(incoming)
            if problem:
                raise OSError(f"The downloaded game files failed validation: {problem}")
        journal = {
            "destination": destination_root,
            "state": "installing",
            "items": items,
            "original_items": [item for item in items if os.path.lexists(os.path.join(destination_root, item))],
        }
        atomic_write_json(os.path.join(stage_root, "journal.json"), journal)
        try:
            for item in items:
                destination = os.path.join(destination_root, item)
                old_path = os.path.join(previous, item)
                new_path = os.path.join(incoming, item)
                if os.path.lexists(destination):
                    _safe_replace(destination, old_path)
                _safe_replace(new_path, destination)
            if installed_validator:
                problem = installed_validator(destination_root)
                if problem:
                    raise OSError(f"The installed game failed validation: {problem}")
        except Exception:
            _rollback_install_transaction(stage_root, destination_root, journal)
            raise
    except Exception:
        # Before the journal is written, nothing in the installed game was touched.
        if os.path.exists(os.path.join(stage_root, "journal.json")):
            try:
                _rollback_install_transaction(stage_root, destination_root, journal)
            except Exception:
                # Preserve the journal and old files for recovery at next launch.
                raise
            else:
                shutil.rmtree(stage_root, ignore_errors=True)
        else:
            shutil.rmtree(stage_root, ignore_errors=True)
        raise
    journal["state"] = "committed"
    atomic_write_json(os.path.join(stage_root, "journal.json"), journal)
    shutil.rmtree(stage_root, ignore_errors=True)
