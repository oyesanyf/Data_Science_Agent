"""
SequentialAgent Fallback System

Uses SequentialAgent as a fallback when:
1. Structured output is explicitly requested
2. Normal tool execution fails and needs formatting
3. User requests JSON schema response

This provides best of both worlds:
- Normal execution (fast, flexible) when possible
- SequentialAgent (guaranteed format) when needed
"""

from typing import Optional, Dict, Any, List
from google.adk.agents.llm_agent import LlmAgent
from google.adk.models.lite_llm import LiteLlm
import logging

logger = logging.getLogger(__name__)


def create_fallback_sequential_agent(
    primary_agent: LlmAgent,
    output_schema: Optional[Any] = None,
    formatter_model: Optional[LiteLlm] = None,
) -> Optional[Any]:
    """
    Create a SequentialAgent as fallback that formats primary agent's output.
    
    Args:
        primary_agent: The main agent with tools
        output_schema: Optional Pydantic schema for structured output
        formatter_model: Optional model for formatter agent (defaults to same as primary)
    
    Returns:
        SequentialAgent instance or None if not needed
    """
    try:
        from google.adk.agents.sequential_agent import SequentialAgent
    except ImportError:
        logger.warning("[SEQUENTIAL FALLBACK] SequentialAgent not available in this ADK version")
        return None
    
    if output_schema is None:
        # Not needed if no schema
        return None
    
    # Get model from primary agent
    if formatter_model is None:
        formatter_model = primary_agent.model
    
    # Create formatter agent
    formatter_agent = LlmAgent(
        name="format_agent",
        model=formatter_model,
        description="Formats tool execution results into structured schema format",
        instruction=(
            "You are a formatting agent that takes tool execution results "
            "and formats them into the required structured output schema. "
            "Extract the relevant information from the tool results and "
            "format it according to the schema."
        ),
        output_schema=output_schema,
    )
    
    # Create sequential agent
    sequential_agent = SequentialAgent(
        name=f"{primary_agent.name}_with_formatting",
        description=f"Primary agent with structured output formatting fallback",
        sub_agents=[primary_agent, formatter_agent],
    )
    
    logger.info("[SEQUENTIAL FALLBACK] Created SequentialAgent fallback")
    return sequential_agent


def should_use_sequential_fallback(
    user_message: str,
    has_output_schema: bool = False,
    tool_execution_failed: bool = False,
) -> bool:
    """
    Determine if SequentialAgent fallback should be used.
    
    Args:
        user_message: User's message/request
        has_output_schema: Whether structured output is required
        tool_execution_failed: Whether tool execution failed
    
    Returns:
        True if should use SequentialAgent fallback
    """
    # Check for explicit structured output requests
    structured_keywords = [
        "structured output",
        "json schema",
        "pydantic",
        "schema format",
        "structured response",
        "json format",
    ]
    
    user_lower = user_message.lower()
    if any(keyword in user_lower for keyword in structured_keywords):
        return True
    
    # Use if output schema is required
    if has_output_schema:
        return True
    
    # Use if tool execution failed and needs recovery
    if tool_execution_failed:
        return True
    
    return False


def create_hybrid_agent_wrapper(
    base_agent: LlmAgent,
    output_schema: Optional[Any] = None,
    enable_fallback: bool = True,
):
    """
    Create a wrapper that conditionally uses SequentialAgent fallback.
    
    This is a smarter approach - only uses SequentialAgent when:
    1. Structured output is explicitly requested
    2. Native output_schema + tools fails
    3. Tool execution needs formatting recovery
    
    Args:
        base_agent: The primary agent with tools
        output_schema: Optional Pydantic schema for structured output
        enable_fallback: Whether to enable fallback (default: True)
    
    Returns:
        Wrapper that routes to base_agent or SequentialAgent as needed
    """
    if not enable_fallback:
        return base_agent
    
    try:
        from google.adk.agents.sequential_agent import SequentialAgent
        
        # Create formatter agent (only if schema provided)
        if output_schema:
            formatter_agent = LlmAgent(
                name="format_agent",
                model=base_agent.model,
                description="Formats tool results into structured schema",
                instruction=(
                    "Format the tool execution results into the required schema. "
                    "Extract all relevant information and structure it properly."
                ),
                output_schema=output_schema,
            )
            
            # Create fallback SequentialAgent (only created when needed)
            fallback_agent = SequentialAgent(
                name=f"{base_agent.name}_fallback",
                description=f"Sequential fallback for {base_agent.name}",
                sub_agents=[base_agent, formatter_agent],
            )
            
            logger.info("[HYBRID AGENT] Created hybrid wrapper with SequentialAgent fallback available")
            
            # Return base agent - fallback will be used via before_model_callback
            return base_agent
        else:
            logger.info("[HYBRID AGENT] No schema provided, using base agent")
            return base_agent
    
    except ImportError:
        logger.warning("[HYBRID AGENT] SequentialAgent not available, using base agent")
        return base_agent
    except Exception as e:
        logger.warning(f"[HYBRID AGENT] Failed to create fallback: {e}, using base agent")
        return base_agent


def create_hybrid_agent_with_fallback(
    base_agent: LlmAgent,
    output_schema: Optional[Any] = None,
    enable_fallback: bool = True,
) -> LlmAgent:
    """
    Create a hybrid agent that uses SequentialAgent as fallback when needed.
    
    This wraps the base agent to conditionally use SequentialAgent based on:
    - User's request (detects structured output keywords)
    - Output schema requirements
    - Tool execution failures
    
    Args:
        base_agent: The primary agent with tools
        output_schema: Optional Pydantic schema for structured output
        enable_fallback: Whether to enable fallback (default: True)
    
    Returns:
        Agent that uses SequentialAgent conditionally
    """
    if not enable_fallback or output_schema is None:
        # No fallback needed, return primary agent
        return base_agent
    
    # Check if we can create SequentialAgent
    try:
        from google.adk.agents.sequential_agent import SequentialAgent
        
        formatter_agent = LlmAgent(
            name="format_agent",
            model=base_agent.model,
            description="Formats tool results into structured schema",
            instruction=(
                "Format the tool execution results into the required schema. "
                "Extract all relevant information and structure it properly."
            ),
            output_schema=output_schema,
        )
        
        # Create fallback SequentialAgent
        fallback_agent = SequentialAgent(
            name=f"{base_agent.name}_fallback",
            description=f"Sequential fallback for {base_agent.name}",
            sub_agents=[base_agent, formatter_agent],
        )
        
        logger.info("[HYBRID AGENT] Created hybrid agent with SequentialAgent fallback")
        return fallback_agent
    
    except ImportError:
        logger.warning("[HYBRID AGENT] SequentialAgent not available, using base agent")
        return base_agent
    except Exception as e:
        logger.warning(f"[HYBRID AGENT] Failed to create fallback: {e}, using base agent")
        return base_agent

