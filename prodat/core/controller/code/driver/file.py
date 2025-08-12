import os
import shutil
import errno
import tempfile
import hashlib
import pathspec
import checksumdir

from prodat.core.util.misc_functions import list_all_filepaths
from prodat.core.util.i18n import get as __
from prodat.core.util.exceptions import (
    PathDoesNotExist,
    FileIOError,
    UnstagedChanges,
    CodeNotInitialized,
    CommitDoesNotExist,
)
from prodat.core.controller.code.driver import CodeDriver


class FileCodeDriver(CodeDriver):
    """File-based Code Driver handles source-control-like snapshots for a project.

    Notes:
    - Tracked files are discovered relative to self.root (via list_all_filepaths).
    - Commits are recorded as small files inside self._code_filepath (one file per commit id).
      File contents are lines "relative/path/to/file, <filehash>".
    - Actual file contents are stored under self._code_filepath/<relative/path>/<filehash>
      so multiple versions of same file can co-exist.
    """

    def __init__(self, root, prodat_directory_name):
        super(FileCodeDriver, self).__init__()
        self.root = root
        if not os.path.exists(self.root):
            raise PathDoesNotExist(
                __("error", "controller.code.driver.git.__init__.dne", root)
            )

        self._prodat_directory_name = prodat_directory_name
        self._prodat_directory_path = os.path.join(self.root, self._prodat_directory_name)
        # "code" folder inside the prodat directory used to store commits and file blobs
        self._code_filepath = os.path.join(self._prodat_directory_path, "code")
        self._prodat_ignore_filepath = os.path.join(self.root, ".prodatignore")
        # type marker
        self.type = "file"

    @property
    def is_initialized(self):
        """Whether the prodat/code layout exists on disk."""
        is_init = os.path.isdir(self._prodat_directory_path) and os.path.isdir(self._code_filepath)
        return is_init

    def init(self):
        """Initialize the code store (create prodat/code directories)."""
        # Ensure prodat directory exists
        if not os.path.isdir(self._prodat_directory_path):
            os.makedirs(self._prodat_directory_path, exist_ok=True)
        # Create code path if does not exist
        if not os.path.isdir(self._code_filepath):
            os.makedirs(self._code_filepath, exist_ok=True)
        return True

    def _get_tracked_files(self):
        """Return list of tracked files relative to the root directory.

        Excludes:
         - the prodat directory itself
         - .git directory
         - paths matched by .prodatignore (if present)
        """
        all_files = set(list_all_filepaths(self.root))

        # Build patterns for directories that must be ignored (relative names)
        prodat_pattern = self._prodat_directory_name
        git_pattern = ".git"

        # Use gitwildmatch for directory patterns
        spec = pathspec.PathSpec.from_lines("gitwildmatch", [prodat_pattern])
        dot_prodat_files = set(spec.match_tree(self.root))

        spec = pathspec.PathSpec.from_lines("gitwildmatch", [git_pattern])
        dot_git_files = set(spec.match_tree(self.root))

        # Load .prodatignore if present (gitignore style)
        prodatignore_files = set()
        if os.path.isfile(self._prodat_ignore_filepath):
            with open(self._prodat_ignore_filepath, "r") as f:
                spec = pathspec.PathSpec.from_lines("gitignore", f)
                prodatignore_files.update(spec.match_tree(self.root))

        ignored = dot_prodat_files.union(dot_git_files).union(prodatignore_files)

        tracked = sorted(list(all_files - ignored))
        return tracked

    def _calculate_commit_hash(self, tracked_files):
        """Create a temporary snapshot of tracked files and return a directory-hash.

        Uses checksumdir.dirhash on a temporary directory created inside self._code_filepath.
        """
        temp_dir = None
        try:
            temp_dir = tempfile.mkdtemp(dir=self._code_filepath)
            for rel_filepath in tracked_files:
                filename = os.path.basename(rel_filepath)
                rel_dirpath = rel_filepath[: -len(filename)] if filename else rel_filepath
                new_dirpath = os.path.join(temp_dir, rel_dirpath)
                # Ensure directory exists
                os.makedirs(new_dirpath, exist_ok=True)

                old_filepath = os.path.join(self.root, rel_filepath)
                new_filepath = os.path.join(new_dirpath, filename)
                # Only copy if source exists; missing file is an error in tracked list
                if not os.path.isfile(old_filepath):
                    raise PathDoesNotExist(
                        __("error", "controller.code.driver.file._calculate_commit_hash", old_filepath)
                    )
                shutil.copy2(old_filepath, new_filepath)
            # Return directory hash (checksumdir.dirhash default behavior)
            return self._get_dirhash(temp_dir)
        finally:
            # Clean up temporary directory if it was created
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except OSError as exc:
                    # If directory already gone, ignore; else raise
                    if exc.errno != errno.ENOENT:
                        raise

    @staticmethod
    def _get_filehash(absolute_filepath):
        """Return an md5 hex digest of a file's bytes."""
        if not os.path.isfile(absolute_filepath):
            raise PathDoesNotExist(
                __("error", "util.misc_functions.get_filehash", absolute_filepath)
            )
        BUFF_SIZE = 65536
        md5 = hashlib.md5()
        with open(absolute_filepath, "rb") as f:
            while True:
                data = f.read(BUFF_SIZE)
                if not data:
                    break
                md5.update(data)
        return md5.hexdigest()

    @staticmethod
    def _get_dirhash(absolute_dirpath):
        """Return a hash for the contents of a directory using checksumdir.dirhash."""
        # checksumdir.dirhash may raise exceptions if dir doesn't exist; let it bubble up
        return checksumdir.dirhash(absolute_dirpath)

    def _has_unstaged_changes(self):
        """Return whether there are unstaged changes.

        Special-case: if there are zero tracked files and there are no commits,
        consider that 'unstaged' to force an initial commit.
        """
        tracked_filepaths = self._get_tracked_files()

        # If no tracked files: if there are no commits, treat as unstaged (require initial commit).
        commits = self.list_refs() or []
        if not tracked_filepaths:
            return len(commits) == 0

        commit_hash = self._calculate_commit_hash(tracked_filepaths)
        return not self.exists_ref(commit_hash)

    def current_hash(self):
        """Return the current working tree hash; this will raise if there are unstaged changes."""
        self.check_unstaged_changes()
        tracked_filepaths = self._get_tracked_files()
        return self._calculate_commit_hash(tracked_filepaths)

    def create_ref(self, commit_id=None):
        """Create a commit snapshot or validate an existing commit id.

        If commit_id is provided, it must already exist.
        Otherwise, create a commit record and copy blobs into the code folder.

        Returns commit_id string.
        """
        if not self.is_initialized:
            raise CodeNotInitialized()

        # If commit given, validate existence and return
        if commit_id:
            if not self.exists_ref(commit_id):
                raise CommitDoesNotExist(
                    __("error", "controller.code.driver.file.create_ref.no_commit", commit_id)
                )
            return commit_id

        # Build list of tracked files and commit hash
        tracked_filepaths = self._get_tracked_files()
        commit_hash = self._calculate_commit_hash(tracked_filepaths)

        # If commit already exists, return
        if self.exists_ref(commit_hash):
            return commit_hash

        # Ensure code path exists
        os.makedirs(self._code_filepath, exist_ok=True)

        # Create commit record file (one line per tracked file: "relpath,filehash")
        commit_filepath = os.path.join(self._code_filepath, commit_hash)
        try:
            with open(commit_filepath, "a+", encoding="utf-8") as f:
                for tracked_filepath in tracked_filepaths:
                    absolute_filepath = os.path.join(self.root, tracked_filepath)
                    if not os.path.isfile(absolute_filepath):
                        raise FileIOError(
                            __("error", "controller.code.driver.file.create_ref.missing_file", absolute_filepath)
                        )

                    # Directory under code where file-version blobs are stored:
                    # code/<relative/path/to/file>/  and inside it filehash
                    blob_dir = os.path.join(self._code_filepath, tracked_filepath)
                    os.makedirs(blob_dir, exist_ok=True)

                    # compute file hash and copy content into blob store
                    filehash = self._get_filehash(absolute_filepath)
                    new_blob_path = os.path.join(blob_dir, filehash)
                    # Copy only if not already present
                    if not os.path.isfile(new_blob_path):
                        shutil.copy2(absolute_filepath, new_blob_path)

                    # Append record to commit file
                    f.write(f"{tracked_filepath},{filehash}\n")
        except OSError as exc:
            raise FileIOError(
                __("error", "controller.code.driver.file.create_ref.io_error", str(exc))
            )

        return commit_hash

    def current_ref(self):
        """Return the hash that corresponds to the current working tree (does not require staging)."""
        if not self.is_initialized:
            raise CodeNotInitialized()
        tracked_filepaths = self._get_tracked_files()
        return self._calculate_commit_hash(tracked_filepaths)

    def latest_ref(self):
        """Return the most-recent commit filename (or None if no commits exist)."""
        if not self.is_initialized:
            raise CodeNotInitialized()

        commit_hashes = self.list_refs() or []
        if not commit_hashes:
            return None

        # Build full paths for files and sort by mtime
        full_paths = []
        for h in commit_hashes:
            p = os.path.join(self._code_filepath, h)
            if os.path.isfile(p):
                full_paths.append(p)

        if not full_paths:
            return None

        full_paths.sort(key=os.path.getmtime, reverse=True)
        # Return filename (commit id)
        return os.path.basename(full_paths[0])

    def exists_ref(self, commit_id):
        """Return True if commit exists."""
        if not self.is_initialized:
            raise CodeNotInitialized()
        commit_hashes = self.list_refs() or []
        return commit_id in commit_hashes

    def delete_ref(self, commit_id):
        """Remove the commit file (does not remove blobs)."""
        if not self.is_initialized:
            raise CodeNotInitialized()
        if not self.exists_ref(commit_id):
            raise FileIOError(
                __("error", "controller.code.driver.file.delete_ref")
            )
        commit_filepath = os.path.join(self._code_filepath, commit_id)
        try:
            os.remove(commit_filepath)
        except OSError as exc:
            raise FileIOError(
                __("error", "controller.code.driver.file.delete_ref.io", str(exc))
            )
        return True

    def list_refs(self):
        """List all commit files (filenames) contained directly in the code directory."""
        if not self.is_initialized:
            raise CodeNotInitialized()
        if not os.path.isdir(self._code_filepath):
            return []

        entries = []
        try:
            for name in os.listdir(self._code_filepath):
                full = os.path.join(self._code_filepath, name)
                if os.path.isfile(full):
                    entries.append(name)
        except OSError as exc:
            raise FileIOError(
                __("error", "controller.code.driver.file.list_refs.io", str(exc))
            )
        return entries

    def check_unstaged_changes(self):
        """Raise UnstagedChanges if there are unstaged changes; otherwise return False."""
        if not self.is_initialized:
            raise CodeNotInitialized()

        if self._has_unstaged_changes():
            raise UnstagedChanges()

        return False

    def checkout_ref(self, commit_id):
        """Checkout a specific commit by restoring files recorded in that commit.

        This removes existing tracked files (best-effort; missing files are ignored) and
        replaces them with blobs recorded for commit_id.
        """
        if not self.is_initialized:
            raise CodeNotInitialized()

        if not self.exists_ref(commit_id):
            raise FileIOError(
                __("error", "controller.code.driver.file.checkout_ref")
            )

        # Prevent checkout when there are unstaged changes
        if self._has_unstaged_changes():
            raise UnstagedChanges()

        # If already at that commit, nothing to do
        tracked_filepaths = self._get_tracked_files()
        if self._calculate_commit_hash(tracked_filepaths) == commit_id:
            return True

        # Remove all currently tracked files (ignore missing)
        for tracked_filepath in tracked_filepaths:
            absolute_filepath = os.path.join(self.root, tracked_filepath)
            try:
                if os.path.isfile(absolute_filepath):
                    os.remove(absolute_filepath)
            except OSError:
                # best-effort removal; continue
                pass

        # Read commit record and restore files from blob store
        commit_filepath = os.path.join(self._code_filepath, commit_id)
        if not os.path.isfile(commit_filepath):
            raise FileIOError(
                __("error", "controller.code.driver.file.checkout_ref.missing_commit", commit_filepath)
            )

        with open(commit_filepath, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.rstrip()
                if not stripped:
                    continue
                try:
                    tracked_filepath, filehash = stripped.split(",", 1)
                except ValueError:
                    # malformed line in commit file
                    raise FileIOError(
                        __("error", "controller.code.driver.file.checkout_ref.bad_entry", stripped)
                    )

                source_absolute_filepath = os.path.join(self._code_filepath, tracked_filepath, filehash)
                if not os.path.isfile(source_absolute_filepath):
                    raise FileIOError(
                        __("error", "controller.code.driver.file.checkout_ref.missing_blob", source_absolute_filepath)
                    )

                destination_absolute_filepath = os.path.join(self.root, tracked_filepath)
                dest_dir = os.path.dirname(destination_absolute_filepath)
                if dest_dir:
                    os.makedirs(dest_dir, exist_ok=True)

                shutil.copy2(source_absolute_filepath, destination_absolute_filepath)

        return True
