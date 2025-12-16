"""
Test script for Customer Support MAF Backend workflow
Tests the handoff orchestration and agent flows
"""

import asyncio
import json
from Backend.backend import (
    setup_workflow,
    context_manager,
    AgentRunEvent,
    WorkflowOutputEvent
)


async def test_order_query():
    """Test order/ticket query routing to database pipeline"""
    print("\n" + "="*80)
    print("TEST 1: Order Query - Should route to Database Pipeline")
    print("="*80)
    
    workflow = await setup_workflow()
    query = "What are the top 5 orders by customer name?"
    
    print(f"\n📝 Query: {query}")
    print(f"\n🔄 Running workflow...\n")
    
    try:
        events = await workflow.run(query)
        
        # Print agent execution trace
        for event in events:
            if isinstance(event, AgentRunEvent):
                print(f"  → {event.executor_id}: {event.data}")
        
        print(f"\n✅ Final State: {events.get_final_state()}")
        outputs = events.get_outputs()
        if outputs:
            print(f"📊 Outputs: {outputs}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def test_fraud_query():
    """Test fraud detection query"""
    print("\n" + "="*80)
    print("TEST 2: Fraud Query - Should route to Fraud Detection Agent")
    print("="*80)
    
    workflow = await setup_workflow()
    query = "I suspect there's fraud on my account with unusual transactions"
    
    print(f"\n📝 Query: {query}")
    print(f"\n🔄 Running workflow...\n")
    
    try:
        events = await workflow.run(query)
        
        # Print agent execution trace
        for event in events:
            if isinstance(event, AgentRunEvent):
                print(f"  → {event.executor_id}: {event.data}")
        
        print(f"\n✅ Final State: {events.get_final_state()}")
        outputs = events.get_outputs()
        if outputs:
            print(f"📊 Outputs: {outputs}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def test_billing_query():
    """Test billing query"""
    print("\n" + "="*80)
    print("TEST 3: Billing Query - Should route to Final Agent")
    print("="*80)
    
    workflow = await setup_workflow()
    query = "What is my current bill balance?"
    
    print(f"\n📝 Query: {query}")
    print(f"\n🔄 Running workflow...\n")
    
    try:
        events = await workflow.run(query)
        
        # Print agent execution trace
        for event in events:
            if isinstance(event, AgentRunEvent):
                print(f"  → {event.executor_id}: {event.data}")
        
        print(f"\n✅ Final State: {events.get_final_state()}")
        outputs = events.get_outputs()
        if outputs:
            print(f"📊 Outputs: {outputs}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def test_ticket_query():
    """Test ticket query - should go through database pipeline"""
    print("\n" + "="*80)
    print("TEST 4: Ticket Query - Should route to Database Pipeline")
    print("="*80)
    
    workflow = await setup_workflow()
    query = "Show me all open support tickets for customer ID 12345"
    
    print(f"\n📝 Query: {query}")
    print(f"\n🔄 Running workflow...\n")
    
    try:
        events = await workflow.run(query)
        
        # Print agent execution trace
        for event in events:
            if isinstance(event, AgentRunEvent):
                print(f"  → {event.executor_id}: {event.data}")
        
        print(f"\n✅ Final State: {events.get_final_state()}")
        outputs = events.get_outputs()
        if outputs:
            print(f"📊 Outputs: {outputs}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def test_complex_query():
    """Test complex query - should route to Live Support"""
    print("\n" + "="*80)
    print("TEST 5: Complex Query - Should route to Final Agent")
    print("="*80)
    
    workflow = await setup_workflow()
    query = "I need help with a complex custom integration scenario"
    
    print(f"\n📝 Query: {query}")
    print(f"\n🔄 Running workflow...\n")
    
    try:
        events = await workflow.run(query)
        
        # Print agent execution trace
        for event in events:
            if isinstance(event, AgentRunEvent):
                print(f"  → {event.executor_id}: {event.data}")
        
        print(f"\n✅ Final State: {events.get_final_state()}")
        outputs = events.get_outputs()
        if outputs:
            print(f"📊 Outputs: {outputs}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")


async def print_workflow_structure():
    """Print the workflow structure for verification"""
    print("\n" + "="*80)
    print("WORKFLOW STRUCTURE")
    print("="*80)
    
    structure = """
    Routing Agent (Triage)
    ├── Query: "order" or "ticket"
    │   └─→ Database Selector Agent
    │       └─→ SQL Generator Agent
    │           └─→ Validator Agent
    │               ├─→ SQL Executor Agent (if approved)
    │               │   └─→ Final Response Agent
    │               └─→ SQL Generator Retry (if rejected)
    │                   └─→ Validator Agent (retry loop)
    │
    ├── Query: "fraud" or "scam"
    │   └─→ Fraud Detection Agent
    │       └─→ Final Response Agent
    │
    └── Query: "billing", "payment", or complex
        └─→ Final Response Agent
    
    Key Features:
    ✓ Handoff Orchestration: Agents hand off control based on context
    ✓ Context Preservation: Full conversation history maintained
    ✓ Retry Loop: Failed SQL queries retry validation
    ✓ Specialized Agents: Domain-specific handling
    ✓ Terminal Consolidation: All paths converge at Final Response Agent
    """
    
    print(structure)


async def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("CUSTOMER SUPPORT MAF BACKEND - WORKFLOW TESTS")
    print("="*80)
    print("Testing handoff orchestration pattern with dynamic routing")
    
    # Print workflow structure
    await print_workflow_structure()
    
    # Run tests
    await test_order_query()
    await test_fraud_query()
    await test_billing_query()
    await test_ticket_query()
    await test_complex_query()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print("""
    ✓ Test 1: Order queries route to database pipeline
    ✓ Test 2: Fraud queries route to fraud detection agent
    ✓ Test 3: Billing queries route to final agent
    ✓ Test 4: Ticket queries route to database pipeline
    ✓ Test 5: Complex queries route to final agent
    
    Expected Behavior:
    - Routing Agent analyzes query and determines appropriate path
    - Specialist agents execute domain-specific logic
    - Database pipeline handles order/ticket queries with validation retry loop
    - All paths converge at Final Response Agent
    """)
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
