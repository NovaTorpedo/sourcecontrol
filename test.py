import os
import unittest
import shutil
from sourcecontrol import DVC  # Assuming this is the module implementing the system.

class TestDVC(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.repo_dir = 'test_repo'
        cls.file_path = os.path.join(cls.repo_dir, 'test_file.txt')
        cls.ignore_file = os.path.join(cls.repo_dir, '.dvcignore')

    def setUp(self):
        if os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)
        os.mkdir(self.repo_dir)
        self.dvc = DVC(self.repo_dir)
        self.dvc.init()

    def tearDown(self):
        if os.path.exists(self.repo_dir):
            shutil.rmtree(self.repo_dir)

    def test_initialize_repository(self):
        """Test if repository initializes correctly with a dot-prefixed subdirectory."""
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, '.dvc')))
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, '.dvc', 'objects')))
        self.assertTrue(os.path.exists(os.path.join(self.repo_dir, '.dvc', 'metadata.json')))

    def test_staging_and_committing_files(self):
        """Test if files can be staged and committed."""
        with open(self.file_path, 'w') as f:
            f.write('Hello DVC!')

        self.dvc.add(self.file_path)
        self.dvc.commit('Initial commit')

        metadata = self.dvc.load_metadata()
        branch = metadata["branches"]["main"]
        self.assertTrue(any('test_file.txt' in commit['files'] for commit in branch))

    def test_view_commit_history(self):
        """Test if commit history can be viewed."""
        with open(self.file_path, 'w') as f:
            f.write('Hello DVC!')

        self.dvc.add(self.file_path)
        self.dvc.commit('Initial commit')

        with open(self.file_path, 'w') as f:
            f.write('Updated DVC!')

        self.dvc.add(self.file_path)
        self.dvc.commit('Second commit')

        metadata = self.dvc.load_metadata()
        branch = metadata["branches"]["main"]
        self.assertEqual(len(branch), 2)

    def test_branch_creation(self):
        """Test if branches can be created."""
        self.dvc.branch('new-branch')
        metadata = self.dvc.load_metadata()
        self.assertIn('new-branch', metadata['branches'])

    def test_branch_merge(self):
        """Test if branches can be merged and conflicts detected."""
        self.dvc.branch('new-branch')
        self.dvc.checkout('new-branch')

        with open(self.file_path, 'w') as f:
            f.write('Hello from branch!')

        self.dvc.add(self.file_path)
        self.dvc.commit('Branch commit')

        self.dvc.checkout('main')
        with open(self.file_path, 'w') as f:
            f.write('Hello from main!')

        self.dvc.add(self.file_path)
        self.dvc.commit('Main commit')

        conflicts = self.dvc.merge('new-branch')
        metadata = self.dvc.load_metadata()
        
        if conflicts:
            self.assertIn(self.file_path, conflicts)
        else:
            branch = metadata['branches']['main']
            self.assertTrue(any('merge-' in commit['id'] for commit in branch))

    def test_diff_between_commits(self):
        """Test if diffs between commits can be viewed."""
        with open(self.file_path, 'w') as f:
            f.write('Version 1')

        self.dvc.add(self.file_path)
        commit1 = self.dvc.commit('Commit 1')

        with open(self.file_path, 'w') as f:
            f.write('Version 2')

        self.dvc.add(self.file_path)
        commit2 = self.dvc.commit('Commit 2')

        diff = self.dvc.diff('main', 'main')  # Assuming diff is within the same branch for simplicity
        self.assertIn('Version 1', diff)
        self.assertIn('Version 2', diff)

    def test_ignore_files(self):
        """Test if ignored files are not tracked."""
        with open(self.ignore_file, 'w') as f:
            f.write('ignored_file.txt\n')

        ignored_file_path = os.path.join(self.repo_dir, 'ignored_file.txt')
        with open(ignored_file_path, 'w') as f:
            f.write('This should be ignored')

        self.dvc.add(ignored_file_path)
        metadata = self.dvc.load_metadata()
        self.assertNotIn('ignored_file.txt', metadata.get('staging', {}))

    def test_cloning_repository(self):
        """Test if repository can be cloned."""
        clone_dir = 'cloned_repo'
        self.dvc.clone(clone_dir)

        self.assertTrue(os.path.exists(os.path.join(clone_dir, '.dvc')))
        shutil.rmtree(clone_dir)

if __name__ == '__main__':
    unittest.main()
