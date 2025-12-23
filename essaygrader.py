"""
Essay grading helper using a local AI model (e.g., Ollama) with a robust fallback.

This module exposes a single primary function:

    grade_essay(essay: str, requirements: list[str], ...)

It attempts to grade a written essay against a list of factual/topic requirements
by calling a local, appropriately sized LLM via Ollama's HTTP API
(`http://localhost:11434/api/generate` by default). If a local model is not
available, it falls back to a simple heuristic based on textual coverage of the
requirements.

Why these design choices?
- Local-first: Many classrooms or grading tools prefer local inference for
  privacy, cost, and latency reasons. Ollama provides a lightweight HTTP API
  suitable for this.
- Deterministic fallback: When the model is not available or returns malformed
  output, we still provide a best-effort grade using a transparent heuristic so
  the caller always gets a usable structured result.

Environment variables:
  - ESSAYGRADER_MODEL: The model name to use with Ollama (default: "llama3.1:8b")
  - ESSAYGRADER_OLLAMA_BASE_URL: Base URL for Ollama (default: "http://localhost:11434")

No external dependencies are required; this module uses the Python standard
library (urllib) to avoid adding requirements to the project.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class GradeResult:
    """Structured result returned by :func:`grade_essay`.

    We keep this as a dataclass primarily for clarity and easy conversion to a
    regular dict via :meth:`to_dict`. The fields deliberately mirror what we
    expect the LLM to return, plus metadata about which backend was used.
    """
    grade: int
    reasons: List[str]
    coverage: List[Dict[str, Any]]
    backend: str  # "ollama" or "fallback"
    model_used: Optional[str] = None
    raw_response: Optional[str] = None
    semantic_similarity: Optional[float] = None
    domain_analysis: Optional[str] = None
    # New detailed-deductions fields
    max_points: Optional[int] = None
    deductions: Optional[List[Dict[str, Any]]] = None  # [{reason, points, requirement?, evidence?, category?}]
    total_deductions: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain dict representation suitable for JSON serialization.

        We intentionally keep keys stable so downstream code can rely on this
        structure regardless of whether we used the LLM or the heuristic path.
        """
        return {
            "grade": self.grade,
            "reasons": self.reasons,
            "coverage": self.coverage,
            "backend": self.backend,
            "model_used": self.model_used,
            "raw_response": self.raw_response,
            "semantic_similarity": self.semantic_similarity,
            "domain_analysis": self.domain_analysis,
            # New keys (backwards compatible additions)
            "max_points": self.max_points,
            "deductions": self.deductions,
            "total_deductions": self.total_deductions,
        }


