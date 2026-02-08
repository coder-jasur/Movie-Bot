from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.database.models import Referral


class ReferralActions:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_referral(self, name: str) -> Referral:
        referral = Referral(name=name)
        self.session.add(referral)
        await self.session.commit()
        await self.session.refresh(referral)
        return referral

    async def get_referral(self, referral_id: int) -> Referral | None:
        stmt = select(Referral).where(Referral.referral_id == referral_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_referrals(self) -> list[Referral]:
        stmt = select(Referral).order_by(Referral.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def increment_joined_count(self, referral_id: int):
        stmt = update(Referral).where(Referral.referral_id == referral_id).values(
            joined_count=Referral.joined_count + 1
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def delete_referral(self, referral_id: int):
        stmt = delete(Referral).where(Referral.referral_id == referral_id)
        await self.session.execute(stmt)
        await self.session.commit()
