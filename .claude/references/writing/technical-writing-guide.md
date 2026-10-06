# Technical writing guide

HMS Commander is an independent open source project that complements and builds on the work of the U.S. Army Corps of Engineers Hydrologic Engineering Center (HEC). Its documentation explains how to use the library with HEC-HMS. HMS Commander is not affiliated with, endorsed by, or supported by HEC or USACE.

This guide applies to HMS Commander's repository-maintained documentation, notebook explanations, API docstrings, comments that explain technical behavior, user-facing messages, agent skills, and release notes. The [extended writing standard](technical-writing-standard.md) supplies terminology, citation rules, examples, and the reasons for style choices. **Must** identifies a project requirement; **should** identifies a recommendation. These are HMS Commander editorial rules, not NASA, ASCE, or USACE requirements imposed on this project.

## Scope

This standard governs repository-maintained HMS Commander content and contributions intended for this repository. It does not govern users' projects, scripts, notebooks, reports, papers, maps, websites, or other deliverables outside HMS Commander, including content created with the library or its agents. Using HMS Commander, loading its agent skills, or requesting a modeling workflow does not opt a user into this editorial standard. An explicit request for writing advice on an external artifact permits scoped advice under the user's requirements, not automatic enforcement of this repository's rules.

## HEC sources and independent voice

