import os
import json
import hashlib
import shutil
from datetime import datetime

def hash_file(path):
    """Generate a hash for a file."""
    hasher = hashlib.sha1()
    with open(path, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

class DVC:
    def __init__(self, repo_path):
        self.repo_path = os.path.abspath(repo_path)
        self.dvc_dir = os.path.join(self.repo_path, '.dvc')
        self.objects_dir = os.path.join(self.dvc_dir, 'objects')
        self.meta_file = os.path.join(self.dvc_dir, 'metadata.json')
        self.ignore_file = os.path.join(self.dvc_dir, '.dvcignore')

    def init(self):
        """Initialize a repository."""
        ensure_dir(self.dvc_dir)
        ensure_dir(self.objects_dir)
        if not os.path.exists(self.meta_file):
            metadata = {
                "branches": {"main": []},
                "current_branch": "main",
                "head": None
            }
            with open(self.meta_file, 'w') as f:
                json.dump(metadata, f)
        print("Repository initialized.")

    def load_metadata(self):
        with open(self.meta_file, 'r') as f:
            return json.load(f)

    def save_metadata(self, metadata):
        with open(self.meta_file, 'w') as f:
            json.dump(metadata, f, indent=4)

    def get_ignored_files(self):
        if os.path.exists(self.ignore_file):
            with open(self.ignore_file, 'r') as f:
                return set(line.strip() for line in f if line.strip())
        return set()

    def add(self, file_path):
        """Stage a file."""
        metadata = self.load_metadata()
        staged_files = metadata.get("staging", {})

        abs_path = os.path.abspath(file_path)
        if not abs_path.startswith(self.repo_path):
            raise ValueError("File must be within the repository.")

        rel_path = os.path.relpath(abs_path, self.repo_path)
        ignored = self.get_ignored_files()
        if rel_path in ignored:
            print(f"File '{rel_path}' is ignored.")
            return

        file_hash = hash_file(abs_path)
        staged_files[rel_path] = file_hash
        metadata["staging"] = staged_files

        # Ensure the directory exists for the file hash
        ensure_dir(os.path.join(self.objects_dir, file_hash))
        shutil.copy2(abs_path, os.path.join(self.objects_dir, file_hash))

        self.save_metadata(metadata)
        print(f"File '{file_path}' staged.")

    def commit(self, message):
        """Commit staged files."""
        metadata = self.load_metadata()
        branch = metadata["current_branch"]
        head = metadata["head"]
        staged_files = metadata.pop("staging", {})

        if not staged_files:
            print("No changes to commit.")
            return

        commit_id = hashlib.sha1((message + datetime.now().isoformat()).encode()).hexdigest()
        commit = {
            "id": commit_id,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "files": staged_files,
            "parent": head
        }

        metadata["branches"][branch].append(commit)
        metadata["head"] = commit_id

        self.save_metadata(metadata)
        print(f"Commit '{commit_id}' created.")

    def log(self):
        """Show commit history."""
        metadata = self.load_metadata()
        branch = metadata["current_branch"]
        commits = metadata["branches"].get(branch, [])

        for commit in reversed(commits):
            parent_id = commit.get("parent", "None")
            print(f"Commit: {commit['id']}\nMessage: {commit['message']}\nTime: {commit['timestamp']}\nParent: {parent_id}\n")

    def branch(self, branch_name):
        """Create a new branch."""
        metadata = self.load_metadata()
        if branch_name in metadata["branches"]:
            print("Branch already exists.")
            return

        current_branch = metadata["current_branch"]
        metadata["branches"][branch_name] = list(metadata["branches"][current_branch])
        self.save_metadata(metadata)
        print(f"Branch '{branch_name}' created.")

    def checkout(self, branch_name):
        """Switch to a branch."""
        metadata = self.load_metadata()
        if branch_name not in metadata["branches"]:
            print("Branch does not exist.")
            return

        metadata["current_branch"] = branch_name
        metadata["head"] = metadata["branches"][branch_name][-1]["id"] if metadata["branches"][branch_name] else None
        self.save_metadata(metadata)
        print(f"Switched to branch '{branch_name}'.")

    def diff(self, commit1_id, commit2_id):
        """Show differences between two commits."""
        metadata = self.load_metadata()
        branch = metadata["current_branch"]
        commits = {c["id"]: c for c in metadata["branches"].get(branch, [])}

        if commit1_id not in commits or commit2_id not in commits:
            print("One or both commits not found.")
            return "Error: Commit(s) not found."

        files1 = commits[commit1_id]["files"]
        files2 = commits[commit2_id]["files"]

        added = set(files2) - set(files1)
        removed = set(files1) - set(files2)
        modified = {f for f in (set(files1) & set(files2)) if files1[f] != files2[f]}

        diff_output = (
            f"Added: {', '.join(added) or 'None'}\n"
            f"Removed: {', '.join(removed) or 'None'}\n"
            f"Modified: {', '.join(modified) or 'None'}"
        )

        print(diff_output)
        return diff_output

    def merge(self, target_branch):
        """Merge another branch into the current branch."""
        metadata = self.load_metadata()
        current_branch = metadata["current_branch"]

        if target_branch not in metadata["branches"]:
            print(f"Branch '{target_branch}' does not exist.")
            return []

        current_commits = metadata["branches"].get(current_branch, [])
        target_commits = metadata["branches"].get(target_branch, [])

        current_files = {k: v for commit in current_commits for k, v in commit["files"].items()}
        target_files = {k: v for commit in target_commits for k, v in commit["files"].items()}

        # Detect conflicts by checking for same file paths with different hashes
        conflicts = [
            f for f in current_files if f in target_files and current_files[f] != target_files[f]
        ]

        if conflicts:
            print("Merge conflicts detected:")
            for conflict in conflicts:
                print(f"Conflict in file: {conflict}")
            return conflicts  # Return the list of conflicts

        # No conflicts, proceed with merging
        merged_files = {**current_files, **target_files}
        merge_commit = {
            "id": f"merge-{datetime.now().isoformat()}",
            "message": f"Merge branch '{target_branch}' into '{current_branch}'",
            "timestamp": datetime.now().isoformat(),
            "files": merged_files,
            "parent": metadata["head"]
        }

        metadata["branches"][current_branch].append(merge_commit)
        metadata["head"] = merge_commit["id"]

        self.save_metadata(metadata)
        print(f"Branch '{target_branch}' successfully merged into '{current_branch}'.")
        return None  # Indicate no conflicts occurred

    def clone(self, target_path):
        """Clone the repository."""
        if os.path.exists(target_path):
            print("Target path already exists.")
            return

        # Clone only the .dvc directory and reconstruct the working directory
        shutil.copytree(self.dvc_dir, target_path)
        print(f"Repository cloned to '{target_path}'.")
