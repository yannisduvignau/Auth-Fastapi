from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Union

SECRET_KEY = "455f1f4c554957c70d41757f4384ce7db6524680c0b1803d3062a4b435fe9f60"  # Clé secrète pour le JWT
ALGORITHM = "HS256"  # Algorithme de cryptage utilisé pour le JWT
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # Durée d'expiration du token d'accès

# Base de données fictive contenant des utilisateurs
db = {}

# Modèle pour représenter le token d'accès
class Token(BaseModel):
    access_token: str
    token_type: str
    
# Modèle pour représenter les données du token
class TokenData(BaseModel):
    username: Union[str, None] = None
    
# Modèle pour représenter un utilisateur
class User(BaseModel):
    username: str
    email: EmailStr  # Utilisation d'EmailStr pour une validation de l'email
    full_name: Union[str, None] = None
    disabled: Union[bool, None] = None

# Modèle pour représenter un utilisateur lors de l'inscription
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: Union[str, None] = None
    password: str  # Ajout d'un champ pour le mot de passe

# Modèle pour représenter un utilisateur dans la base de données avec le mot de passe haché
class UserInDB(User):
    hashed_password: str

# Configuration de l'algorithme de hachage
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # Définition du schéma d'authentification OAuth2

app = FastAPI()  # Création de l'instance de l'application FastAPI

def verify_password(plain_password, hashed_password):
    """Vérifie si le mot de passe en clair correspond au mot de passe haché."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Retourne le mot de passe haché à partir d'un mot de passe en clair."""
    return pwd_context.hash(password)

def get_user(db, username: str):
    """Récupère un utilisateur de la base de données par son nom d'utilisateur."""
    if username in db:
        user_data = db[username]
        return UserInDB(**user_data)  # Retourne l'utilisateur sous forme de UserInDB
    
def authenticate_user(db, username: str, password: str):
    """Authentifie un utilisateur en vérifiant son nom d'utilisateur et son mot de passe."""
    user = get_user(db, username)
    if not user:
        return False  # Utilisateur non trouvé
    if not verify_password(password, user.hashed_password):
        return False  # Mot de passe incorrect
    
    return user  # Retourne l'utilisateur si l'authentification réussit

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    """Crée un token d'accès avec une date d'expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta  # Date d'expiration personnalisée
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)  # Date d'expiration par défaut de 15 minutes
        
    to_encode.update({"exp": expire})  # Ajoute la date d'expiration au payload
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # Encode le token
    
    return encoded_jwt  # Retourne le token encodé

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Récupère l'utilisateur actuel à partir du token fourni."""
    credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Couldn't validate credentials", headers={"WWW-Authenticate": "Bearer"})
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # Décode le token
        username: str = payload.get("sub")  # Récupère le nom d'utilisateur du payload
        if username is None:
            raise credential_exception  # Lève une exception si le nom d'utilisateur est absent
        
        token_data = TokenData(username=username)
    except JWTError:
        raise credential_exception  # Lève une exception en cas d'erreur de décodage
    
    user = get_user(db, username=token_data.username)  # Récupère l'utilisateur de la base de données
    if user is None:
        raise credential_exception  # Lève une exception si l'utilisateur n'existe pas

    return user  # Retourne l'utilisateur

async def get_current_active_user(current_user: UserInDB = Depends(get_current_user)):
    """Vérifie si l'utilisateur actuel est actif (non désactivé)."""
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")  # Lève une exception si l'utilisateur est désactivé
    
    return current_user  # Retourne l'utilisateur actif

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """Endpoint pour obtenir un token d'accès après authentification."""
    user = authenticate_user(db, form_data.username, form_data.password)  # Authentifie l'utilisateur
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # Durée d'expiration du token
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)  # Crée le token
    
    return {"access_token": access_token, "token_type": "bearer"}  # Retourne le token et son type

@app.post("/register", response_model=User)
async def register(user: UserCreate):
    """Endpoint pour l'inscription d'un nouvel utilisateur."""
    # Vérifie si l'utilisateur existe déjà
    if user.username in db:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Hache le mot de passe de l'utilisateur
    hashed_password = get_password_hash(user.password)
    
    # Crée un nouvel utilisateur et l'ajoute à la base de données
    db[user.username] = {
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "hashed_password": hashed_password,
        "disabled": False
    }
    
    return user  # Retourne les informations de l'utilisateur enregistré

@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Endpoint pour récupérer les informations de l'utilisateur actuel."""
    return current_user  # Retourne l'utilisateur actuel

@app.get("/users/me/items")
async def read_own_items(current_user: User = Depends(get_current_active_user)):
    """Endpoint pour récupérer les éléments de l'utilisateur actuel."""
    return [{"item_id": 1, "owner": current_user}]  # Retourne une liste d'éléments appartenant à l'utilisateur
