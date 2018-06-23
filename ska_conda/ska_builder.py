import os
import subprocess
import git
import yaml

ska_conda_path = os.path.abspath(os.path.dirname(__file__))
pkg_defs_path = os.path.join(ska_conda_path, "pkg_defs")
build_list = os.path.join(ska_conda_path, "build_order.txt")

class SkaBuilder(object):

    def __init__(self, ska_root=None):
        if ska_root is None:
            ska_root = "/tmp/ska3_pkg/"
        self.ska_root = ska_root
        self.ska_build_dir = os.path.join(self.ska_root, "builds")
        self.ska_src_dir = os.path.join(self.ska_root, "src")
        os.environ["SKA_TOP_SRC_DIR"] = self.ska_src_dir

    def _clone_repo(self, name):
        if name == "ska":
            return
        print("Cloning source %s." % name)
        clone_path = os.path.join(self.ska_src_dir, name)
        if os.path.exists(clone_path):
            print("Source %s exists, skipping." % name)
            return
        yml = os.path.join(pkg_defs_path, name, "meta.yaml")
        with open(yml) as f:
            requires = False
            while not requires:
                line = f.readline().strip()
                if line.startswith("path:"):
                    requires = True
            data = yaml.load(f)
            url = data['about']['home']
            git.Repo.clone_from(url, clone_path)

    def clone_one_package(self, name):
        self._clone_repo(name)

    def clone_all_packages(self):
        with open(build_list, "r") as f:
            for line in f.readlines():
                pkg_name = line.strip()
                if not pkg_name.startswith("#"):
                    self._clone_repo(pkg_name)

    def _get_repo(self, name):
        if name == "ska":
            return None
        repo_path = os.path.join(self.ska_src_dir, name)
        if not os.path.exists(repo_path):
            self._clone_repo(name)
        repo = git.Repo(repo_path)
        return repo

    def _build_package(self, name):
        print("Building package %s." % name)
        pkg_path = os.path.join(pkg_defs_path, name)
        cmd_list = ["conda", "build", pkg_path, "--croot",
                    self.ska_build_dir, "--no-test",
                    "--no-anaconda-upload"]
        subprocess.run(cmd_list)

    def build_one_package(self, name):
        repo = self._get_repo(name)
        if repo is not None:
            repo.remote().pull()
        self._build_package(name)

    def build_updated_packages(self, new_only=True):
        with open(build_list, "r") as f:
            for line in f.readlines():
                pkg_name = line.strip()
                if not pkg_name.startswith("#"):
                    repo = self._get_repo(pkg_name)
                    if repo is None:
                        build = True
                    else:
                        current_tag = repo.tags[-1].name
                        repo.remote().pull()
                        build = repo.tags[-1].name != current_tag
                    if build or not new_only:
                        self._build_package(pkg_name)

    def build_all_packages(self):
        self.build_updated_packages(new_only=False)
