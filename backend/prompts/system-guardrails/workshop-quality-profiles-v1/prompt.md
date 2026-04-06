# system.guardrails.workshop-quality-profiles

- Version: `1.0.0`
- Category: `system-guardrails`
- Status: `wired`

## Purpose

Provide the canonical quality-level copy bundle for workshop safety posture,
render thresholds, and output-depth limits.

## Input Contract

- Workshop quality level keys: `low`, `mid`, `high`
- Backend quality-control runtime that converts this bundle into
  `QualityControlProfile` objects

## Output Contract

Return a JSON object with `profiles.low`, `profiles.mid`, and `profiles.high`.
Each profile must include the fields consumed by
`backend/services/api/src/polio_api/services/quality_control.py`.

## Forbidden

- Promising unsupported admissions outcomes
- Encouraging fabricated activity, fabricated evidence, or hidden provenance
- Defining a quality level that outruns student context or source support

## Uncertainty Handling

- If a higher-intensity profile lacks enough support, the backend should safely
  downgrade before rendering
- Keep thresholds and descriptions explicit so parallel edits do not drift

## Evaluation Criteria

- The copy stays aligned with the current product guardrails
- Each level is distinct, realistic, and safe
- The bundle is stable enough for both backend logic and UI-facing metadata

## Change Log

- `1.0.0`: Initial workshop quality profile bundle extracted from backend inline copy.

## Prompt Body

{
  "profiles": {
    "low": {
      "level": "low",
      "label": "안전형",
      "emoji": "🛡️",
      "color": "emerald",
      "description": "교과 개념에 충실하고 학생이 실제로 수행 가능한 범위만 사용합니다.",
      "detail": "낯선 전문어와 과장된 결론을 줄이고, 검증 가능한 사실과 직접 확인 가능한 활동만 남깁니다.",
      "student_fit": "교과 개념 충실, 안전형",
      "safety_posture": "교과 개념과 검증 가능성을 최우선으로 둡니다.",
      "authenticity_policy": "학생이 실제로 한 활동과 확인된 사실만 남깁니다.",
      "hallucination_guardrail": "없는 실험, 없는 수치, 없는 경험은 자동 차단합니다.",
      "starter_mode": "핵심 개념 정리와 수행 가능 범위 확인부터 시작",
      "followup_mode": "용어를 쉽게 풀고, 다음 행동을 좁게 제안",
      "reference_policy": "optional",
      "reference_intensity": "none",
      "render_depth": "교과 개념 설명 + 실제로 가능한 활동 정리",
      "expression_policy": "짧고 정확한 문장, 과장 없는 1인칭/학생 맥락 중심",
      "advanced_features_allowed": false,
      "max_output_chars": 900,
      "temperature": 0.2,
      "minimum_turn_count": 2,
      "minimum_reference_count": 0,
      "render_threshold": 45
    },
    "mid": {
      "level": "mid",
      "label": "표준형",
      "emoji": "📝",
      "color": "blue",
      "description": "교과 응용과 간단한 확장을 포함하되 학생 수준을 넘지 않게 조절합니다.",
      "detail": "한 학기 안에 마무리할 수 있는 탐구 질문과 근거 계획을 만들고, 결론의 세기를 통제합니다.",
      "student_fit": "교과 응용 + 간단한 확장",
      "safety_posture": "응용은 허용하되 결론의 세기를 보수적으로 유지합니다.",
      "authenticity_policy": "학생이 말한 활동과 간단한 자료 해석만 허용합니다.",
      "hallucination_guardrail": "수행과 계획, 사실과 해석을 분리해서 서술합니다.",
      "starter_mode": "질문 구체화와 증거 계획 설계 중심",
      "followup_mode": "근거 보강과 결론 세기 조절 중심",
      "reference_policy": "recommended",
      "reference_intensity": "light",
      "render_depth": "교과 응용 + 간단한 분석/소결론",
      "expression_policy": "설명과 해석의 균형, 안전한 확장만 허용",
      "advanced_features_allowed": false,
      "max_output_chars": 1300,
      "temperature": 0.35,
      "minimum_turn_count": 3,
      "minimum_reference_count": 0,
      "render_threshold": 60
    },
    "high": {
      "level": "high",
      "label": "심화형",
      "emoji": "🔬",
      "color": "violet",
      "description": "심화형이지만 학생이 실제로 말한 맥락과 근거에만 기대어 작성합니다.",
      "detail": "출처와 학생 실제 경험을 분리해서 쓰며, 근거가 빈약하면 자동으로 더 안전한 수준으로 낮춥니다.",
      "student_fit": "심화형이지만 학생 실제 맥락 기반",
      "safety_posture": "심화 연결은 허용하지만 학생 맥락과 출처 분리를 강제합니다.",
      "authenticity_policy": "학생 경험, 해석, 외부 근거를 반드시 분리합니다.",
      "hallucination_guardrail": "근거가 빈약하면 자동 강등 후 안전 재작성합니다.",
      "starter_mode": "심화 질문을 실제 경험과 자료로 좁히는 방식",
      "followup_mode": "주장·근거·출처를 분리해 심화를 안전하게 유지",
      "reference_policy": "required",
      "reference_intensity": "required",
      "render_depth": "심화 연결 + 출처 기반 해석, 단 학생 실제 맥락 한정",
      "expression_policy": "전문성보다 학생 현실감 우선, 고교 맥락 밖 비약 금지",
      "advanced_features_allowed": true,
      "max_output_chars": 1700,
      "temperature": 0.45,
      "minimum_turn_count": 4,
      "minimum_reference_count": 1,
      "render_threshold": 75
    }
  }
}
