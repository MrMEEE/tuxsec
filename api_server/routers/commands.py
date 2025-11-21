from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db, Command, Agent
from ..schemas import CommandRequest, CommandResponse, AgentCommand
from ..command_dispatcher import CommandDispatcher
from ..auth import verify_agent_api_key

router = APIRouter()
command_dispatcher = CommandDispatcher()


@router.post("/{agent_id}/commands", response_model=CommandResponse)
async def execute_command(
    agent_id: str,
    command_request: CommandRequest,
    db: Session = Depends(get_db)
):
    """Execute command on agent"""
    try:
        command_id = await command_dispatcher.dispatch_command(
            agent_id, 
            command_request.command, 
            command_request.params
        )
        
        return CommandResponse(
            command_id=command_id,
            status="pending",
            message="Command queued for execution"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_id}/commands", response_model=List[AgentCommand])
async def list_agent_commands(
    agent_id: str, 
    agent: Agent = Depends(verify_agent_api_key),
    db: Session = Depends(get_db)
):
    """
    List pending commands for an agent (pull mode).
    Requires X-API-Key header for authentication.
    """
    # Verify the agent_id matches the authenticated agent
    if agent.agent_id != agent_id:
        raise HTTPException(
            status_code=403, 
            detail="Cannot access commands for another agent"
        )
    
    commands = db.query(Command).filter(
        Command.agent_id == agent_id,
        Command.status == "pending"
    ).all()
    return commands


@router.get("/commands/{command_id}", response_model=AgentCommand)
async def get_command_status(command_id: str, db: Session = Depends(get_db)):
    """Get command status and result"""
    command = db.query(Command).filter(Command.id == command_id).first()
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    return command


@router.post("/{agent_id}/results/{command_id}")
async def submit_command_result(
    agent_id: str,
    command_id: str,
    result: dict,
    agent: Agent = Depends(verify_agent_api_key),
    db: Session = Depends(get_db)
):
    """
    Submit command execution result (pull mode).
    Requires X-API-Key header for authentication.
    
    Expected result format:
    {
        "success": true,
        "result": {...},
        "error": null,
        "timestamp": "2025-11-21T10:30:00Z"
    }
    """
    # Verify the agent_id matches the authenticated agent
    if agent.agent_id != agent_id:
        raise HTTPException(
            status_code=403, 
            detail="Cannot submit results for another agent"
        )
    
    command = db.query(Command).filter(
        Command.command_id == command_id,
        Command.agent_id == agent_id
    ).first()
    
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    
    # Update command with result
    command.status = "completed" if result.get("success") else "failed"
    command.result = result.get("result")
    command.error = result.get("error")
    command.executed_at = datetime.utcnow()
    command.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Result received",
        "command_id": command_id,
        "status": command.status
    }


@router.delete("/commands/{command_id}")
async def cancel_command(command_id: str, db: Session = Depends(get_db)):
    """Cancel a pending command"""
    command = db.query(Command).filter(Command.id == command_id).first()
    if not command:
        raise HTTPException(status_code=404, detail="Command not found")
    
    if command.status != "pending":
        raise HTTPException(status_code=400, detail="Command cannot be cancelled")
    
    command.status = "cancelled"
    db.commit()
    
    return {"message": "Command cancelled successfully"}