def grade_essay(
    essay: str,
    requirements: List[str],
    *,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: float = 0.2,
    timeout: float = 30.0,
    max_points: int = 100,
) -> Dict[str, Any]:
    """
    Grade an essay against explicit requirements using a local AI model, returning a structured result.

    Parameters:
      essay: The student's essay text.
      requirements: A list of sentences describing facts/topics the essay should address.
      model: The local model to use (defaults to env ESSAYGRADER_MODEL or "llama3.1:8b").
      base_url: Base URL for the local model server (defaults to env ESSAYGRADER_OLLAMA_BASE_URL or "http://localhost:11434").
      temperature: Sampling temperature for the model.
      timeout: Network timeout in seconds for the LLM call.
      max_points: Total possible points for the essay (default: 100).

    Returns:
      A dict with fields: grade (0-max_points), reasons (list[str]), coverage (list[dict]),
      and detailed deductions from the maximum possible grade:
        - max_points: int
        - deductions: list of {reason, points, requirement?, evidence?, category?}
        - total_deductions: int (should equal max_points - grade)
    """
    # Basic input validation ensures downstream logic can assume proper types
    # and non-empty content. We validate early and fail fast with clear errors.
    if not isinstance(essay, str) or not essay.strip():
        raise ValueError("essay must be a non-empty string")
    if not isinstance(requirements, list) or not all(isinstance(x, str) for x in requirements):
        raise ValueError("requirements must be a list of strings")

    # Resolve configuration with sensible environment defaults. This allows
    # callers to omit parameters in typical deployments while also supporting
    # explicit overrides for tests or special environments.
    #model = model or os.getenv("ESSAYGRADER_MODEL", "llama3.1:8b")
    model = model or os.getenv("ESSAYGRADER_MODEL", "qwen2.5:14b-instruct")

    base_url = base_url or os.getenv("ESSAYGRADER_OLLAMA_BASE_URL", "http://localhost:11434")
    base_url = base_url.rstrip("/")

    # Try Ollama first; if it fails, fall back to heuristic grading.
    try:
        # 1. Semantic Embedding Step (New)
        # We ask the local model for vector embeddings of the essay and requirements.
        # This provides a mathematical "relevance" score (0.0 to 1.0).
        similarity_score = _compute_semantic_score(
            base_url=base_url,
            model=model,
            essay=essay,
            requirements=requirements,
            timeout=timeout
        )

        # 2. Build a sophisticated prompt (The "Fine-Tuning" Strategy)
        # We inject the similarity score and instruct the model to use its
        # internal domain knowledge, acting like a subject matter expert.
        prompt = _build_prompt(essay, requirements, similarity_score, max_points)

        # Perform a single non-streaming generation call for simplicity and to
        # keep the interface stable. Temperature is exposed but defaults low
        # for output stability.
        response_text = _ollama_generate(
            base_url=base_url,
            model=model,
            prompt=prompt,
            temperature=temperature,
            timeout=timeout,
        )
        # The model is instructed to return JSON, but in practice models can be
        # non-deterministic. We attempt to parse strictly, then try to extract
        # a first JSON object if surrounded by extra text.
        parsed = _parse_llm_json(response_text)
        if parsed is None:
            # LLM returned non-JSON; synthesize from text but still use LLM backend
            # We retain the raw LLM output for transparency and compute coverage
            # heuristically to maintain a consistent structured return shape.
            coverage = _heuristic_coverage(essay, requirements)
            reasons = [
                "LLM returned non-JSON. Extracted text provided in raw_response; using heuristic coverage for structure.",
                "Consider adjusting the prompt or model to improve JSON adherence.",
            ]
            grade = _coverage_to_grade(coverage, max_points)
            deductions, total_ded = _synthesize_deductions(
                grade=grade,
                max_points=max_points,
                coverage=coverage,
            )
            return GradeResult(
                grade=grade,
                reasons=reasons,
                coverage=coverage,
                backend="ollama",
                model_used=model,
                raw_response=response_text,
                semantic_similarity=similarity_score,
                max_points=max_points,
                deductions=deductions,
                total_deductions=total_ded,
            ).to_dict()

        # Ensure required fields exist and are well-formed
        # We clamp grade to [0, max_points] defensively as models sometimes produce
        # out-of-range values or floats as strings.
        grade = int(max(0, min(max_points, int(parsed.get("grade", 0)))))
        reasons = parsed.get("reasons") or []
        coverage = parsed.get("coverage") or []
        domain_analysis = parsed.get("domain_analysis")
        # New optional LLM-provided deductions
        llm_deductions = parsed.get("deductions") if isinstance(parsed, dict) else None
        
        # If coverage missing or malformed, compute heuristically
        if not isinstance(coverage, list) or not coverage:
            coverage = _heuristic_coverage(essay, requirements)

        # Validate deductions; if missing or invalid, synthesize
        deductions: List[Dict[str, Any]]
        total_ded: int
        if isinstance(llm_deductions, list) and llm_deductions:
            # Normalize and clamp points
            normalized: List[Dict[str, Any]] = []
            for d in llm_deductions:
                if not isinstance(d, dict):
                    continue
                reason = str(d.get("reason") or d.get("note") or "Deduction")
                try:
                    pts = int(d.get("points"))
                except Exception:
                    pts = 0
                pts = max(0, pts)
                item = {
                    "reason": reason,
                    "points": pts,
                }
                # pass-through optional fields if present
                if d.get("requirement") is not None:
                    item["requirement"] = d.get("requirement")
                if d.get("evidence") is not None:
                    item["evidence"] = d.get("evidence")
                if d.get("category") is not None:
                    item["category"] = d.get("category")
                normalized.append(item)
            total_ded = sum(int(x.get("points", 0)) for x in normalized)
            # If the sum deviates too much, trust the grade but append a reconciliation note
            expected = max_points - grade
            if total_ded != expected:
                normalized.append({
                    "reason": f"Reconciliation: deductions ({total_ded}) did not equal max_points-grade ({expected}); keeping grade and recording actual difference.",
                    "points": max(0, expected - total_ded),
                    "category": "reconciliation",
                })
                total_ded = expected
            deductions = normalized
        else:
            deductions, total_ded = _synthesize_deductions(grade=grade, max_points=max_points, coverage=coverage)

        return GradeResult(
            grade=grade,
            reasons=list(map(str, reasons)) or ["Model did not provide reasons."],
            coverage=coverage,
            backend="ollama",
            model_used=model,
            raw_response=json.dumps(parsed, ensure_ascii=False),
            semantic_similarity=similarity_score,
            domain_analysis=domain_analysis,
            max_points=max_points,
            deductions=deductions,
            total_deductions=total_ded,
        ).to_dict()
    except Exception as e:
        # Fallback grading (no local model available or call failed)
        # We intentionally do not re-raise network/parse errors here to provide
        # a resilient API. The reason is included in the reasons list for
        # observability by callers.
        coverage = _heuristic_coverage(essay, requirements)
        grade = _coverage_to_grade(coverage, max_points)
        deductions, total_ded = _synthesize_deductions(grade=grade, max_points=max_points, coverage=coverage)
        reasons = [
            "Local model unavailable or call failed; applied heuristic grading.",
            f"Reason: {type(e).__name__}: {e}",
        ]
        return GradeResult(
            grade=grade,
            reasons=reasons,
            coverage=coverage,
            backend="fallback",
            model_used=None,
            raw_response=None,
            max_points=max_points,
            deductions=deductions,
            total_deductions=total_ded,
        ).to_dict()


