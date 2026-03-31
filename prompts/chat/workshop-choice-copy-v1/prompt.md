# chat.workshop-choice-copy

- Version: `1.0.0`
- Category: `chat`
- Status: `wired`

## Purpose

Provide the canonical copy bundle for workshop starter choices, follow-up
choices, and acknowledgement messages.

## Input Contract

- Current workshop quality level
- Quest title, target major, and output type when starter choices are built
- Current turn count when follow-up choices are built
- Applied quality profile fields such as `followup_mode` and `render_depth`

## Output Contract

Return a JSON object with:

- `starter_templates`
- `followup_templates`
- `acknowledgements`

The backend formats these templates with runtime values.

## Forbidden

- Overpromising depth that the current quality level does not allow
- Fabricating student activity, outcomes, or source support
- Turning acknowledgements into salesy or guaranteed wording

## Uncertainty Handling

- Keep choice prompts narrow enough to collect one truthful next step
- Use acknowledgement copy that keeps the user grounded in what is still being
  collected

## Evaluation Criteria

- Choice labels are clear and actionable
- Prompt templates stay aligned with the quality level guardrails
- Acknowledgement text reinforces authenticity rather than polish pressure

## Change Log

- `1.0.0`: Initial workshop choice and acknowledgement copy extracted from backend inline strings.

## Prompt Body

