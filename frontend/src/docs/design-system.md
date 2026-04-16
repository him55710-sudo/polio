# Uni Foli Design System (Vibrant & Premium)

이 문서는 Uni Foli의 최신 디자인 시스템 가이드를 정의합니다. 모든 컴포넌트 개발 시 아래의 토큰과 가이드를 준수하여 일관된 프리미엄 경험을 유지하십시오.

## 1. Core Colors (Indigo-Purple Theme)

우리의 주요 색상은 신뢰감 있는 **Indigo**와 미래지향적인 **Purple**의 조합입니다.

- **Brand Primary**: `indigo-600` (#4f46e5)
- **Brand Secondary**: `purple-600` (#9333ea)
- **Background Gradient**: `from-indigo-600 via-indigo-500 to-purple-600`
- **Text Gradient**: `.text-gradient` 클래스 사용

## 2. Global Utilities (index.css)

### Glassmorphism
투명하고 고급스러운 레이어 효과를 위해 사용합니다.
```html
<div class="glass-card">...</div>
```

### Claymorphism
입체적이고 생동감 있는 버튼 및 카드 효과입니다.
```html
<div class="clay-card">...</div>
<button class="clay-btn-primary">...</button>
```

### Animations
- `animate-float`: 둥둥 떠 있는 효과 (히어로 섹션 등)
- `animate-pulse-soft`: 은은하게 빛나는 효과 (CTA 강조 등)
- `animate-shine`: 빛이 슥 지나가는 효과

## 3. UI Primitives

- **Buttons**: `frontend/src/components/ui/button.tsx`의 `primary` variant를 우선 사용하십시오.
- **Cards**: `SectionCard`, `SurfaceCard` 프리미티브를 활용하여 일관된 여백과 라운딩(Border Radius)을 유지하십시오.

## 4. Typography
- **Heading**: `font-black` (가장 두꺼운 웨이트)와 `tracking-tight`를 조합하여 현대적인 인상을 줍니다.
- **Body**: `font-medium` 또는 `font-bold`를 사용하여 가독성을 확보하십시오.

---

> [!TIP]
> 새로운 컴포넌트 추가 시 하드코딩된 색상(#1d4fff 등) 대신 Tailwind의 `indigo-600` 또는 정의된 유틸리티 클래스를 사용하면 디자인 시스템과 자동으로 동기화됩니다.
