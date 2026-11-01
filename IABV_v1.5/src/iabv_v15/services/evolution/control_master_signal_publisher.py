                empty_hooks = Path(tmp) / "empty-git-hooks"
                empty_hooks.mkdir()
                self._run_git(["config", "core.hooksPath", str(empty_hooks)], cwd=checkout)
