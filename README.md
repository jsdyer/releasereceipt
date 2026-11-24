# Release Receipt

[Explore Canada's GDP release history](https://coolcode.ca/releasereceipt/) · [Download every observation](https://coolcode.ca/releasereceipt/receipts.csv) · [Versioned datasets](https://github.com/jsdyer/releasereceipt/releases)

<!-- coolcode:guide -->
Choose a reference month and an industry group to see the six-month window of growth estimates printed in successive Statistics Canada bulletins. The tool measures the difference between the first regular table and the latest archived table in percentage points. Select a month in the revision ranking to see the dated evidence, or download the figures and their source links.
<!-- /coolcode:guide -->

For example, Canada's June 2026 growth was +0.3% in the August 28 release and +0.4% in the September 29 release. Each table describes that same June relative to May. More complete survey and administrative information and seasonal adjustment can change an estimate. As a result, a change to a historical estimate does not imply a second change in economic activity on the publication date.

[August 28 bulletin](https://www150.statcan.gc.ca/n1/daily-quotidien/260828/dq260828b-eng.htm) · [September 29 bulletin](https://www150.statcan.gc.ca/n1/daily-quotidien/260929/dq260929a-eng.htm)

## Coverage and data dictionary

The archive starts with the October 31, 2025 bulletin. Each bulletin covers six reference months and three national aggregates. The earliest five months can have later estimates even when the first publication predates this archive. Publication dates, reference months and latest source check are displayed independently in the explorer. Source tables give seasonally adjusted growth at basic prices in chained volume terms. Each snapshot covers the six months printed in that bulletin. Longer-term benchmark revisions and advance estimates in the article text fall outside this collection.

| CSV column | Meaning |
| --- | --- |
| reference_month | Calendar month of economic activity, YYYY-MM |
| industry_group | all, goods, or services, as labelled in the source table |
| publication_date | Date Statistics Canada published this vintage |
| publication_stage | First table for the newest month in a release, later table for the previous five |
| monthly_growth_percent | Real GDP change from the preceding month, rounded to one decimal in the source |
| source_table | Direct link to the exact vintage used |

The JSON groups rows by bulletin, with each array running from oldest to newest month. A published -0.0 and 0.0 have the same numerical value here. The rank uses the absolute percentage-point difference at displayed precision and requires a first and at least one later table. The current selection is reflected in the address for sharing. Browsing uses saved public observations and the site's shared visit counter.

## Maintenance

The scheduled Pages workflow checks the release date of Statistics Canada table 36-10-0434-01 twice a week. It finds the corresponding Daily article and follows its previous-release links until it reaches an existing bulletin. A changed table layout or missing month fails the refresh, preserving the last working deployment. The workflow regenerates the long-format CSV, checks the build and browser interactions, then saves the verified update and deploys it. A manual run of **Browser tool · Check and publish** also refreshes the archive.

Run locally with Python 3.11+ and Node.js 20+:

```sh
python3 scripts/refresh.py
python3 scripts/dataset.py
node --test tests/*.test.mjs
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 -m http.server --directory dist
```

## Publishing a citable snapshot

Open [Publish dataset release](https://github.com/jsdyer/releasereceipt/actions/workflows/dataset-release.yml), click **Run workflow**, select **main**, and enter an unused version such as `2026.11.22.1`. Supply only the version number. If the version already exists, the manual run explains the collision and stops. Start a fresh run to choose a different version. Pushing a new version in `dataset-version.txt` also publishes it. Repeat pushes of an existing version leave that release intact.

A successful new release has a link in the run summary. Open it to see the matching `dataset-<version>` tag and an attached ZIP with the CSV, JSON, source licence, this dictionary and SHA-256 checksums.

To mint DOIs for future versions, sign in at [Zenodo's GitHub settings](https://zenodo.org/account/settings/github/), click **Sync now**, find **jsdyer/releasereceipt**, and turn on its repository switch before publishing a new GitHub release. Zenodo archives the tagged repository with the data under `web/`. Its resource type, attribution and licence are set by `.zenodo.json`. Inspect the resulting record for the assigned DOI. The HTML explorer also publishes Schema.org Dataset metadata with direct CSV and JSON distributions for dataset search engines.

## Attribution

Adapted from Statistics Canada, The Daily, Monthly gross domestic product by industry, publication and reference dates as shown in the dataset. This does not constitute an endorsement by Statistics Canada of this product. [Statistics Canada Open Licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence) · [Original tables](https://doi.org/10.25318/3610043401-eng)

<!-- schedule-reliability -->
## Schedule reliability

Public GitHub repositories can have scheduled workflows disabled after 60 days of inactivity. A separate weekly [schedule guard](.github/workflows/schedule-guard.yml) calls GitHub's enable-workflow API for an explicit list of refresh workflows and itself. It can restore workflows disabled for inactivity, preserves manually disabled workflows, and runs independently of collection failures.

This is an interim mitigation, not a scheduling guarantee: GitHub does not document active-workflow renewal as a permanent exemption, and scheduled runs can be delayed or dropped. A scheduler on our own Linux server is the planned independent trigger. The guard does not collect data, create dummy commits, or change source/check timestamps; successful collection and published data freshness still need monitoring.
<!-- /schedule-reliability -->
