# Remaining research tasks

Ordered by what is needed for a defensible paper, without launching a new strategy search. Preserve all existing outputs and the frozen FMA source. Any corrected experiment must receive a new version and immutable output set.

## Blocking final conclusions

1. **Reference fidelity:** freeze a test manifest of representative dates, signal-rich and empty days, high-volatility days, and cap-boundary days. Compare the candidate pool, features, ranks, selections, rejections, share counts and orders produced by the research integration with frozen FMA. Record exact match rates and differences. The existing 17-case exit check and 4,874 signal checks set a starting point; they do not establish order parity. Locate the reported 408/408 sampled exit-formula audit artifact or label it user-reported context.
2. **Dividend and action materiality:** inventory only events affecting held positions on each path; confirm amount, ex-date and pay date where local data permit. Quantify upper/lower NAV sensitivity to unsettled receivables and the adjusted-stop assumption. Preserve original NAVs. If material ambiguity remains, frame performance as conditional rather than definitive.
3. **Constraint timing:** for V5-U breach dates, reconstruct T-close plan, T+1 pre-open state, post-open fills, and close. Explain own-budget and sector excesses separately. Verify whether any entry order was already outside an intended planning limit. This is needed before saying a policy enforces constraints.
4. **Protocol decision:** researcher approves the primary estimands, V5-U/V4 display order, and uncertainty wording in `docs/RESEARCH_PROTOCOL_V1.md`. Freeze that choice before drafting the main result interpretation; no parameter optimization.
5. **Reproducibility manifest:** document Python/dependency versions, exact local input paths and hashes, reference source hashes, code revision, output hashes, and invocation order. Keep licensed data private; report how an authorized researcher can obtain equivalent inputs.

## Needed for a complete manuscript, can proceed alongside the above

6. Build Methods, Results, limitations and discussion tables directly from the evidence matrix. Distinguish verified arithmetic from provisional economic interpretation. State the inspected-sample and current-constituent limitations at first mention of performance.
7. Compute a clearly specified paired descriptive time-series analysis of capital deployment, risk-budget exceedance and costs. If uncertainty intervals are used, state dependence treatment and exploratory status; do not turn post-hoc exploration into a confirmatory p-value story.
8. Verify literature and citations from primary sources during drafting. No literature novelty or source claim is currently certified by this package.

## Optional extensions

- Obtain point-in-time membership or a genuinely untouched future period for external validity if feasible; neither can be retroactively assigned to the inspected 282 sessions.
- Model integrated cash interest and cost/liquidity sensitivities under newly versioned assumptions.
- Study auxiliary allocations only as a separate future protocol.

**Next draft milestone:** after the researcher accepts the V1 outcome hierarchy and the fidelity/action audit has bounded any material effect on the reported comparisons, start the paper's Methods and qualified descriptive Results sections using `docs/RESULTS_EVIDENCE_MATRIX.md`. The Introduction and literature review can begin in parallel once sources are verified.
