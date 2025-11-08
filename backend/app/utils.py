"""Utility functions for Anthropic OpenAI Bridge"""
from typing import Any, Dict


def openai_response_to_dict(response: Any) -> Dict[str, Any]:
    """Convert OpenAI response object to dictionary."""
    if hasattr(response, 'model_dump'):
        return response.model_dump()
    elif hasattr(response, 'dict'):
        return response.dict()
    elif hasattr(response, '__dict__'):
        # Convert manually
        result: Dict[str, Any] = {
            "id": getattr(response, 'id', ''),
            "choices": [],
            "usage": {}
        }
        
        if hasattr(response, 'choices') and response.choices:
            for choice in response.choices:
                choice_dict = {
                    "message": {},
                    "finish_reason": getattr(choice, 'finish_reason', None)
                }
                
                if hasattr(choice, 'message'):
                    msg = choice.message
                    choice_dict["message"] = {
                        "role": getattr(msg, 'role', 'assistant'),
                        "content": getattr(msg, 'content', None) or "",
                        "tool_calls": []
                    }
                    
                    # Handle tool_calls
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            tc_dict = {
                                "id": getattr(tool_call, 'id', ''),
                                "type": getattr(tool_call, 'type', 'function'),
                                "function": {}
                            }
                            
                            if hasattr(tool_call, 'function'):
                                func = tool_call.function
                                tc_dict["function"] = {
                                    "name": getattr(func, 'name', ''),
                                    "arguments": getattr(func, 'arguments', '{}')
                                }
                            
                            choice_dict["message"]["tool_calls"].append(tc_dict)
                
                result["choices"].append(choice_dict)
        
        # Handle usage
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            result["usage"] = {
                "prompt_tokens": getattr(usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(usage, 'completion_tokens', 0),
                "total_tokens": getattr(usage, 'total_tokens', 0)
            }
        
        return result
    else:
        # Assume it's already a dict
        return response if isinstance(response, dict) else {}



