Alright, let’s turn that fluffy “How can ChatGPT best help you with this project?” into something with actual teeth.

I’ll give you **(1) an ontology** (what concepts you should specify) and **(2) a clean syntax** (how to express it), plus **examples** you can copy-paste and tweak.

---

## 1. Ontology: What you should tell GPT

Think of this as the *fields* in a “ChatGPT contract” for a project.

### A. Project Meta

* **project_name** – Short handle for what we’re doing.
* **project_type** – e.g. “learning”, “coding project”, “research”, “career search”, “creative writing”.
* **project_description** – 2–5 sentences of context so GPT doesn’t guess.

---

### B. Objectives & Scope

* **primary_objectives** – The main outcomes you want (ordered list).
* **secondary_objectives** – Nice-to-haves.
* **out_of_scope** – Things you *don’t* want GPT to do (prevents it from wandering off).

---

### C. Inputs & Outputs

* **input_sources** – What you’ll provide: e.g. “specs”, “code”, “papers”, “transcripts”.
* **desired_outputs** – What you want back: “step-by-step plan”, “code with comments”, “summary”, “list of examples”, etc.
* **level_of_detail** – “high-level overview”, “mid-level”, or “brutally detailed”.

---

### D. Focus & Constraints

* **focus_topics** – Areas to lean into (e.g. “Python performance”, “user experience”, “testability”).
* **avoid_topics** – Stuff to skip (e.g. “no math proofs”, “no frontend CSS advice”).
* **constraints** – Time, tech stack, rules, or limitations (e.g. “must run on M2 Mac”, “no paid APIs”, “assume intermediate Python”).

---

### E. Style & Tone

* **tone** – e.g. “formal”, “friendly”, “professorial”, “snarky”, “coaching”.
* **persona_for_assistant** – e.g. “senior Python engineer”, “math tutor”, “editor”, “PM”.
* **verbosity** – “concise”, “normal”, “detailed”, “hyper-detailed”.
* **language** – English, Spanish, mixed, etc.

---

### F. Interaction Style

* **question_policy** – When should GPT ask you clarifying questions vs. just make assumptions.
* **error_handling_style** – e.g. “if you’re unsure, show alternatives”, “explicitly say when you’re guessing”.
* **iteration_style** – How you want to refine: “propose v1, then we iterate”, “give options”, etc.
* **feedback_tolerance** – e.g. “be direct”, “be gentle”, “assume I’m technical”.

---

### G. Formatting & Structure

* **preferred_formats** – Markdown sections, tables, bullet lists, code blocks, JSON, etc.
* **code_style** – For coding tasks: language, version, style (PEP8, docstrings, comments level).
* **section_template** – If you want every answer to follow a fixed outline (e.g. “Context → Plan → Examples → Next Actions”).

---

## 2. Syntax: A compact, machine-friendly way to answer

You can express all of that in a tight JSON-ish block that you paste as your first message, or as your answer to “How can ChatGPT best help…”.

### 2.1. JSON-style “assistant contract”

```jsonc
{
  "project_meta": {
    "project_name": "STRING",
    "project_type": "STRING",
    "project_description": "STRING"
  },
  "objectives": {
    "primary_objectives": ["STRING", "STRING"],
    "secondary_objectives": ["STRING"],
    "out_of_scope": ["STRING"]
  },
  "io": {
    "input_sources": ["STRING"],
    "desired_outputs": ["STRING"],
    "level_of_detail": "overview | medium | deep | ultra_deep"
  },
  "focus": {
    "focus_topics": ["STRING"],
    "avoid_topics": ["STRING"],
    "constraints": ["STRING"]
  },
  "style": {
    "tone": "STRING",
    "persona_for_assistant": "STRING",
    "verbosity": "low | medium | high | extreme",
    "language": "STRING"
  },
  "interaction": {
    "question_policy": "always_ask | ask_if_blocked | rarely_ask",
    "error_handling_style": "show_uncertainty | give_alternatives | pick_best_guess",
    "iteration_style": "versioned_drafts | one_shot | options_then_refine",
    "feedback_tolerance": "direct | neutral | gentle"
  },
  "formatting": {
    "preferred_formats": ["markdown_headings", "bullets", "tables", "code_blocks", "json"],
    "code_style": {
      "language": "STRING",
      "version": "STRING",
      "notes": "STRING"
    },
    "section_template": ["STRING"]
  }
}
```

You don’t have to fill everything; partial is fine as long as you keep the keys.

---

### 2.2. Natural language template (if you don’t want JSON)

If you prefer words over braces, you can answer like this:

> * **Project**: [name, type, 2–3 sentence description]
> * **Main goals**: [what I want by the end]
> * **What I’ll give you**: [inputs, links, code, etc.]
> * **What I want back**: [plan, code, explanations, summaries, formats]
> * **Focus on**: [topics, constraints, tech stack]
> * **Do NOT do**: [things to avoid]
> * **Tone & persona**: [tone, how you should “act”]
> * **Detail level**: [overview / detailed / extremely detailed]
> * **Interaction style**: [when to ask questions, how direct to be, how to iterate]
> * **Formatting**: [markdown, tables, code style, section order]

