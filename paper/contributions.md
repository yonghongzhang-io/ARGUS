# Contributions

1. **ARGUS**, a *bounded-agentic*, responsible-AI framework that audits causal
   *identification credibility* — not causal truth — in DID environmental-policy
   evaluation, with a fixed deterministic pipeline and agency confined to two
   scoped sub-tasks (extraction, assessment).

2. An **identification rubric** of 11 auditable dimensions and a **flaw taxonomy**
   that maps each known identification threat one-to-one onto a dimension
   (`config/`), giving the system an explicit, inspectable contract.

3. A **flaw-injection evaluation methodology** that yields reproducible *local
   ground truth* (detection / false-alarm / localization) without access to the
   true causal effect.

4. An **honest deterministic baseline and a negative result**: once the
   sentinel-sentence leakage that made naive evaluation circular is removed,
   keyword-based detection collapses from a trivial 1.000 to ~0.18, and the
   baseline is systematically blind to *commission*-type threats (flawed-but-
   present evidence). This quantifies the gap a reasoning-based auditor must
   close and motivates the doctoral research programme.
