# ubiquitous-meme

This repository contains a command line tool for capturing pricing information from [21st Century Distributing](https://21stcenturydist.com/).

## Features

- Authenticates against the distributor portal using the same AJAX endpoint that powers the website sign-in form.
- Downloads manufacturer listing pages and extracts structured product data including item numbers, descriptions, pricing text, stock indicators, and per-branch inventory counts.
- Exports the collected data as CSV or JSON files for further analysis or archival.

## Installation

Clone the repository (or download the source) and make sure you are working from the project root before installing. From the root directory run:

```bash
git clone <repo-url>
cd ubiquitous-meme
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

If the `pip install -e .` step is executed from another directory (for example, your home folder), `pip` will raise `does not appear to be a Python project` because it cannot find this project's `pyproject.toml`. Always run the install command from the folder that contains `pyproject.toml` (the repository root).

## Usage

The `pricing-recorder` entry point requires valid credentials for the portal. Credentials can be provided either via command line flags or the `CENTURY21_EMAIL` and `CENTURY21_PASSWORD` environment variables.

```bash
export CENTURY21_EMAIL="you@example.com"
export CENTURY21_PASSWORD="super-secret"
pricing-recorder "AC INFINITY" --output data/ac-infinity.csv --format csv --verbose
```

Multiple manufacturers can be specified in one invocation and the output directory will be created automatically.

> **Note:** The scraper honours the site's access controls. If the account does not have permission to view pricing the resulting dataset will contain blank `price_text` fields.

### Scraping public listings

Some manufacturer listing pages are publicly accessible without a login. For those cases you can pass `--skip-login` and omit credentials entirely:

```bash
pricing-recorder "AV Distribution" --skip-login --output data/av-distribution.csv --format csv --verbose
```

### Troubleshooting authentication

The CLI now mirrors the browser login flow by first visiting the portal home page so that Azure Application Gateway cookies are issued before the credential check. If you continue to see `Authorization failed` messages:

- Double-check the email and password being supplied to the tool. Copy/paste errors are the most common cause.
- Ensure your account can sign in via the website directly. Accounts without B2B access will be rejected by the portal even though the scraper handshakes correctly.
- Some corporate networks block outbound traffic to the distributor. Running the command with `--verbose` will surface HTTP errors encountered during the login or collection steps.

## Development

Run the unit tests with:

```bash
pytest
```
