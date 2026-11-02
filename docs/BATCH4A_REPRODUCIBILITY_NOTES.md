# Batch 4A reproducibility and restricted-data inventory

## Acquisition design

The new pipeline is independent of V4/V5-U. Windows Python calls the installed Norgate package by stable `assetid` for each symbol in `S&P 500 Current & Past`, plus SPY for calendar comparison. It records source description, acquisition UTC timestamp, Python and package versions, manually recorded NDU version, requested date range, explicit modes/padding, candidate count and extractor SHA-256 in the private SQLite `metadata` table. The WSL validator records its own hash, the private SQLite checksum, the existing SPY calendar checksum, record counts and quality results in a private JSON file. Norgate provides no immutable, researcher-visible price vintage; its [data FAQ](https://norgatedata.com/data-package-faq.php) says corrections are applied without notification or versioning. These hashes identify our local acquisition, not a provider version.

`nd.assetid(symbol)` supplies a stable Norgate asset identity; `nd.symbol(assetid)` may return a later symbol. The current watchlist spelling and asset ID are retained privately. The batch does not claim a verified historical ticker timeline. A future independent mapping is needed for symbol changes and external sector joins.

## Restricted inventory and lifecycle

All locations below are **local to the researcher's WSL repository** under ignored `/home/elliot/signal-conditioned-portfolio-risk/restricted_norgate/`:

| File | Source/content | Classification | Cleanup |
|---|---|---|---|
| `sample_20261102.sqlite` | Failed zero-byte first attempt | Private attempt log | Researcher may remove after review. |
| `sample_v2_20261102.sqlite` | Failed identity lookup; no prices or membership | Private metadata/errors | Researcher may remove after review. |
| `sample_v3_20261102.sqlite` | Norgate AAPL, delisted sample and SPY: prices, membership, capital flags, identifiers | Licensed Content | Delete at expiry absent imminent renewal. |
| `batch4a_full_v1_20261102.sqlite` | Planned/full Norgate source rows, daily membership, events, asset IDs, metadata | Licensed Content | Delete at expiry absent imminent renewal. |
| `batch4a_validation_v1_20261102.json` | Local checksums, acquisition metadata and aggregates | **REQUIRES_LICENSE_CLARIFICATION** for retention/publication; keep private | Review and delete with extract unless rights clarified. |
| `batch4a_validation_v2_20261102.json` | Checksums, aggregates and private anomaly dates/identities | Licensed Content / **REQUIRES_LICENSE_CLARIFICATION** for aggregates | Keep private; delete source-level details at expiry absent imminent renewal. |
| `batch4a_validation_v3_20261102.json` | Intermediate validator checksums, aggregates and private anomaly dates/identities | Licensed Content / **REQUIRES_LICENSE_CLARIFICATION** for aggregates | Keep private; delete source-level details at expiry absent imminent renewal. |
| `batch4a_validation_v4_20261102.json` | Final validator checksums, aggregates and private anomaly dates/identities | Licensed Content / **REQUIRES_LICENSE_CLARIFICATION** for aggregates | Keep private; delete source-level details at expiry absent imminent renewal. |
| `batch4a_actions_v1_20261102.json`, `batch4a_actions_v2_20261102.json` | Aggregate cross-provider checks; v2 also has per-security dividend exceptions | Licensed Content / **REQUIRES_LICENSE_CLARIFICATION** for aggregates | Keep private; delete source-level exceptions at expiry absent imminent renewal. |
| `batch4a_actions_v3_20261102.json` | Final aggregate cross-provider checks, script hash and per-security dividend exceptions | Licensed Content / **REQUIRES_LICENSE_CLARIFICATION** for aggregates | Keep private; delete source-level exceptions at expiry absent imminent renewal. |

Windows-local temporary SQLite files are automatically removed by the extractor's `TemporaryDirectory` after the copy; no persistent Windows extract is intended. The Norgate Data Updater database is part of the licensed installation and is **not** a pipeline output. Check for local backups, copies and sync tools before expiry. Do not upload any `restricted_norgate/` file to GitHub, external APIs, chat or cloud storage. Keep logs limited to progress counts and error stages; error text stays private in SQLite.

The [Norgate subscription FAQ](https://norgatedata.com/faq.php) and [EULA](https://norgatedata.com/subscribe/eula.php) permit personal non-commercial academic processing during an active subscription. They require exported/extracted Content, including metadata, snapshots and backups, to be deleted after expiry when renewal is not imminent; Derived Data such as substantially transformed trading results and statistics may be retained under the agreement. This document does not presume that a particular audit table meets the EULA's derived-data test. Aggregate counts in the repository's local batch reports are **REQUIRES_LICENSE_CLARIFICATION before publication or post-expiry retention**; detailed per-date counts, IDs and event-level rows remain private. No batch file was committed, pushed or published.

## Researcher-operated cleanup procedure

At expiry without imminent renewal, first inventory `restricted_norgate/`, Windows Downloads/Documents/temporary exports, backup software and any copies made during analysis. Preserve only material confirmed to qualify as Derived Data. Then delete Norgate Content and its backups through the researcher's normal secure-file workflow and record the action/date in a private research log. No automated deletion is provided or performed by Batch 4A. Do not delete the repository's frozen V4/V5-U outputs merely because this new extract expires; assess their source-data status separately under applicable licenses.
