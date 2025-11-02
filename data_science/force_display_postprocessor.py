"""
NUCLEAR OPTION: Force Display Post-Processor

The LLM refuses to show __display__ content no matter how aggressive the instructions.
This post-processor FORCIBLY injects display content into responses.

Strategy:
1. After LLM generates response, check if a tool was called
2. If tool returned __display__ and LLM didn't include it
3. INJECT the display content into the response
4. Bypass LLM's instruction-following failure entirely
"""

import re
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ForceDisplayPostProcessor:
    """
    Post-processes LLM responses to forcibly inject tool display content
    when the LLM fails to show it.
    """
    
    def __init__(self):
        self.last_tool_result: Optional[Dict[str, Any]] = None
        self.last_tool_name: Optional[str] = None
    
    def register_tool_call(self, tool_name: str, result: Dict[str, Any]):
        """
        Register a tool call result for potential injection.
        
        Args:
            tool_name: Name of the tool that was called
            result: The tool's return value (should have __display__)
        """
        self.last_tool_result = result
        self.last_tool_name = tool_name
        logger.info(f"[FORCE DISPLAY] Registered tool call: {tool_name}")
    
    def process_response(self, llm_response: str) -> str:
        """
        Process LLM response and inject display content if missing.
        
        Args:
            llm_response: The LLM's generated response
            
        Returns:
            Modified response with injected display content (if needed)
        """
        # No tool called, return as-is
        if not self.last_tool_result or not self.last_tool_name:
            return llm_response
        
        # Get display content
        display_content = self.last_tool_result.get('__display__', '')
        if not display_content or len(display_content) < 10:
            logger.warning(f"[FORCE DISPLAY] No __display__ content for {self.last_tool_name}")
            return llm_response
        
        # Check if LLM already included the display content
        # Use fuzzy matching to detect if ANY significant portion is present
        display_sample = self._extract_sample(display_content)
        if self._content_is_present(llm_response, display_sample):
            logger.info(f"[FORCE DISPLAY] ✓ LLM included display content for {self.last_tool_name}")
            return llm_response
        
        # LLM FAILED to show content - INJECT IT
        logger.warning(f"[FORCE DISPLAY] ✗ LLM ignored __display__ for {self.last_tool_name} - INJECTING NOW")
        
        # Build injected response
        injected = self._inject_display_content(
            llm_response=llm_response,
            tool_name=self.last_tool_name,
            display_content=display_content
        )
        
        # Clear state
        self.last_tool_result = None
        self.last_tool_name = None
        
        return injected
    
    def _extract_sample(self, content: str, length: int = 100) -> str:
        """Extract a sample of content for fuzzy matching."""
        # Remove markdown formatting, extra whitespace
        cleaned = re.sub(r'[*_`|─━]', '', content)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned[:length]
    
    def _content_is_present(self, response: str, sample: str) -> bool:
        """Check if sample content is present in response (fuzzy match)."""
        # Clean response for comparison
        cleaned_response = re.sub(r'[*_`|─━]', '', response)
        cleaned_response = re.sub(r'\s+', ' ', cleaned_response).strip()
        
        # Split sample into words and check if most are present
        sample_words = sample.split()
        if len(sample_words) < 3:
            return False
        
        matches = sum(1 for word in sample_words if word.lower() in cleaned_response.lower())
        match_ratio = matches / len(sample_words)
        
        # If >60% of words from sample are in response, consider it present
        return match_ratio > 0.6
    
    def _inject_display_content(self, llm_response: str, tool_name: str, display_content: str) -> str:
        """
        Inject display content into LLM response.
        
        Strategy:
        1. Add a clear separator
        2. Show the tool output with a header
        3. Keep the LLM's "next steps" if present
        """
        # Detect if LLM provided next steps
        has_next_steps = any(phrase in llm_response.lower() for phrase in [
            'next steps', 'what would you like', 'would you like to', 
            'consider', 'you can', 'options:'
        ])
        
        # Build injected response
        parts = []
        
        # Header explaining what happened
        parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        parts.append(f"✅ **{tool_name.replace('_', ' ').title()} Results:**")
        parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        parts.append("")
        
        # The actual display content
        parts.append(display_content)
        parts.append("")
        
        # Separator before next steps
        parts.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        # If LLM provided next steps, keep them
        if has_next_steps:
            parts.append("")
            # Extract just the "next steps" part
            next_steps_match = re.search(
                r'((?:next steps|what would you like|consider).*)',
                llm_response,
                re.IGNORECASE | re.DOTALL
            )
            if next_steps_match:
                parts.append(next_steps_match.group(1))
        else:
            # Provide default next steps based on tool
            parts.append("")
            parts.append("**What would you like to do next?**")
            parts.append("")
            parts.append("1. **describe()** - View statistical summary")
            parts.append("2. **head()** - View first few rows")
            parts.append("3. **plot()** - Generate visualizations")
            parts.append("4. **stats()** - Advanced statistical analysis")
            parts.append("5. **data_quality_report()** - Check data quality")
            parts.append("")
            parts.append("Type a number or tool name to continue!")
        
        return "\n".join(parts)


# Global instance
_force_display_processor = ForceDisplayPostProcessor()


def register_tool_call(tool_name: str, result: Dict[str, Any]):
    """Register a tool call result."""
    global _force_display_processor
    _force_display_processor.register_tool_call(tool_name, result)


def process_response(llm_response: str) -> str:
    """Process LLM response and inject display if needed."""
    global _force_display_processor
    return _force_display_processor.process_response(llm_response)

