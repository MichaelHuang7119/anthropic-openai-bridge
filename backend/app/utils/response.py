"""Response conversion utilities."""
from typing import Any, Dict


def openai_response_to_dict(response: Any) -> Dict[str, Any]:
    """Convert OpenAI response object to dictionary."""
    if hasattr(response, 'model_dump'):
        # Pydantic model - use model_dump, preserving None values
        result = response.model_dump()
        # Ensure choices is preserved as-is (None, [], or list with items)
        if hasattr(response, 'choices'):
            result['choices'] = response.choices
        return result
    elif hasattr(response, 'dict'):
        # Pydantic v1 style
        result = response.dict()
        # Ensure choices is preserved as-is
        if hasattr(response, 'choices'):
            result['choices'] = response.choices
        return result
    elif hasattr(response, '__dict__'):
        # Convert manually - preserve None values
        result: Dict[str, Any] = {
            "id": getattr(response, 'id', ''),
            "usage": {}
        }
        
        # Preserve choices as-is (None, [], or list)
        if hasattr(response, 'choices'):
            choices_value = getattr(response, 'choices', None)
            if choices_value is None:
                result["choices"] = None
            elif isinstance(choices_value, list):
                result["choices"] = []
                for choice in choices_value:
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
            else:
                # Unexpected type, set to None
                result["choices"] = None
        else:
            # No choices attribute, set to None
            result["choices"] = None
        
        # Handle usage
        if hasattr(response, 'usage') and response.usage:
            usage = response.usage
            result["usage"] = {
                "prompt_tokens": getattr(usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(usage, 'completion_tokens', 0),
                "total_tokens": getattr(usage, 'total_tokens', 0)
            }
        elif hasattr(response, 'usage') and response.usage is None:
            result["usage"] = {}
        
        return result
    else:
        # Assume it's already a dict - preserve as-is
        if isinstance(response, dict):
            return response
        else:
            return {}

