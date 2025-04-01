import uuid
from fastapi_users.authentication import AuthenticationBackend, BearerTransport
from fastapi_users.authentication import JWTStrategy
from fastapi_users import FastAPIUsers
from .database import User
from .manager import get_user_manager

bearer_transport = BearerTransport(tokenUrl="/auth/jwt/login")

SECRET = "SECRET"

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])