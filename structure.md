# Project Stucture

collector/
├── AGENTS.md
├── subagents.yaml
├── collector.py
├── requirements.txt
├── skills/
│   ├── source_discovery/
│   │   └── SKILL.md
│   ├── webpage_collection/
│   │   └── SKILL.md
│   ├── dedup_triage/
│   │   └── SKILL.md
│   ├── timeline_builder/
│   │   └── SKILL.md
│   └── final_report/
│       └── SKILL.md
├── workspace/
│   └── runs/
│       └── <task_id>/
│           ├── task.json
│           ├── raw_sources.jsonl
│           ├── extracted_notes.jsonl
│           ├── notes.md
│           ├── timeline.md
│           ├── gaps.md
│           └── report.md
└── prompts/
    ├── planner.md
    ├── collector.md
    ├── analyst.md
    └── reporter.md
