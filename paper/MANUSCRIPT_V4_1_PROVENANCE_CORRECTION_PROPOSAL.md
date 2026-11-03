# Proposed versioned Batch 4C.1 provenance correction — researcher review only

**Status: PROPOSED; NOT APPLIED.** This document describes a possible archival addendum. It does not change the Batch 4C.1 manifest, validation file, source journals, official Batch 4B outputs or any empirical result.

## Observed discrepancy

| Item | SHA-256 |
|:--|:--|
| Existing Batch 4C.1 `reproducibility_manifest.json` bytes | `ae08dfa574a1740d2955ab990ff6555d874ea931ecd7e54b10829556d52c59c0` |
| Validation-file hash recorded inside that manifest | `fc908ea071655291dfe6df091cd449ee9f2b0326485e8ccef8711177b1b66a59` |
| Current Batch 4C.1 `independent_validation.json` bytes | `7d6b6bc2c815abfec99681e508fb6a58f615da4ca760edf221af46f9dd08f918` |

The mismatch was first documented in Batch 4C.2 and carried through Batch 4C.3 and 4C.4. The current cause is **unknown**. The existing validation JSON is not used to support Manuscript V4.1 numerical claims. The official Batch 4B source identities and the Batch 4C.1 tables used by the manuscript passed the later read-only hash checks.

## Proposed non-destructive resolution

After researcher approval, create a **new** addendum such as `restricted_norgate/batch4c1_implementation_gap/provenance_addendum_v2.json` or a separately approved restricted audit location. Do not overwrite the first-run manifest or validation JSON. The addendum should record:

1. Both immutable file paths and all three hashes above, plus the date/time and person or process approving the addendum.
2. The frozen Batch 4B run IDs and original source-hash manifest against which the Batch 4C.1 arithmetic was checked.
3. A factual chronology only if supported by retained logs or filesystem evidence; otherwise `cause: UNDETERMINED`.
4. A separately named, **new** read-only validation run against the frozen journals and outputs, with its script hash, result hash, and exact comparison scope. Do not describe it as the missing original first-run bytes.
5. A supersession statement limited to archival **provenance**: the new addendum explains the inconsistency but does not change the Batch 4C.1 empirical tables, the Batch 4B primary estimand, or any old checksum entry.
6. A disclosure decision for the manuscript and future data-availability package under Norgate licensing terms.

Suggested record fields for review (illustrative, not an executed correction):

```json
{
  "schema": "BATCH4C1_PROVENANCE_ADDENDUM_V2_PROPOSED",
  "status": "PENDING_RESEARCHER_APPROVAL",
  "original_manifest_sha256": "ae08dfa574a1740d2955ab990ff6555d874ea931ecd7e54b10829556d52c59c0",
  "original_manifest_expected_validation_sha256": "fc908ea071655291dfe6df091cd449ee9f2b0326485e8ccef8711177b1b66a59",
  "observed_validation_sha256": "7d6b6bc2c815abfec99681e508fb6a58f615da4ca760edf221af46f9dd08f918",
  "cause": "UNDETERMINED",
  "prior_files_preserved": true,
  "new_validation": "TO_BE_RECORDED_ONLY_AFTER_APPROVED_READ_ONLY_RUN"
}
```

**Approval question for the researcher:** whether this addendum design is sufficient for the final private archive. No approval is inferred from the request for a proposal, and no addendum has been written to the restricted Batch 4C.1 directory.
