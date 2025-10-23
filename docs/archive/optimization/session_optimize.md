# Session Optimization Plan

## Current State Analysis

### Session Structure
```python
{
    'session_id': str,
    'created_at': str,  # ISO format
    'messages': List[Dict],
    'last_active': float,  # timestamp
    'metadata': Dict[str, Any]  # Currently unstructured
}
```

### Identified Issues
1. Unstructured metadata
2. No validation for metadata fields
3. No default metadata values
4. No standardized metadata schema
5. No metadata update tracking

## Proposed Improvements

### 1. Metadata Schema Definition
```python
class SessionMetadata(TypedDict, total=False):
    name: str                # Session name
    turn_count: int         # Conversation turn count
    is_starred: bool        # Starred/favorite status
    tags: List[str]        # Session tags
    description: str        # Session description
    category: str          # Session category
    language: str          # Primary programming language
    status: str           # Session status (active/archived/deleted)
    last_modified: str    # Last metadata modification time
    modified_by: str      # Last modifier identifier
    model: str           # LLM model used
    context_window: int  # Context window size
    max_tokens: int     # Max tokens setting
```

### 2. Default Metadata Implementation
```python
DEFAULT_METADATA = {
    "name": "",
    "turn_count": 0,
    "is_starred": False,
    "tags": [],
    "description": "",
    "category": "general",
    "language": "python",
    "status": "active",
    "last_modified": None,
    "modified_by": None,
    "model": None,
    "context_window": None,
    "max_tokens": None
}
```

### 3. Metadata Validation Functions
```python
def validate_metadata(metadata: Dict[str, Any]) -> bool:
    required_fields = ["name", "status"]
    if not all(field in metadata for field in required_fields):
        return False
        
    type_checks = {
        "turn_count": int,
        "is_starred": bool,
        "tags": list,
        "context_window": (int, type(None)),
        "max_tokens": (int, type(None))
    }
    
    return all(
        isinstance(metadata.get(field), types)
        for field, types in type_checks.items()
        if field in metadata
    )
```

### 4. Enhanced Metadata Management Methods

#### Create Session with Metadata
```python
def create_session(self, metadata: Optional[Dict] = None) -> Dict:
    base_metadata = DEFAULT_METADATA.copy()
    if metadata:
        base_metadata.update(metadata)
    base_metadata["last_modified"] = datetime.now().isoformat()
    
    session = {
        'session_id': str(uuid.uuid4()),
        'created_at': datetime.now().isoformat(),
        'messages': [],
        'last_active': time.time(),
        'metadata': base_metadata
    }
    return session
```

#### Update Metadata with Validation
```python
def update_session_metadata(self, session_id: str, 
                          metadata: Dict[str, Any],
                          modifier: str = None) -> bool:
    session = self.get_session(session_id)
    if not session:
        return False
        
    if not validate_metadata(metadata):
        return False
        
    session['metadata'].update(metadata)
    session['metadata']['last_modified'] = datetime.now().isoformat()
    session['metadata']['modified_by'] = modifier
    
    self._persist_session(session_id, session)
    return True
```

### 5. Metadata Search and Filter Functions

```python
def find_sessions_by_metadata(self, 
                            filters: Dict[str, Any]) -> List[Dict]:
    """Find sessions matching metadata filters"""
    matches = []
    for session in self.sessions.values():
        if all(
            session['metadata'].get(k) == v 
            for k, v in filters.items()
        ):
            matches.append(session)
    return matches

def get_sessions_by_tag(self, tag: str) -> List[Dict]:
    """Get all sessions with specific tag"""
    return [
        session for session in self.sessions.values()
        if tag in session['metadata'].get('tags', [])
    ]

def get_starred_sessions(self) -> List[Dict]:
    """Get all starred sessions"""
    return [
        session for session in self.sessions.values()
        if session['metadata'].get('is_starred', False)
    ]
```

## Implementation Plan

1. Add TypedDict definition for metadata schema
2. Implement metadata validation functions
3. Update session creation with default metadata
4. Add metadata update tracking
5. Implement metadata search functions
6. Add tests for metadata validation and management
7. Update documentation with metadata schema details

## Migration Plan

1. Create migration script to update existing sessions
2. Add metadata schema version field
3. Implement backward compatibility checks
4. Add metadata validation on session load
5. Create metadata repair functions for invalid data

## Benefits

1. Structured metadata management
2. Improved session organization
3. Better search and filter capabilities
4. Metadata validation and consistency
5. Tracking of metadata changes
6. Enhanced session management features

## Future Enhancements

1. Advanced metadata querying
2. Metadata analytics and reporting
3. Custom metadata fields support
4. Metadata versioning
5. Bulk metadata updates
6. Metadata templates for different session types

## Testing Strategy

1. Unit tests for metadata validation
2. Integration tests for metadata updates
3. Migration tests for existing sessions
4. Performance tests for metadata queries
5. Edge case handling tests
6. Concurrent metadata update tests