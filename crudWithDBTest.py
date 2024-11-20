from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Configuration de la base de données
DATABASE_URL = "sqlite:///./test.db"  # Utilisation de SQLite
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modèle de données pour la base de données
class ItemModel(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Integer)
    is_offer = Column(Boolean, default=False)

# Créer les tables dans la base de données
Base.metadata.create_all(bind=engine)

# Modèle de données pour l'API
class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = None

# Initialiser l'application FastAPI
app = FastAPI()

# Dépendance pour obtenir une session de base de données
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()





@app.post("/items/", response_model=Item)
def create_item(item: Item, db: Session = Depends(get_db)):
    """Crée un nouvel item dans la base de données."""
    db_item = ItemModel(name=item.name, price=item.price, is_offer=item.is_offer)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/items/", response_model=list[Item])
def read_items(db: Session = Depends(get_db)):
    """Récupère tous les items de la base de données."""
    items = db.query(ItemModel).all()
    return items

@app.get("/items/{item_id}", response_model=Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    """Récupère un item spécifique à partir de son ID."""
    item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item: Item, db: Session = Depends(get_db)):
    """Met à jour un item existant."""
    db_item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db_item.name = item.name
    db_item.price = item.price
    db_item.is_offer = item.is_offer
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Supprime un item de la base de données."""
    db_item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(db_item)
    db.commit()
    return {"detail": "Item deleted"}
