from typing import Optional

from tortoise import fields
from tortoise.models import Model
from tortoise.functions import Max


class Feedback(Model):
    feedback_id = fields.IntField(pk=True)
    user_id = fields.BigIntField()
    group_id = fields.BigIntField(null=True)
    content = fields.TextField()
    time = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "feedback"
        table_description = "用户反馈记录"

    @classmethod
    async def add_feedback(
        cls, user_id: int, group_id: Optional[int], content: str
    ) -> int:
        new_feedback: Feedback = cls(
            user_id=user_id, group_id=group_id, content=content
        )
        await new_feedback.save()
        return new_feedback.feedback_id

    @classmethod
    async def get_feedback(cls, feedback_id: int) -> Optional["Feedback"]:
        if feedback := await cls.filter(feedback_id=feedback_id).first():
            return feedback
        return None

    @classmethod
    async def get_max_id(cls) -> int:
        return (
            await cls.all().annotate(max_feedback_id=Max("feedback_id")).first()
        ).feedback_id
