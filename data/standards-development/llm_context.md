# Instructions

You are answering questions about HL7 International standards development. Use only the organizational context in this file and the data tables that follow it.

When you answer:

- Cite the indicator name and the time period for every number.
- A blank cell is missing data. It is not zero. A reported zero is written as 0.
- If a measurement note qualifies a value, quote that note with the value. Notes often record data-quality gaps or which ballot cycles fell inside the trimester.
- Annual targets apply to a calendar year. A trimester value is one slice of that year. Say so when you compare them. Respect the target operation: `sum` means add the trimesters in that year; `average` means average them.
- `higher` means a larger value is better. `lower` means a smaller value is better.
- Do not invent indicators, periods, ballot dates, or causes that are not in this prompt.
- If the question cannot be answered from this prompt, say what is missing.

# How time periods work

Dashboard periods use `YYYY-TN`. Reports and counts bucket months this way:

- `T1` is January–April, and includes the January Working Group Meeting.
- `T2` is May–August, and includes the May Working Group Meeting.
- `T3` is September–December, and includes the September Working Group Meeting.

A label that does not match `YYYY-TN`, such as `2026-AllTime`, is a separate snapshot. It is not a fourth trimester.

Ballot-cycle codes in measurement notes, such as `202605` or `202609`, are `YYYYMM` cycle names. They are not trimester labels. A trimester can contain more than one cycle. Use the note's consensus-group counts when a period mixes cycles.

# Organization

HL7 International is a nonprofit that develops healthcare interoperability standards. In April 2013, HL7 made its standards freely available. Before that, access required membership.

In 2022, HL7 created two divisions, Standards Development and Standards Implementation, and hired a Chief Standards Development Officer. Indicators in this prompt are the ones shown on the Standards Development dashboard that produced it. Some are shared with HL7 International.

# FHIR core ballots

This calendar is maintained by hand in `data/standards-development/llm_context.md`. It is not extracted from the indicator tables.

Publication dates and version labels come from the [FHIR publication directory](https://hl7.org/fhir/directory.html). Scope notes come from each version's ballot introduction. Use this list to tell a FHIR core ballot apart from an ordinary implementation-guide ballot.

Measurement notes name the HL7 cycles inside a trimester (`YYYYMM`). The aligned cycle below is the cycle that opens with that publication: a mid-December publication opens the January cycle of the next year, an early-April publication opens the May cycle, and a July or August publication opens the September cycle. A December publication and the Working Group Meeting can fall in different trimesters. The only R6 cycle named in the ballot text is January 2026: the [ballot 3 introduction](https://hl7.org/fhir/6.0.0-ballot3/ballot-intro.html) says the following full ballot was expected in that cycle, and [ballot 4](https://hl7.org/fhir/6.0.0-ballot4/ballot-intro.html) is that publication.

## FHIR R6

R6 is not published as a final release in this list. The current published release in the directory is still FHIR R5 (`5.0.0`, 26 Mar 2023). `6.0.0-snapshot1` (17 Jul 2026, "FHIR R6 Stable (Sept 2026)") is a snapshot, not a ballot.

| Version | Published | Dashboard period | Aligned HL7 cycle | What was balloted |
| --- | --- | --- | --- | --- |
| [6.0.0-ballot1](https://hl7.org/fhir/6.0.0-ballot1/ballot-intro.html) | 2023-12-19 | 2023-T3 | January 2024 (`202401`) | 1st draft. Focused review only, not a full normative ballot. In scope: ActorDefinition, ExampleScenario, GraphDefinition, ImplementationGuide, MessageHeader, Requirements. Comments outside that list were out of scope. |
| [6.0.0-ballot2](https://hl7.org/fhir/6.0.0-ballot2/ballot-intro.html) | 2024-08-13 | 2024-T2 | September 2024 (`202409`) | 2nd draft. Another focused draft ballot of candidate normative content, not the full specification. |
| [6.0.0-ballot3](https://hl7.org/fhir/6.0.0-ballot3/ballot-intro.html) | 2025-04-03 | 2025-T1 | May 2025 (`202505`) | 3rd draft, and the last draft ballot. The ballot introduction said the next ballot, expected in the January 2026 cycle, would be the full mixed normative/trial-use ballot. Review focus included readiness for normative, Additional Resources, Group, RelativeTime, and new or removed resources (DeviceAlert, InsuranceProduct, MolecularDefinition, PersonalRelationship; EvidenceReport removed). |
| [6.0.0-ballot4](https://hl7.org/fhir/6.0.0-ballot4/ballot-intro.html) | 2025-12-18 | Published in 2025-T3; January cycle closes in 2026-T1 | January 2026 (`202601`) | 1st full ballot, and the first normative ballot of R6. The whole specification was balloted as a full normative ANSI standard. The version history calls it "R6 1st Normative Ballot." Substantive changes after this ballot require another ballot. |
| [6.0.0-ballot5](https://hl7.org/fhir/6.0.0-ballot5/ballot-intro.html) | 2026-07-17 | 2026-T2 | September 2026 (`202609`) | 2nd full ballot. Also a normative ballot of the whole specification. The ballot introduction says the implementable content is fully normative: no draft or trial-use content remains. A further full ballot was still expected. |

## Earlier FHIR core ballots

These rows are the other ballot publications in the same directory, not implementation-guide ballots. The path label is the cycle name HL7 published with that package. Where the directory date and the path label disagree, both are shown.

| Version | Directory date | Path label | What was balloted |
| --- | --- | --- | --- |
| 3.2.0 | 2018-04-02 | 2018Jan | Draft for comment. First candidate normative content for R4. |
| 3.3.0 | 2018-04-02 | 2018May | R4 Ballot #1. Mixed normative/trial use. First normative ballot. |
| 3.5.0 | 2018-08-21 | 2018Sep | R4 Ballot #2. Mixed normative/trial use. Second normative ballot. |
| 3.5a.0 | 2018-11-09 | 2018Dec | Special R4 Ballot #3. Normative packages for terminology, conformance, and Observation. |
| 4.1.0 | 2021-03-11 | 2021Mar | R4B Ballot #1. |
| 4.6.0 | 2021-04-15 | 2021May | R5 draft ballot. |
| 5.0.0-ballot | 2022-09-10 | 2022Sep | R5 ballot. R5 (`5.0.0`) was published 26 Mar 2023 as trial use, not as a normative release. |

Cycles that appear in the measurement notes and are absent from these tables are other HL7 ballots. Do not call them FHIR R6 unless this file says so.
