from uuid import UUID

from sqlalchemy.orm import Session

from db.model.sponsorship import SponsorshipDB
from db.schema.sponsorship import SponsorshipSave


class SponsorshipCRUD:

    _db: Session

    def __init__(self, db: Session):
        self._db = db

    def get(self, sponsor_id: UUID, receiver_id: UUID) -> SponsorshipDB | None:
        return self._db.query(SponsorshipDB).filter(
            SponsorshipDB.sponsor_id == sponsor_id,
            SponsorshipDB.receiver_id == receiver_id,
        ).first()

    def get_all_by_sponsor(self, sponsor_id: UUID, skip: int = 0, limit: int = 100) -> list[SponsorshipDB]:
        # noinspection PyTypeChecker
        return self._db.query(SponsorshipDB).filter(
            SponsorshipDB.sponsor_id == sponsor_id,
        ).offset(skip).limit(limit).all()

    def get_all_by_receiver(self, receiver_id: UUID, skip: int = 0, limit: int = 100) -> list[SponsorshipDB]:
        # noinspection PyTypeChecker
        return self._db.query(SponsorshipDB).filter(
            SponsorshipDB.receiver_id == receiver_id,
        ).offset(skip).limit(limit).all()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[SponsorshipDB]:
        # noinspection PyTypeChecker
        return self._db.query(SponsorshipDB).offset(skip).limit(limit).all()

    def create(self, create_data: SponsorshipSave) -> SponsorshipDB:
        sponsorship = SponsorshipDB(**create_data.model_dump())
        self._db.add(sponsorship)
        self._db.commit()
        self._db.refresh(sponsorship)
        return sponsorship

    def update(self, update_data: SponsorshipSave) -> SponsorshipDB | None:
        sponsorship = self.get(update_data.sponsor_id, update_data.receiver_id)
        if sponsorship:
            for key, value in update_data.model_dump().items():
                setattr(sponsorship, key, value)
            self._db.commit()
            self._db.refresh(sponsorship)
        return sponsorship

    def save(self, data: SponsorshipSave) -> SponsorshipDB:
        updated_sponsorship = self.update(data)
        if updated_sponsorship:
            return updated_sponsorship  # available only if update was successful
        return self.create(data)

    def delete(self, sponsor_id: UUID, receiver_id: UUID) -> SponsorshipDB | None:
        sponsorship = self.get(sponsor_id, receiver_id)
        if sponsorship:
            self._db.delete(sponsorship)
            self._db.commit()
        return sponsorship

    def delete_all_by_receiver(self, receiver_id: UUID) -> int:
        result = self._db.query(SponsorshipDB).filter(
            SponsorshipDB.receiver_id == receiver_id,
        ).delete(synchronize_session = False)  # optimizes by assuming no other session will use these objects
        self._db.commit()
        return result
