from typing import Union, List, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# Modèle de données pour un item
class Item(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None


# Dictionnaire pour stocker les items
items_db: Dict[int, Item] = {}
current_id = 0

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/items/", response_model=Item)
def create_item(item: Item):
    """Crée un nouvel item et l'ajoute à la base de données."""
    global current_id
    current_id += 1
    items_db[current_id] = item
    return item

@app.get("/items/", response_model=List[Item])
def read_items():
    """Récupère tous les items de la base de données."""
    return list(items_db.values())

@app.get("/items/{item_id}", response_model=Item)
def read_item(item_id: int):
    """Récupère un item spécifique à partir de son ID."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]

@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item: Item):
    """Met à jour un item existant."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    items_db[item_id] = item
    return item

@app.delete("/items/{item_id}")
def delete_item(item_id: int):
    """Supprime un item de la base de données."""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del items_db[item_id]
    return {"detail": "Item deleted"}
