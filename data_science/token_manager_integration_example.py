"""
Token Manager Integration Examples
===================================

Practical examples showing how to integrate the Intelligent Token Manager
into existing data science agent code.
"""

from token_manager import (
    IntelligentTokenManager,
    safe_llm_call,
    ensure_token_limit,
    get_token_manager
)
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# EXAMPLE 1: Protecting LLM Calls in Tool Functions
# ============================================================================

def analyze_dataset_with_llm(df_summary: str, user_query: str) -> Dict[str, Any]:
    """
    Original function that might exceed token limits with large datasets.
    NOW PROTECTED with token manager.
    """
    from openai import OpenAI
    
    client = OpenAI()
    manager = IntelligentTokenManager(model="gpt-4o-mini")
    
    # Build comprehensive prompt
    system_prompt = """You are an expert data scientist. Analyze the dataset summary 
    and provide actionable insights including:
    - Key patterns and trends
    - Data quality issues
    - Recommended next steps
    - Potential modeling approaches"""
    
    # Prepare prompt with automatic token management
    formatted_prompt, token_breakdown = manager.prepare_prompt(
        system=system_prompt,
        user=user_query,
        context=f"Dataset Summary:\n{df_summary}",
        examples=[
            "Example: For a dataset with high null%, recommend imputation strategies",
            "Example: For imbalanced classes, suggest rebalancing techniques"
        ]
    )
    
    logger.info(f"[ANALYZE] Token usage: {token_breakdown['total']}/{token_breakdown['available']}")
    
    # Safe LLM call
    messages = [
        {"role": "system", "content": formatted_prompt}
    ]
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7
    )
    
    return {
        "analysis": response.choices[0].message.content,
        "token_info": token_breakdown
    }


# ============================================================================
# EXAMPLE 2: Protecting Recommendation System
# ============================================================================

def recommend_model_with_protection(
    dataset_info: Dict[str, Any],
    constraints: Dict[str, Any]
) -> str:
    """
    Model recommendation that handles large dataset descriptions.
    """
    from openai import OpenAI
    
    client = OpenAI()
    manager = IntelligentTokenManager(model="gpt-4o-mini", reserved_for_response=500)
    
    # Convert dataset info to string (might be very long)
    dataset_str = "\n".join([
        f"- {key}: {value}" for key, value in dataset_info.items()
    ])
    
    constraints_str = "\n".join([
        f"- {key}: {value}" for key, value in constraints.items()
    ])
    
    # Use fit_content to ensure it fits
    fitted_dataset = manager.fit_content(dataset_str, priority="important")
    fitted_constraints = manager.fit_content(constraints_str, priority="important")
    
    messages = [
        {
            "role": "system",
            "content": "You are an ML expert. Recommend the best model based on dataset characteristics."
        },
        {
            "role": "user",
            "content": f"Dataset:\n{fitted_dataset}\n\nConstraints:\n{fitted_constraints}\n\nRecommend a model."
        }
    ]
    
    # Validate before calling
    safe_messages, token_info = safe_llm_call(messages, model="gpt-4o-mini")
    
    if token_info["exceeds"]:
        logger.warning(f"[RECOMMEND] Truncated: {token_info['total']} -> {token_info['fixed_total']} tokens")
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=safe_messages
    )
    
    return response.choices[0].message.content


# ============================================================================
# EXAMPLE 3: Conversational Agent with History Management
# ============================================================================

