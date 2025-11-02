"""
Intelligent Token Management for LLM Calls
==========================================

Prevents token limit exceeded errors by:
1. Accurately counting tokens for different models
2. Intelligently truncating/summarizing content
3. Prioritizing important information
4. Supporting multiple LLM providers
"""

import logging
import re
from typing import Any, Dict, List, Optional, Union, Tuple
from functools import lru_cache
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TokenBudget:
    """Token budget configuration for an LLM call."""
    model: str
    max_tokens: int
    reserved_for_response: int = 1000
    safety_margin: int = 100
    
    @property
    def available_for_prompt(self) -> int:
        """Tokens available for the prompt after reserving for response."""
        return self.max_tokens - self.reserved_for_response - self.safety_margin


# Model token limits (conservative estimates)
MODEL_TOKEN_LIMITS = {
    # OpenAI models
    "gpt-4": 8192,
    "gpt-4-32k": 32768,
    "gpt-4-turbo": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-3.5-turbo": 16385,
    "gpt-3.5-turbo-16k": 16385,
    
    # Gemini models
    "gemini-pro": 32768,
    "gemini-1.5-pro": 1048576,  # 1M tokens
    "gemini-1.5-flash": 1048576,
    "gemini-2.0-flash": 1048576,
    "gemini-ultra": 32768,
    
    # Claude models
    "claude-3-opus": 200000,
    "claude-3-sonnet": 200000,
    "claude-3-haiku": 200000,
    "claude-2": 100000,
    
    # Other models
    "llama-2-70b": 4096,
    "mixtral-8x7b": 32768,
}


