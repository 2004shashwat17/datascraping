"""
Authentication endpoints for user registration and login.
Handles JWT token generation and user management.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.models.mongo_models import User, PlatformEnum
from app.core.config import get_settings
from app.services.no_api_collector import no_api_collector

settings = get_settings()

# Temporary in-memory user storage (fallback when MongoDB is not available)
temp_users = {}
mongodb_available = False

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

router = APIRouter()


class UserCreate(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


async def get_user_by_username(username: str) -> Optional[User]:
    """Get user by username."""
    try:
        user = await User.find_one(User.username == username)
        return user
    except Exception as e:
        print(f"Database query failed: {e}")
        # Fallback to in-memory storage
        if username in temp_users:
            # Create a mock User object for compatibility
            user_data = temp_users[username]
            # Create a simple object that behaves like a User
            class MockUser:
                def __init__(self, data):
                    self.username = data.get('username')
                    self.email = data.get('email')
                    self.full_name = data.get('full_name')
                    self.hashed_password = data.get('hashed_password')
                    self.is_active = data.get('is_active', True)
                    self.id = data.get('id')
                    
                    # Add missing attributes from the real User model
                    self.enabled_platforms = data.get('enabled_platforms', [])
                    self.permissions_granted = data.get('permissions_granted', False)
                    self.last_permissions_update = data.get('last_permissions_update')
                    self.created_at = data.get('created_at')
                    self.updated_at = data.get('updated_at')
                    
                async def save(self):
                    """Mock save method for compatibility"""
                    # Update the in-memory storage
                    temp_users[self.username] = {
                        'username': self.username,
                        'email': self.email,
                        'full_name': self.full_name,
                        'hashed_password': self.hashed_password,
                        'is_active': self.is_active,
                        'id': self.id,
                        'enabled_platforms': self.enabled_platforms,
                        'permissions_granted': self.permissions_granted,
                        'last_permissions_update': self.last_permissions_update,
                        'created_at': self.created_at,
                        'updated_at': self.updated_at
                    }
            
            return MockUser(user_data)
        return None


async def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email."""
    try:
        return await User.find_one(User.email == email)
    except Exception as e:
        print(f"Database query failed: {e}")
        # Fallback to in-memory storage
        for user_data in temp_users.values():
            if user_data.get("email") == email:
                # Create a mock User object for compatibility
                class MockUser:
                    def __init__(self, data):
                        self.username = data.get('username')
                        self.email = data.get('email')
                        self.full_name = data.get('full_name')
                        self.hashed_password = data.get('hashed_password')
                        self.is_active = data.get('is_active', True)
                        self.id = data.get('id')
                        
                        # Add missing attributes from the real User model
                        self.enabled_platforms = data.get('enabled_platforms', [])
                        self.permissions_granted = data.get('permissions_granted', False)
                        self.last_permissions_update = data.get('last_permissions_update')
                        self.created_at = data.get('created_at')
                        self.updated_at = data.get('updated_at')
                        
                    async def save(self):
                        """Mock save method for compatibility"""
                        # Update the in-memory storage
                        temp_users[self.username] = {
                            'username': self.username,
                            'email': self.email,
                            'full_name': self.full_name,
                            'hashed_password': self.hashed_password,
                            'is_active': self.is_active,
                            'id': self.id,
                            'enabled_platforms': self.enabled_platforms,
                            'permissions_granted': self.permissions_granted,
                            'last_permissions_update': self.last_permissions_update,
                            'created_at': self.created_at,
                            'updated_at': self.updated_at
                        }
                
                return MockUser(user_data)
        return None


async def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user credentials."""
    user = await get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = await get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=Token)
async def register(user_data: UserCreate):
    """Register a new user."""
    # Check if user already exists
    existing_user = await get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    existing_email = await get_user_by_email(user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    
    # Try to create and save user to MongoDB
    try:
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
            is_active=True
        )
        await user.insert()
        user_id = str(user.id)
    except Exception as db_error:
        print(f"MongoDB save failed: {db_error}")
        # Fallback to in-memory storage
        import uuid
        user_id = str(uuid.uuid4())
        user_dict = {
            "username": user_data.username,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "hashed_password": hashed_password,
            "is_active": True,
            "permissions_granted": False,
            "enabled_platforms": []
        }
        temp_users[user_data.username] = user_dict
        # Don't create User object in fallback mode, create response directly
        user = None
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data.username}, expires_delta=access_token_expires
    )
    
    # Create user response
    if user:
        # MongoDB successful
        user_response = UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active
        )
    else:
        # Fallback mode
        user_response = UserResponse(
            id=user_id,
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            is_active=True
        )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_response
    )


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login user and return access token."""
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active
        )
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout user (client should remove token)."""
    # In a JWT-based system, logout is handled client-side by removing the token
    # This endpoint confirms the user was authenticated before logout
    return {"message": f"User {current_user.username} successfully logged out"}


class PlatformPermissions(BaseModel):
    platforms: List[str]


@router.post("/permissions")
async def update_permissions(
    permissions: PlatformPermissions,
    current_user: User = Depends(get_current_user)
):
    """Update user's social media platform permissions and trigger data collection."""
    # Convert permissions to list of enabled platforms
    enabled_platforms = []
    
    for platform_str in permissions.platforms:
        try:
            platform_enum = PlatformEnum(platform_str.lower())
            enabled_platforms.append(platform_enum)
        except ValueError:
            # Skip invalid platform names
            continue
    
    # Update user permissions
    current_user.enabled_platforms = enabled_platforms
    current_user.permissions_granted = True
    current_user.last_permissions_update = datetime.utcnow()
    
    await current_user.save()
    
    # Trigger HYBRID data collection if platforms are enabled
    collection_result = None
    if enabled_platforms:
        try:
            collection_result = await no_api_collector.collect_data_for_user(current_user)
        except Exception as e:
            # Log error but don't fail the permission update
            print(f"Hybrid collection error: {e}")
            collection_result = {"error": "Hybrid collection failed", "message": str(e)}
    
    response = {
        "message": "Permissions updated successfully",
        "enabled_platforms": [platform.value for platform in enabled_platforms]
    }
    
    if collection_result:
        response["data_collection"] = collection_result
    
    return response


@router.post("/collect-data")
async def trigger_data_collection(current_user: User = Depends(get_current_user)):
    """Manually trigger data collection for the current user."""
    if not current_user.permissions_granted or not current_user.enabled_platforms:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No platforms enabled for data collection"
        )
    
    try:
        result = await no_api_collector.collect_data_for_user(current_user)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hybrid data collection failed: {str(e)}"
        )


@router.get("/permissions")
async def get_permissions(current_user: User = Depends(get_current_user)):
    """Get user's current platform permissions."""
    return {
        "permissions_granted": current_user.permissions_granted,
        "enabled_platforms": [platform.value for platform in current_user.enabled_platforms],
        "last_update": current_user.last_permissions_update
    }