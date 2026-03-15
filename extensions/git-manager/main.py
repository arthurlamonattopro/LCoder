import os
import re
import subprocess
from dataclasses import dataclass

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


@dataclass
class GitStatusEntry:
    path: str
    status: str
    staged: bool
    unstaged: bool
    untracked: bool


class GitManagerDialog(QDialog):
    def __init__(self, context):
        super().__init__()
        self.context = context
        self.repo_root = self._detect_repo_root()
        self.setWindowTitle("Git Manager")
        self.resize(980, 640)

        self.status_label = QLabel()
        self.changes_list = QListWidget()
        self.diff_box = QTextEdit()
        self.diff_box.setReadOnly(True)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.commit_entry = QLineEdit()
        self.branch_combo = QComboBox()
        self.remote_label = QLabel("Remote: (not detected)")

        self._build_ui()
        self._wire_events()
        self.refresh_all()

    def _build_ui(self):
        root = QVBoxLayout(self)

        root.addWidget(self.status_label)

        split = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Changes"))
        left_layout.addWidget(self.changes_list)

        left_buttons = QHBoxLayout()
        self.btn_refresh = QPushButton("Refresh")
        self.btn_stage = QPushButton("Stage Selected")
        self.btn_unstage = QPushButton("Unstage Selected")
        self.btn_discard = QPushButton("Discard Selected")
        left_buttons.addWidget(self.btn_refresh)
        left_buttons.addWidget(self.btn_stage)
        left_buttons.addWidget(self.btn_unstage)
        left_buttons.addWidget(self.btn_discard)
        left_layout.addLayout(left_buttons)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Diff / Output"))
        right_layout.addWidget(self.diff_box)
        right_layout.addWidget(QLabel("Git Output"))
        right_layout.addWidget(self.log_box)

        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 2)
        root.addWidget(split)

        commit_form = QFormLayout()
        commit_form.addRow("Commit message:", self.commit_entry)
        root.addLayout(commit_form)

        commit_row = QHBoxLayout()
        self.btn_commit = QPushButton("Commit")
        self.btn_push = QPushButton("Push")
        self.btn_pull = QPushButton("Pull")
        self.btn_fetch = QPushButton("Fetch")
        commit_row.addWidget(self.btn_commit)
        commit_row.addWidget(self.btn_push)
        commit_row.addWidget(self.btn_pull)
        commit_row.addWidget(self.btn_fetch)
        root.addLayout(commit_row)

        branch_row = QHBoxLayout()
        branch_row.addWidget(QLabel("Branch:"))
        branch_row.addWidget(self.branch_combo)
        self.btn_checkout = QPushButton("Checkout")
        self.btn_new_branch = QPushButton("New Branch")
        branch_row.addWidget(self.btn_checkout)
        branch_row.addWidget(self.btn_new_branch)
        root.addLayout(branch_row)

        remote_row = QHBoxLayout()
        remote_row.addWidget(self.remote_label)
        self.btn_open_repo = QPushButton("Open Repo")
        self.btn_open_issues = QPushButton("Open Issues")
        self.btn_open_prs = QPushButton("Open PR/MR")
        remote_row.addWidget(self.btn_open_repo)
        remote_row.addWidget(self.btn_open_issues)
        remote_row.addWidget(self.btn_open_prs)
        root.addLayout(remote_row)

    def _wire_events(self):
        self.btn_refresh.clicked.connect(self.refresh_all)
        self.btn_stage.clicked.connect(self.stage_selected)
        self.btn_unstage.clicked.connect(self.unstage_selected)
        self.btn_discard.clicked.connect(self.discard_selected)
        self.btn_commit.clicked.connect(self.commit_changes)
        self.btn_push.clicked.connect(lambda: self.run_git_action(["push"]))
        self.btn_pull.clicked.connect(lambda: self.run_git_action(["pull"]))
        self.btn_fetch.clicked.connect(lambda: self.run_git_action(["fetch"]))
        self.btn_checkout.clicked.connect(self.checkout_branch)
        self.btn_new_branch.clicked.connect(self.create_branch)
        self.btn_open_repo.clicked.connect(lambda: self.open_remote_url("repo"))
        self.btn_open_issues.clicked.connect(lambda: self.open_remote_url("issues"))
        self.btn_open_prs.clicked.connect(lambda: self.open_remote_url("prs"))
        self.changes_list.itemSelectionChanged.connect(self.show_selected_diff)

    def _detect_repo_root(self):
        root = None
        if self.context and self.context.workspace:
            root = self.context.workspace.root_path()
        if not root or not os.path.isdir(root):
            return None
        code, out, _ = self._run_git(["rev-parse", "--show-toplevel"], cwd=root)
        if code != 0:
            return None
        return out.strip()

    def _run_git(self, args, cwd=None):
        if cwd is None:
            cwd = self.repo_root
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            return completed.returncode, completed.stdout.strip(), completed.stderr.strip()
        except Exception as exc:
            return 1, "", str(exc)

    def _append_log(self, title, stdout, stderr):
        chunks = []
        if title:
            chunks.append(f"$ git {title}")
        if stdout:
            chunks.append(stdout)
        if stderr:
            chunks.append(stderr)
        if not chunks:
            return
        self.log_box.append("\n".join(chunks))

    def refresh_all(self):
        if not self.repo_root:
            QMessageBox.warning(self, "Git Manager", "No Git repository detected in the current workspace.")
            return
        self.refresh_status()
        self.refresh_branches()
        self.refresh_remote()

    def refresh_status(self):
        code, out, err = self._run_git(["status", "--porcelain=1", "-b"])
        if code != 0:
            self.status_label.setText("Status: error")
            self._append_log("status --porcelain=1 -b", out, err)
            return

        lines = [line for line in out.splitlines() if line.strip()]
        header = lines[0] if lines else "## (unknown)"
        self.status_label.setText(self._format_branch_status(header))

        self.changes_list.clear()
        for line in lines[1:]:
            entry = self._parse_status_line(line)
            if not entry:
                continue
            item = QListWidgetItem(f"{entry.status}  {entry.path}")
            item.setData(Qt.UserRole, entry)
            item.setCheckState(Qt.Unchecked)
            self.changes_list.addItem(item)

    def _format_branch_status(self, header):
        if not header.startswith("## "):
            return "Branch: (unknown)"
        text = header[3:]
        return f"Branch: {text}"

    def _parse_status_line(self, line):
        if len(line) < 3:
            return None
        status = line[:2]
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ")[-1]
        staged = status[0] != " " and status[0] != "?"
        unstaged = status[1] != " "
        untracked = status == "??"
        return GitStatusEntry(
            path=path.strip(),
            status=status,
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
        )

    def show_selected_diff(self):
        items = self.changes_list.selectedItems()
        if not items:
            self.diff_box.clear()
            return
        entry = items[0].data(Qt.UserRole)
        if not isinstance(entry, GitStatusEntry):
            self.diff_box.clear()
            return
        args = ["diff"]
        if entry.staged and not entry.unstaged:
            args = ["diff", "--cached"]
        elif entry.staged and entry.unstaged:
            args = ["diff"]
        args.append("--")
        args.append(entry.path)
        code, out, err = self._run_git(args)
        if code != 0 and err:
            self.diff_box.setPlainText(err)
        else:
            self.diff_box.setPlainText(out or "(no diff)")

    def _collect_checked_paths(self):
        paths = []
        for idx in range(self.changes_list.count()):
            item = self.changes_list.item(idx)
            if item.checkState() == Qt.Checked:
                entry = item.data(Qt.UserRole)
                if isinstance(entry, GitStatusEntry):
                    paths.append(entry.path)
        return paths

    def stage_selected(self):
        paths = self._collect_checked_paths()
        if not paths:
            QMessageBox.information(self, "Git Manager", "Select items to stage.")
            return
        code, out, err = self._run_git(["add", "--", *paths])
        self._append_log("add -- ...", out, err)
        self.refresh_status()

    def unstage_selected(self):
        paths = self._collect_checked_paths()
        if not paths:
            QMessageBox.information(self, "Git Manager", "Select items to unstage.")
            return
        code, out, err = self._run_git(["restore", "--staged", "--", *paths])
        self._append_log("restore --staged -- ...", out, err)
        self.refresh_status()

    def discard_selected(self):
        paths = self._collect_checked_paths()
        if not paths:
            QMessageBox.information(self, "Git Manager", "Select items to discard.")
            return
        confirm = QMessageBox.question(
            self,
            "Discard changes",
            "This will discard local changes for the selected files. Continue?",
        )
        if confirm != QMessageBox.Yes:
            return
        for path in paths:
            entry = self._find_entry_by_path(path)
            if entry and entry.untracked:
                code, out, err = self._run_git(["clean", "-f", "--", path])
                self._append_log("clean -f -- ...", out, err)
            else:
                code, out, err = self._run_git(["restore", "--", path])
                self._append_log("restore -- ...", out, err)
        self.refresh_status()

    def _find_entry_by_path(self, path):
        for idx in range(self.changes_list.count()):
            item = self.changes_list.item(idx)
            entry = item.data(Qt.UserRole)
            if isinstance(entry, GitStatusEntry) and entry.path == path:
                return entry
        return None

    def commit_changes(self):
        message = self.commit_entry.text().strip()
        if not message:
            QMessageBox.warning(self, "Git Manager", "Commit message is required.")
            return
        code, out, err = self._run_git(["commit", "-m", message])
        self._append_log("commit -m ...", out, err)
        if code == 0:
            self.commit_entry.clear()
        else:
            QMessageBox.warning(self, "Git Manager", "Commit failed. Check the output for details.")
        self.refresh_status()

    def run_git_action(self, args):
        code, out, err = self._run_git(args)
        self._append_log(" ".join(args), out, err)
        if code != 0:
            QMessageBox.warning(self, "Git Manager", "Git command failed. Check the output for details.")
        self.refresh_status()

    def refresh_branches(self):
        code, out, err = self._run_git(["branch", "--all", "--format=%(refname:short)"])
        if code != 0:
            self._append_log("branch --all --format=%(refname:short)", out, err)
            return
        branches = [line.strip() for line in out.splitlines() if line.strip()]
        self.branch_combo.clear()
        self.branch_combo.addItems(branches)

    def checkout_branch(self):
        branch = self.branch_combo.currentText().strip()
        if not branch:
            return
        if branch.startswith("remotes/"):
            branch = branch.replace("remotes/", "", 1)
        if branch.startswith("origin/"):
            code, out, err = self._run_git(["checkout", "-t", branch])
        else:
            code, out, err = self._run_git(["checkout", branch])
        self._append_log(f"checkout {branch}", out, err)
        if code != 0:
            QMessageBox.warning(self, "Git Manager", "Checkout failed. Check the output for details.")
        self.refresh_status()
        self.refresh_branches()

    def create_branch(self):
        name, ok = QInputDialog.getText(self, "New Branch", "Branch name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        code, out, err = self._run_git(["checkout", "-b", name])
        self._append_log(f"checkout -b {name}", out, err)
        if code != 0:
            QMessageBox.warning(self, "Git Manager", "Branch creation failed. Check the output for details.")
        self.refresh_status()
        self.refresh_branches()

    def refresh_remote(self):
        code, out, err = self._run_git(["remote", "get-url", "origin"])
        if code != 0:
            self.remote_label.setText("Remote: (not detected)")
            self._append_log("remote get-url origin", out, err)
            return
        self.remote_url = out.strip()
        self.remote_label.setText(f"Remote: {self.remote_url}")

    def open_remote_url(self, target):
        url = self._normalize_remote_url()
        if not url:
            QMessageBox.warning(self, "Git Manager", "Remote URL not detected.")
            return
        if target == "issues":
            url = f"{url}/issues"
        elif target == "prs":
            if "gitlab" in url:
                url = f"{url}/-/merge_requests"
            else:
                url = f"{url}/pulls"
        QDesktopServices.openUrl(QUrl(url))

    def _normalize_remote_url(self):
        if not hasattr(self, "remote_url"):
            return None
        raw = self.remote_url
        if not raw:
            return None
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw[:-4] if raw.endswith(".git") else raw
        ssh_match = re.match(r"git@([^:]+):(.+)", raw)
        if ssh_match:
            host, path = ssh_match.groups()
            path = path[:-4] if path.endswith(".git") else path
            return f"https://{host}/{path}"
        ssh_url_match = re.match(r"ssh://git@([^/]+)/(.+)", raw)
        if ssh_url_match:
            host, path = ssh_url_match.groups()
            path = path[:-4] if path.endswith(".git") else path
            return f"https://{host}/{path}"
        return None


def activate(context):
    def open_git_manager():
        dialog = GitManagerDialog(context)
        if dialog.repo_root is None:
            if context.window:
                context.window.show_warning("No Git repository detected in the current workspace.")
            return
        dialog.exec()

    context.commands.register_command(
        "gitManager.open",
        open_git_manager,
        title="Git Manager: Open",
    )
    context.log("[git-manager] Activated.\n")


def deactivate():
    return None