{
  "starter_templates": {
    "low": [
      {
        "id": "low_core_concept",
        "label": "핵심 개념부터 정리",
        "description": "교과 개념과 실제로 가능한 활동 범위를 먼저 맞춥니다.",
        "prompt_template": "'{quest_label}'에서 먼저 확인해야 할 교과 개념 2개와, 이번 학기 안에 실제로 할 수 있는 활동만 골라 줘."
      },
      {
        "id": "low_finishable_scope",
        "label": "가능한 방법 고르기",
        "description": "학생 수준에서 끝낼 수 있는 방법만 좁힙니다.",
        "prompt_template": "'{quest_label}'를 {major_label}와 연결하되 학교 안에서 마칠 수 있는 방법 3가지만 좁혀 줘."
      },
      {
        "id": "low_record_sentence",
        "label": "기록 문장 방향 잡기",
        "description": "과장 없는 세특 문장 톤을 먼저 정합니다.",
        "prompt_template": "'{quest_label}'를 바탕으로 실제 학생 맥락에서 쓸 수 있는 기록 문장 방향만 안전하게 정리해 줘."
      }
    ],
    "mid": [
      {
        "id": "mid_question",
        "label": "탐구 질문 구체화",
        "description": "교과 응용 질문을 한 학기 안에 끝낼 수 있게 좁힙니다.",
        "prompt_template": "'{quest_label}'를 {major_label}와 연결되는 하나의 구체적인 탐구 질문으로 좁혀 줘."
      },
      {
        "id": "mid_evidence_plan",
        "label": "증거 계획 세우기",
        "description": "관찰·자료·비교 포인트를 3개 안팎으로 정리합니다.",
        "prompt_template": "'{quest_label}'로 {output_label}을 만들기 위해 필요한 근거와 기록 포인트를 3개로 정리해 줘."
      },
      {
        "id": "mid_safe_conclusion",
        "label": "안전한 결론 톤 잡기",
        "description": "결론은 세게 쓰지 않고 학생 수준으로 맞춥니다.",
        "prompt_template": "'{quest_label}'의 결론을 과장 없이 쓰려면 어떤 표현까지 허용되는지 안전한 기준을 잡아 줘."
      }
    ],
    "high": [
      {
        "id": "high_narrow_question",
        "label": "심화 질문 좁히기",
        "description": "심화 질문을 학생 실제 맥락 안으로 좁힙니다.",
        "prompt_template": "'{quest_label}'를 심화형으로 다루되 학생이 실제로 수행하거나 말한 범위 안에서만 질문을 좁혀 줘."
      },
      {
        "id": "high_source_frame",
        "label": "출처 기반 분석 틀",
        "description": "핵심 주장과 필요한 출처를 먼저 분리합니다.",
        "prompt_template": "'{quest_label}'로 {output_label}을 만들 때 학생 경험, 해석, 외부 출처를 각각 어떻게 나눌지 틀을 잡아 줘."
      },
      {
        "id": "high_grounded_depth",
        "label": "경험과 심화 연결",
        "description": "실제 활동과 심화 개념의 연결만 남깁니다.",
        "prompt_template": "'{quest_label}'에서 학생이 직접 한 것과 심화 해석을 구분해, {major_label} 맥락에 맞는 연결만 남겨 줘."
      }
    ]
  },
  "followup_templates": {
    "low": [
      {
        "id_template": "low_followup_simple_{turn_count}",
        "label": "용어를 더 쉽게 풀기",
        "description": "어려운 표현을 교과 수준으로 낮춥니다.",
        "prompt_template": "방금 내용에서 어려운 표현을 교과 수준 말로 다시 풀어 줘."
      },
      {
        "id_template": "low_followup_next_step_{turn_count}",
        "label": "지금 할 수 있는 다음 행동",
        "description": "이번 주 안에 할 수 있는 작은 행동으로 좁힙니다.",
        "prompt_template": "지금 수준에서 바로 해볼 수 있는 다음 행동 2가지만 골라 줘."
      },
      {
        "id_template": "low_followup_record_{turn_count}",
        "label": "세특 문장 한 줄로",
        "description": "과장 없는 기록 문장 톤을 확인합니다.",
        "prompt_template": "이 내용을 세특 문장 한 줄로 쓰면 어떤 톤이 안전한지 보여 줘."
      }
    ],
    "mid": [
      {
        "id_template": "mid_followup_evidence_{turn_count}",
        "label": "근거를 3단계로 정리",
        "description": "주장-근거-기록 포인트를 바로 정리합니다.",
        "prompt_template": "지금까지 나온 내용을 주장, 근거, 기록 포인트 3단계로 정리해 줘."
      },
      {
        "id_template": "mid_followup_compare_{turn_count}",
        "label": "비교 포인트 하나 더",
        "description": "교과 응용 범위 안에서 비교 관점을 더합니다.",
        "prompt_template": "과하지 않은 비교 포인트를 하나 더 찾아 줘."
      },
      {
        "id_template": "mid_followup_tone_{turn_count}",
        "label": "결론을 안전하게 다듬기",
        "description": "결론의 세기를 학생 수준으로 맞춥니다.",
        "prompt_template": "결론이 너무 세지 않도록 안전한 표현으로 다시 다듬어 줘."
      }
    ],
    "high": [
      {
        "id_template": "high_followup_source_{turn_count}",
        "label": "출처가 필요한 주장만 고르기",
        "description": "학생 경험과 외부 근거를 분리합니다.",
        "prompt_template": "지금까지 나온 내용 중에서 반드시 출처가 필요한 주장만 골라 줘."
      },
      {
        "id_template": "high_followup_split_{turn_count}",
        "label": "학생이 한 것과 해석 분리",
        "description": "허위 경험 생성 위험을 먼저 줄입니다.",
        "prompt_template": "학생이 실제로 한 것과 그에 대한 해석을 분리해서 정리해 줘."
      },
      {
        "id_template": "high_followup_school_level_{turn_count}",
        "label": "심화 표현을 고교 수준으로",
        "description": "심화는 유지하되 학생 수준을 넘지 않게 다듬습니다.",
        "prompt_template": "심화 개념은 유지하되 고교 학생이 실제로 쓸 수 있는 표현으로 다시 낮춰 줘."
      }
    ]
  },
  "acknowledgements": {
    "choice_template": "[{profile_label}] '{label}' 방향으로 워크샵 맥락을 더 구체화했습니다. 이 수준에서는 {followup_mode}에 맞춰 한 단계씩 좁혀 가겠습니다.",
    "message_template": "[{profile_label}] 입력한 내용을 학생 실제 맥락으로 저장했습니다. {render_depth}을 목표로 계속 수집합니다. {guidance}",
    "guidance_template": "다음으로는 '{next_choice_label}' 쪽으로 이어가면 좋습니다."
  }
}
