from typing import Optional

from google.genai import types


def _string_schema(*, nullable: bool = True) -> types.Schema:
    return types.Schema(type=types.Type.STRING, nullable=nullable)


def _array_schema(item_schema: types.Schema, *, nullable: bool = True) -> types.Schema:
    return types.Schema(type=types.Type.ARRAY, items=item_schema, nullable=nullable)


def _integer_schema(*, nullable: bool = True) -> types.Schema:
    return types.Schema(type=types.Type.INTEGER, nullable=nullable)


def _number_schema(*, nullable: bool = True) -> types.Schema:
    return types.Schema(type=types.Type.NUMBER, nullable=nullable)


def _object_schema(
    properties: dict[str, types.Schema],
    *,
    required: Optional[list[str]] = None,
    nullable: bool = False,
) -> types.Schema:
    return types.Schema(
        type=types.Type.OBJECT,
        properties=properties,
        required=required or [],
        nullable=nullable,
    )


CONTACT_SCHEMA = _object_schema(
    {
        "email": _string_schema(nullable=True),
        "phone": _string_schema(nullable=True),
        "location": _string_schema(nullable=True),
        "linkedin": _string_schema(nullable=True),
        "github": _string_schema(nullable=True),
        "website": _string_schema(nullable=True),
    },
    nullable=False,
)

CANDIDATE_SCHEMA = _object_schema(
    {
        "full_name": _string_schema(),
        "headline": _string_schema(nullable=True),
        "contact": CONTACT_SCHEMA,
    },
    required=["full_name", "contact"],
)

SKILLS_SCHEMA = _object_schema(
    {
        "primary": _array_schema(_string_schema(), nullable=False),
        "secondary": _array_schema(_string_schema(), nullable=False),
        "tools": _array_schema(_string_schema(), nullable=False),
    },
    required=["primary", "secondary", "tools"],
)

EXPERIENCE_ITEM_SCHEMA = _object_schema(
    {
        "title": _string_schema(),
        "company": _string_schema(),
        "employment_type": _string_schema(nullable=True),
        "start_date": _string_schema(nullable=True),
        "end_date": _string_schema(nullable=True),
        "location": _string_schema(nullable=True),
        "achievements": _array_schema(_string_schema(), nullable=False),
        "tech_stack": _array_schema(_string_schema(), nullable=False),
        "impact": _array_schema(_string_schema(), nullable=False),
    },
    required=["title", "company"],
)

EDUCATION_ITEM_SCHEMA = _object_schema(
    {
        "institution": _string_schema(),
        "degree": _string_schema(nullable=True),
        "field_of_study": _string_schema(nullable=True),
        "start_date": _string_schema(nullable=True),
        "end_date": _string_schema(nullable=True),
        "achievements": _array_schema(_string_schema(), nullable=False),
    },
    required=["institution"],
)

CERTIFICATION_ITEM_SCHEMA = _object_schema(
    {
        "name": _string_schema(),
        "issuer": _string_schema(nullable=True),
        "date": _string_schema(nullable=True),
    },
    required=["name"],
)

PROJECT_ITEM_SCHEMA = _object_schema(
    {
        "name": _string_schema(),
        "description": _string_schema(nullable=True),
        "role": _string_schema(nullable=True),
        "start_date": _string_schema(nullable=True),
        "end_date": _string_schema(nullable=True),
        "tech_stack": _array_schema(_string_schema(), nullable=False),
        "impact": _array_schema(_string_schema(), nullable=False),
    },
    required=["name"],
)

AWARD_ITEM_SCHEMA = _object_schema(
    {
        "name": _string_schema(),
        "issuer": _string_schema(nullable=True),
        "date": _string_schema(nullable=True),
    },
    required=["name"],
)

KEYWORDS_SCHEMA = _object_schema(
    {
        "domain": _array_schema(_string_schema(), nullable=False),
        "methodologies": _array_schema(_string_schema(), nullable=False),
        "tools": _array_schema(_string_schema(), nullable=False),
    },
    required=["domain", "methodologies", "tools"],
)

CV_RESPONSE_SCHEMA = _object_schema(
    {
        "candidate": CANDIDATE_SCHEMA,
        "summary": _string_schema(nullable=True),
        "skills": SKILLS_SCHEMA,
        "experience": _array_schema(EXPERIENCE_ITEM_SCHEMA, nullable=False),
        "education": _array_schema(EDUCATION_ITEM_SCHEMA, nullable=False),
        "certifications": _array_schema(CERTIFICATION_ITEM_SCHEMA, nullable=False),
        "projects": _array_schema(PROJECT_ITEM_SCHEMA, nullable=False),
        "languages": _array_schema(_string_schema(), nullable=False),
        "awards": _array_schema(AWARD_ITEM_SCHEMA, nullable=False),
        "keywords": KEYWORDS_SCHEMA,
    },
    required=[
        "candidate",
        "summary",
        "skills",
        "experience",
        "education",
        "certifications",
        "projects",
        "languages",
        "awards",
        "keywords",
    ],
)

APPROACH_INITIAL_PLAN_SCHEMA = _object_schema(
    {
        "plan_summary": _string_schema(),
        "assumptions": _array_schema(_string_schema(), nullable=True),
    },
    required=["plan_summary"],
)

