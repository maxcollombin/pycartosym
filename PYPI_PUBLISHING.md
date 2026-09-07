# Publishing to PyPI

Releases are published by `.github/workflows/publish.yml` using PyPI
["Trusted Publishing"](https://docs.pypi.org/trusted-publishers/) (OIDC) —
no API token is stored as a repository secret.

## One-time setup

Do this once, before the first publish.

### 1. Register a trusted publisher on TestPyPI

1. Create a [TestPyPI](https://test.pypi.org/account/register/) account
   (separate from your real PyPI account).
2. Go to <https://test.pypi.org/manage/account/publishing/> and add a
   **pending publisher**:
   - PyPI project name: `pycartosym`
   - Owner: `maxcollombin`
   - Repository name: `pycartosym`
   - Workflow name: `publish.yml`
   - Environment name: `testpypi`

### 2. Register a trusted publisher on the real PyPI

Same as above at <https://pypi.org/manage/account/publishing/>, with
environment name `pypi` instead.

### 3. Create the two GitHub environments

In the repo: **Settings → Environments**, create `testpypi` and `pypi`
(names must match the trusted publisher config above exactly). Consider
adding a required reviewer on `pypi` only, so a real release needs a
manual approval click even after the workflow is triggered.

## Publishing a dry run (TestPyPI)

**Actions → Publish → Run workflow**, target = `testpypi`. Then verify the
install works from TestPyPI (it only has TestPyPI's own package index, so
dependencies must be pulled from the real PyPI):

```bash
pip install --index-url https://test.pypi.org/simple/ \
  --extra-index-url https://pypi.org/simple/ pycartosym
```

A version can only be uploaded to (Test)PyPI **once** — re-running the dry
run after a failed attempt requires bumping the version first.

## Publishing a real release

1. Bump `version` in `pyproject.toml`.
2. Commit, push.
3. Tag and push the tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
4. Create a GitHub Release from that tag (**Releases → Draft a new
   release**) and publish it — this triggers the `pypi` job.
