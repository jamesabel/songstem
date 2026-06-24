# Contributing

Thanks for working on Songstem. This project uses a simple branch-and-PR workflow: `main`
stays clean and every change lands through a pull request.

## Branch and PR workflow

1. **Branch off `main`.** Never commit directly to `main`.

   ```pwsh
   git switch main
   git pull
   git switch -c <type>/<short-topic>     # e.g. feature/openunmix-backend
   ```

   Suggested branch prefixes: `feature/`, `fix/`, `docs/`, `chore/`, `refactor/`.

2. **Make your change** and keep it focused — one logical change per branch.

3. **Verify before pushing** (see Checks below): tests and lint must pass.

4. **Open a pull request** for review:

   ```pwsh
   git push -u origin <branch>
   gh pr create --fill        # or write a title/body describing the change
   ```

5. **Review.** PRs are always opened for review rather than pushed straight to `main`.
   Leave the PR open for the maintainer unless asked to merge it.

6. **Merge** with a squash once approved, then delete the branch:

   ```pwsh
   gh pr merge --squash --delete-branch
   ```

## Local setup

See the [README](README.md) for full setup. In short:

```pwsh
.\setup_venv.bat            # creates .venv and installs songstem with dev extras
.\.venv\Scripts\Activate.ps1
```

## Checks

Run both before opening a PR:

```pwsh
pytest                      # all tests must pass
ruff check .                # lint must be clean
```

The default test suite is dependency-light and does not download the Demucs model or touch
iTunes, so it runs anywhere. Tests that would require the ML model, a GUI display, or live
iTunes are exercised manually rather than in the default suite.

## Conventions

- **Keep heavy/platform imports local** to the functions that use them (torch, Demucs,
  PySide, soundfile, win32com), so the core stays importable and testable without the full
  stack. See [CLAUDE.md](CLAUDE.md) for the architecture overview.
- **Separation runs on CPU by default** (`Settings.device = "cpu"`) for compatibility; don't
  assume a GPU is available.
- New separation backends implement `separation.base.Separator` and register in
  `separation.registry` — nothing else should need to change.

## Commit messages

Write imperative, present-tense subjects (e.g. "Add Open-Unmix backend"). Keep the subject
short and put rationale in the body when it isn't obvious from the diff.