APPROACH_SYSTEM_SCHEMA = _object_schema(
    {
        "api_endpoints": _string_schema(),
        "database_schema": _string_schema(nullable=True),
        "job_queue_handling": _string_schema(nullable=True),
    },
    required=["api_endpoints"],
)

APPROACH_LLM_SCHEMA = _object_schema(
    {
        "model_choice": _string_schema(),
        "prompt_design": _string_schema(),
        "chaining_logic": _string_schema(nullable=True),
        "rag_strategy": _string_schema(nullable=True),
    },
    required=["model_choice", "prompt_design"],
)

APPROACH_RESILIENCE_SCHEMA = _object_schema(
    {
        "failure_handling": _string_schema(),
        "retry_strategy": _string_schema(nullable=True),
        "randomness_mitigation": _string_schema(nullable=True),
    },
    required=["failure_handling"],
)

APPROACH_EDGE_CASES_SCHEMA = _object_schema(
    {
        "scenarios": _array_schema(_string_schema(), nullable=False),
        "testing": _string_schema(nullable=True),
    },
    required=["scenarios"],
)

APPROACH_DESIGN_SCHEMA = _object_schema(
    {
        "initial_plan": APPROACH_INITIAL_PLAN_SCHEMA,
        "system_design": APPROACH_SYSTEM_SCHEMA,
        "llm_integration": APPROACH_LLM_SCHEMA,
        "prompting_examples": _array_schema(_string_schema(), nullable=False),
        "resilience": APPROACH_RESILIENCE_SCHEMA,
        "edge_cases": APPROACH_EDGE_CASES_SCHEMA,
    },
    required=[
        "initial_plan",
        "system_design",
        "llm_integration",
        "prompting_examples",
        "resilience",
        "edge_cases",
    ],
)

RESULTS_OUTCOME_SCHEMA = _object_schema(
    {
        "successes": _array_schema(_string_schema(), nullable=False),
        "challenges": _array_schema(_string_schema(), nullable=False),
    },
    required=["successes", "challenges"],
)

RESULTS_EVALUATION_SCHEMA = _object_schema(
    {
        "analysis": _string_schema(),
        "stability_factors": _array_schema(_string_schema(), nullable=True),
    },
    required=["analysis"],
)

RESULTS_FUTURE_SCHEMA = _object_schema(
    {
        "improvements": _array_schema(_string_schema(), nullable=False),
        "constraints": _array_schema(_string_schema(), nullable=True),
    },
    required=["improvements"],
)

RESULTS_REFLECTION_SCHEMA = _object_schema(
    {
        "outcome": RESULTS_OUTCOME_SCHEMA,
        "evaluation": RESULTS_EVALUATION_SCHEMA,
        "future_improvements": RESULTS_FUTURE_SCHEMA,
    },
    required=["outcome", "evaluation", "future_improvements"],
)

PROJECT_REPORT_SCHEMA = _object_schema(
    {
        "title": _string_schema(),
        "candidate": _object_schema(
            {
                "full_name": _string_schema(),
                "email": _string_schema(),
            },
            required=["full_name", "email"],
        ),
        "repository": _object_schema(
            {
                "url": _string_schema(),
                "notes": _string_schema(nullable=True),
            },
            required=["url"],
        ),
        "approach_design": APPROACH_DESIGN_SCHEMA,
        "results_reflection": RESULTS_REFLECTION_SCHEMA,
        "bonus_work": _array_schema(_string_schema(), nullable=True),
    },
    required=[
        "title",
        "candidate",
        "repository",
        "approach_design",
        "results_reflection",
    ],
)

CV_MATCH_EVALUATION_SCHEMA = _object_schema(
    {
        "technical_skills_match": _integer_schema(),
        "technical_skills_notes": _string_schema(),
        "experience_level": _integer_schema(),
        "experience_level_notes": _string_schema(),
        "relevant_achievements": _integer_schema(),
        "relevant_achievements_notes": _string_schema(),
        "cultural_collaboration_fit": _integer_schema(),
        "cultural_collaboration_fit_notes": _string_schema(),
        "cv_match_rate": _number_schema(),
        "cv_feedback": _string_schema(),
    },
    required=[
        "technical_skills_match",
        "technical_skills_notes",
        "experience_level",
        "experience_level_notes",
        "relevant_achievements",
        "relevant_achievements_notes",
        "cultural_collaboration_fit",
        "cultural_collaboration_fit_notes",
        "cv_match_rate",
        "cv_feedback",
    ],
)


PROJECT_DELIVERABLE_EVALUATION_SCHEMA = _object_schema(
    {
        "correctness": _integer_schema(),
        "correctness_notes": _string_schema(),
        "code_quality_structure": _integer_schema(),
        "code_quality_structure_notes": _string_schema(),
        "resilience_error_handling": _integer_schema(),
        "resilience_error_handling_notes": _string_schema(),
        "documentation_explanation": _integer_schema(),
        "documentation_explanation_notes": _string_schema(),
        "creativity_bonus": _integer_schema(),
        "creativity_bonus_notes": _string_schema(),
        "project_score": _number_schema(),
        "project_feedback": _string_schema(),
    },
    required=[
        "correctness",
        "correctness_notes",
        "code_quality_structure",
        "code_quality_structure_notes",
        "resilience_error_handling",
        "resilience_error_handling_notes",
        "documentation_explanation",
        "documentation_explanation_notes",
        "creativity_bonus",
        "creativity_bonus_notes",
        "project_score",
        "project_feedback",
    ],
)
