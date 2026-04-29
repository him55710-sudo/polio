from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from unifoli_api.api.deps import get_current_user, get_db
from unifoli_api.db.models.user import User
from unifoli_api.schemas.user import UserProfileRead, UserProfileUpdate, UserGoalsUpdate
from unifoli_api.services.user_service import update_user_profile, update_user_goals

router = APIRouter()


@router.get("/me", response_model=UserProfileRead)
def get_my_profile(current_user: User = Depends(get_current_user)) -> UserProfileRead:
    return UserProfileRead.model_validate(current_user)


@router.patch("/me/targets", response_model=UserProfileRead)
def update_my_targets(
    payload: UserGoalsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileRead:
    user = update_user_goals(
        db,
        current_user,
        target_university=payload.target_university,
        target_major=payload.target_major,
        admission_type=payload.admission_type,
        interest_universities=payload.interest_universities,
    )
    return UserProfileRead.model_validate(user)


@router.post("/onboarding/profile", response_model=UserProfileRead)
def onboarding_my_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileRead:
    user = update_user_profile(
        db,
        current_user,
        grade=payload.grade,
        track=payload.track,
        career=payload.career,
        interest_universities=payload.interest_universities,
        marketing_agreed=payload.marketing_agreed,
    )
    return UserProfileRead.model_validate(user)


@router.post("/onboarding/goals", response_model=UserProfileRead)
def onboarding_my_goals(
    payload: UserGoalsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserProfileRead:
    user = update_user_goals(
        db,
        current_user,
        target_university=payload.target_university,
        target_major=payload.target_major,
        admission_type=payload.admission_type,
        interest_universities=payload.interest_universities,
    )
    return UserProfileRead.model_validate(user)
@router.get("/me/interests")
def get_my_interests(current_user: User = Depends(get_current_user)):
    import json
    keywords = []
    if current_user.starred_keywords_json:
        try:
            keywords = json.loads(current_user.starred_keywords_json)
        except:
            keywords = []
    return {"starred_keywords": keywords}
