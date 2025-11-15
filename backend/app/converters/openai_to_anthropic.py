"""Convert OpenAI API format to Anthropic format."""
import uuid
import json
from typing import Dict, Any, Iterator, Union
from ..core import TextContent


def convert_openai_response_to_anthropic(
    openai_response: Dict[str, Any],
    model: str,
    stream: bool = False
) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
    """Convert OpenAI response format to Anthropic format."""
    if stream:
        # Handle streaming response
        def stream_generator():
            for chunk in openai_response:
                chunk_data = chunk.choices[0] if hasattr(chunk, 'choices') else chunk
                delta = getattr(chunk_data, 'delta', {}) if hasattr(chunk_data, 'delta') else chunk_data.get('delta', {})
                
                # Handle content delta
                if 'content' in delta and delta['content']:
                    yield {
                        "type": "content_block_delta",
                        "index": 0,
                        "delta": {
                            "type": "text_delta",
                            "text": delta['content']
                        }
                    }
                
                # Handle tool calls
                if 'tool_calls' in delta and delta.get('tool_calls'):
                    for tool_call in delta['tool_calls']:
                        if tool_call.get('type') == 'function':
                            func = tool_call.get('function', {})
                            if tool_call.get('index') == 0:
                                yield {
                                    "type": "content_block_start",
                                    "index": 0,
                                    "content_block": {
                                        "type": "tool_use",
                                        "id": tool_call.get('id', ''),
                                        "name": func.get('name', ''),
                                        "input": {}
                                    }
                                }
                            if 'arguments' in func:
                                yield {
                                    "type": "content_block_delta",
                                    "index": 0,
                                    "delta": {
                                        "type": "input_json_delta",
                                        "partial_json": func['arguments']
                                    }
                                }
                
                # Handle finish
                if getattr(chunk_data, 'finish_reason', None) or chunk_data.get('finish_reason'):
                    finish_reason = getattr(chunk_data, 'finish_reason', None) or chunk_data.get('finish_reason')
                    if finish_reason == 'stop':
                        yield {
                            "type": "message_stop"
                        }
                    elif finish_reason == 'tool_calls':
                        yield {
                            "type": "content_block_stop",
                            "index": 0
                        }
                
                # Handle usage
                if hasattr(chunk, 'usage') and chunk.usage:
                    yield {
                        "type": "message_delta",
                        "delta": {
                            "stop_reason": getattr(chunk_data, 'finish_reason', None) or chunk_data.get('finish_reason')
                        },
                        "usage": {
                            "input_tokens": getattr(chunk.usage, 'prompt_tokens', 0),
                            "output_tokens": getattr(chunk.usage, 'completion_tokens', 0)
                        }
                    }
        
        return stream_generator()
    else:
        # Handle non-streaming response
        choices = openai_response.get('choices')
        
        # Handle None, empty list, or missing choices
        if choices is None:
            error = openai_response.get('error', {})
            if error:
                error_msg = error.get('message', 'Unknown error')
                error_type = error.get('type', 'api_error')
                raise ValueError(f"OpenAI API error ({error_type}): {error_msg}")
            raise ValueError("Invalid OpenAI response: choices is None. This usually indicates the API request failed or was rejected.")
        
        if not isinstance(choices, list) or len(choices) == 0:
            error = openai_response.get('error', {})
            if error:
                error_msg = error.get('message', 'Unknown error')
                error_type = error.get('type', 'api_error')
                raise ValueError(f"OpenAI API error ({error_type}): {error_msg}")
            raise ValueError("Invalid OpenAI response: no choices in response. Response may be empty or malformed.")
        
        choice = choices[0]
        
        # Handle both dict and Pydantic object - convert to dict
        if not isinstance(choice, dict):
            # Pydantic object - convert to dict
            if hasattr(choice, 'model_dump'):
                choice = choice.model_dump()
            elif hasattr(choice, 'dict'):
                choice = choice.dict()
            elif hasattr(choice, '__dict__'):
                # Manual conversion
                choice_dict = {
                    'message': {},
                    'finish_reason': getattr(choice, 'finish_reason', None)
                }
                if hasattr(choice, 'message'):
                    msg = choice.message
                    if hasattr(msg, 'model_dump'):
                        choice_dict['message'] = msg.model_dump()
                    elif hasattr(msg, 'dict'):
                        choice_dict['message'] = msg.dict()
                    elif hasattr(msg, '__dict__'):
                        choice_dict['message'] = {
                            'role': getattr(msg, 'role', 'assistant'),
                            'content': getattr(msg, 'content', None) or "",
                            'tool_calls': []
                        }
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            for tc in msg.tool_calls:
                                tc_dict = {
                                    'id': getattr(tc, 'id', ''),
                                    'type': getattr(tc, 'type', 'function'),
                                    'function': {}
                                }
                                if hasattr(tc, 'function'):
                                    func = tc.function
                                    tc_dict['function'] = {
                                        'name': getattr(func, 'name', ''),
                                        'arguments': getattr(func, 'arguments', '{}')
                                    }
                                choice_dict['message']['tool_calls'].append(tc_dict)
                    else:
                        choice_dict['message'] = {}
                choice = choice_dict
            else:
                # Fallback: try to access attributes directly and create dict
                original_choice = choice  # Save reference
                choice = {
                    'message': {},
                    'finish_reason': getattr(original_choice, 'finish_reason', 'stop')
                }
                if hasattr(original_choice, 'message'):
                    msg = original_choice.message
                    choice['message'] = {
                        'role': getattr(msg, 'role', 'assistant'),
                        'content': getattr(msg, 'content', None) or "",
                        'tool_calls': []
                    }
        
        # Now choice is guaranteed to be a dict
        message = choice.get('message', {})
        
        # Build content blocks
        content_blocks = []
        text_content = ""
        
        # Handle text content
        if 'content' in message and message['content']:
            text_content = message['content']
            content_blocks.append({
                "type": "text",
                "text": text_content,
                "citations": None  # Per Anthropic spec, text blocks include citations field
            })
        
        # Handle tool calls
        tool_calls = message.get('tool_calls')
        if not tool_calls:  # Handles None, [], and empty iterables
            tool_calls = []
        for tool_call in tool_calls:
            if tool_call.get('type') == 'function':
                func = tool_call.get('function', {})
                try:
                    input_data = json.loads(func.get('arguments', '{}'))
                except:
                    input_data = {}
                
                content_blocks.append({
                    "type": "tool_use",
                    "id": tool_call.get('id', ''),
                    "name": func.get('name', ''),
                    "input": input_data
                })
        
        # Determine stop reason - map OpenAI finish_reason to Anthropic stop_reason
        finish_reason = choice.get('finish_reason', 'stop')
        stop_reason = None
        if finish_reason == 'stop':
            stop_reason = 'end_turn'
        elif finish_reason == 'tool_calls':
            stop_reason = 'tool_use'  # When model invokes tools
        elif finish_reason == 'length':
            stop_reason = 'max_tokens'
        # Note: Anthropic also supports 'stop_sequence', 'pause_turn', 'refusal', 
        # 'model_context_window_exceeded' but OpenAI doesn't have direct equivalents
        
        # Build Anthropic response - per official spec at https://docs.claude.com/en/api/messages
        usage = openai_response.get('usage', {})
        
        # Generate a unique message ID if not present (per Anthropic format)
        message_id = openai_response.get('id', '')
        if not message_id or not message_id.startswith('msg_'):
            # Anthropic uses format: msg_<24 hex chars>
            message_id = f"msg_{uuid.uuid4().hex[:24]}"
        
        response = {
            "id": message_id,
            "type": "message",  # Always "message" per spec
            "role": "assistant",  # Always "assistant" per spec
            "content": content_blocks if content_blocks else [{"type": "text", "text": ""}],  # Ensure at least one block
            "model": model,
            "stop_reason": stop_reason,  # Required field, can be: end_turn, max_tokens, stop_sequence, tool_use, pause_turn, refusal, model_context_window_exceeded
            "stop_sequence": None,  # Required field, null if no custom stop sequence
            "usage": {
                "input_tokens": usage.get('prompt_tokens', 0),
                "output_tokens": usage.get('completion_tokens', 0)
            },
            # Optional fields per spec (set to None if not available)
            "context_management": None,
            "container": None
        }
        
        return response