class IntelligentTokenManager:
    """
    Intelligent token management for LLM calls.
    
    Features:
    - Accurate token counting using tiktoken (OpenAI) or approximation
    - Smart content truncation with priority preservation
    - Automatic summarization for large content
    - Multi-provider support
    - Caching for performance
    """
    
    def __init__(self, model: str = "gpt-4o-mini", reserved_for_response: int = 1000):
        """
        Initialize token manager.
        
        Args:
            model: Model identifier (e.g., "gpt-4o-mini", "gemini-2.0-flash")
            reserved_for_response: Tokens to reserve for the model's response
        """
        self.model = model
        self.max_tokens = self._get_model_limit(model)
        self.reserved_for_response = reserved_for_response
        self.budget = TokenBudget(
            model=model,
            max_tokens=self.max_tokens,
            reserved_for_response=reserved_for_response
        )
        
        # Try to load tiktoken for accurate counting
        self.tokenizer = self._load_tokenizer()
        
        logger.info(f"[TOKEN MANAGER] Initialized for {model}: {self.max_tokens} max tokens, "
                   f"{self.budget.available_for_prompt} available for prompt")
    
    def _get_model_limit(self, model: str) -> int:
        """Get token limit for a model."""
        # Check exact match first
        if model in MODEL_TOKEN_LIMITS:
            return MODEL_TOKEN_LIMITS[model]
        
        # Check partial matches (e.g., "gpt-4" in "gpt-4-0125-preview")
        for model_key, limit in MODEL_TOKEN_LIMITS.items():
            if model_key in model.lower():
                return limit
        
        # Default fallback
        logger.warning(f"[TOKEN MANAGER] Unknown model '{model}', using default 8192 tokens")
        return 8192
    
    def _load_tokenizer(self) -> Optional[Any]:
        """Load appropriate tokenizer for the model."""
        try:
            import tiktoken
            
            # Map model to tiktoken encoding
            if "gpt-4" in self.model.lower():
                return tiktoken.encoding_for_model("gpt-4")
            elif "gpt-3.5" in self.model.lower():
                return tiktoken.encoding_for_model("gpt-3.5-turbo")
            else:
                # Use cl100k_base for most modern models
                return tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("[TOKEN MANAGER] tiktoken not available, using approximation")
            return None
        except Exception as e:
            logger.warning(f"[TOKEN MANAGER] Could not load tokenizer: {e}")
            return None
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.
        
        Args:
            text: Input text
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Use tiktoken if available (most accurate)
        if self.tokenizer:
            try:
                return len(self.tokenizer.encode(str(text)))
            except Exception as e:
                logger.warning(f"[TOKEN MANAGER] Tokenizer failed: {e}, using approximation")
        
        # Fallback: approximation (1 token ≈ 4 characters for English)
        return len(str(text)) // 4
    
    def count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Count tokens in a list of messages (chat format).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Total token count including overhead
        """
        total = 0
        for message in messages:
            # Count role
            total += self.count_tokens(message.get("role", ""))
            # Count content
            total += self.count_tokens(message.get("content", ""))
            # Add per-message overhead (approximately 4 tokens per message)
            total += 4
        
        # Add base overhead for the conversation
        total += 3
        
        return total
    
    def truncate_text(
        self, 
        text: str, 
        max_tokens: int,
        strategy: str = "middle"
    ) -> str:
        """
        Intelligently truncate text to fit within token limit.
        
        Args:
            text: Text to truncate
            max_tokens: Maximum tokens allowed
            strategy: Truncation strategy - "start", "middle", "end", or "smart"
            
        Returns:
            Truncated text
        """
        current_tokens = self.count_tokens(text)
        
        if current_tokens <= max_tokens:
            return text
        
        # Calculate approximate character limit
        # Use conservative ratio to ensure we don't exceed
        char_limit = int(max_tokens * 3.5)  # Conservative: ~3.5 chars per token
        
        if strategy == "start":
            # Keep the beginning
            truncated = text[:char_limit]
            return truncated + "\n\n[... content truncated ...]"
        
        elif strategy == "end":
            # Keep the end
            truncated = text[-char_limit:]
            return "[... content truncated ...]\n\n" + truncated
        
        elif strategy == "middle":
            # Keep beginning and end, remove middle
            half = char_limit // 2
            start = text[:half]
            end = text[-half:]
            return f"{start}\n\n[... middle section truncated ...]\n\n{end}"
        
        elif strategy == "smart":
            # Preserve structure: keep headings, first/last paragraphs
            return self._smart_truncate(text, char_limit)
        
        else:
            raise ValueError(f"Unknown truncation strategy: {strategy}")
    
    def _smart_truncate(self, text: str, char_limit: int) -> str:
        """
        Smart truncation that preserves structure.
        
        Keeps:
        - Headings (lines starting with #, ##, etc.)
        - First and last paragraphs
        - Code blocks (```...```)
        - Important markers
        """
        lines = text.split('\n')
        
        # Extract important elements
        important_lines = []
        for i, line in enumerate(lines):
            # Keep headings
            if line.strip().startswith('#'):
                important_lines.append((i, line, 'heading'))
            # Keep code blocks
            elif line.strip().startswith('```'):
                important_lines.append((i, line, 'code'))
            # Keep first 5 and last 5 lines
            elif i < 5 or i >= len(lines) - 5:
                important_lines.append((i, line, 'boundary'))
        
        # Reconstruct with important elements
        if important_lines:
            result = []
            last_idx = -1
            
            for idx, line, line_type in sorted(important_lines):
                if idx > last_idx + 1:
                    result.append("[...]")
                result.append(line)
                last_idx = idx
            
            truncated = '\n'.join(result)
            
            # If still too long, fall back to simple truncation
            if len(truncated) > char_limit:
                return truncated[:char_limit] + "\n\n[... content truncated ...]"
            
            return truncated
        
        # Fallback to simple truncation
        return text[:char_limit] + "\n\n[... content truncated ...]"
    
    def fit_content(
        self,
        content: Union[str, List[str], Dict[str, str]],
        priority: str = "recent"
    ) -> Union[str, List[str], Dict[str, str]]:
        """
        Fit content within available token budget.
        
        Args:
            content: Content to fit (string, list, or dict)
            priority: Priority strategy - "recent" (keep latest), "important" (keep key info)
            
        Returns:
            Fitted content of same type as input
        """
        available = self.budget.available_for_prompt
        
        if isinstance(content, str):
            return self.truncate_text(content, available, strategy="smart")
        
        elif isinstance(content, list):
            return self._fit_list(content, available, priority)
        
        elif isinstance(content, dict):
            return self._fit_dict(content, available, priority)
        
        else:
            logger.warning(f"[TOKEN MANAGER] Unknown content type: {type(content)}")
            return content
    
    def _fit_list(self, items: List[str], max_tokens: int, priority: str) -> List[str]:
        """Fit list of strings within token budget."""
        if not items:
            return items
        
        # Count tokens for each item
        item_tokens = [(item, self.count_tokens(item)) for item in items]
        total_tokens = sum(tokens for _, tokens in item_tokens)
        
        if total_tokens <= max_tokens:
            return items
        
        # Apply priority strategy
        if priority == "recent":
            # Keep most recent items
            result = []
            used_tokens = 0
            
            for item, tokens in reversed(item_tokens):
                if used_tokens + tokens <= max_tokens:
                    result.insert(0, item)
                    used_tokens += tokens
                else:
                    break
            
            if len(result) < len(items):
                result.insert(0, f"[... {len(items) - len(result)} earlier items truncated ...]")
            
            return result
        
        elif priority == "important":
            # Keep items with important keywords
            keywords = ["error", "warning", "critical", "important", "summary", "result"]
            
            important = []
            regular = []
            
            for item, tokens in item_tokens:
                if any(kw in item.lower() for kw in keywords):
                    important.append((item, tokens))
                else:
                    regular.append((item, tokens))
            
            # Allocate 70% to important, 30% to regular
            important_budget = int(max_tokens * 0.7)
            regular_budget = max_tokens - important_budget
            
            result = []
            used_tokens = 0
            
            # Add important items first
            for item, tokens in important:
                if used_tokens + tokens <= important_budget:
                    result.append(item)
                    used_tokens += tokens
            
            # Fill remaining with regular items
            for item, tokens in regular:
                if used_tokens + tokens <= max_tokens:
                    result.append(item)
                    used_tokens += tokens
            
            return result
        
        else:
            # Default: proportional truncation
            return items[:len(items)//2] + [f"[... {len(items)//2} items truncated ...]"]
    
    def _fit_dict(self, data: Dict[str, str], max_tokens: int, priority: str) -> Dict[str, str]:
        """Fit dictionary values within token budget."""
        if not data:
            return data
        
        # Count tokens for each key-value pair
        item_tokens = {}
        total_tokens = 0
        
        for key, value in data.items():
            key_tokens = self.count_tokens(key)
            value_tokens = self.count_tokens(str(value))
            item_tokens[key] = (value, key_tokens + value_tokens)
            total_tokens += key_tokens + value_tokens
        
        if total_tokens <= max_tokens:
            return data
        
        # Priority keys that should be preserved
        priority_keys = ["instruction", "system", "prompt", "query", "question", "result"]
        
        result = {}
        used_tokens = 0
        
        # Add priority keys first
        for key in priority_keys:
            if key in item_tokens:
                value, tokens = item_tokens[key]
                if used_tokens + tokens <= max_tokens:
                    result[key] = value
                    used_tokens += tokens
                    del item_tokens[key]
        
        # Add remaining keys
        for key, (value, tokens) in item_tokens.items():
            if used_tokens + tokens <= max_tokens:
                result[key] = value
                used_tokens += tokens
            else:
                # Truncate this value
                remaining = max_tokens - used_tokens
                if remaining > 50:  # Only add if meaningful space left
                    result[key] = self.truncate_text(str(value), remaining, strategy="start")
                break
        
        return result
    
    def prepare_prompt(
        self,
        system: str = "",
        user: str = "",
        context: str = "",
        examples: List[str] = None
    ) -> Tuple[str, Dict[str, int]]:
        """
        Prepare a complete prompt that fits within token budget.
        
        Args:
            system: System prompt
            user: User query
            context: Additional context
            examples: Example inputs/outputs
            
        Returns:
            Tuple of (formatted_prompt, token_breakdown)
        """
        # Allocate budget
        available = self.budget.available_for_prompt
        
        # Reserve tokens for system and user (highest priority)
        system_tokens = self.count_tokens(system)
        user_tokens = self.count_tokens(user)
        
        # Ensure system and user fit
        if system_tokens > available * 0.3:
            system = self.truncate_text(system, int(available * 0.3), strategy="smart")
            system_tokens = self.count_tokens(system)
        
        if user_tokens > available * 0.3:
            user = self.truncate_text(user, int(available * 0.3), strategy="start")
            user_tokens = self.count_tokens(user)
        
        # Remaining budget for context and examples
        remaining = available - system_tokens - user_tokens
        
        # Fit context
        context_budget = int(remaining * 0.6) if examples else remaining
        if context:
            context_tokens = self.count_tokens(context)
            if context_tokens > context_budget:
                context = self.truncate_text(context, context_budget, strategy="smart")
                context_tokens = self.count_tokens(context)
        else:
            context_tokens = 0
        
        # Fit examples
        examples_budget = remaining - context_tokens
        fitted_examples = []
        if examples and examples_budget > 100:
            fitted_examples = self._fit_list(examples, examples_budget, priority="important")
        
        examples_tokens = sum(self.count_tokens(ex) for ex in fitted_examples)
        
        # Build final prompt
        parts = []
        if system:
            parts.append(f"SYSTEM: {system}")
        if context:
            parts.append(f"\nCONTEXT:\n{context}")
        if fitted_examples:
            parts.append(f"\nEXAMPLES:\n" + "\n---\n".join(fitted_examples))
        if user:
            parts.append(f"\nUSER: {user}")
        
        formatted = "\n".join(parts)
        
        breakdown = {
            "system": system_tokens,
            "user": user_tokens,
            "context": context_tokens,
            "examples": examples_tokens,
            "total": system_tokens + user_tokens + context_tokens + examples_tokens,
            "available": available,
            "reserved_for_response": self.budget.reserved_for_response
        }
        
        logger.info(f"[TOKEN MANAGER] Prompt prepared: {breakdown['total']}/{available} tokens used")
        
        return formatted, breakdown
    
    def validate_and_fix(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Validate messages fit within token limit and fix if needed.
        
        Args:
            messages: List of message dicts (chat format)
            
        Returns:
            Fixed messages that fit within limit
        """
        total_tokens = self.count_messages_tokens(messages)
        available = self.budget.available_for_prompt
        
        if total_tokens <= available:
            logger.debug(f"[TOKEN MANAGER] Messages OK: {total_tokens}/{available} tokens")
            return messages
        
        logger.warning(f"[TOKEN MANAGER] Messages exceed limit: {total_tokens}/{available} tokens, truncating...")
        
        # Strategy: Keep system message, recent user/assistant messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]
        
        # Always keep system message (truncate if needed)
        result = []
        used_tokens = 0
        
        if system_msgs:
            system_msg = system_msgs[0]  # Take first system message
            content = system_msg.get("content", "")
            tokens = self.count_tokens(content)
            
            if tokens > available * 0.3:
                content = self.truncate_text(content, int(available * 0.3), strategy="smart")
                tokens = self.count_tokens(content)
            
            result.append({"role": "system", "content": content})
            used_tokens += tokens + 4  # +4 for message overhead
        
        # Add recent messages in reverse order
        remaining = available - used_tokens
        recent_msgs = []
        
        for msg in reversed(other_msgs):
            content = msg.get("content", "")
            role = msg.get("role", "user")
            tokens = self.count_tokens(content) + self.count_tokens(role) + 4
            
            if used_tokens + tokens <= remaining:
                recent_msgs.insert(0, msg)
                used_tokens += tokens
            else:
                # Try to fit truncated version
                available_for_msg = remaining - used_tokens - 4
                if available_for_msg > 50:
                    truncated = self.truncate_text(content, available_for_msg, strategy="start")
                    recent_msgs.insert(0, {"role": role, "content": truncated})
                break
        
        result.extend(recent_msgs)
        
        final_tokens = self.count_messages_tokens(result)
        logger.info(f"[TOKEN MANAGER] Truncated {len(messages)} -> {len(result)} messages, "
                   f"{total_tokens} -> {final_tokens} tokens")
        
        return result


# Global instance for convenience
_default_manager: Optional[IntelligentTokenManager] = None


def get_token_manager(model: str = "gpt-4o-mini") -> IntelligentTokenManager:
    """Get or create default token manager."""
    global _default_manager
    if _default_manager is None or _default_manager.model != model:
        _default_manager = IntelligentTokenManager(model=model)
    return _default_manager


def safe_llm_call(
    messages: List[Dict[str, str]],
    model: str = "gpt-4o-mini",
    auto_fix: bool = True
) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    """
    Ensure messages are safe for LLM call.
    
    Args:
        messages: Chat messages
        model: Model identifier
        auto_fix: Automatically fix if exceeds limit
        
    Returns:
        Tuple of (safe_messages, token_info)
        
    Raises:
        ValueError: If messages exceed limit and auto_fix is False
    """
    manager = get_token_manager(model)
    total_tokens = manager.count_messages_tokens(messages)
    available = manager.budget.available_for_prompt
    
    token_info = {
        "total": total_tokens,
        "available": available,
        "reserved": manager.budget.reserved_for_response,
        "exceeds": total_tokens > available
    }
    
    if total_tokens > available:
        if auto_fix:
            logger.warning(f"[SAFE LLM CALL] Token limit exceeded ({total_tokens}/{available}), auto-fixing...")
            fixed_messages = manager.validate_and_fix(messages)
            token_info["fixed_total"] = manager.count_messages_tokens(fixed_messages)
            return fixed_messages, token_info
        else:
            raise ValueError(
                f"Messages exceed token limit: {total_tokens} > {available}. "
                f"Set auto_fix=True to automatically truncate."
            )
    
    return messages, token_info


# Convenience decorator
def ensure_token_limit(model: str = "gpt-4o-mini"):
    """
    Decorator to ensure function calls don't exceed token limits.
    
    Usage:
        @ensure_token_limit(model="gpt-4o-mini")
        def my_llm_call(messages, **kwargs):
            return client.chat.completions.create(messages=messages, **kwargs)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract messages argument
            messages = kwargs.get("messages") or (args[0] if args else None)
            
            if messages and isinstance(messages, list):
                safe_messages, token_info = safe_llm_call(messages, model=model)
                
                if token_info["exceeds"]:
                    logger.info(f"[ENSURE TOKEN LIMIT] Fixed token overflow: "
                               f"{token_info['total']} -> {token_info.get('fixed_total', 0)}")
                
                # Replace messages
                if "messages" in kwargs:
                    kwargs["messages"] = safe_messages
                elif args:
                    args = (safe_messages,) + args[1:]
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

