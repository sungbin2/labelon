"""모델 출력 JSON 스키마 (business-logic-model.md 1.2, 2.2)."""

from __future__ import annotations

JUDGE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["facts", "scene", "cot", "dialogue_turns", "persona_task_fit", "missing_in_image", "impossible_reason_suggestion",
                 "qa_matches_cot3", "task_qa_direction_match", "appliance_controls_visible", "archetype_suggestion",
                 "archetype_fits_environment", "environment_note", "impossible_flags", "text_issues"],
    "properties": {
        "facts": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["index", "verdict", "evidence"],
                "properties": {
                    "index": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["TRUE", "FALSE", "UNKNOWN"]},
                    "evidence": {"type": "string"},
                },
            },
        },
        "scene": {
            "type": "object", "additionalProperties": False, "required": ["consistent", "note"],
            "properties": {"consistent": {"type": "boolean"}, "note": {"type": "string"}},
        },
        "cot": {
            "type": "array", "minItems": 3, "maxItems": 3,
            "items": {
                "type": "object", "additionalProperties": False, "required": ["field", "consistent", "role_fits", "note"],
                "properties": {
                    "field": {"type": "string", "enum": ["cot1", "cot2", "cot3"]},
                    "consistent": {"type": "boolean"},
                    "role_fits": {"type": "boolean"},
                    "note": {"type": "string"},
                },
            },
        },
        "dialogue_turns": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False, "required": ["turn", "consistent", "beyond_cot3", "note"],
                "properties": {"turn": {"type": "integer"}, "consistent": {"type": "boolean"}, "beyond_cot3": {"type": "boolean"}, "note": {"type": "string"}},
            },
        },
        "persona_task_fit": {
            "type": "object", "additionalProperties": False, "required": ["cot_fits", "dialogue_fits", "note"],
            "properties": {"cot_fits": {"type": "boolean"}, "dialogue_fits": {"type": "boolean"}, "note": {"type": "string"}},
        },
        "missing_in_image": {"type": "array", "items": {"type": "string"}},
        "impossible_reason_suggestion": {"type": "string"},
        "qa_matches_cot3": {"type": "boolean"},
        "task_qa_direction_match": {"type": "boolean"},
        "appliance_controls_visible": {"type": ["boolean", "null"]},
        "archetype_suggestion": {
            "type": "object", "additionalProperties": False, "required": ["fits", "suggested", "reason"],
            "properties": {"fits": {"type": "boolean"}, "suggested": {"type": "string"}, "reason": {"type": "string"}},
        },
        # 사이클 4
        "archetype_fits_environment": {"type": "boolean"},
        "environment_note": {"type": "string"},
        "impossible_flags": {
            "type": "object", "additionalProperties": False,
            "required": ["core_error_propagated", "persona_infeasible_guidance", "unsafe_guidance", "note"],
            "properties": {
                "core_error_propagated": {"type": "boolean"},
                "persona_infeasible_guidance": {"type": "boolean"},
                "unsafe_guidance": {"type": "boolean"},
                "note": {"type": "string"},
            },
        },
        "text_issues": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False, "required": ["field", "kind", "wrong", "correct"],
                "properties": {
                    "field": {"type": "string"},
                    "kind": {"type": "string", "enum": ["typo", "speculation", "number", "direction"]},
                    "wrong": {"type": "string"},
                    "correct": {"type": "string"},
                },
            },
        },
    },
}

REVISE_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": ["scene", "facts", "cot1", "cot2", "cot3", "dialogue_assistant", "change_notes"],
    "properties": {
        "scene": {"type": "string"},
        "facts": {"type": "array", "items": {"type": "string"}},
        "cot1": {"type": "string"},
        "cot2": {"type": "string"},
        "cot3": {"type": "string"},
        "dialogue_assistant": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False, "required": ["turn", "assistant"],
                "properties": {"turn": {"type": "integer"}, "assistant": {"type": "string"}, "drop": {"type": "boolean"}},
            },
        },
        "change_notes": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False, "required": ["field", "reason"],
                "properties": {"field": {"type": "string"}, "reason": {"type": "string"}},
            },
        },
    },
}
