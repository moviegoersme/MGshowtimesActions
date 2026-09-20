# MGshowtimesActions

Scheduled GitHub Actions workflows for [Moviegoers Showtimes](https://moviegoersme.com). Lives in a public repo so these runs use GitHub's free/unlimited public-repo Actions minutes instead of the private app repo's own monthly budget.

Each workflow checks out the private app repo at run time (via a read-only, single-repo access token stored as a secret here) to run its scraper script — no application source code is stored in this repo, only the workflow definitions.

## Required secrets

- `PRIVATE_REPO_TOKEN` — fine-grained PAT, read-only access to the private app repo's contents.
- `APP_URL`, `CRON_SECRET` — used to submit scraped results back to the app.
- `DECODO_USERNAME`, `DECODO_PASSWORD` — residential proxy credentials, used by workflows that need one.
