"""LangGraph workflow for the Coloring Book Assistant with per-component evaluation."""

import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from agents.design.executor import get_executor_tools, EXECUTOR_SYSTEM_PROMPT
from tools.design.user_tools import save_report, display_results, UserQuestionException, get_pending_question, clear_pending_question
from state.workflow_state import ColoringBookState

load_dotenv()


def create_executor_node():
    """Create the executor node that generates content."""
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    tools = get_executor_tools()
    
    executor = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SystemMessage(content=EXECUTOR_SYSTEM_PROMPT),
    )
    
    return executor


def executor_node(state: ColoringBookState) -> ColoringBookState:
    """Execute the content generation using the executor agent."""
    print("\n🔄 Executor Agent - Generating content with quality evaluation...")
    
    executor = create_executor_node()
    new_state = state.copy()
    
    # Initialize status fields if not present
    if "theme_status" not in new_state:
        new_state["theme_status"] = "pending"
    if "title_status" not in new_state:
        new_state["title_status"] = "pending"
    if "prompts_status" not in new_state:
        new_state["prompts_status"] = "pending"
    if "keywords_status" not in new_state:
        new_state["keywords_status"] = "pending"
    
    # Check if we have a pending answer from the user (resuming after question)
    if state.get("user_answer"):
        # Resume with the user's answer - add it to existing messages or create new context
        existing_messages = state.get("messages", [])
        if existing_messages:
            # Continue from where we left off
            messages = existing_messages + [
                HumanMessage(content=f"User clarification: {state['user_answer']}")
            ]
        else:
            # Start fresh with the clarification
            user_message = f"Please create a complete coloring book design package for: {state['user_request']}\n\nUser clarification: {state['user_answer']}"
            messages = [HumanMessage(content=user_message)]
        # Clear the answer so we don't reuse it
        new_state["user_answer"] = ""
        new_state["pending_question"] = ""
    else:
        # Starting fresh
        user_message = f"Please create a complete coloring book design package for: {state['user_request']}"
        messages = [HumanMessage(content=user_message)]

    # Run the executor agent - catch questions
    try:
        result = executor.invoke({"messages": messages})
        # Check for pending question in case exception was caught by framework
        pending_q = get_pending_question()
        if pending_q:
            print(f"\n❓ Agent Question: {pending_q}")
            new_state["pending_question"] = pending_q
            new_state["status"] = "waiting_for_user"
            new_state["user_answer"] = ""  # Clear any previous answer
            clear_pending_question()
            return new_state
    except UserQuestionException as e:
        # Agent asked a question - pause workflow and store it
        print(f"\n❓ Agent Question: {e.question}")
        new_state["pending_question"] = e.question
        new_state["status"] = "waiting_for_user"
        new_state["user_answer"] = ""  # Clear any previous answer
        clear_pending_question()
        return new_state
    except Exception as e:
        # Check if it's a wrapped UserQuestionException
        pending_q = get_pending_question()
        if pending_q:
            print(f"\n❓ Agent Question: {pending_q}")
            new_state["pending_question"] = pending_q
            new_state["status"] = "waiting_for_user"
            new_state["user_answer"] = ""
            clear_pending_question()
            return new_state
        # Re-raise if it's a different exception
        raise
    
    # Extract the generated content from tool calls
    new_state["messages"] = result.get("messages", [])
    new_state["status"] = "complete"
    new_state["pending_question"] = ""  # Clear any pending question
    
    # Extract results from tool messages
    for message in result.get("messages", []):
        if hasattr(message, "name") and hasattr(message, "content"):
            tool_name = message.name
            try:
                content = message.content
                
                # Parse content if it's a string
                if isinstance(content, str):
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError:
                        continue
                
                # Handle theme expansion tool
                if tool_name == "expand_and_research_theme":
                    if isinstance(content, dict):
                        new_state["expanded_theme"] = content.get("final_theme", {})
                        new_state["theme_attempts"] = content.get("attempts", [])
                        new_state["theme_score"] = content.get("final_score", 0)
                        new_state["theme_passed"] = content.get("passed", False)
                        new_state["style_research"] = content.get("style_research", {})
                        # Update status
                        new_state["theme_status"] = "completed" if content.get("passed", False) else "completed"
                
                # Handle the generate_and_refine tools
                elif tool_name == "generate_and_refine_title_description":
                    if isinstance(content, dict):
                        final_content = content.get("final_content", {})
                        new_state["title"] = final_content.get("title", "")
                        new_state["description"] = final_content.get("description", "")
                        new_state["title_attempts"] = content.get("attempts", [])
                        new_state["title_score"] = content.get("final_score", 0)
                        new_state["title_passed"] = content.get("passed", False)
                        # Update status
                        new_state["title_status"] = "completed"
                        
                elif tool_name == "generate_and_refine_prompts":
                    if isinstance(content, dict):
                        new_state["midjourney_prompts"] = content.get("final_content", [])
                        new_state["prompts_attempts"] = content.get("attempts", [])
                        new_state["prompts_score"] = content.get("final_score", 0)
                        new_state["prompts_passed"] = content.get("passed", False)
                        # Update status
                        new_state["prompts_status"] = "completed"
                        
                elif tool_name == "generate_and_refine_keywords":
                    if isinstance(content, dict):
                        new_state["seo_keywords"] = content.get("final_content", [])
                        new_state["keywords_attempts"] = content.get("attempts", [])
                        new_state["keywords_score"] = content.get("final_score", 0)
                        new_state["keywords_passed"] = content.get("passed", False)
                        # Update status
                        new_state["keywords_status"] = "completed"
                
                # Legacy tool support
                elif tool_name == "generate_title_description":
                    if isinstance(content, dict):
                        new_state["title"] = content.get("title", "")
                        new_state["description"] = content.get("description", "")
                        
                elif tool_name == "generate_midjourney_prompts":
                    if isinstance(content, list):
                        new_state["midjourney_prompts"] = content
                        
                elif tool_name == "extract_seo_keywords":
                    if isinstance(content, list):
                        new_state["seo_keywords"] = content
                        
            except Exception as e:
                print(f"Warning: Error parsing tool result {tool_name}: {e}")
    
    # Print summary
    print(f"\n   📊 Results Summary:")
    
    # Theme expansion summary
    expanded_theme = new_state.get('expanded_theme', {})
    if expanded_theme:
        print(f"      Theme: '{expanded_theme.get('expanded_theme', '')[:40]}...' "
              f"(Score: {new_state.get('theme_score', 'N/A')}/100, "
              f"Attempts: {len(new_state.get('theme_attempts', []))})")
        print(f"      Artistic Style: {expanded_theme.get('artistic_style', 'N/A')}")
        print(f"      Signature Artist: {expanded_theme.get('signature_artist', 'N/A')}")
        print(f"      Unique Angle: {expanded_theme.get('unique_angle', 'N/A')[:50]}...")
    
    print(f"      Title: '{new_state.get('title', '')[:40]}...' "
          f"(Score: {new_state.get('title_score', 'N/A')}/100, "
          f"Attempts: {len(new_state.get('title_attempts', []))})")
    print(f"      Prompts: {len(new_state.get('midjourney_prompts', []))} generated "
          f"(Score: {new_state.get('prompts_score', 'N/A')}/100, "
          f"Attempts: {len(new_state.get('prompts_attempts', []))})")
    print(f"      Keywords: {len(new_state.get('seo_keywords', []))} generated "
          f"(Score: {new_state.get('keywords_score', 'N/A')}/100, "
          f"Attempts: {len(new_state.get('keywords_attempts', []))})")
    
    return new_state


