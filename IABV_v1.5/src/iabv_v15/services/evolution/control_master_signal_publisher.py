                self._run_git([
                    "push", "origin", f"HEAD:refs/heads/{_SIGNAL_BRANCH}",
                ], cwd=checkout)
