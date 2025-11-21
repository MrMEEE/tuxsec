from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import secrets

from ..database import get_db, Agent
from ..schemas import AgentRegistration, AgentInfo, AgentStatusUpdate, AgentHeartbeat
from ..agent_manager import AgentManager
from ..auth import verify_agent_api_key

router = APIRouter()
agent_manager = AgentManager()


@router.post("/register", response_model=AgentInfo)
async def register_agent(agent_data: AgentRegistration, db: Session = Depends(get_db)):
    """
    Register a new agent.
    If no api_key is provided, generates a new one.
    Returns the api_key only during registration - store it securely!
    """
    try:
        # Generate API key if not provided
        api_key = agent_data.api_key or secrets.token_urlsafe(32)
        
        # Check if agent already exists
        existing_agent = db.query(Agent).filter(Agent.hostname == agent_data.hostname).first()
        if existing_agent:
            # Update existing agent
            for key, value in agent_data.dict(exclude={'api_key'}).items():
                if hasattr(existing_agent, key):
                    setattr(existing_agent, key, value)
            # Only update API key if provided in request
            if agent_data.api_key:
                existing_agent.api_key = api_key
            existing_agent.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_agent)
            # Don't return API key for existing agents unless it was just set
            if not agent_data.api_key:
                existing_agent.api_key = None
            return existing_agent
        
        # Create new agent
        agent_dict = agent_data.dict()
        agent_dict['api_key'] = api_key
        agent = Agent(**agent_dict)
        db.add(agent)
        db.commit()
        db.refresh(agent)
        
        # Generate certificate if requested
        if agent_data.certificate_request:
            cert_pem = await agent_manager.generate_agent_certificate(agent.id)
            agent.certificate_issued = True
            db.commit()
        
        # Return agent info with API key (only time it's returned)
        return agent
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[AgentInfo])
async def list_agents(db: Session = Depends(get_db)):
    """List all registered agents"""
    agents = db.query(Agent).all()
    return agents


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get specific agent details"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}/status")
async def update_agent_status(
    agent_id: str, 
    status_update: AgentStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update agent status"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent.status = status_update.status
    agent.last_seen = status_update.timestamp
    agent.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Status updated successfully"}


@router.post("/heartbeat")
async def agent_heartbeat(
    heartbeat: AgentHeartbeat,
    agent: Agent = Depends(verify_agent_api_key),
    db: Session = Depends(get_db)
):
    """
    Agent heartbeat endpoint - updates status, last_seen, and available modules.
    Agents should call this periodically to report their health and capabilities.
    Requires X-API-Key header for authentication.
    """
    # Verify the agent_id matches the authenticated agent
    if agent.agent_id != heartbeat.agent_id:
        raise HTTPException(
            status_code=403, 
            detail="Agent ID in request does not match authenticated agent"
        )
    
    # Update agent status and last seen
    agent.status = heartbeat.status.value
    agent.last_seen = heartbeat.timestamp
    agent.updated_at = datetime.utcnow()
    
    # Update available modules
    if heartbeat.available_modules:
        agent.available_modules = heartbeat.available_modules
    
    # Update version if provided
    if heartbeat.version:
        agent.version = heartbeat.version
    
    db.commit()
    
    return {
        "message": "Heartbeat received",
        "agent_id": agent.agent_id,
        "modules_registered": len(heartbeat.available_modules) if heartbeat.available_modules else 0
    }


@router.delete("/{agent_id}")
async def delete_agent(agent_id: str, db: Session = Depends(get_db)):
    """Delete an agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    db.delete(agent)
    db.commit()
    
    return {"message": "Agent deleted successfully"}


@router.get("/{agent_id}/certificate")
async def get_agent_certificate(agent_id: str, db: Session = Depends(get_db)):
    """Get agent certificate"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    if not agent.certificate_issued:
        raise HTTPException(status_code=404, detail="Certificate not issued")
    
    cert_pem = await agent_manager.get_agent_certificate(agent_id)
    if not cert_pem:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
    return {"certificate": cert_pem}


@router.post("/{agent_id}/certificate")
async def issue_agent_certificate(agent_id: str, db: Session = Depends(get_db)):
    """Issue certificate for agent"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    try:
        cert_pem = await agent_manager.generate_agent_certificate(agent_id)
        agent.certificate_issued = True
        agent.updated_at = datetime.utcnow()
        db.commit()
        
        return {"certificate": cert_pem}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))