Either the JSON style or the bullet template will work nicely with any GPT model.

---

## 3. Example: Coding / AI project

**Answer to “How can ChatGPT best help you with this project?” using the JSON-ish syntax:**

```jsonc
{
  "project_meta": {
    "project_name": "AI Coding Tutor",
    "project_type": "learning + coding",
    "project_description": "I’m building a small Python project while also leveling up my understanding of AI/ML tooling and good engineering practices."
  },
  "objectives": {
    "primary_objectives": [
      "Help me design and implement the core features step by step.",
      "Explain tradeoffs and concepts at a BS-in-CS level without dumbing it down."
    ],
    "secondary_objectives": [
      "Suggest improvements that make the project portfolio-worthy."
    ],
    "out_of_scope": [
      "No hand-wavy explanations without code or concrete examples."
    ]
  },
  "io": {
    "input_sources": [
      "My code snippets",
      "High-level feature descriptions",
      "Occasional error messages"
    ],
    "desired_outputs": [
      "Rewritten or new code with comments",
      "Short conceptual explanations per change",
      "Checklists or step-by-step plans for next steps"
    ],
    "level_of_detail": "deep"
  },
  "focus": {
    "focus_topics": [
      "Code clarity and structure",
      "Testability",
      "Handling edge cases"
    ],
    "avoid_topics": [
      "Non-Python languages unless explicitly requested"
    ],
    "constraints": [
      "Python 3.11",
      "No paid external APIs",
      "Keep dependencies minimal"
    ]
  },
  "style": {
    "tone": "friendly, a bit snarky, like a senior dev who has seen some things",
    "persona_for_assistant": "senior Python engineer and AI tutor",
    "verbosity": "high",
    "language": "English"
  },
  "interaction": {
    "question_policy": "ask_if_blocked",
    "error_handling_style": "show_uncertainty",
    "iteration_style": "versioned_drafts",
    "feedback_tolerance": "direct"
  },
  "formatting": {
    "preferred_formats": [
      "markdown_headings",
      "bullets",
      "code_blocks"
    ],
    "code_style": {
      "language": "python",
      "version": "3.11",
      "notes": "PEP8, type hints where useful, docstrings for public functions"
    },
    "section_template": [
      "Summary",
      "Code",
      "Explanation",
      "Next Steps"
    ]
  }
}
```

Paste that (modified to fit your reality) as your answer, and any halfway competent GPT instance will snap into the right behavior.

---

## 4. Example: Writing / documentation project

Same idea, different domain:

```jsonc
{
  "project_meta": {
    "project_name": "API Documentation Overhaul",
    "project_type": "technical writing",
    "project_description": "I’m cleaning up and expanding our API docs so that new developers can understand and use the API without asking the original engineers a million questions."
  },
  "objectives": {
    "primary_objectives": [
      "Turn rough notes and scattered comments into clean, structured documentation.",
      "Standardize terminology and naming across the docs."
    ],
    "secondary_objectives": [
      "Add examples and common pitfalls sections."
    ],
    "out_of_scope": [
      "Changing the underlying API design",
      "Adding features that don't exist"
    ]
  },
  "io": {
    "input_sources": [
      "Existing docs",
      "Code snippets",
      "My rough notes"
    ],
    "desired_outputs": [
      "Polished documentation text",
      "Consistent section templates per endpoint",
      "Lists of missing or unclear areas"
    ],
    "level_of_detail": "medium"
  },
  "focus": {
    "focus_topics": [
      "Clarity",
      "Consistency",
      "Examples first"
    ],
    "avoid_topics": [
      "Marketing fluff"
    ],
    "constraints": [
      "Audience is intermediate developers",
      "Assume they know HTTP/JSON but not our domain"
    ]
  },
  "style": {
    "tone": "clear, straightforward, mildly informal",
    "persona_for_assistant": "technical writer + senior backend dev",
    "verbosity": "medium",
    "language": "English"
  },
  "interaction": {
    "question_policy": "ask_if_blocked",
    "error_handling_style": "give_alternatives",
    "iteration_style": "options_then_refine",
    "feedback_tolerance": "neutral"
  },
  "formatting": {
    "preferred_formats": [
      "markdown_headings",
      "tables",
      "code_blocks"
    ],
    "code_style": {
      "language": "curl + one high-level client (e.g. JS or Python)",
      "version": "N/A",
      "notes": "Short, runnable examples"
    },
    "section_template": [
      "Overview",
      "Authentication",
      "Endpoint List",
      "Per-Endpoint Details",
      "Examples",
      "Common Errors"
    ]
  }
}
```

---

If you tell me what project you’re actually thinking about, I can spit out a **tailored “assistant contract”** you can reuse across chats so every instance of GPT behaves the way you want instead of doing its default people-pleasing improv routine.
