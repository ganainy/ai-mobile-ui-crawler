# Contract: CredentialManager

**Module**: `mobile_crawler.domain.credential_manager`  
**Purpose**: Manages storage and retrieval of encrypted app authentication credentials

## Interface

### `class CredentialManager`

Manages encrypted credential storage per app package.

#### Constructor

```python
def __init__(
    self,
    user_config_store: UserConfigStore,
    credential_store: CredentialStore
) -> None
```

**Parameters**:
- `user_config_store`: User configuration store for database access
- `credential_store`: Credential encryption/decryption service

---

### Methods

#### `store_credentials(app_package: str, username: str, password: str, email: str) -> None`

Stores encrypted credentials for an app package.

**Parameters**:
- `app_package`: Android package name (e.g., "com.example.app")
- `username`: Login username
- `password`: Login password
- `email`: Email address used for signup

**Behavior**:
- Encrypts credentials as JSON string
- Stores in `app_credentials` table
- Sets `created_at`, `updated_at`, `last_successful_login_at` timestamps
- Replaces existing credentials if app_package already exists

**Raises**:
- `ValueError`: If any parameter is empty or invalid
- `DatabaseError`: If database operation fails

---

#### `get_credentials(app_package: str) -> Optional[AppCredentials]`

Retrieves decrypted credentials for an app package.

**Parameters**:
- `app_package`: Android package name

**Returns**: `AppCredentials` object if found, `None` if not found or decryption fails

**Behavior**:
- Retrieves encrypted credentials from database
- Decrypts using CredentialStore
- Updates `last_used_at` timestamp
- Returns None if credentials don't exist or decryption fails

**Raises**:
- `DatabaseError`: If database operation fails

---

#### `update_last_successful_login(app_package: str) -> None`

Updates the last successful login timestamp.

**Parameters**:
- `app_package`: Android package name

**Behavior**:
- Updates `last_successful_login_at` timestamp
- Updates `last_used_at` timestamp
- No-op if credentials don't exist

**Raises**:
- `DatabaseError`: If database operation fails

---

#### `delete_credentials(app_package: str) -> bool`

Deletes stored credentials for an app package.

**Parameters**:
- `app_package`: Android package name

**Returns**: `True` if credentials were deleted, `False` if they didn't exist

**Behavior**:
- Removes credentials from database
- Used when login fails (credentials may be invalid)

**Raises**:
- `DatabaseError`: If database operation fails

---

#### `has_credentials(app_package: str) -> bool`

Checks if credentials exist for an app package.

**Parameters**:
- `app_package`: Android package name

**Returns**: `True` if credentials exist, `False` otherwise

**Behavior**:
- Quick check without decryption
- Used to determine if login should be attempted

**Raises**:
- `DatabaseError`: If database operation fails

---

#### `list_apps_with_credentials() -> List[str]`

Lists all app packages that have stored credentials.

**Returns**: List of app package names

**Behavior**:
- Returns all app_package values from database
- Used for debugging or credential management UI

**Raises**:
- `DatabaseError`: If database operation fails

---

## Data Types

### `AppCredentials`

```python
@dataclass
class AppCredentials:
    app_package: str
    username: str
    password: str
    email: str
    created_at: datetime
    last_used_at: Optional[datetime]
    last_successful_login_at: Optional[datetime]
    updated_at: datetime
```

---

## Error Types

### `DatabaseError`

Raised when database operations fail.

```python
class DatabaseError(Exception):
    """Raised when credential database operation fails."""
    pass
```

---

## Usage Example

```python
# Initialize
credential_manager = CredentialManager(
    user_config_store=user_config_store,
    credential_store=credential_store
)

# Store credentials after successful signup
credential_manager.store_credentials(
    app_package="com.example.app",
    username="testuser",
    password="password123",
    email="test@example.com"
)

# Check if credentials exist
if credential_manager.has_credentials("com.example.app"):
    # Retrieve credentials
    creds = credential_manager.get_credentials("com.example.app")
    if creds:
        # Use credentials for login
        username = creds.username
        password = creds.password

# Update after successful login
credential_manager.update_last_successful_login("com.example.app")

# Delete if login fails
credential_manager.delete_credentials("com.example.app")
```

---

## Database Schema

See [data-model.md](../data-model.md) for `app_credentials` table schema.
