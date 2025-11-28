#!/usr/bin/env python3
"""
Test script to validate streaming output format compliance.
This script tests the convert_openai_stream_to_anthropic_async function
against the four required format scenarios.
"""

import asyncio
import json
import sys
import os
from typing import AsyncIterator, Dict, Any
from unittest.mock import AsyncMock

# Add backend directory to path to import modules
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
sys.path.insert(0, backend_path)

try:
    from backend.app.converters.streaming import convert_openai_stream_to_anthropic_async
except ImportError as e:
    print(f"Warning: Could not import convert_openai_stream_to_anthropic_async: {e}")
    print("Some tests may not work properly.")
    convert_openai_stream_to_anthropic_async = None


class MockOpenAIChunk:
    """Mock OpenAI streaming chunk for testing"""
    
    def __init__(self, content=None, tool_calls=None, finish_reason=None, usage=None,
                 thinking=None, signature=None):
        self.choices = []
        if content is not None or tool_calls is not None or finish_reason is not None:
            choice = MockChoice(content, tool_calls, finish_reason)
            self.choices = [choice]
        self.usage = usage
        self.signature = signature
        self.thinking = thinking


class MockChoice:
    """Mock choice object"""
    
    def __init__(self, content=None, tool_calls=None, finish_reason=None, thinking=None):
        self.delta = MockDelta(content, tool_calls, thinking)
        self.finish_reason = finish_reason
        # Also store thinking at choice level for some API formats
        self.thinking = thinking


class MockDelta:
    """Mock delta object"""
    
    def __init__(self, content=None, tool_calls=None, thinking=None):
        self.content = content
        self.tool_calls = tool_calls
        self.thinking = thinking


class MockToolCall:
    """Mock tool call object"""
    
    def __init__(self, index, id=None, function=None):
        self.index = index
        self.id = id
        self.function = function


class MockFunction:
    """Mock function object"""
    
    def __init__(self, name=None, arguments=None):
        self.name = name
        self.arguments = arguments


async def collect_stream(stream: AsyncIterator[Dict[str, Any]]) -> list:
    """Collect all events from a stream into a list"""
    events = []
    async for event in stream:
        events.append(event)
    return events


def format_event(event: Dict[str, Any]) -> str:
    """Format event as SSE format string"""
    event_type = event.get("type")
    if event_type == "ping":
        return "event: ping\ndata: {\"type\": \"ping\"}"
    else:
        return f"event: {event_type}\ndata: {json.dumps(event)}"


