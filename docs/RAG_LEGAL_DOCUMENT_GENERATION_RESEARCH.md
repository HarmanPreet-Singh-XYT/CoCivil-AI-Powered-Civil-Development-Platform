# RAG & AI for Legal/Regulatory Document Generation: Comprehensive Research

**Date:** 2026-03-07
**Purpose:** Architecture-informing research for AI-assisted generation of government submission documents for land development (planning rationales, zoning analyses, etc.)

---

## Table of Contents

1. [RAG Architecture for Legal Documents](#1-rag-architecture-for-legal-documents)
2. [Hallucination Prevention in Legal Context](#2-hallucination-prevention-in-legal-context)
3. [Human-in-the-Loop for Legal AI](#3-human-in-the-loop-for-legal-ai)
4. [Existing Products and Approaches](#4-existing-products-and-approaches)
5. [Regulatory Considerations (Ontario/Canada)](#5-regulatory-considerations-ontariocanada)
6. [Technical Implementation Patterns](#6-technical-implementation-patterns)
7. [Recommended Architecture](#7-recommended-architecture-for-our-system)

---

## 1. RAG Architecture for Legal Documents

### 1.1 Why RAG is Well-Suited for Legal Work

Legal tasks are particularly well suited to RAG because of the availability of high-quality databases of statutes, cases, regulations, bylaws, and policy documents. Unlike conventional LLMs whose expensive training process limits the frequency of introducing new knowledge, RAG vector databases can be updated frequently as bylaws and policies change.

**Key advantages for our use case:**
- Bylaws, Official Plans, and Provincial Policy Statements change regularly; RAG databases can be updated without retraining
- Every claim in a generated document can be traced back to a specific source document and section
- The system retrieves from a known, bounded corpus (municipal bylaws, provincial policies) rather than the open internet

**Source:** [Harvard JOLT - RAG for Legal Work](https://jolt.law.harvard.edu/digest/retrieval-augmented-generation-rag-towards-a-promising-llm-architecture-for-legal-work)

### 1.2 Embedding Models for Legal/Regulatory Text

**Recommended approach: Hybrid retrieval combining dense + sparse methods**

| Model | Strengths | Legal Suitability |
|-------|-----------|-------------------|
| **BGE-M3** | Supports 100+ languages, generates both dense AND sparse embeddings simultaneously, handles long contexts | Excellent for hybrid search on legal text; critical for bilingual Canadian documents |
| **E5-Base-v2** | Strong accuracy (83-85%), reasonable latency, no prefix prompts needed | Good general-purpose option |
| **Legal-BERT** | Pre-trained on legal corpora, understands specialized vocabulary ("force majeure", "easement", "setback") | Best semantic understanding of legal terms |
| **BGE-Large-en-v1.5** | High accuracy on MTEB benchmark, handles long sequences | Strong performer for English-only corpora |

**Recommendation for our system:** Use BGE-M3 for hybrid search (dense + sparse) as the primary retrieval model. Consider fine-tuning on a corpus of Ontario planning documents, bylaws, and Official Plans to improve domain-specific retrieval.

**Sources:**
- [Zilliz - Embedding Models for Legal Documents](https://zilliz.com/ai-faq/what-embedding-models-work-best-for-legal-documents)
- [John Snow Labs - Legal NLP E5 and BGE Models](https://www.johnsnowlabs.com/legal-nlp-releases-e5-and-bge-sentence-embedding-models-and-two-subpoena-demo-apps/)

### 1.3 Chunking Strategy for Bylaws and Policy Documents

**Critical insight:** Legal documents have legally significant structure. Clauses must stay intact. Cross-references are pervasive. Splitting a zoning provision across chunks destroys its meaning.

**Recommended approach: Hierarchical + Semantic Chunking**

1. **Document-aware parsing first:** Parse bylaws and Official Plans using their inherent structure (Parts, Sections, Subsections, Clauses)
2. **Recursive chunking:** Apply splitting rules hierarchically -- first by sections, then paragraphs, finally sentences -- until chunks fit size limits
3. **Chunk size:** Start with 512 tokens with 50-100 token overlap (10-20% overlap)
4. **Preserve cross-references:** When a section references another section (e.g., "Subject to Section 4.3.2"), include the referenced section as metadata or linked context
5. **Maintain hierarchy metadata:** Each chunk should carry metadata about its position in the document hierarchy (e.g., `Zoning Bylaw > Part 4 > Section 4.3 > Subsection 4.3.2`)

**For zoning bylaws specifically:**
- Keep entire zoning provisions as single chunks where possible (a single zone's permitted uses, height limits, setbacks)
- Use parent-child relationships: a chunk about "R4 Zone permitted uses" should link to its parent "Part 4: Residential Zones"
- Sliding window overlap ensures cross-clause context is preserved

**Sources:**
- [Weaviate - Chunking Strategies for RAG](https://weaviate.io/blog/chunking-strategies-for-rag)
- [Unstructured - Chunking Best Practices](https://unstructured.io/blog/chunking-for-rag-best-practices)
- [Microsoft Azure - RAG Chunking Phase](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-chunking-phase)

### 1.4 Handling Cross-References Between Documents

**This is a critical challenge for planning documents.** A planning rationale must cross-reference:
- Municipal Zoning Bylaw
- Official Plan policies
- Provincial Policy Statement (PPS)
- Growth Plan for the Greater Golden Horseshoe
- Potentially: Secondary Plans, Community Design Plans, Site Plan guidelines

**Recommended approach: Graph RAG / Knowledge Graph Layer**

Recent research (2025) on ontology-driven Graph RAG for legal norms provides an excellent architectural model:

1. **Multi-layered knowledge graph:**
   - **Norm nodes:** Abstract documents (e.g., "City of Ottawa Zoning Bylaw 2008-250")
   - **Component nodes:** Hierarchical elements (Parts, Sections, Articles) maintaining identity across amendments
   - **Temporal Version nodes:** Snapshots at specific points in time (critical as bylaws are amended)
   - **Text Unit nodes:** Actual text attached to specific versions

2. **Cross-document thematic communities:** Link Theme nodes (e.g., "building height", "lot coverage", "parking requirements") to relevant Components across multiple documents (Bylaw + Official Plan + PPS)

3. **Scoped vector search:** Users select an entry point (a theme or specific provision), the system traverses the graph to gather all related provisions across documents, then performs semantic search only on this pre-filtered subset

4. **Temporal handling:** When a bylaw is amended, new Temporal Versions are created only for changed components. Parent components aggregate the latest child versions. This enables deterministic point-in-time retrieval.

**Source:** [Ontology-Driven Graph RAG for Legal Norms](https://arxiv.org/html/2505.00039v5)

---

## 2. Hallucination Prevention in Legal Context

### 2.1 The Scale of the Problem

**The Stanford study (2025) is the definitive reference here:**

- **Lexis+ AI** hallucinated 17% of the time
- **Westlaw AI-Assisted Research** hallucinated 33% of the time
- **GPT-4 (raw)** hallucinated 43% of the time

RAG reduces but does NOT eliminate hallucinations. For a high-stakes document like a planning rationale submitted to a municipality, even 17% is unacceptable.

The study identified two dimensions of hallucination:
1. **Correctness:** Is the factual content accurate?
2. **Groundedness:** Does the response actually match what the cited sources say?

A response can cite a real bylaw section but misstate what it says (grounded but incorrect) or state a true fact but attribute it to the wrong source (correct but ungrounded).

**Sources:**
- [Stanford HAI - AI on Trial: Legal Models Hallucinate](https://hai.stanford.edu/news/ai-trial-legal-models-hallucinate-1-out-6-or-more-benchmarking-queries)
- [Stanford Legal RAG Hallucinations Study](https://law.stanford.edu/publications/hallucination-free-assessing-the-reliability-of-leading-ai-legal-research-tools/)

### 2.2 Five-Layer Hallucination Prevention Strategy

For our system, we need MULTIPLE layers of defense:

#### Layer 1: Constrained Retrieval Scope
- Only retrieve from our verified, curated corpus of bylaws, Official Plans, and policy documents
- Never allow the LLM to use its parametric knowledge for factual claims about zoning or policy
- Every factual statement must be grounded in a retrieved chunk

#### Layer 2: Citation-Grounded Generation (Architectural Constraint)
- Require the LLM to cite specific source chunks for every factual claim
- Use inline citation markers (e.g., `<c>doc_id.chunk_id</c>`) during generation
- The LLM literally cannot cite documents it hasn't retrieved -- this is hallucination prevention through architectural constraint rather than probabilistic detection

**Implementation pattern:**
```
Prompt: "For every factual claim about zoning provisions, setbacks, permitted uses,
or policy compliance, you MUST include a citation in the format [SOURCE: document_name,
section_number]. If you cannot find a source for a claim, state 'UNVERIFIED' instead."
```

#### Layer 3: NLI-Based Post-Generation Verification
- After generation, use a Natural Language Inference (NLI) model to verify each claim
- For each generated sentence with a citation, check whether the cited source actually ENTAILS the claim
- Classify each claim as: **Grounded** (source supports claim), **Misgrounded** (source cited but doesn't support), or **Ungrounded** (no citation)
- Flag misgrounded and ungrounded claims for human review

#### Layer 4: Automated Fact Checks
- **Number verification:** Cross-check all numbers (setbacks, heights, densities, FAR) against source documents
- **Section reference verification:** Verify that cited bylaw sections actually exist and contain what's claimed
- **Consistency checking:** Ensure the document doesn't contradict itself

#### Layer 5: Human Review (see Section 3)

**Sources:**
- [Anytime AI - 5 Ways to Prevent AI Hallucination in Legal AI](https://www.anytimeai.ai/blog/5-ways-to-prevent-ai-hallucination-in-legal-ai/)
- [NCSC - Legal Practitioner's Guide to AI & Hallucinations](https://www.ncsc.org/resources-courts/legal-practitioners-guide-ai-hallucinations)
- [PrefixNLI: Detecting Factual Inconsistencies](https://arxiv.org/abs/2511.01359)

### 2.3 Citation Chain Implementation

**The gold standard: Every sentence in the generated document must trace back to a source.**

Technical implementation pattern from Tensorlake's citation-aware RAG:

1. **At index time:** Extract spatial metadata (page numbers, section numbers) alongside text. Insert lightweight citation anchors within chunk text.
2. **At retrieval time:** Standard retrieval -- no modification needed.
3. **At generation time:** LLM receives chunks with anchors and is instructed to preserve citation IDs in output.
4. **Post-generation:** Citation IDs are resolved to specific document locations (document name, page, section, paragraph).

```json
{
  "generated_claim": "The subject property is zoned R4 which permits a maximum building height of 14.5 metres",
  "citations": ["zoning_bylaw_2008-250.section_164.3"],
  "verification_status": "GROUNDED",
  "nli_confidence": 0.94,
  "source_text": "In the R4 Zone, no building shall exceed a height of 14.5 metres"
}
```

**Sources:**
- [Tensorlake - Citation-Aware RAG](https://www.tensorlake.ai/blog/rag-citations)
- [LLMWare - Automated Source Citation Verification](https://llmware.ai/resources/techniques-for-automated-source-citation-verification-for-rag)
- [LlamaIndex - Citation Query Engine](https://developers.llamaindex.ai/python/examples/workflow/citation_query_engine/)

---

## 3. Human-in-the-Loop for Legal AI

### 3.1 When Human Review is REQUIRED vs. Optional

**REQUIRED (non-negotiable):**
- Final review of any document before submission to a municipality or tribunal
- Any section where the system flags low confidence or ungrounded claims
- Legal conclusions and professional opinions (e.g., "the proposed development conforms with the Official Plan")
- Any novel or unusual planning arguments
- Cross-referencing of all cited bylaw sections and policy provisions

**OPTIONAL (but recommended):**
- Review of factual descriptions of the site and surrounding area
- Verification of standard boilerplate language
- Review of formatting and document structure

### 3.2 Professional Liability Framework

**Key principle: Liability flows upward to the humans and organizations that deployed the AI.**

Courts assess:
1. Whether professionals understood AI limitations before relying on outputs
2. Whether effective oversight involved meaningful human review (not rubber-stamping)
3. Whether professional liability standards were met regardless of AI involvement

**For planning professionals:** A Registered Professional Planner (RPP) who signs off on an AI-assisted planning rationale bears the same professional responsibility as if they wrote it entirely themselves. The AI tool is a productivity aid, not a shield from liability.

**Practical implication for our system:** The product must be positioned as a drafting tool that creates a first draft for professional review, NOT as an autonomous document generator.

### 3.3 Recommended Workflow

```
1. INTAKE: User provides property details, development proposal, applicable bylaws
     |
2. RETRIEVAL: System retrieves relevant bylaw sections, OP policies, PPS provisions
     |
3. OUTLINE GENERATION: AI generates document outline with section headings
     |  --> Human reviews/adjusts outline
4. SECTION-BY-SECTION DRAFTING: AI drafts each section with inline citations
     |
5. AUTOMATED VERIFICATION: NLI checks, number verification, citation verification
     |  --> Low-confidence sections flagged in yellow/red
6. HUMAN REVIEW: Professional planner reviews entire document
     |  --> Especially flagged sections
     |  --> Verifies all citations against source documents
     |  --> Adds professional opinion and judgment
7. FINALIZATION: Human approves, signs off, adds professional stamp
```

### 3.4 Required Disclaimers

Based on research across multiple jurisdictions, the system should:

1. **Internal disclaimer (shown to the planner/user):**
   "This document was generated with AI assistance and requires professional review. All citations, factual claims, and professional opinions must be independently verified before submission. [Your firm name] retains full professional responsibility for the accuracy of submitted documents."

2. **Submission disclaimer (on the document itself, as required by OLT):**
   "Artificial intelligence (AI) was used to assist in preparing this document. All AI-generated content has been reviewed and verified by [Name], RPP, [License Number]."

**Sources:**
- [LITL Framework - Lawyer-In-The-Loop](https://theformtool.com/the-lawyer-in-the-loop-litl-the-new-professional-standard-for-ai-in-legal-work/)
- [Strata.io - Human-in-the-loop Legal Liability](https://www.strata.io/blog/agentic-identity/humans-ai-legal-liability/)
- [TechLifeFuture - AI Liability 2026](https://www.techlifefuture.com/ai-liability-professional-services/)

---

## 4. Existing Products and Approaches

### 4.1 Legal AI Document Generation Tools

#### Harvey AI
- **Approach:** Uses law firms' approved legal templates, populates with case-specific facts and legal arguments
- **Technical:** Partnered with OpenAI for custom-trained case law model; every sentence is supported with cited cases
- **Safeguards:** Advanced encryption, enterprise-level security, full audit trails, mandatory human verification
- **Key insight:** "You must validate everything coming out of the system. You have to check everything."
- **Source:** [Harvey AI](https://www.harvey.ai/) | [Harvey AI Policy](https://www.harvey.ai/legal/ai-policy)

#### Spellbook (formerly Rally)
- **Approach:** AI copilot for contract drafting, operates within Microsoft Word
- **Technical:** Uses proprietary document corpus for fine-tuning + few-shot examples + prompt engineering on top of GPT-4o
- **Key insight:** Started with document templating (Rally, 2017), then layered AI on top -- suggests template-first approach is sound
- **Source:** [Spellbook](https://www.spellbook.legal/)

#### Casetext (CoCounsel, acquired by Thomson Reuters)
- **Approach:** RAG-based legal research + document drafting
- **Safeguards:** Citations linked to primary sources; attorney verification required

### 4.2 PropTech / Planning-Adjacent Tools

#### TestFit
- **Focus:** Automated site planning, feasibility analysis, building layout optimization
- **Approach:** Generative AI for real-time building layouts based on zoning parameters (setbacks, density, parking, FAR)
- **Scale:** 650 feasibility runs per week
- **Limitation:** Does NOT generate planning rationale documents; focuses on design feasibility
- **Source:** [TestFit](https://www.testfit.io/news/testfit-launches-groundbreaking-generative-design-for-better-building-optimization)

#### Archistar
- **Focus:** Site analysis, feasibility studies, AI-driven design generation
- **Approach:** ML algorithms analyze site conditions, zoning regulations, and market data
- **Scale:** 11 million+ generated designs
- **Notable:** Partnered with City of Burlington, Ontario for zoning compliance automation
- **Source:** [Archistar](https://www.archistar.ai/)

#### Deepblocks
- **Focus:** Financial viability studies, zoning data
- **Approach:** Digitized zoning for 16.4 million parcels; merges zoning data with financial modeling
- **Limitation:** Does NOT generate narrative planning documents

#### Plotzy
- **Focus:** AI-powered parcel and zoning search/research
- **Approach:** Automated zoning code interpretation and report generation
- **Source:** [Plotzy](https://plotzy.ai/)

#### Zenerate
- **Focus:** AI feasibility studies for land development
- **Source:** [Zenerate](https://www.zenerate.ai/)

### 4.3 Burlington, Ontario Case Study (Directly Relevant)

The City of Burlington collaborated with Archistar to develop AI tools for planning:
- Integrated local zoning bylaws AND the Ontario Building Code
- Focused on industrial buildings in zones BC1, GE1, GE2
- Automated zoning features: setbacks, heights, parking ratios
- Four-phase approach: (1) Review submissions to understand complexities, (2) Develop standardized assessment template, (3) Build compliance engine, (4) Automate assessment

**Key takeaway:** Even the most advanced municipal AI tools focus on compliance CHECKING, not document GENERATION. Our product would be differentiated by generating the actual planning rationale document.

**Source:** [Burlington City Report BDS-04-24](https://burlingtonpublishing.escribemeetings.com/filestream.ashx?DocumentId=80449)

### 4.4 Gap in the Market

No existing product generates complete planning rationale documents or development application narratives. Current tools focus on:
- Zoning compliance checking (Archistar, Plotzy)
- Feasibility analysis (TestFit, Deepblocks, Zenerate)
- Legal contract drafting (Harvey, Spellbook)
- Legal research (Casetext, Lexis+)

**Our product fills the gap between zoning analysis tools and legal document drafters.**

---

## 5. Regulatory Considerations (Ontario/Canada)

### 5.1 Ontario Land Tribunal (OLT) AI Practice Direction -- CRITICAL

**Effective March 30, 2026** -- This is imminent and directly affects our product.

**Key requirements:**
1. **Mandatory disclosure:** Parties must disclose AI use to create or generate content in documents filed with the Tribunal
2. **Declaration format:** "Artificial intelligence (AI) was used to generate content in this document [at paragraphs x to y]. All content generated by AI, and the authenticity of all authorities cited in this document, has been reviewed and verified by [name of party/representative]."
3. **Verification obligation:** All AI-generated content must be reviewed and verified by a named individual
4. **Enforcement:** Inaccurate/misleading AI-generated material may be struck from the record; non-compliance can trigger cost awards; false declarations constitute unreasonable conduct
5. **Exception:** No declaration needed when AI merely suggests edits that humans independently implement

**Implication for our product:** We MUST build in functionality to generate the required OLT AI declaration. We should also track which paragraphs are AI-generated vs. human-written to support the "at paragraphs x to y" requirement.

**Source:** [OLT AI Practice Direction](https://olt.gov.on.ca/wp-content/uploads/AI-Practice-Direction.html) | [OLT Blog Announcement](https://olt.gov.on.ca/blog/news/ai-declaration-requirement-advance-notice/)

### 5.2 Ontario Rules of Civil Procedure (O. Reg. 384/24)

Ontario Regulation 384/24 requires every lawyer filing a factum to certify the authenticity of every authority cited. While this applies to court filings specifically, it establishes the principle that AI-generated citations must be independently verified.

**Source:** [Osler - AI in Canadian Courts](https://www.osler.com/en/insights/updates/artificial-advocacy-how-canadian-courts-and-legislators-are-responding-to-generative-ai/)

### 5.3 Ontario's Trustworthy AI Framework

Ontario is the first Canadian province to establish guardrails for responsible AI use in the public sector, setting requirements for risk management, disclosure, and accountability.

**Source:** [Ontario Trustworthy AI Framework](https://www.ontario.ca/page/ontarios-trustworthy-artificial-intelligence-ai-framework)

### 5.4 Federal AI Regulation (AIDA / Bill C-27)

**Status as of March 2026:** Bill C-27 died when Parliament was prorogued in January 2025. After the April 2025 federal election, Minister Evan Solomon confirmed AIDA will NOT return in its original form. Canada currently has NO federal AI legislation -- still running on PIPEDA (2000).

The government has signaled a "light, tight, right" approach to future AI regulation. This means our product currently faces no federal AI-specific regulatory requirements, but this will likely change.

**Source:** [AIDA Companion Document](https://ised-isde.canada.ca/site/innovation-better-canada/en/artificial-intelligence-and-data-act-aida-companion-document) | [White & Case - AI Watch Canada](https://www.whitecase.com/insight-our-thinking/ai-watch-global-regulatory-tracker-canada)

### 5.5 Law Society of Ontario Guidance

The LSO's April 2024 White Paper on Licensee Use of Generative AI establishes:
- Lawyers must verify all AI-generated information for accuracy before use or submission
- AI-generated output is the lawyer's professional responsibility
- Client consent to AI use is recommended but "not a panacea"
- Key risks: confidentiality breaches, hallucinations, bias, unauthorized practice of law
- Firms must develop overarching AI governance policies

**Source:** [LSO White Paper (PDF)](https://lawsocietyontario-dwd0dscmayfwh7bj.a01.azurefd.net/media/lso/media/lawyers/practice-supports-resources/white-paper-on-licensee-use-of-generative-artificial-intelligence-en.pdf) | [Osler Summary](https://www.osler.com/en/insights/updates/law-society-of-ontario-publishes-guidance-for-licensees-with-respect-to-the-use-of-generative-ai/)

### 5.6 Canadian Bar Association Guidelines

The CBA's "Ethics of Artificial Intelligence for the Legal Practitioner" (2024) establishes:
- **Mandatory verification:** All AI-generated content must be tested, verified, and validated before use
- **Disclosure to clients:** Lawyers should disclose AI use and explain how it will be used
- **Competence:** Lawyers need not understand AI technically but MUST understand its risks
- **Confidentiality:** Never input client information into free commercial AI systems
- **Bias screening:** Results must be screened for discriminatory outputs
- **Prohibition:** Cannot delegate core legal judgment to AI

**Source:** [CBA Ethics of AI](https://www.cba.org/resources/practice-tools/ethics-of-artificial-intelligence-for-the-legal-practitioner/) | [CBA Guidelines Relating to Use](https://www.cba.org/resources/practice-tools/ethics-of-artificial-intelligence-for-the-legal-practitioner/3-guidelines-relating-to-use/)

### 5.7 OPPI (Ontario Professional Planners Institute) Position

OPPI acknowledges AI tools can assist planners with:
- Generating rough first drafts of planning documents for review and refinement
- Creating standard responses for public engagement
- Summarizing community input during consultation

**OPPI's key position:** "ChatGPT will not replace human planners but rather can be used as a tool to assist them." Planners must "always use AI tools in conjunction with their own expertise and judgement."

**Identified risks:** Bias, lack of accountability, transparency limitations, security, job displacement, unexplainability.

**Source:** [OPPI - AI and Urban/Regional Planning](https://ontarioplanners.ca/inspiring-knowledge/case-studies/case-studies/artificial-intelligence-and-urban-and-regional-planning-opportunity,-threat,-or-both)

### 5.8 Professional Liability Summary

| Entity | Position |
|--------|----------|
| Ontario Land Tribunal | Mandatory AI disclosure effective March 30, 2026; verification required |
| Law Society of Ontario | Professional responsibility unchanged; must verify all AI output |
| Canadian Bar Association | Cannot delegate legal judgment to AI; must verify everything |
| OPPI | AI as a tool to assist planners, not replace them |
| Federal (AIDA) | No current legislation; future "light, tight, right" approach |

**Bottom line:** The professional who signs the document bears full liability regardless of AI involvement. Our product must be designed and marketed as a professional drafting tool, not an autonomous document generator.

---

## 6. Technical Implementation Patterns

### 6.1 Template-Based vs. Free-Form Generation

**Strong recommendation: Template-based with AI-assisted section filling.**

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **Template-based** | Consistent structure, format compliance, predictable output, easier verification | Less flexible, requires template development | **RECOMMENDED** |
| **Free-form AI** | More flexible, handles novel situations | Unpredictable structure, harder to verify, format inconsistencies | Not suitable for legal documents |
| **Hybrid** | Template structure with AI-generated content per section | Best of both worlds; requires careful prompt engineering | **BEST APPROACH** |

**For planning rationales, the hybrid approach works like this:**
1. Define a document template with required sections (e.g., Site Description, Planning Context, Official Plan Analysis, Zoning Analysis, PPS Conformity, Planning Opinion)
2. For each section, AI generates content grounded in retrieved documents
3. Each section has its own retrieval scope (e.g., "Zoning Analysis" retrieves from the Zoning Bylaw; "Official Plan Analysis" retrieves from the OP)
4. Output is constrained to match the expected format for that section type

### 6.2 Multi-Stage Generation Pipeline

**Recommended: Compiler-style multi-stage pipeline**

```
Stage 1: INTAKE & ANALYSIS
  Input:  Property address, development proposal, municipality
  Output: Structured data (zoning, OP designation, applicable policies)

Stage 2: RETRIEVAL & ASSEMBLY
  Input:  Structured data from Stage 1
  Output: Retrieved chunks organized by document section
  Process: For each template section, retrieve relevant bylaw/policy chunks

Stage 3: OUTLINE GENERATION
  Input:  Template + retrieved chunks
  Output: Detailed outline with section headings and key points per section
  Review: HUMAN CHECKPOINT -- planner reviews/adjusts outline

Stage 4: SECTION-BY-SECTION DRAFTING
  Input:  Outline + retrieved chunks per section
  Output: Draft text with inline citations
  Constraint: Each section generated independently with its own retrieval context

Stage 5: CROSS-REFERENCE RESOLUTION
  Input:  All drafted sections
  Output: Consistent document with resolved cross-references
  Process: Verify internal consistency, resolve cross-section references

Stage 6: VERIFICATION
  Input:  Complete draft
  Output: Verification report with confidence scores per claim
  Process: NLI checks, number verification, citation verification
  Flag:   Low-confidence sections marked for mandatory human review

Stage 7: HUMAN REVIEW & FINALIZATION
  Input:  Draft + verification report
  Output: Final document
  Process: Professional planner reviews, edits, approves, signs
```

### 6.3 Confidence Scoring Per Section/Claim

Each generated claim should carry a confidence indicator:

```json
{
  "claim": "The property is designated 'General Urban Area' in the Official Plan",
  "confidence": "HIGH",
  "basis": "DIRECTLY_STATED",
  "citation": "Official Plan, Section 3.6.1",
  "source_text_match": 0.95
}
```

**Confidence levels:**
- **HIGH** (green): Claim is directly stated in a retrieved source with high NLI entailment score (>0.9)
- **MEDIUM** (yellow): Claim is reasonably inferred from sources but not directly stated (NLI 0.7-0.9)
- **LOW** (red): Claim has weak source support or relies on inference (NLI <0.7)
- **UNVERIFIED** (red, mandatory review): No source found for this claim

### 6.4 Structured Output with Citation Chains

Each section of the generated document should produce structured output:

```json
{
  "section": "4.2 Zoning By-law Analysis",
  "paragraphs": [
    {
      "text": "The subject property is zoned R4, Residential Fourth Density Zone, under the City of Ottawa Zoning By-law 2008-250.",
      "citations": [
        {
          "document": "Zoning By-law 2008-250",
          "section": "Part 5, Section 164",
          "page": 234,
          "retrieved_chunk_id": "zb_2008_250_chunk_1847",
          "nli_score": 0.97,
          "verification": "GROUNDED"
        }
      ],
      "confidence": "HIGH"
    }
  ]
}
```

### 6.5 Diff Against Reference Documents

For format compliance, the system should:
1. Maintain a corpus of approved/successful planning rationales from each municipality
2. Compare generated document structure against reference documents
3. Flag structural deviations (missing sections, unusual ordering)
4. Score format compliance as a percentage

---

## 7. Recommended Architecture for Our System

### 7.1 High-Level Architecture

```
                    +---------------------+
                    |   User Interface    |
                    | (Property Input,    |
                    |  Document Review)   |
                    +---------------------+
                             |
                    +---------------------+
                    |  Orchestration      |
                    |  Layer (Pipeline    |
                    |  Controller)        |
                    +---------------------+
                        |         |
               +--------+         +--------+
               |                           |
    +-------------------+      +-------------------+
    | Retrieval Layer    |      | Generation Layer  |
    | - Vector DB        |      | - LLM (Claude/    |
    | - Knowledge Graph  |      |   GPT-4o)         |
    | - Hybrid Search    |      | - Template Engine |
    | - Reranker         |      | - Citation Engine |
    +-------------------+      +-------------------+
               |                           |
    +-------------------+      +-------------------+
    | Document Store     |      | Verification      |
    | - Bylaws           |      | Layer             |
    | - Official Plans   |      | - NLI Model       |
    | - PPS / Growth     |      | - Number Check    |
    |   Plan             |      | - Citation Verify |
    | - Reference Docs   |      | - Confidence Score|
    +-------------------+      +-------------------+
```

### 7.2 Technology Stack Recommendations

| Component | Recommended Technology | Rationale |
|-----------|----------------------|-----------|
| **Vector DB** | Weaviate or Qdrant | Both support hybrid search (dense + sparse); Weaviate has built-in multi-tenancy for per-municipality data |
| **Knowledge Graph** | Neo4j | Mature graph DB; excellent for cross-reference traversal; GraphRAG support |
| **Embedding Model** | BGE-M3 (primary) + domain-fine-tuned variant | Hybrid search, long context support, bilingual capability |
| **LLM** | Claude Opus / GPT-4o | Best reasoning for legal/policy analysis; structured output support |
| **NLI Model** | DeBERTa-v3-large-mnli or fine-tuned variant | High accuracy for entailment checking |
| **Reranker** | Cohere Rerank or BGE-Reranker | Improves retrieval precision for legal text |
| **Document Parser** | Unstructured.io or LlamaParse | Structure-aware parsing of PDF bylaws and Official Plans |
| **Orchestration** | LangGraph or custom pipeline | Multi-stage pipeline with human checkpoints |

### 7.3 Key Design Principles

1. **Every claim must have a source.** No exceptions. If the system cannot ground a claim in a retrieved document, it must say so explicitly.

2. **Template-first, AI-assisted.** Use document templates that mirror approved planning rationale formats. AI fills sections, not structures.

3. **Multi-stage with checkpoints.** Generation happens in stages with verification at each stage, not as a single pass.

4. **Transparency by default.** Every output includes its citation chain, confidence scores, and verification status. The professional reviewer can see exactly what the AI is confident about and what needs scrutiny.

5. **Audit trail.** Log every retrieval, every generation, every verification check. This supports both professional liability defense and OLT disclosure requirements.

6. **Municipal-specific configuration.** Different municipalities have different bylaw structures, Official Plan formats, and submission requirements. The system must be configurable per municipality.

7. **Temporal awareness.** Bylaws are amended frequently. The system must track which version of a bylaw was used and flag when a newer version is available.

### 7.4 Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Hallucinated bylaw provisions | Citation-grounded generation + NLI verification + human review |
| Outdated bylaw references | Temporal version tracking + "last updated" metadata + automated staleness alerts |
| Format non-compliance | Template-based generation + diff against reference documents |
| Professional liability exposure | Clear positioning as drafting tool + mandatory human sign-off + audit trail |
| OLT non-compliance | Built-in AI declaration generation + paragraph-level AI tracking |
| Misinterpreted cross-references | Knowledge graph for cross-document relationships + scoped retrieval |

---

## Sources Index

### Academic / Research
- [Harvard JOLT - RAG for Legal Work](https://jolt.law.harvard.edu/digest/retrieval-augmented-generation-rag-towards-a-promising-llm-architecture-for-legal-work)
- [Stanford - Legal RAG Hallucinations Study](https://law.stanford.edu/publications/hallucination-free-assessing-the-reliability-of-leading-ai-legal-research-tools/)
- [Ontology-Driven Graph RAG for Legal Norms](https://arxiv.org/html/2505.00039v5)
- [ScienceDirect - Enhancing Legal Document Building with RAG](https://www.sciencedirect.com/science/article/pii/S2212473X25001014)
- [PrefixNLI: Detecting Factual Inconsistencies](https://arxiv.org/abs/2511.01359)
- [CaLM: Contrasting LLMs for Grounded Generation Verification](https://arxiv.org/pdf/2406.05365)

### Regulatory / Government
- [Ontario Land Tribunal AI Practice Direction](https://olt.gov.on.ca/wp-content/uploads/AI-Practice-Direction.html)
- [Ontario Trustworthy AI Framework](https://www.ontario.ca/page/ontarios-trustworthy-artificial-intelligence-ai-framework)
- [AIDA Companion Document](https://ised-isde.canada.ca/site/innovation-better-canada/en/artificial-intelligence-and-data-act-aida-companion-document)
- [Legal Aid Ontario - 2026 AI Compliance](https://www.legalaid.on.ca/in-briefs/2025-12-12_2026-update-to-lawyer-self-report-ai-compliance-confirmation/)

### Professional Bodies
- [LSO White Paper on Generative AI](https://lawsocietyontario-dwd0dscmayfwh7bj.a01.azurefd.net/media/lso/media/lawyers/practice-supports-resources/white-paper-on-licensee-use-of-generative-artificial-intelligence-en.pdf)
- [CBA Ethics of AI for Legal Practitioners](https://www.cba.org/resources/practice-tools/ethics-of-artificial-intelligence-for-the-legal-practitioner/)
- [CBA Guidelines Relating to Use](https://www.cba.org/resources/practice-tools/ethics-of-artificial-intelligence-for-the-legal-practitioner/3-guidelines-relating-to-use/)
- [OPPI - AI and Urban/Regional Planning](https://ontarioplanners.ca/inspiring-knowledge/case-studies/case-studies/artificial-intelligence-and-urban-and-regional-planning-opportunity,-threat,-or-both)
- [Law Society of Alberta - Gen AI Rules](https://www.lawsociety.ab.ca/resource-centre/key-resources/professional-conduct/gen-ai-rules-of-engagement-for-canadian-lawyers/)

### Industry / Products
- [Harvey AI](https://www.harvey.ai/) | [AI Policy](https://www.harvey.ai/legal/ai-policy)
- [Spellbook](https://www.spellbook.legal/)
- [TestFit](https://www.testfit.io/)
- [Archistar](https://www.archistar.ai/)
- [Plotzy](https://plotzy.ai/)
- [Zenerate](https://www.zenerate.ai/)

### Technical Implementation
- [Tensorlake - Citation-Aware RAG](https://www.tensorlake.ai/blog/rag-citations)
- [LLMWare - Source Citation Verification](https://llmware.ai/resources/techniques-for-automated-source-citation-verification-for-rag)
- [LlamaIndex - Citation Query Engine](https://developers.llamaindex.ai/python/examples/workflow/citation_query_engine/)
- [Weaviate - Chunking Strategies for RAG](https://weaviate.io/blog/chunking-strategies-for-rag)
- [Unstructured - Chunking Best Practices](https://unstructured.io/blog/chunking-for-rag-best-practices)
- [Zilliz - Embedding Models for Legal Documents](https://zilliz.com/ai-faq/what-embedding-models-work-best-for-legal-documents)
- [John Snow Labs - Legal NLP E5 and BGE](https://www.johnsnowlabs.com/legal-nlp-releases-e5-and-bge-sentence-embedding-models-and-two-subpoena-demo-apps/)
- [Neo4j - RAG on Knowledge Graph Tutorial](https://neo4j.com/blog/developer/rag-tutorial/)
- [Microsoft Azure - RAG Chunking Phase](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/rag/rag-chunking-phase)

### Market / Context
- [Lincoln Institute - AI in City Planning](https://www.lincolninst.edu/publications/land-lines-magazine/articles/could-ai-make-city-planning-more-efficient/)
- [AI-Powered Zoning Tools](https://zweiggroup.com/blogs/news/ai-powered-zoning-tools)
- [Bisnow - AI Zoning Intelligence](https://www.bisnow.com/national/news/proptech/how-ai-powered-zoning-intelligence-services-are-changing-the-acquisition-game-130557)
- [Generative AI for Zoning Acquisition](https://medium.com/urban-ai/generative-ai-for-zoning-acquisition-cd7375684a73)
