"""Built-in SRE Production Readiness Review (PRR) rubric.

Sourced from Google's *The Site Reliability Workbook* (O'Reilly, 2018),
principally Chapter 18 "SRE Engagement Model" (which defines the PRR as the
gate SRE runs before accepting on-call/operational ownership of a service),
plus the chapters that define what "ready" means in each dimension the PRR
checks: Ch.2 Implementing SLOs, Ch.4 Monitoring, Ch.5 Alerting on SLOs,
Ch.6 Eliminating Toil, Ch.8 On-Call, Ch.9 Incident Response,
Ch.11 Managing Load, Ch.16 Canarying Releases.
(https://sre.google/workbook/ — CC BY-NC-ND 4.0, paraphrased here, not
reproduced.)

This is intentionally organization-agnostic — no internal policy, standard,
or contract is referenced. A team with its own SRE readiness checklist
should instead run `prr-readiness normalize-criteria` against it and pass
the resulting rubric to `assess --rubric`.
"""
from __future__ import annotations

from arch_compliance.rubric import RubricItem

DEFAULT_RUBRIC: list[RubricItem] = [
    # SLOs & error budget — Ch.2 Implementing SLOs
    RubricItem("SLO-1", "SLIs are defined for the service's critical user journeys (availability, latency, or other measurable indicators)", "slo", True, 5),
    RubricItem("SLO-2", "SLOs (targets on those SLIs) are documented and agreed with stakeholders", "slo", True, 5),
    RubricItem("SLO-3", "An error budget is defined from the SLO, with an agreed policy for what happens when it's exhausted (e.g. a release freeze)", "slo", True, 4),
    # Monitoring — Ch.4 Monitoring
    RubricItem("MON-1", "Monitoring measures the defined SLIs directly (symptom-based), not just proxy/cause signals", "monitoring", True, 5),
    RubricItem("MON-2", "Monitoring covers the service's key dependencies, not only the service itself", "monitoring", True, 3),
    RubricItem("MON-3", "Dashboards exist for the SLIs and are usable during an incident (a human can tell in seconds whether the service is healthy)", "monitoring", False, 3),
    # Alerting — Ch.5 Alerting on SLOs
    RubricItem("ALR-1", "Alerts are defined on SLO burn rate (or an equivalent symptom-based condition), not just static thresholds on causes", "alerting", True, 5),
    RubricItem("ALR-2", "Alerting balances precision, recall, and detection time — alerts page only when the error budget is genuinely at risk, with fast-burn and slow-burn windows", "alerting", True, 4),
    RubricItem("ALR-3", "Alerts route to the team that will actually respond (the right pager, not a shared inbox)", "alerting", True, 4),
    # Toil — Ch.6 Eliminating Toil
    RubricItem("TOIL-1", "Manual, repetitive operational tasks needed to run the service have been identified and, where possible, automated", "toil", False, 2),
    # On-call — Ch.8 On-Call
    RubricItem("ONCALL-1", "A sustainable on-call rotation is established for the service, with defined roles and coverage", "on-call", True, 4),
    RubricItem("ONCALL-2", "Escalation policy and secondary/backup on-call are defined", "on-call", True, 3),
    RubricItem("ONCALL-3", "On-call engineers have tested runbooks/playbooks for the service's known failure modes — not just written procedures, but ones that have actually been exercised", "on-call", True, 5),
    # Incident response — Ch.9 Incident Response
    RubricItem("INC-1", "An incident management process (roles such as incident commander, communication lead) is in place and known to the on-call team", "incident-response", True, 3),
    RubricItem("INC-2", "A postmortem process exists so operational learnings from this service's incidents will be captured (Ch.10 Postmortem Culture)", "incident-response", False, 2),
    # Managing load / capacity — Ch.11 Managing Load, Ch.12 NALSD
    RubricItem("CAP-1", "Capacity has been planned or load/stress tested against expected traffic, with headroom for growth and failover", "capacity", True, 4),
    RubricItem("CAP-2", "The service degrades gracefully under overload (load shedding, backpressure, or equivalent) rather than failing hard", "capacity", False, 3),
    # Rollout safety — Ch.16 Canarying Releases
    RubricItem("ROL-1", "Releases are canaried or staged with automated evaluation against the service's SLIs before full rollout", "rollout", True, 4),
    RubricItem("ROL-2", "A tested rollback path exists so a bad release can be reverted quickly", "rollout", True, 5),
    # Dependencies & architecture — Ch.18 SRE Engagement Model (PRR scope)
    RubricItem("DEP-1", "The service's critical dependencies are identified, and their own reliability/SLOs are understood to be sufficient to meet this service's SLO", "dependencies", True, 3),
    RubricItem("DEP-2", "Single points of failure in the architecture have been identified and either mitigated or explicitly accepted as a known risk", "dependencies", True, 3),
    # Documentation — Ch.18 SRE Engagement Model (PRR scope)
    RubricItem("DOC-1", "Architecture and operational documentation (design, data flows, deployment process) is current and accessible to the on-call team", "documentation", True, 3),
]
