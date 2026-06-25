# Public Deployment

NeuroDEG is a Python/Streamlit application. GitHub Pages can host only a
static site, so the functional analysis application should be deployed with
Streamlit Community Cloud while GitHub remains the code and data source.

## Deployment Target

Use:

- Repository: `1am-not-sleep/NueroDEG`
- Branch: `codex/test-new-polish`
- Entry point: `streamlit_app.py`
- Python: `3.12`

## Before Deployment

Run:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/deployment_smoke_test.py
```

The smoke test verifies that:

- required offline GO and marker data are present
- the Streamlit entrypoint can be compiled
- the example analysis produces a valid report and result manifest

## Streamlit Community Cloud

1. Open <https://share.streamlit.io/>.
2. Sign in with the GitHub account that can access the repository.
3. Select **Create app**.
4. Choose **Yup, I have an app**.
5. Enter the repository, branch, and entrypoint listed above.
6. In advanced settings select Python 3.12.
7. Pick an available public app URL.
8. Deploy.

No secrets are required for offline analysis. Enrichr is optional and may be
unavailable in restricted cloud environments; local GO and curated pathway
analysis remain functional.

## Updating the Public Site

After deployment, pushes to the configured GitHub branch trigger an app
rebuild. Before pushing an update, run the test and smoke-test commands.

## GitHub Pages

GitHub Pages cannot execute this application because it does not run Python
server code. It can be added later as a static project landing page linking to
the Streamlit application.