class ConversationalAgent:
    """Agent that maintains conversation history with automatic token management."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.manager = IntelligentTokenManager(model=model)
        self.conversation_history: List[Dict[str, str]] = []
        self.system_prompt = {
            "role": "system",
            "content": "You are a helpful data science assistant."
        }
    
    def chat(self, user_message: str) -> str:
        """
        Send a message and get response.
        Automatically manages token limits for conversation history.
        """
        from openai import OpenAI
        
        client = OpenAI()
        
        # Add user message
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Build full message list
        messages = [self.system_prompt] + self.conversation_history
        
        # Validate and fix if needed (keeps recent messages)
        safe_messages = self.manager.validate_and_fix(messages)
        
        # Check if truncation happened
        if len(safe_messages) < len(messages):
            logger.info(f"[CHAT] Truncated conversation: {len(messages)} -> {len(safe_messages)} messages")
        
        # Make LLM call
        response = client.chat.completions.create(
            model=self.model,
            messages=safe_messages
        )
        
        assistant_message = response.choices[0].message.content
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        return assistant_message
    
    def get_token_stats(self) -> Dict[str, int]:
        """Get current token usage statistics."""
        messages = [self.system_prompt] + self.conversation_history
        total = self.manager.count_messages_tokens(messages)
        available = self.manager.budget.available_for_prompt
        
        return {
            "total_tokens": total,
            "available_tokens": available,
            "usage_percent": int((total / available) * 100),
            "messages_count": len(self.conversation_history)
        }


# ============================================================================
# EXAMPLE 4: Batch Processing with Token Limits
# ============================================================================

def process_multiple_datasets_with_llm(datasets: List[Dict[str, Any]]) -> List[str]:
    """
    Process multiple datasets with LLM, ensuring each stays within limits.
    """
    from openai import OpenAI
    
    client = OpenAI()
    manager = IntelligentTokenManager(model="gpt-4o-mini")
    
    results = []
    
    for i, dataset in enumerate(datasets):
        logger.info(f"[BATCH] Processing dataset {i+1}/{len(datasets)}")
        
        # Convert dataset to string
        dataset_str = str(dataset)
        
        # Check if it fits
        tokens = manager.count_tokens(dataset_str)
        
        if tokens > manager.budget.available_for_prompt:
            logger.warning(f"[BATCH] Dataset {i+1} exceeds limit ({tokens} tokens), truncating...")
            dataset_str = manager.truncate_text(
                dataset_str,
                max_tokens=manager.budget.available_for_prompt,
                strategy="smart"
            )
        
        # Make safe LLM call
        messages = [
            {"role": "system", "content": "Analyze this dataset and provide insights."},
            {"role": "user", "content": dataset_str}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        
        results.append(response.choices[0].message.content)
    
    return results


# ============================================================================
# EXAMPLE 5: Using Decorator for Clean Integration
# ============================================================================

@ensure_token_limit(model="gpt-4o-mini")
def generate_executive_report(data: str, analysis: str, models: str) -> str:
    """
    Generate executive report - automatically protected from token limits.
    
    The decorator handles all token management transparently.
    """
    from openai import OpenAI
    
    client = OpenAI()
    
    messages = [
        {
            "role": "system",
            "content": "You are an expert at creating executive-level data science reports."
        },
        {
            "role": "user",
            "content": f"""Create an executive report with:

DATA OVERVIEW:
{data}

ANALYSIS RESULTS:
{analysis}

MODELS TRAINED:
{models}