def _build_prompt(essay: str, requirements: List[str], similarity_score: Optional[float], max_points: int) -> str:
    """Construct a sophisticated prompt for the local model.

    We simulate a 'fine-tuned' persona by providing detailed context and strict
    role instructions. We also inject the semantic similarity score to ground
    the AI's evaluation.
    """
    rubric_lines = "\n".join(f"- {req.strip()}" for req in requirements if req and req.strip())
    
    sim_context = ""
    if similarity_score is not None:
        sim_context = (
            f"CONTEXT - SEMANTIC RELEVANCE SCORE: {similarity_score:.2f} / 1.0\n"
            "(A score below 0.5 suggests the essay may be off-topic, regardless of keywords.)\n\n"
        )

    return (
        "You are an expert academic professor and subject matter expert. "
        "Your goal is to provide a rigorous, fair, and holistic evaluation of a student essay.\n\n"
        f"{sim_context}"
        "GRADING STRATEGY:\n"
        "1. PRIMARY: Check the essay against the explicit requirements below.\n"
        "2. SECONDARY: Apply your own domain knowledge. Reward deep insights, clarity, and accuracy. "
        "Penalize factual errors or contradictions even if they satisfy a requirement keyword-wise.\n\n"
        "Output strictly in JSON with the following structure:\n"
        "{\n"
        f'  "grade": int (0-{max_points}),\n'
        '  "reasons": [list of string explanations],\n'
        '  "coverage": [{"requirement": string, "addressed": bool, "evidence": string}],\n'
        '  "domain_analysis": "A brief paragraph adding expert context, noting factual accuracy or depth beyond the rubric.",\n'
        f'  "max_points": {max_points},\n'
        '  "deductions": [\n'
        '     { "reason": string, "points": int, "requirement": string|null, "evidence": string|null, "category": "missing_requirement"|"partial_coverage"|"factual_error"|"off_topic"|"clarity/style" }\n'
        '  ],\n'
        '  "total_deductions": int\n'
        "}\n\n"
        "REQUIREMENTS:\n"
        f"{rubric_lines}\n\n"
        "STUDENT ESSAY:\n"
        + essay.strip()
    )


