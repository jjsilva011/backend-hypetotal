# C:\Users\jails\OneDrive\Desktop\Backend HypeTotal\src\models\__init__.py
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(64), nullable=False, unique=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Float, default=0.0)
    stock = db.Column(db.Integer, nullable=False, default=0)  # <— NOVO
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f"<Product id={self.id} sku={self.sku!r} name={self.name!r}>"

__all__ = ["db", "Product"]