def print_events(events: list, title: str):
    """Print events in SSE format"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    for event in events:
        print(format_event(event))
        print()


async def test_basic_format():
    """Test basic streaming format (text only)"""
    print("\n" + "="*80)
    print("TEST 1: Basic Streaming Format")
    print("="*80)
    
    # Create mock stream with text content
    async def mock_stream():
        yield MockOpenAIChunk(content="Hello")
        yield MockOpenAIChunk(content="!")
        yield MockOpenAIChunk(finish_reason="stop", usage={"prompt_tokens": 25, "completion_tokens": 15})
    
    # Convert to Anthropic format
    stream = convert_openai_stream_to_anthropic_async(
        mock_stream(), 
        model="claude-sonnet-4-5-20250929",
        initial_input_tokens=25
    )
    
    events = await collect_stream(stream)
    print_events(events, "Basic Format Output")
    
    # Validate structure
    validate_basic_format(events)
    return events


async def test_tool_call_format():
    """Test tool call streaming format"""
    print("\n" + "="*80)
    print("TEST 2: Tool Call Streaming Format")
    print("="*80)
    
    # Create mock stream with tool calls
    async def mock_stream():
        # Text content first
        yield MockOpenAIChunk(content="Okay, let's check")
        
        # Tool call start
        tool_call = MockToolCall(
            index=0,
            id="toolu_01T1x1fJ34qAmk2tNTrN7Up6",
            function=MockFunction(name="get_weather", arguments="")
        )
        yield MockOpenAIChunk(tool_calls=[tool_call])
        
        # Tool call arguments (partial)
        tool_call = MockToolCall(
            index=0,
            function=MockFunction(arguments="{\"location\":")
        )
        yield MockOpenAIChunk(tool_calls=[tool_call])
        
        tool_call = MockToolCall(
            index=0,
            function=MockFunction(arguments=" \"San")
        )
        yield MockOpenAIChunk(tool_calls=[tool_call])
        
        tool_call = MockToolCall(
            index=0,
            function=MockFunction(arguments=" Francisco,")
        )
        yield MockOpenAIChunk(tool_calls=[tool_call])
        
        tool_call = MockToolCall(
            index=0,
            function=MockFunction(arguments=" CA\"")
        )
        yield MockOpenAIChunk(tool_calls=[tool_call])
        
        tool_call = MockToolCall(
            index=0,
            function=MockFunction(arguments=", \"unit\": \"fahrenheit\"}")
        )
        yield MockOpenAIChunk(tool_calls=[tool_call])
        
        # Finish with tool_use
        yield MockOpenAIChunk(finish_reason="tool_calls", usage={"prompt_tokens": 472, "completion_tokens": 89})
    
    # Convert to Anthropic format
    stream = convert_openai_stream_to_anthropic_async(
        mock_stream(), 
        model="claude-sonnet-4-5-20250929",
        initial_input_tokens=472
    )
    
    events = await collect_stream(stream)
    print_events(events, "Tool Call Format Output")
    
    # Validate structure
    validate_tool_call_format(events)
    return events


async def test_thinking_format():
    """Test thinking content streaming format"""
    print("\n" + "="*80)
    print("TEST 3: Thinking Content Streaming Format")
    print("="*80)
    
    # Create mock stream with thinking content
    async def mock_stream():
        # Thinking content - OpenAI format has thinking in the chunk itself, not in choices
        # This simulates how some providers (like aiping) send thinking content
        class ThinkingChunk:
            def __init__(self, thinking_content):
                self.thinking = thinking_content
                self.choices = []  # No choices for thinking-only chunks
        
        yield ThinkingChunk("Let me solve this step by step:\n\n1. First break down 27 * 453")
        yield ThinkingChunk("\n2. 453 = 400 + 50 + 3")
        yield ThinkingChunk("\n3. 27 * 400 = 10,800")
        yield ThinkingChunk("\n4. 27 * 50 = 1,350")
        yield ThinkingChunk("\n5. 27 * 3 = 81")
        yield ThinkingChunk("\n6. 10,800 + 1,350 + 81 = 12,231")
        
        # Signature
        class SignatureChunk:
            def __init__(self, sig):
                self.signature = sig
                self.choices = []
        
        yield SignatureChunk("EqQBCgIYAhIM1gbcDa9GJwZA2b3hGgxBdjrkzLoky3dl1pkiMOYds...")
        
        # Text content
        yield MockOpenAIChunk(content="27 * 453 = 12,231")
        
        # Finish
        yield MockOpenAIChunk(finish_reason="stop")
    
    # Convert to Anthropic format
    stream = convert_openai_stream_to_anthropic_async(
        mock_stream(), 
        model="claude-sonnet-4-5-20250929",
        initial_input_tokens=0
    )
    
    events = await collect_stream(stream)
    print_events(events, "Thinking Format Output")
    
    # Validate structure
    validate_thinking_format(events)
    return events


async def test_web_search_format():
    """Test web search tool streaming format"""
    print("\n" + "="*80)
    print("TEST 4: Web Search Tool Streaming Format")
    print("="*80)
    
    # Create mock stream with web search tool
    async def mock_stream():
        # Text content
        yield MockOpenAIChunk(content="I'll check")
        yield MockOpenAIChunk(content=" the current weather in New York City for you")
        yield MockOpenAIChunk(content=".")
        
        # Web search tool call
        tool_call = MockToolCall(
            index=0,
            id="srvtoolu_014hJH82Qum7Td6UV8gDXThB",
            function=MockFunction(name="web_search", arguments="")
        )
        yield MockOpenAIChunk(tool_calls=[tool_call])
        
        # Tool arguments (partial)
        tool_call = MockToolCall(
            index=0,
            function=MockFunction(arguments="{\"query")
        )
        yield MockOpenAIChunk(tool_calls=[tool_call])
        
        tool_call = MockToolCall(
            index=0,
            function=MockFunction(arguments="\": \"weather")
        )
        yield MockOpenAIChunk(tool_calls=[tool_call])
        
        tool_call = MockToolCall(
            index=0,
            function=MockFunction(arguments=" NYC")
        )
        yield MockOpenAIChunk(tool_calls=[tool_call])
        
        tool_call = MockToolCall(
            index=0,
            function=MockFunction(arguments=" today\"}")
        )
        yield MockOpenAIChunk(tool_calls=[tool_call])
        
        # Note: In real scenario, web search results would come after tool execution
        # For this test, we'll just finish the stream
        yield MockOpenAIChunk(finish_reason="stop")
    
    # Convert to Anthropic format
    stream = convert_openai_stream_to_anthropic_async(
        mock_stream(), 
        model="claude-sonnet-4-5-20250929",
        initial_input_tokens=2679
    )
    
    events = await collect_stream(stream)
    print_events(events, "Web Search Format Output")
    
    # Validate structure
    validate_web_search_format(events)
    return events


def validate_basic_format(events):
    """Validate basic format compliance"""
    print("\n--- Validation Results ---")
    
    # Check required events in order
    event_types = [e.get("type") for e in events]
    print(f"Event sequence: {event_types}")
    
    # Required events for basic format
    required_events = ["message_start", "ping", "content_block_start", 
                      "content_block_delta", "content_block_delta", 
                      "content_block_stop", "message_delta", "message_stop"]
    
    # Check if all required events are present
    for i, required in enumerate(required_events):
        if i >= len(event_types):
            print(f"❌ Missing event at position {i}: {required}")
            continue
            
        if event_types[i] != required:
            print(f"❌ Event {i}: expected '{required}', got '{event_types[i]}'")
        else:
            print(f"✓ Event {i}: {required}")
    
    # Validate message_start structure
    message_start = events[0]
    if message_start.get("type") == "message_start":
        msg = message_start.get("message", {})
        required_fields = ["id", "type", "role", "content", "model", "stop_reason", "stop_sequence", "usage"]
        for field in required_fields:
            if field not in msg:
                print(f"❌ message_start.message missing field: {field}")
            else:
                print(f"✓ message_start.message has field: {field}")
        
        # Check usage has input_tokens and output_tokens
        usage = msg.get("usage", {})
        if "input_tokens" not in usage or "output_tokens" not in usage:
            print("❌ message_start.message.usage missing input_tokens or output_tokens")
        else:
            print(f"✓ message_start.message.usage: input_tokens={usage['input_tokens']}, output_tokens={usage['output_tokens']}")
    
    # Validate content_block_start
    content_start = next((e for e in events if e.get("type") == "content_block_start"), None)
    if content_start:
        block = content_start.get("content_block", {})
        if block.get("type") != "text":
            print(f"❌ content_block_start content_block.type should be 'text', got '{block.get('type')}'")
        else:
            print("✓ content_block_start has correct type: text")
    
    # Validate content_block_delta events
    delta_events = [e for e in events if e.get("type") == "content_block_delta"]
    for delta in delta_events:
        delta_data = delta.get("delta", {})
        if delta_data.get("type") != "text_delta":
            print(f"❌ content_block_delta delta.type should be 'text_delta', got '{delta_data.get('type')}'")
        else:
            print("✓ content_block_delta has correct type: text_delta")
    
    # Validate message_delta
    message_delta = next((e for e in events if e.get("type") == "message_delta"), None)
    if message_delta:
        delta = message_delta.get("delta", {})
        if delta.get("stop_reason") != "end_turn":
            print(f"❌ message_delta delta.stop_reason should be 'end_turn', got '{delta.get('stop_reason')}'")
        else:
            print("✓ message_delta has correct stop_reason: end_turn")
        
        if "usage" not in message_delta:
            print("❌ message_delta missing usage field")
        else:
            print("✓ message_delta has usage field")


def validate_tool_call_format(events):
    """Validate tool call format compliance"""
    print("\n--- Validation Results ---")
    
    event_types = [e.get("type") for e in events]
    print(f"Event sequence: {event_types}")
    
    # Check for required events
    required_events = ["message_start", "content_block_start", "content_block_delta", 
                      "content_block_stop", "content_block_start", "content_block_delta",
                      "content_block_stop", "message_delta", "message_stop"]
    
    # Find tool_use content_block_start
    tool_starts = [e for e in events if e.get("type") == "content_block_start" 
                   and e.get("content_block", {}).get("type") == "tool_use"]
    
    if not tool_starts:
        print("❌ No tool_use content_block_start found")
    else:
        print(f"✓ Found {len(tool_starts)} tool_use content_block_start events")
        for tool_start in tool_starts:
            block = tool_start.get("content_block", {})
            if "id" not in block or "name" not in block:
                print("❌ tool_use content_block missing id or name")
            else:
                print(f"✓ tool_use content_block: id={block['id']}, name={block['name']}")
    
    # Find input_json_delta events
    json_deltas = [e for e in events if e.get("type") == "content_block_delta"
                   and e.get("delta", {}).get("type") == "input_json_delta"]
    
    if not json_deltas:
        print("❌ No input_json_delta events found")
    else:
        print(f"✓ Found {len(json_deltas)} input_json_delta events")
        for delta in json_deltas:
            delta_data = delta.get("delta", {})
            partial_json = delta_data.get("partial_json", "")
            print(f"✓ input_json_delta partial_json length: {len(partial_json)}")
    
    # Check message_delta stop_reason
    message_delta = next((e for e in events if e.get("type") == "message_delta"), None)
    if message_delta:
        delta = message_delta.get("delta", {})
        if delta.get("stop_reason") != "tool_use":
            print(f"❌ message_delta stop_reason should be 'tool_use', got '{delta.get('stop_reason')}'")
        else:
            print("✓ message_delta has correct stop_reason: tool_use")


def validate_thinking_format(events):
    """Validate thinking format compliance"""
    print("\n--- Validation Results ---")
    
    event_types = [e.get("type") for e in events]
    print(f"Event sequence: {event_types}")
    
    # Find thinking content_block_start
    thinking_starts = [e for e in events if e.get("type") == "content_block_start"
                       and e.get("content_block", {}).get("type") == "thinking"]
    
    if not thinking_starts:
        print("❌ No thinking content_block_start found")
    else:
        print(f"✓ Found {len(thinking_starts)} thinking content_block_start events")
    
    # Find thinking_delta events
    thinking_deltas = [e for e in events if e.get("type") == "content_block_delta"
                       and e.get("delta", {}).get("type") == "thinking_delta"]
    
    if not thinking_deltas:
        print("❌ No thinking_delta events found")
    else:
        print(f"✓ Found {len(thinking_deltas)} thinking_delta events")
        total_thinking = "".join([d.get("delta", {}).get("thinking", "") for d in thinking_deltas])
        print(f"✓ Total thinking content length: {len(total_thinking)}")
    
    # Find signature_delta events
    signature_deltas = [e for e in events if e.get("type") == "content_block_delta"
                        and e.get("delta", {}).get("type") == "signature_delta"]
    
    if not signature_deltas:
        print("❌ No signature_delta events found")
    else:
        print(f"✓ Found {len(signature_deltas)} signature_delta events")
        for delta in signature_deltas:
            sig = delta.get("delta", {}).get("signature")
            print(f"✓ signature_delta signature length: {len(sig) if sig else 0}")
    
    # Check that thinking block comes before text block
    thinking_indices = [e.get("index") for e in events if e.get("type") == "content_block_start"
                       and e.get("content_block", {}).get("type") == "thinking"]
    text_indices = [e.get("index") for e in events if e.get("type") == "content_block_start"
                   and e.get("content_block", {}).get("type") == "text"]
    
    if thinking_indices and text_indices:
        if min(thinking_indices) < min(text_indices):
            print("✓ Thinking block comes before text block")
        else:
            print("❌ Text block should come after thinking block")


def validate_web_search_format(events):
    """Validate web search tool format compliance"""
    print("\n--- Validation Results ---")
    
    event_types = [e.get("type") for e in events]
    print(f"Event sequence: {event_types}")
    
    # Web search tools use server_tool_use content type, not tool_use
    tool_starts = [e for e in events if e.get("type") == "content_block_start"
                   and e.get("content_block", {}).get("type") == "server_tool_use"]
    
    if not tool_starts:
        print("❌ No server_tool_use content_block_start found")
    else:
        for tool_start in tool_starts:
            block = tool_start.get("content_block", {})
            if block.get("name") == "web_search":
                print("✓ Found web_search server_tool_use")
            else:
                print(f"✓ Found server_tool_use with name: {block.get('name')}")


async def main():
    """Run all tests"""
    print("Testing Streaming Format Compliance")
    print("=" * 80)

    if convert_openai_stream_to_anthropic_async is None:
        print("❌ Cannot run tests - convert_openai_stream_to_anthropic_async not available")
        return

    try:
        # Test 1: Basic format
        await test_basic_format()

        # Test 2: Tool call format
        await test_tool_call_format()

        # Test 3: Thinking format
        await test_thinking_format()

        # Test 4: Web search format
        await test_web_search_format()

        print("\n" + "="*80)
        print("All tests completed!")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())