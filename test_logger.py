import asyncio
import logging
from tools.session_logger import UniversalLogger, log_tool_call

# Mock objects to simulate LiveKit context
class MockSession:
    def __init__(self):
        self.universal_logger = None

class MockContext:
    def __init__(self, session):
        self.session = session

# Mock tool using the decorator
@log_tool_call
async def sample_tool(ctx, arg1, arg2="default"):
    print(f"Executing tool with {arg1}, {arg2}")
    return {"status": "success", "value": arg1}

async def run_test():
    print("Initializing Logger...")
    # 1. Setup Logger
    logger = UniversalLogger("test_job_123", "test_agent")
    
    # 2. Setup Session
    session = MockSession()
    session.universal_logger = logger
    
    # 3. Setup Context
    ctx = MockContext(session)
    
    print("Running Tool...")
    # 4. Run Tool
    result = await sample_tool(ctx, "hello", arg2="world")
    
    print(f"Tool Result: {result}")
    
    # 5. Clean up
    logger.close()
    print(f"Check log file: {logger.filename}")
    
    # Read back the log file to verify
    with open(logger.filename, "r") as f:
        content = f.read()
        print("\n--- LOG CONTENT START ---")
        print(content)
        print("--- LOG CONTENT END ---")
        
        if "TOOL CALL: Executing: sample_tool" in content and "TOOL ARGS: {'arg1': 'hello', 'arg2': 'world'}" in content:
            print("\nSUCCESS: Tool call logged correctly.")
        else:
            print("\nFAILURE: Log content missing expected strings.")

if __name__ == "__main__":
    asyncio.run(run_test())