def _synthesize_deductions(*, grade: int, max_points: int, coverage: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """Create a detailed list of deductions that explain why points were lost.

    Strategy (deterministic):
    - Identify requirements not addressed and distribute the missing points across them.
    - If all requirements addressed but points still missing (due to heuristic rounding), add a generic quality deduction.
    - Provide evidence snippets when available from coverage.
    """
    missing_points = max(0, max_points - int(grade))
    deductions: List[Dict[str, Any]] = []
    if missing_points == 0:
        return deductions, 0

    missed = [c for c in (coverage or []) if not c.get("addressed")]
    if missed:
        n = len(missed)
        base = missing_points // n
        remainder = missing_points - base * n
        for idx, c in enumerate(missed):
            pts = base + (1 if idx < remainder else 0)
            deductions.append({
                "reason": f"Missing requirement: {c.get('requirement', '')}",
                "points": pts,
                "requirement": c.get("requirement"),
                "evidence": c.get("evidence"),
                "category": "missing_requirement",
            })
        return deductions, missing_points

    # No explicit missed requirements but still lost points -> add a generic deduction
    deductions.append({
        "reason": "Partial coverage/quality issues (brevity, clarity, depth, or minor inaccuracies)",
        "points": missing_points,
        "category": "partial_coverage",
    })
    return deductions, missing_points


def _compute_semantic_score(
    base_url: str, model: str, essay: str, requirements: List[str], timeout: float
) -> Optional[float]:
    """Compute cosine similarity between the essay and the combined requirements.
    
    Returns None if the model does not support embeddings or the call fails.
    """
    try:
        # Combine requirements into a single "ideal" text block for comparison
        ideal_text = " ".join(requirements)
        
        # Get embeddings from Ollama
        # Note: Many chat models in Ollama (like llama3) also support embeddings!
        vec_essay = _ollama_embedding(base_url, model, essay, timeout)
        vec_ideal = _ollama_embedding(base_url, model, ideal_text, timeout)
        
        if not vec_essay or not vec_ideal:
            return None
            
        return _cosine_similarity(vec_essay, vec_ideal)
    except Exception:
        # Fail silently on embeddings to allow the main grading to proceed
        return None


def _ollama_embedding(base_url: str, model: str, text: str, timeout: float) -> List[float]:
    """Call Ollama's /api/embeddings endpoint."""
    url = f"{base_url}/api/embeddings"
    # Truncate text slightly to avoid context limit errors on embeddings if text is huge
    payload = {
        "model": model,
        "prompt": text[:8000], 
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
        parsed = json.loads(body)
        return parsed.get("embedding", [])


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two vectors using standard library."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(a * a for a in v2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
        
    return dot_product / (magnitude1 * magnitude2)


def _ollama_generate(
    *, base_url: str, model: str, prompt: str, temperature: float, timeout: float
) -> str:
    """Call Ollama's non-streaming generate endpoint and return the text.

    This function keeps the transport layer minimal by using urllib from the
    standard library. We avoid external dependencies to keep this module
    lightweight and easy to adopt.
    """
    url = f"{base_url}/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": float(temperature)},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    # Ollama returns {"model":..., "created_at":..., "response": "...", "done": true}
    try:
        parsed = json.loads(body)
        # Prefer the concise text field if present
        if isinstance(parsed, dict) and "response" in parsed:
            return str(parsed["response"]).strip()
    except json.JSONDecodeError:
        pass
    return body.strip()


def _parse_llm_json(text: str) -> Optional[Dict[str, Any]]:
    """Parse the model output as JSON, with a best-effort extraction fallback.

    Many models occasionally wrap JSON with extra text. We first try a strict
    parse and then attempt to extract the first top-level JSON object using
    brace matching. If both fail, return None.
    """
    # Try direct JSON parse first
    try:
        return json.loads(text)
    except Exception:
        pass

    # Attempt to extract the first JSON object via a simple brace match
    match = _extract_first_json_object(text)
    if match:
        try:
            return json.loads(match)
        except Exception:
            return None
    return None


def _extract_first_json_object(text: str) -> Optional[str]:
    """Return the first top-level JSON object substring using brace matching.

    This is a minimal, streaming-friendly approach that does not require a full
    parser. It is sufficient for rescuing many "almost-JSON" model responses.
    """
    # Simple brace matching to find the first top-level {...} block
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _heuristic_coverage(essay: str, requirements: List[str]) -> List[Dict[str, Any]]:
    """Compute a coarse coverage map of requirements within the essay text.

    This heuristic looks for lexical overlap between requirement tokens and the
    essay. It is intentionally simple, fast, and transparent. While it cannot
    capture deep semantics, it provides a reasonable fallback signal when the
    LLM cannot be used.
    """
    essay_lc = essay.lower()
    coverage: List[Dict[str, Any]] = []

    for req in requirements:
        req_str = (req or "").strip()
        if not req_str:
            continue

        addressed, evidence = _simple_requirement_match(essay_lc, req_str)
        coverage.append({
            "requirement": req_str,
            "addressed": addressed,
            "evidence": evidence,
        })

    return coverage


def _simple_requirement_match(essay_lc: str, requirement: str) -> Tuple[bool, str]:
    """Very simple lexical match between a requirement and the essay.

    Strategy:
      - Tokenize the requirement into alphanumeric words, ignoring very short
        tokens (<=2 chars) that are often stopwords or noise.
      - Count token presence using word-boundary regex to avoid substring
        artifacts (e.g., "ox" in "oxygen").
      - Consider a requirement addressed if at least half of its tokens appear
        or at least 3 tokens match (helps longer requirements).
      - If addressed, try to extract a short snippet around the first matching
        token to serve as lightweight evidence.
    """
    # Tokenize requirement into content words (very light filtering)
    tokens = [t for t in re.split(r"[^a-z0-9]+", requirement.lower()) if len(t) > 2]
    if not tokens:
        return False, ""

    # Count matches in essay
    matches = sum(1 for t in tokens if re.search(rf"\b{re.escape(t)}\b", essay_lc))
    ratio = matches / max(1, len(tokens))

    addressed = ratio >= 0.5 or matches >= 3

    # Provide a short evidence snippet when possible
    evidence = ""
    if addressed:
        for t in tokens:
            m = re.search(rf"(.{{0,40}}\b{re.escape(t)}\b.+?\.)", essay_lc)
            if m:
                snippet = m.group(0).strip()
                evidence = f"...{snippet}"
                break
    return addressed, evidence


def _coverage_to_grade(coverage: List[Dict[str, Any]], max_points: int) -> int:
    """Map coverage results to a 0–max_points integer score.

    Currently we use a linear mapping (ratio * max_points) clamped to [0, max_points]. This
    is intentionally simple; callers can layer additional policy if desired.
    """
    if not coverage:
        return 0
    addressed = sum(1 for c in coverage if c.get("addressed"))
    ratio = addressed / len(coverage)
    # Map ratio to 0-max_points, with a slight reward for near-complete coverage
    score = int(round(min(max_points, max(0, ratio * max_points))))
    return score


__all__ = ["grade_essay", "GradeResult"]
