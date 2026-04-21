from textwrap import dedent


TOPIC_DECOMPOSITION_PROMPT = dedent("""
You are decomposing an engineering intelligence topic into researchable subtopics.

Task:
Break the user's topic into a set of focused intelligence collection subtopics.

Requirements:
1. The subtopics must be researchable.
2. The subtopics must help produce an engineering intelligence brief.
3. Prefer decomposition by:
   - technology routes
   - representative cases
   - engineering bottlenecks
   - commercialization progress
   - industry players
   - strategic implications
4. Avoid generic or overlapping subtopics.
5. If the topic is already narrow, keep the decomposition concise.

Output format:
Return a JSON object with this schema:
{
  "topic": "...",
  "subtopics": [
    {
      "title": "...",
      "purpose": "...",
      "priority": "high|medium|low"
    }
  ]
}

User topic:
{topic}
""")


SOURCE_COLLECTION_PROMPT = dedent("""
You are collecting source material for an engineering intelligence task.

Task:
Given a topic and a subtopic, identify what kinds of sources should be collected and what information matters most.

Collection priorities:
1. official company / project / lab / certification sources
2. technical reports or institutional materials
3. high-quality industry media
4. secondary commentary only when needed

When reviewing sources, prioritize extracting:
- technical route
- device or project name
- organization / company
- country or region
- engineering parameters
- deployment method
- maturity stage
- milestone or timeline
- explicit advantages
- explicit limitations

Output format:
Return a JSON object:
{
  "subtopic": "...",
  "collection_targets": [
    {
      "source_type": "...",
      "reason": "...",
      "priority": "high|medium|low"
    }
  ],
  "key_questions": [
    "..."
  ]
}

Topic:
{topic}

Subtopic:
{subtopic}
""")


SOURCE_SUMMARY_PROMPT = dedent("""
You are reading source material for an offshore engineering intelligence collector.

Task:
Summarize a single source into structured intelligence notes.

Important:
- Prefer technical and engineering information over publicity language.
- Preserve uncertainty when the source is incomplete.
- Do not invent values.
- Distinguish clearly between fact and interpretation.
- Keep the summary concise but information-dense.

Return a JSON object with this schema:
{
  "source_title": "...",
  "source_type": "...",
  "organization": "...",
  "date": "...",
  "summary": "...",
  "facts": [
    "..."
  ],
  "engineering_data": [
    {
      "field": "...",
      "value": "..."
    }
  ],
  "signals": [
    "..."
  ],
  "limitations_or_uncertainties": [
    "..."
  ]
}

Source text:
{text}
""")


TECH_PROFILE_EXTRACTION_PROMPT = dedent("""
You are extracting a normalized technology profile from engineering source material.

Task:
Convert the material into a structured technology/project profile.

Requirements:
1. Normalize the content into fields.
2. Leave missing fields blank instead of guessing.
3. Capture engineering and deployment characteristics.
4. Preserve maturity and uncertainty accurately.
5. If the content is about a project rather than a product, still structure it as a profile.

Return a JSON object with this schema:
{
  "name": "",
  "company": "",
  "institution": "",
  "country": "",
  "energy_type": "",
  "tech_route": "",
  "system_type": "",
  "capacity": "",
  "deployment": "",
  "water_depth": "",
  "key_components": "",
  "engineering_features": "",
  "advantages": "",
  "limitations": "",
  "maturity": "",
  "timeline": "",
  "source_reference": ""
}

Material:
{text}
""")


CASE_COMPARISON_PROMPT = dedent("""
You are comparing multiple technology or project cases for an engineering intelligence report.

Task:
Compare the cases explicitly and identify meaningful differences.

Comparison dimensions:
- technical principle
- structural or deployment form
- engineering complexity
- cost reduction logic
- survivability / reliability
- maintainability
- scalability
- commercialization stage
- strategic relevance

Requirements:
1. Do not merely list the cases.
2. Explicitly identify where cases are similar and different.
3. Highlight which routes appear more mature and which remain exploratory.
4. Preserve uncertainty where evidence is weak.

Return a JSON object with this schema:
{
  "comparison_dimensions": [
    "..."
  ],
  "key_differences": [
    "..."
  ],
  "notable_patterns": [
    "..."
  ],
  "commercialization_observation": "...",
  "engineering_observation": "...",
  "open_questions": [
    "..."
  ]
}

Cases:
{cases}
""")


TREND_ANALYSIS_PROMPT = dedent("""
You are writing a trend and implication analysis for an engineering intelligence brief.

Task:
Infer the major industry signals from the collected cases and comparisons.

Focus on:
- technology direction
- commercialization trajectory
- engineering bottlenecks
- supply chain signals
- infrastructure implications
- integration opportunities
- areas worth continued tracking

Requirements:
1. Base the analysis on the collected evidence.
2. Separate observed trend from speculative future judgment.
3. Avoid exaggerated claims.
4. Use concise intelligence-brief style.

Return a JSON object with this schema:
{
  "observed_trends": [
    "..."
  ],
  "bottlenecks": [
    "..."
  ],
  "opportunity_areas": [
    "..."
  ],
  "watchpoints": [
    "..."
  ],
  "brief_editorial_note": "..."
}

Input material:
{material}
""")


EDITORIAL_NOTE_PROMPT = dedent("""
You are writing a short editorial-style note for an engineering intelligence bulletin.

Task:
Write a concise editorial note similar to a professional internal technology briefing.

Requirements:
1. Highlight why the topic matters.
2. Point out the engineering or industrial significance.
3. Mention what deserves close attention next.
4. Keep it sharp and evidence-linked.
5. Avoid vague slogans and generic optimism.

Length:
80-180 words.

Input:
{material}
""")


FINAL_REPORT_PROMPT = dedent("""
You are writing a professional engineering intelligence report.

Task:
Generate a structured report that resembles a technology intelligence brief.

Report requirements:
1. Clear topic overview
2. Technical classification or background
3. Representative cases
4. Comparative analysis
5. Industry trends and signals
6. Editorial note / implications
7. Open questions
8. Source list

Writing rules:
- concise and structured
- engineering-oriented
- avoid blog style
- avoid overstatement
- preserve uncertainty
- use concrete terminology
- prefer short paragraphs and clear headings

Output format:
Return markdown.

Input package:
Topic:
{topic}

Background:
{background}

Cases:
{cases}

Comparison:
{comparison}

Trend analysis:
{trend_analysis}

Editorial note:
{editorial_note}

Sources:
{sources}
""")


CASE_TABLE_PROMPT = dedent("""
You are generating a compact comparison table for engineering intelligence use.

Task:
Convert the case set into a markdown table.

Prefer columns such as:
- Name
- Company / Institution
- Country
- Tech Route
- Capacity
- Deployment
- Maturity
- Key Feature

Requirements:
1. Use only information supported by the inputs.
2. Leave blank if unknown.
3. Keep wording compact.
4. Return markdown only.

Cases:
{cases}
""")


GAP_ANALYSIS_PROMPT = dedent("""
You are identifying information gaps in an engineering intelligence collection task.

Task:
Review the current material and identify what is still missing.

Focus on:
- missing engineering parameters
- unclear maturity
- lack of representative domestic or overseas cases
- missing cost or deployment information
- unresolved contradictions
- missing commercialization evidence

Return a JSON object with this schema:
{
  "gaps": [
    {
      "gap": "...",
      "why_it_matters": "...",
      "priority": "high|medium|low"
    }
  ]
}

Current material:
{material}
""")