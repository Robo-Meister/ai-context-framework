# Releasing caiengine

This checklist outlines the steps required to publish a new release of the caiengine package.

## 1. Prepare the Release
- [ ] Update the version in `pyproject.toml` and `setup.py`.
- [ ] Document the changes in `CHANGELOG.md` under a new version heading.
- [ ] Ensure documentation updates are committed, especially if the release introduces new developer workflows.

## 2. Verify Code Quality
- [ ] Run the unit test suite (`pytest`) and linting tools used by the project.
- [ ] Regenerate any artifacts or documentation that depend on the code, if applicable.

## 3. Build Artifacts
- [ ] Clean the `dist/` directory and run `python -m build` from the project root.
- [ ] Inspect the resulting source distribution and wheel to confirm provider modules, docs, and the CLI entry point are present.

## 4. Smoke-Test the Wheel
- [ ] Create a fresh virtual environment.
- [ ] Install the newly built wheel with `pip install dist/*.whl`.
- [ ] If the CLI relies on optional providers (e.g., torch-backed storage), install the extras with `pip install 'dist/*.whl[ai]'`.
- [ ] Run `context --help` to confirm the CLI entry point works once dependencies are satisfied.

## 5. Publish
- [ ] Upload artifacts with `twine upload dist/*` (or the organization-specific publishing command).
- [ ] Tag the release in version control and push the tag.
- [ ] Announce the release through the appropriate communication channels.

Keeping a log of each release run helps future maintainers debug issues quickly.
