# Technical writing standard

This standard defines HMS Commander's editorial choices for library documentation and public technical text. It is a companion to the [concise writing guide](technical-writing-guide.md). It applies to new and substantially revised text; existing material can be assessed in a scoped audit. Adoption does not assert compliance with an external publication standard or a retroactive review of the entire library.

This standard governs repository-maintained HMS Commander content and contributions intended for this repository. It does not govern users' projects, scripts, notebooks, reports, papers, maps, websites, or other deliverables outside HMS Commander, including content created with the library or its agents. Using HMS Commander, loading its agent skills, or requesting a modeling workflow does not opt a user into this editorial standard. An explicit request for writing advice on an external artifact permits scoped advice under the user's requirements, not automatic enforcement of this repository's rules.

## Contents

- [Purpose and authority](#purpose-and-authority)
- [HEC relationship and references](#hec-relationship-and-references)
- [Style selection](#style-selection)
- [Terminology](#terminology)
- [Numbers, units, and spatial and temporal references](#numbers-units-and-spatial-and-temporal-references)
- [Evidence and quality claims](#evidence-and-quality-claims)
- [Content patterns](#content-patterns)
- [Citations and acknowledgment](#citations-and-acknowledgment)
- [Editing and auditing](#editing-and-auditing)
- [Source selection and adaptation](#source-selection-and-adaptation)

## Purpose and authority

The reader should be able to determine what an operation does, which HMS files it changes, what its output means, and what evidence supports the description. Documentation serves modelers learning Python, experienced hydrologic engineers, developers, researchers, and agents using the API. State the intended audience when it materially changes the explanation.

In this standard, **must** is an HMS Commander requirement and **should** is a recommendation with room for a justified exception. "May" grants an option when permission is the intended meaning; use "might" or a stated uncertainty when describing a possibility. Use ordinary present-tense statements for implemented behavior. Reserve "shall" for an accurately quoted requirement or an external deliverable whose governing standard requires it.

Use authority by subject:

| Subject | Primary evidence | Complementary evidence |
|---|---|---|
| HEC-HMS terminology, documented methods, component editors, file semantics | Relevant official HEC-HMS Technical Reference Manual, User's Manual, release notes, or published guidance, selected by version | Original studies cited by HEC; reproducible example-project evidence |
| HMS Commander signature, default, return shape, mutation, supported operation | Current source, docstrings, `hms_commander/schemas.py`, and relevant test records | Runnable examples and release history |
| HMS Commander observations, experiments, and original findings | Reproducible project records, methods, conditions, and measured results | HEC documentation and independent studies for context or comparison |
| Precipitation-frequency and observed data | Provider metadata and methods, such as NOAA Atlas 14, TP-40, AORC, or USGS documentation | Applicable project and agency guidance |
| HEC-DSS storage and pathname semantics | HEC-DSS documentation and the shared `ras-commander` DSS implementation that HMS Commander uses | Example DSS catalogs |
| Regulatory or project acceptance | Governing jurisdiction, agency, project requirements, and responsible engineer | HEC technical documentation and independent research |
| Editorial presentation | This project standard | NASA KSC, ASCE, USACE, and selected Simplified Technical English principles within their stated scope |

HEC remains the primary source for its documented HEC-HMS methods and terminology. HMS Commander speaks with authority about its own implemented capabilities and evidence-supported findings. Those claims do not require HEC approval or a HEC citation. Reproducible observations of HEC-HMS behavior, such as the documented workarounds in `.claude/rules/hec-hms/critical-bugs-workarounds.md`, may add information beyond a manual; describe the observed conditions, HEC-HMS version, and scope directly. A description must distinguish documented behavior, implementation, observation, and interpretation. A source unavailable for inspection cannot be treated as verified evidence.

## HEC relationship and references

### Project identity

Use this relationship statement in introductory project material:

> HMS Commander is an independent open source project that complements and builds on HEC's work by providing Python tools for HEC-HMS workflows. HEC-HMS is developed by the U.S. Army Corps of Engineers Hydrologic Engineering Center (HEC). HMS Commander is not affiliated with, endorsed by, or supported by HEC or USACE.

Do not imply that HEC authored, certified, approved, supports, or partnered on an HMS Commander feature. "HEC recommends" requires a source containing that recommendation, with its conditions intact. A local implementation choice, such as the clone workflow or a default time interval, must be identified as local. HMS Commander must not speak as HEC.

Credit the relevant HEC document at the point of a technical explanation. Avoid praise in place of attribution or statements implying HEC approval because a manual is linked.

### Passive references

HEC references in published HMS Commander content must be normal citations or reader-activated hyperlinks. A reference must stand on its written title, version, and locator even if the reader does not open the link. Prefer official deep links to relevant sections; use the documentation index as a fallback.

Documentation references must not introduce:

- Runtime fetching of HEC pages to populate a help message or explain an API result.
- Embedded HEC pages, remotely loaded documentation previews, or live vendor content required to render a library page.
- Scraping, copied manual trees, or a documentation build that downloads HEC content to create citations.
- Automated issue submission, emails, or contact with HEC.

These are reference rules. They do not prohibit an agent from reading official documents during research, and they do not change separately governed features such as `HmsExamples` project extraction, Atlas 14 or AORC downloads, or the `hms_doc_query` research agent. Link verification should be bounded and performed during review. If a source is unreachable, retain correct known metadata, record the access limitation in the audit, and avoid invented replacement links.

### Respectful technical independence

Present demonstrated capabilities, results, and original contributions plainly. Respectful attribution does not require treating HEC documentation as exhaustive, subordinating project evidence to a manual, or hedging an established result. Give a project recommendation when the audience benefits from it, identify it as HMS Commander's recommendation, and explain its rationale, evidence, and applicability.

Report a discrepancy objectively: describe the operation, HEC-HMS version, source section, expected and observed behavior, and what remains unknown. Separate a reproducible library problem, a source-model condition, and a suspected HEC-HMS behavior; do not assign causation from a symptom alone.

### Version discipline

Use the manual applicable to the documented HEC-HMS version. Distinguish the installed HEC-HMS version, the `Version:` declared in a project file, the manual version, and the library version when they differ. HEC-HMS 3.x and 4.x differ in execution (Python 2-compatible Jython for 3.x), file keywords, and available methods; state which applies. A currently displayed manual or release is not proof that the library supports it.

Prefer versioned URLs for behavior-specific statements. If only a changing `latest` page is available, record the version shown and the access date. Web references need section headings or anchors rather than fabricated page numbers.

## Style selection

Choose a style based on what the reader needs to do. Audience determines the explanation, not whether a supported claim can be stated confidently. For newcomers, explain prerequisites, terms, and how to interpret a result. For hydrologic modelers, emphasize assumptions, parameter meaning, and applicability. For developers and agents, specify exact contracts, data structures, and failure behavior. For reviewers, expose the method, comparisons, uncertainty, and reproduction records.

| Content | Register and tense | Recommended structure | Authority emphasis |
|---|---|---|---|
| Installation and quick start | Direct, present tense, imperative | Requirements; steps; expected output; common failures | Package and runtime contracts |
| Tutorial and notebook | Direct explanation; past tense for retained run results | Purpose; prerequisites; API operation; interpretation; limitations | Example-project evidence plus HEC method references |
| User guide | Neutral explanation; present tense | Task; operation; inputs and outputs; caveats; next reference | Mechanics first; HEC for hydrologic context |
| API and schema | Compact factual prose | Summary; Args; Returns; Raises; Example; Note | Exact source, signature, and `schemas.py` |
| Hydrologic concept or method | Neutral technical explanation | Scope; assumptions; relation to HEC method; library operation; limits | Relevant HEC Technical Reference Manual section |
| Qualification, comparison, report | Third-person evidence-focused prose; past tense for work performed | Question; setup; criteria; results; limitations; references | Versioned records and test data |
| Release notes | Brief factual change statement | Behavior; affected scope; compatibility or migration | Diff and released behavior |
| UI, exception, log | Concise actionable language | Condition; consequence; available next action | Actual control flow and stable message contract |
| Contribution guide, design decision, agent skill | Direct professional prose | Decision or problem; reasons; consequences | Repository policy and `AGENTS.md` |

Use active voice where it clarifies who does what. "The method writes the basin model file" is preferable to hiding the operation's actor. Define project coinages locally and avoid unexplained abbreviations in headings.

## Terminology

Use consistent wording for a concept within its context. Consistency does not justify rewriting established HEC labels or treating distinct concepts as synonyms. The following are local editorial defaults informed by HEC usage; they are not claims that HEC mandates one form.

| Concept | Default in authored prose | Context and protected forms |
|---|---|---|
| Product and project | HEC-HMS; HEC-DSS; HMS Commander | Preserve `hms-commander`, `hms_commander`, `HmsPrj`, and actual API names |
| Project | HEC-HMS project (the `.hms` file and its folder) | Do not call a basin model or run "the model" when the object can be named |
| Basin model | Basin model (`.basin`) containing hydrologic elements | Element types keep HEC names: Subbasin, Reach, Junction, Reservoir, Source, Sink, Diversion |
| Meteorologic model | Meteorologic model (`.met`) | Preserve method names such as Specified Hyetograph, Frequency Storm, Gridded Precipitation |
| Control specifications | Control specifications (`.control`) | "Control file" is acceptable for the file itself; preserve `Time Interval` and date keywords |
| Simulation run | Simulation run (`.run`) | A run selects a basin model, meteorologic model, and control specifications |
| Gage | Follow HEC-HMS usage, "gage," for time-series gages (`.gage`) | Preserve `HmsGaugeData`, `gauge_metadata`, USGS source titles, and existing API spellings |
| Loss, transform, baseflow, routing | Name the selected HEC method, such as SCS Curve Number, Clark Unit Hydrograph, Recession, Muskingum-Cunge | Parameters keep HEC names and units; do not paraphrase method names |
| Precipitation | Precipitation depth, intensity, or hyetograph, with duration | Excess precipitation and runoff are different quantities |
| Discharge | Discharge or flow rate for volumetric rate | Retain DSS C-parts and result labels such as `FLOW`, `Outflow`, `Baseflow` |
| Probability | Annual exceedance probability (AEP); identify the variable | Rainfall and discharge AEP are not interchangeable; preserve source storm names |
| Comparison | Compared with a stated reference | Agreement between models alone does not demonstrate physical accuracy |
| Verification | Name the property verified and criteria | File round-trip, GUI-open, and execution-completion checks have different scope |
| Validation | Name the object and reference, such as schema validation or model validation | `validate_*` APIs and `HmsRoundTripValidator` remain literal |
| Calibration | Adjustment of parameters using specified data and objective | A calibration fit does not by itself establish validation with independent data |
| Approval | Identify the actual reviewer and scope if approval occurred | Automated checks and agent recommendations are not professional engineering approval |

### Frequency terminology

Use "1% AEP 24-hour precipitation depth" when that is the quantity described. "100-year" may appear as a first-use gloss or exact source name. Explain average recurrence when the audience needs it; it is not a schedule for an event.

A precipitation-frequency design storm built with `Atlas14Storm`, `FrequencyStorm`, `BalancedFrequencyStorm`, `ScsTypeStorm`, or `TexasStorm` is legitimate terminology for rainfall. Do not assign its rainfall probability to simulated discharge without stating and supporting that modeling assumption. Areal reduction factors (`HmsArf`, `HmsArfTexas`) change depth for an area; state the source table and area basis.

## Numbers, units, and spatial and temporal references

Use the unit system of the source, project, or documented API contract. Both metric and US customary projects are valid. Do not convert or round data as a prose cleanup. If dual units are needed, declare the primary system, use consistent order, and document the conversion.

Put a space between a quantity and unit (`0.5 in`, `12 mm`, `3.2 m³/s`). `cfs` is acceptable in HEC-related material; define it as cubic feet per second when needed. Preserve exact unit strings in HMS file keywords, DSS records, and schemas. Label dimensional table columns and plot axes. State the denominator for normalized quantities and distinguish percent change from percentage points.

State horizontal CRS independently from vertical datum. Basin model map coordinates and `.geo` or `.sqlite` geometry have their own CRS; do not infer one from another without evidence. Use precision justified by the data or computation; never round away a failing tolerance.

Write dates unambiguously. Use ISO dates for records and identify the time zone where relevant. Distinguish incremental from cumulative precipitation, instantaneous from period-average values, and computation interval from output interval. Preserve HEC-HMS control-specification dates and HEC-DSS time and interval literals.

## Evidence and quality claims

Every consequential claim must be supported and scoped. Describe what was checked, against which reference, under which HEC-HMS and library versions, using which metric or acceptance criterion.

| Claim | Evidence needed |
|---|---|
| Execution completed | Completion evidence (log, DSS output) and the error policy the library used |
| Compatible or supported | Operation, HEC-HMS and library versions, example projects tested, known limits |
| Opens in the GUI | HEC-HMS version and the actual GUI-open observation |
| Faster | Comparable tasks, setup, timing method, and measured results |
| Accurate or validated | Quantity, reference or observations, criterion, coverage, uncertainty, intended purpose |
| Comprehensive or complete | Defined scope and evidence of coverage; otherwise list the actual capabilities |
| Recommended or required | Source and authority, or an explicitly attributed project choice |

Use present tense for implemented behavior and past tense for an observed run. Label proposed behavior and estimates. Preserve uncertainty when evidence is incomplete. Synthetic demonstration data must be identified as synthetic and must not be presented as a completed qualification.

Separate process success, output integrity, numerical agreement, hydrologic adequacy, and engineering acceptance. A report can support one without establishing the others.

## Content patterns

### User guides and procedures

Start with the task and resulting artifact. Identify prerequisites that affect execution, including the installed HEC-HMS version, Java and Jython requirements, optional dependencies (`[dss]`, `[gis]`), and network access. Before the step that causes them, describe changes to HMS files, whether the operation clones or edits in place, and backup behavior.

Use numbered steps for sequences, with one main action per step. A mechanics-focused page can show how to set a parameter and link to HEC's discussion of how to select it. Do not invent a default engineering recommendation merely to complete the tutorial. Separate a documented API default from a hydrologically suitable value for a user's model.

### API docstrings and schemas

Keep the library's Google-style docstring convention (`Args:`, `Returns:`, `Raises:`, `Example:`) described in `STYLE_GUIDE.md`. A public method's summary must state its operation accurately. Document consequential parameters and returns with units, DataFrame columns or dictionary keys, defaults, and missing-data handling. Describe file mutation, written artifacts, backup policy, HEC-HMS version limits, and exceptions when applicable.

Parameter and return names must match the implementation. DataFrame column contracts belong in `hms_commander/schemas.py`; link to them rather than maintaining a divergent list. Code examples must use real APIs and repository conventions.

### Notebooks and generated text

Review explanatory Markdown cells and prose around operations. Describe the purpose before code and interpret the relevant result after it. State whether outputs are retained from a recorded run. Do not alter saved output, run times, images, or completion messages to satisfy a style preference. Read `examples/AGENTS.md` and `.claude/rules/documentation/notebook-standards.md` before editing notebooks. For generated pages, update the generating source.

### Figures, maps, tables, and equations

Introduce a visual near the statement it supports and explain the conclusion the reader can draw. Label quantity, units, element, event, time window, and spatial reference where consequential. Hydrographs and hyetographs need axis units, time basis, and whether values are incremental or cumulative. Provide alt text or a nearby textual explanation; do not rely solely on color.

Introduce an equation, define its symbols and units, state assumptions, and cite its source. Distinguish a governing equation from a library transformation. Reproduced figures and substantial excerpts require provenance and applicable rights review.

### Diagnostics, comments, release notes, and agent skills

Messages should state the condition and consequence and give an available next action. A message claiming that a file was written, cloned, or a run completed must correspond to the actual code path. Preserve machine-consumed tokens and quoted HEC-HMS log messages. A wording change in an exception or log is a compatibility decision if consumers depend on it.

Comments should explain a constraint, reason, or non-obvious behavior. Release notes should name the changed behavior, affected scope, and migration requirements. Agent skills and rules are repository content: their claims about APIs, file paths, and behavior must match the current source.

### Mechanics

Use US spelling for authored prose, sentence-case headings, and parallel list grammar. Preserve source titles, personal names, citation forms, literal UI text, and legal language. Favor concrete verbs and one main idea per paragraph. Avoid filler, repeated importance claims, promotional comparisons, and decorative emoji in technical prose. Sentence length, dashes, bold lead-ins, and list length are review prompts, not automatic failures.

## Citations and acknowledgment

For ordinary web guides and docstrings, use a descriptive link near the supported claim, naming the manual, version, and section where relevant. For substantial reports or methods pages, add a reference list with author or institution, publication date or `n.d.` if genuinely unavailable, exact title, version or report identifier, section locator, official URL or DOI, and access date for mutable web content. A submission's venue requirements take precedence for its formatting.

Do not invent an author, publication year, report number, page, or DOI. Prefer the bibliographic identity printed in the document. Distinguish an official landing page from a directly inspected full document.

Example of a passive topic reference:

> For the method description, see the HEC-HMS Technical Reference Manual, [Frequency Storm](https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/meteorology/precipitation/frequency-storm).

Example of a reference entry with known metadata:

> U.S. Army Corps of Engineers, Hydrologic Engineering Center. n.d. *HEC-HMS Technical Reference Manual*, "Frequency Storm." Official online documentation. Accessed October 6, 2026. [Official section](https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/meteorology/precipitation/frequency-storm).

The date is `n.d.` because the page does not establish a publication date; the access date is not a publication date. Select the version appropriate to the feature being documented.

HEC should receive appropriate acknowledgment for the software, methods, and documentation used. Third-party methods, code, datasets, and figures (for example, NOAA Atlas 14 tables, TP-40 patterns, Texas empirical hyetographs, and code adapted from `ras-commander`) need traceable attribution, including the source repository, file, and revision for adapted code and applicable license requirements.

## Editing and auditing

Read the applicable `AGENTS.md`, select the surface and register, and identify the authored source. Review factual and technical meaning before mechanics. Consult the applicable official HEC source and implementation records for consequential claims. If sources conflict or are unavailable, report the uncertainty and needed evidence rather than guessing.

Protected content includes code identifiers, paths, flags, HMS file keywords, DataFrame columns, DSS pathnames, UI literals, quotations, program output, formulas, numbers, signs, unit strings, hashes, citations, licenses, and saved notebook results. A confirmed defect may require correction, but that is an explicit technical change with evidence and review.

Use the shared `technical-writing-auditor` skill to review a diff, selected surface, or declared broader corpus. Broad audits must report actual files and surfaces reviewed and sampling limits. An unexamined file is not a passing file. Report confirmed defects separately from unresolved technical questions and editorial suggestions.

An editorial review does not grant merge or deploy authority or certify a model, a method, or professional engineering acceptance.

## Source selection and adaptation

This standard was adapted from the RAS Commander technical writing standard (gpt-cmdr/ras-commander, `.claude/references/writing/`, October 2026) and maintained here as an independent copy. HEC-RAS-specific terminology (water surface elevation, cross sections, RAS Mapper, plan and geometry files) was replaced with HEC-HMS hydrologic terminology and file types. The editorial sources below were reviewed for that standard; their scope determines their authority.

| Source | Choice for HMS Commander |
|---|---|
| [HEC-HMS documentation portal](https://www.hec.usace.army.mil/confluence/hmsdocs) and [software documentation page](https://www.hec.usace.army.mil/software/hec-hms/documentation.aspx) (both resolved October 6, 2026) | Route HEC-HMS questions to the applicable Technical Reference Manual, User's Manual, or release notes |
| [HEC-HMS Frequency Storm](https://www.hec.usace.army.mil/confluence/hmsdocs/hmstrm/meteorology/precipitation/frequency-storm) | Retain design-storm terminology; do not assume rainfall and discharge AEP are equal |
| NASA KSC-DF-107 Rev F, *Technical Documentation Style Guide* | Borrow consistency, reader-aware prose, modal clarity, and informative visuals; its layout and dual-unit order do not govern library docs |
| ASCE *Standards Writing Manual for ASCE Standards Committees* (2019) | Borrow clear obligations; omit committee structure and mandatory dual units |
| USACE EP 25-40-1, *Publishing Program Procedures* | Borrow audience awareness and plain language; omit Corps approval and institutional voice |
| ASD-STE100 Simplified Technical English, Issue 9 | Adapt procedural clarity and consistent terms; no claim of full STE compliance |
| NIST SP 811, chapter 7 | Use unit spacing; document the local `1% AEP` typography choice |

This standard complements HEC documentation with library-specific operations, source discipline, and evidence-aware writing. It makes no claim that HEC, NASA, ASCE, USACE, or ASD has reviewed or endorsed these editorial choices.