Format as a professional executive summary."""
        }
    ]
    
    # Decorator automatically validates and fixes messages
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    
    return response.choices[0].message.content


# ============================================================================
# EXAMPLE 6: Smart Context Window Management
# ============================================================================

def smart_context_summarization(
    large_context: str,
    query: str,
    model: str = "gpt-4o-mini"
) -> str:
    """
    When context is too large, intelligently summarize it first.
    """
    from openai import OpenAI
    
    client = OpenAI()
    manager = IntelligentTokenManager(model=model)
    
    context_tokens = manager.count_tokens(large_context)
    available = manager.budget.available_for_prompt
    
    # Reserve tokens for query and system prompt
    query_tokens = manager.count_tokens(query)
    system_tokens = 100  # Estimate
    
    context_budget = available - query_tokens - system_tokens - 500  # 500 buffer
    
    if context_tokens > context_budget:
        logger.info(f"[SMART CONTEXT] Context too large ({context_tokens} tokens), "
                   f"will summarize to fit {context_budget} tokens")
        
        # First pass: Summarize the context
        summary_messages = [
            {
                "role": "system",
                "content": "Summarize the following content, keeping all key information."
            },
            {
                "role": "user",
                "content": manager.truncate_text(
                    large_context,
                    max_tokens=available - 1000,
                    strategy="smart"
                )
            }
        ]
        
        summary_response = client.chat.completions.create(
            model=model,
            messages=summary_messages
        )
        
        context_to_use = summary_response.choices[0].message.content
        logger.info(f"[SMART CONTEXT] Summarized to {manager.count_tokens(context_to_use)} tokens")
    else:
        context_to_use = large_context
    
    # Second pass: Answer query with manageable context
    final_messages = [
        {
            "role": "system",
            "content": "Answer the query based on the provided context."
        },
        {
            "role": "user",
            "content": f"Context:\n{context_to_use}\n\nQuery: {query}"
        }
    ]
    
    response = client.chat.completions.create(
        model=model,
        messages=final_messages
    )
    
    return response.choices[0].message.content


# ============================================================================
# EXAMPLE 7: Real-time Token Monitoring
# ============================================================================

def monitored_llm_call(prompt: str, model: str = "gpt-4o-mini") -> Dict[str, Any]:
    """
    LLM call with comprehensive token monitoring and logging.
    """
    from openai import OpenAI
    
    client = OpenAI()
    manager = IntelligentTokenManager(model=model)
    
    # Pre-call analysis
    prompt_tokens = manager.count_tokens(prompt)
    available = manager.budget.available_for_prompt
    
    logger.info(f"[MONITORED] Pre-call: {prompt_tokens}/{available} tokens ({(prompt_tokens/available)*100:.1f}%)")
    
    if prompt_tokens > available:
        logger.error(f"[MONITORED] ⚠️ Prompt exceeds limit! Will truncate.")
        prompt = manager.truncate_text(prompt, max_tokens=available, strategy="smart")
        prompt_tokens = manager.count_tokens(prompt)
    
    # Make call
    messages = [{"role": "user", "content": prompt}]
    
    response = client.chat.completions.create(
        model=model,
        messages=messages
    )
    
    # Post-call analysis
    completion_tokens = response.usage.completion_tokens
    total_tokens = response.usage.total_tokens
    
    logger.info(f"[MONITORED] Post-call: {total_tokens} total tokens "
               f"(prompt: {prompt_tokens}, completion: {completion_tokens})")
    
    return {
        "response": response.choices[0].message.content,
        "token_stats": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "model_limit": manager.max_tokens,
            "usage_percent": (total_tokens / manager.max_tokens) * 100
        }
    }


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    # Example 1: Simple protection
    print("=" * 60)
    print("Example 1: Simple Dataset Analysis")
    print("=" * 60)
    
    large_summary = "Column info:\n" + "\n".join([f"col_{i}: numeric" for i in range(1000)])
    
    # This would normally fail with token limit error
    # result = analyze_dataset_with_llm(large_summary, "What should I do next?")
    # print(f"Analysis complete, used {result['token_info']['total']} tokens")
    
    # Example 2: Conversational agent
    print("\n" + "=" * 60)
    print("Example 2: Conversational Agent with History")
    print("=" * 60)
    
    agent = ConversationalAgent(model="gpt-4o-mini")
    
    # Simulate long conversation
    for i in range(5):
        response = agent.chat(f"Tell me about topic {i}")
        stats = agent.get_token_stats()
        print(f"Turn {i+1}: {stats['usage_percent']}% of token limit used")
    
    # Example 3: Decorator usage
    print("\n" + "=" * 60)
    print("Example 3: Decorator Protection")
    print("=" * 60)
    
    huge_data = "x" * 100000
    # report = generate_executive_report(huge_data, huge_data, huge_data)
    # print("Report generated successfully despite huge input!")
    
    # Example 4: Token monitoring
    print("\n" + "=" * 60)
    print("Example 4: Real-time Monitoring")
    print("=" * 60)
    
    manager = get_token_manager("gpt-4o-mini")
    
    test_text = "Sample text " * 1000
    tokens = manager.count_tokens(test_text)
    print(f"Text has {tokens} tokens")
    
    if tokens > 1000:
        truncated = manager.truncate_text(test_text, 1000, strategy="smart")
        print(f"Truncated to {manager.count_tokens(truncated)} tokens")
    
    print("\n✓ All examples configured successfully!")
    print("Uncomment API calls to test with actual LLM providers.")