def output_node(state: ColoringBookState) -> ColoringBookState:
    """Display and save the final results."""
    print("\n💾 Saving results...")
    
    new_state = state.copy()
    
    # Display results
    display_results.invoke({
        "title": state.get("title", ""),
        "description": state.get("description", ""),
        "midjourney_prompts": state.get("midjourney_prompts", []),
        "seo_keywords": state.get("seo_keywords", [])
    })
    
    # Save report
    save_result = save_report.invoke({
        "title": state.get("title", ""),
        "description": state.get("description", ""),
        "midjourney_prompts": state.get("midjourney_prompts", []),
        "seo_keywords": state.get("seo_keywords", [])
    })
    
    print(save_result)
    new_state["status"] = "complete"
    
    return new_state


def create_coloring_book_graph():
    """Create and compile the LangGraph workflow."""
    
    # Create the graph
    workflow = StateGraph(ColoringBookState)
    
    # Add nodes
    workflow.add_node("executor", executor_node)
    workflow.add_node("output", output_node)
    
    # Set entry point
    workflow.set_entry_point("executor")
    
    # Add edges - simple linear flow: executor -> output -> end
    workflow.add_edge("executor", "output")
    workflow.add_edge("output", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app


def run_coloring_book_agent(user_request: str) -> ColoringBookState:
    """
    Run the coloring book generation workflow.
    
    Args:
        user_request: The user's description of the coloring book they want.
        
    Returns:
        The final state with all generated content and attempt history.
    """
    print("🎨 Starting Coloring Book Design Generator")
    print("=" * 60)
    print(f"Request: {user_request}")
    print("=" * 60)
    
    # Initialize state
    initial_state: ColoringBookState = {
        "user_request": user_request,
        # Theme expansion with artistic style
        "expanded_theme": {},
        "theme_attempts": [],
        "theme_score": 0,
        "theme_passed": False,
        "style_research": {},
        # Generated content
        "title": "",
        "description": "",
        "midjourney_prompts": [],
        "seo_keywords": [],
        # Attempt history
        "title_attempts": [],
        "prompts_attempts": [],
        "keywords_attempts": [],
        # Quality scores
        "title_score": 0,
        "prompts_score": 0,
        "keywords_score": 0,
        "title_passed": False,
        "prompts_passed": False,
        "keywords_passed": False,
        # Workflow state
        "messages": [],
        "status": "generating",
        # User interaction
        "pending_question": "",
        "user_answer": "",
        # Image generation state
        "images_folder_path": "",
        "uploaded_images": [],
        "images_ready": False,
        # Workflow tracking
        "workflow_stage": "design",
        "completed_stages": [],
        # Step completion status
        "theme_status": "pending",
        "title_status": "pending",
        "prompts_status": "pending",
        "keywords_status": "pending"
    }
    
    # Create and run the graph
    app = create_coloring_book_graph()
    final_state = app.invoke(initial_state)
    
    print("\n" + "=" * 60)
    print("🎉 Workflow complete!")
    print("=" * 60)
    
    return final_state