1. **Use HEC's documentation as the primary source for HEC-HMS methods, terminology, interface labels, and documented HEC-HMS behavior.** Select the relevant manual and version. Use the Technical Reference Manual for method theory (loss, transform, baseflow, routing, meteorologic methods), the User's Manual for operation and component editors, and release notes for version changes. Start with the [HEC-HMS documentation portal](https://www.hec.usace.army.mil/confluence/hmsdocs); the [software documentation page](https://www.hec.usace.army.mil/software/hec-hms/documentation.aspx) also lists manual categories.
2. Speak directly and confidently about HMS Commander's capabilities, implementation, and supported observations. Current source and reproducible project evidence are authoritative for those claims; HEC approval or a HEC citation is not required. Explain the library's inputs, operations, outputs, and limits first. Cite HEC for its methods and hydrologic assumptions. Identify project recommendations as such and support consequential advice with rationale and evidence. A manual citation does not prove that a particular API or project has been tested.
3. Preserve HEC's exact component, method, and parameter names, such as "SCS Curve Number," "Clark Unit Hydrograph," "Muskingum-Cunge," "Frequency Storm," and "Specified Hyetograph." Use physically precise terms in surrounding prose. If a source, implementation, and observed result disagree, record the discrepancy, versions, and evidence. Do not silently reconcile them or assign a cause without evidence.
4. Use passive references: ordinary reader-activated links and citations to official documentation. Published references must not depend on fetching HEC pages at runtime, embedded HEC content, scraping, mirrored manuals, or automated contact with HEC. An agent may consult official sources during research. Existing software, example-project, and data acquisition workflows have their own contracts; this rule governs documentation references.
5. Give HEC appropriate technical credit without speaking on its behalf. State the independent-project relationship in project-level introductory material. Keep technical pages objective and respectful; identify reproducible limitations plainly. Avoid implied certification, partnership, endorsement, or HEC support for the library.

## Select the register

| Surface | Writing style | Include |
|---|---|---|
| Quick start, tutorial, procedure | Direct instructions; imperative verbs; one main action per step | Prerequisites, file changes and cost, API call, expected result, relevant HEC reference |
| User guide, concept explanation | Neutral explanation, mechanics first | Purpose, terminology, inputs and outputs, limitations, links to technical authority |
| API or schema reference | Precise, compact, structured | Types, shapes, units, defaults, file mutation, returns, failure behavior, HMS version limits |
| Qualification, comparison, technical report | Evidence-focused third-person prose | Question, setup, reference, metric, criterion, coverage, result, uncertainty |
| Release note, exception, log, UI text | Brief factual behavior or actionable diagnosis | Changed behavior or condition, impact, available next action |
| Contribution instructions, design decision, agent skill | Direct and professional | Rationale and decisions; first person only with a clear project author |

Use present tense for current behavior, past tense for completed work, and explicit uncertainty for proposals. Prefer active voice where the actor matters. Passive grammatical voice is acceptable when the actor is irrelevant. "Passive reference" describes the link's function, not sentence grammar.

Match detail to the reader: explain prerequisites and interpretation for newcomers; emphasize assumptions, results, and engineering limits for modelers; give exact contracts and failure behavior for developers and agents. State demonstrated results plainly, with their conditions. Respect for HEC does not require apologetic language, unnecessary hedging, or presenting original capabilities and observations as tentative.

## Technical meaning comes first

- Use "HEC-HMS," "HEC-DSS," and "HMS Commander" in prose; preserve package names such as `hms-commander` and `hms_commander` and exact API identifiers such as `HmsBasin` and `init_hms_project`.
- Name the HEC-HMS object an operation acts on: project (`.hms`), basin model (`.basin`), meteorologic model (`.met`), control specifications (`.control`), time-series and paired data (`.gage`, `.pdata`), simulation run (`.run`), and DSS output (`.dss`). A run combines a basin model, a meteorologic model, and control specifications; it is not interchangeable with "project" or "model."
- Distinguish precipitation depth, excess precipitation, runoff volume, and discharge. Prefer "discharge" or "flow rate" for a volumetric rate; retain HEC labels such as "Outflow," "Baseflow," and "Flow" in element results and DSS C-parts.
- Identify the modeled quantity when using annual exceedance probability (AEP). A precipitation-frequency design storm (Atlas 14, TP-40, Frequency Storm) defines rainfall probability; it is not automatically the AEP of the simulated peak discharge. Define symbols such as Q100 if used; preserve source storm names.
- Name the check: schema validation, file round-trip check, execution-completion check, GUI-open check, model comparison, calibration, or validation against observations. State what passed and under which criteria. A completed run or matching file does not establish hydrologic accuracy or engineering approval.
- Use the project's unit system and state it. Basin and meteorologic files may be US customary or metric; do not assume either. Put a space between a value and its unit (`2.5 in`, `150 mi²`, `850 cfs`); label table columns and plot axes. State time intervals and time zones explicitly; HEC-DSS time stamps and interval literals (`15MIN`, `1HOUR`) are protected.
- Tie compatibility, accuracy, performance, and coverage claims to specific HEC-HMS versions (3.x and 4.x behave differently), methods, evidence, and scope. Label synthetic examples and proposed thresholds. Never invent a measurement or generalize one example project to universal support.

## Structure and mechanics

Lead with the reader's task or the result. Keep each paragraph on one topic. Explain a consequential API operation before its code. Put conditions before dependent steps and state which HMS files an operation writes, whether it clones or edits in place, whether it creates backups, and whether it runs HEC-HMS. Use ordered lists for sequences and tables for comparisons. Figures need readable labels, units, explanatory captions, and a text explanation of the result.

Use US spelling in authored prose and sentence-case headings, while preserving source titles and literal labels. Define abbreviations for the page's audience. Prefer concrete verbs and restrained emphasis. Avoid promotional superlatives, decorative emoji, and repeated claims of importance in technical prose. Sentence length and punctuation are judgment calls, not numerical pass/fail rules.

Protect identifiers, code, CLI flags, schema keys and DataFrame column names (`hms_commander/schemas.py`), paths, HMS file keywords, DSS pathnames, quoted output, saved notebook results, formulas, values, citations, and legal text. Flag a suspected defect in these items with evidence and route it to the relevant owner. Edit the source of generated text; do not rewrite historical output to make a result appear better.

## Review before submission

Confirm that the prose matches the implementation and the cited HEC version, that units and evidence make claims interpretable, and that sources are cited near the statements they support. Use descriptive links for ordinary docs and complete reference entries for substantial reports.

Use the shared `technical-writing-auditor` skill for a scoped editorial review or a broader audit. Its report must distinguish confirmed defects, unresolved technical questions, and style suggestions, with locations, evidence, proposed corrections, and coverage limits. An editorial pass cannot certify a hydrologic method or replace professional engineering review. Public API changes also use the shared `api-consistency-auditor` skill.
