"""
Authentication dependencies for API endpoints.
"""

from fastapi import HTTPException, Header, Depends
from sqlalchemy.orm import Session
from typing import Optional

from .database import get_db, Agent


async def verify_agent_api_key(
    x_api_key: str = Header(..., description="Agent API key for authentication"),
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Agent:
    """
    Verify agent API key from X-API-Key header.
    
    Args:
        x_api_key: API key from X-API-Key header
        agent_id: Optional agent ID to verify against
        db: Database session
        
    Returns:
        Agent: Authenticated agent object
        
    Raises:
        HTTPException: 401 if API key is invalid or missing
        HTTPException: 404 if agent not found
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # Query agent by API key
    agent = db.query(Agent).filter(Agent.api_key == x_api_key).first()
    
    if not agent:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # If agent_id provided, verify it matches
    if agent_id and agent.agent_id != agent_id:
        raise HTTPException(
            status_code=403,
            detail="API key does not match agent ID"
        )
    
    return agent


async def verify_agent_api_key_optional(
    x_api_key: Optional[str] = Header(None, description="Agent API key for authentication"),
    db: Session = Depends(get_db)
) -> Optional[Agent]:
    """
    Verify agent API key if provided, otherwise return None.
    Used for endpoints that support both authenticated and unauthenticated access.
    
    Args:
        x_api_key: Optional API key from X-API-Key header
        db: Database session
        
    Returns:
        Agent or None: Authenticated agent object or None if no key provided
    """
    if not x_api_key:
        return None
    
    agent = db.query(Agent).filter(Agent.api_key == x_api_key).first()
    return agent
