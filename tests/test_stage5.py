"""
Stage 5 Tests: Permissions, Targets Registration, Publishing Workflow.
"""
import pytest
from app.database.models import PublishingTarget, Quiz, QuizState
from app.permissions.service import PermissionService, TargetNotFoundError


@pytest.mark.asyncio
async def test_target_registration_and_ownership(db_session, sample_user, other_user):
    """Verifies target registration and strict ownership isolation."""
    target = await PermissionService.register_or_update_target(
        session=db_session,
        user_id=sample_user.id,
        chat_id=-1001234567890,
        chat_type="channel",
        chat_title="قناة الفيزياء للثانوية",
    )
    assert target.id is not None
    assert target.user_id == sample_user.id

    # Accessible by owner
    fetched = await PermissionService.get_target_by_id(db_session, target.id, sample_user.id)
    assert fetched.chat_title == "قناة الفيزياء للثانوية"

    # Blocked for other user
    with pytest.raises(TargetNotFoundError):
        await PermissionService.get_target_by_id(db_session, target.id, other_user.id)
