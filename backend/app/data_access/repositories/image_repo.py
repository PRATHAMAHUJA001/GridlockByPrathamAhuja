from sqlalchemy.orm import Session

from app.data_access.models import Image


class ImageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, image: Image) -> Image:
        self.db.add(image)
        self.db.commit()
        self.db.refresh(image)
        return image

    def get_by_id(self, image_id: str) -> Image | None:
        return self.db.query(Image).filter(Image.id == image_id).first()
