"""LangGraph workflow for the Coloring Book Assistant with per-component evaluation."""

import os
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from dotenv import load_dotenv

from features.design_generation.agents.executor import get_executor_tools, EXECUTOR_SYSTEM_PROMPT
from features.design_generation.tools.user_tools import display_results, UserQuestionException, get_pending_question, clear_pending_question
from features.design_generation.tools.content_tools import (
    generate_and_refine_title_description,
    generate_and_refine_prompts,
    generate_and_refine_cover_prompts,
    generate_and_refine_keywords,
    regenerate_art_style,
    regenerate_title_description,
    regenerate_prompts,
    regenerate_cover_prompts,
    regenerate_keywords,
)
from core.state import ColoringBookState

load_dotenv()


def _build_theme_context_from_concept(concept: dict) -> dict:
    """Build theme_context dict from a concept for content generation tools."""
    theme = concept.get("theme") or concept.get("theme_concept", "")
    style = concept.get("style") or concept.get("art_style", "")
    mixable = concept.get("mixable_components", {})
    if not theme and mixable:
        theme = mixable.get("theme", "")
    if not style and mixable:
        style = mixable.get("style", "")
    expanded = concept.get("expanded_theme") or f"{theme} in {style} style"
    return {
        "original_input": f"{theme} in {style} style",
        "expanded_theme": expanded,
        "main_theme": theme or expanded.split(" in ")[0].strip() if expanded else "",
        "artistic_style": style,
        "style_description": concept.get("style_description", ""),
        "signature_artist": concept.get("signature_artist", "style-inspired artist"),
        "unique_angle": concept.get("unique_angle", ""),
        "target_audience": concept.get("target_audience", "Adults and coloring enthusiasts"),
        "style_keywords": [style] if style else [],
        "visual_elements": concept.get("visual_elements", []),
        "mood": concept.get("mood", ["creative", "relaxing"]),
        "page_ideas": concept.get("page_ideas", []),
    }


def create_executor_node():
    """Create the executor node that generates content."""
    from config import EXECUTOR_MODEL
    llm = ChatOpenAI(
        model=EXECUTOR_MODEL,
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
    new_state = state.copy()

    # When concept is provided, skip agent and call content tools directly
    concept = state.get("concept")
    if concept and not state.get("user_answer"):
        generation_log = []
        generation_log.append({"step": "concept", "message": "Building theme context from concept..."})

        print("\n🎨 Concept-based design - Using pre-defined concept (skipping theme expansion)...")
        theme_context = _build_theme_context_from_concept(concept)
        user_request = theme_context.get("original_input", state.get("user_request", ""))
        new_state["expanded_theme"] = theme_context
        new_state["theme_attempts"] = [{"attempt": 1, "content": theme_context, "evaluation": {"score": 100, "passed": True}, "feedback": ""}]
        new_state["theme_score"] = 100
        new_state["theme_passed"] = True
        new_state["theme_status"] = "completed"
        new_state["style_research"] = {}

        # Generate title and description
        generation_log.append({"step": "title", "message": "Generating title and description..."})
        print("   📝 Generating title and description...")
        title_result = generate_and_refine_title_description.invoke({"user_input": user_request, "theme_context": theme_context})
        if isinstance(title_result, dict) and "final_content" in title_result:
            fc = title_result["final_content"]
            new_state["title"] = fc.get("title", "")
            new_state["description"] = fc.get("description", "")
            new_state["title_attempts"] = title_result.get("attempts", [])
            new_state["title_score"] = title_result.get("final_score", 0)
            new_state["title_passed"] = title_result.get("passed", False)
        new_state["title_status"] = "completed"

        # Generate prompts
        generation_log.append({"step": "prompts", "message": "Generating MidJourney prompts..."})
        print("   🎨 Generating MidJourney prompts...")
        prompts_result = generate_and_refine_prompts.invoke({"description": new_state.get("description", ""), "theme_context": theme_context})
        if isinstance(prompts_result, dict) and "final_content" in prompts_result:
            new_state["midjourney_prompts"] = prompts_result["final_content"]
            new_state["prompts_attempts"] = prompts_result.get("attempts", [])
            new_state["prompts_score"] = prompts_result.get("final_score", 0)
            new_state["prompts_passed"] = prompts_result.get("passed", False)
        new_state["prompts_status"] = "completed"

        # Generate cover prompts
        generation_log.append({"step": "cover_prompts", "message": "Generating cover prompts..."})
        print("   📖 Generating cover prompts...")
        cover_result = generate_and_refine_cover_prompts.invoke({"description": new_state.get("description", ""), "theme_context": theme_context})
        if isinstance(cover_result, dict) and "final_content" in cover_result:
            new_state["cover_prompts"] = cover_result["final_content"]
            new_state["cover_prompts_attempts"] = cover_result.get("attempts", [])
            new_state["cover_prompts_score"] = cover_result.get("final_score", 0)
            new_state["cover_prompts_passed"] = cover_result.get("passed", False)
        new_state["cover_prompts_status"] = "completed"

        # Generate keywords
        generation_log.append({"step": "keywords", "message": "Generating SEO keywords..."})
        print("   🔍 Generating SEO keywords...")
        keywords_result = generate_and_refine_keywords.invoke({"description": new_state.get("description", ""), "theme_context": theme_context})
        if isinstance(keywords_result, dict) and "final_content" in keywords_result:
            new_state["seo_keywords"] = keywords_result["final_content"]
            new_state["keywords_attempts"] = keywords_result.get("attempts", [])
            new_state["keywords_score"] = keywords_result.get("final_score", 0)
            new_state["keywords_passed"] = keywords_result.get("passed", False)
        new_state["keywords_status"] = "completed"

        generation_log.append({"step": "complete", "message": "Design package complete!"})
        new_state["generation_log"] = generation_log
        new_state["status"] = "complete"
        new_state["messages"] = []
        return new_state

    print("\n🔄 Executor Agent - Generating content with quality evaluation...")
    executor = create_executor_node()
    
    # Initialize status fields if not present
    if "theme_status" not in new_state:
        new_state["theme_status"] = "pending"
    if "title_status" not in new_state:
        new_state["title_status"] = "pending"
    if "prompts_status" not in new_state:
        new_state["prompts_status"] = "pending"
    if "cover_prompts_status" not in new_state:
        new_state["cover_prompts_status"] = "pending"
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

                elif tool_name == "generate_and_refine_cover_prompts":
                    if isinstance(content, dict):
                        new_state["cover_prompts"] = content.get("final_content", [])
                        new_state["cover_prompts_attempts"] = content.get("attempts", [])
                        new_state["cover_prompts_score"] = content.get("final_score", 0)
                        new_state["cover_prompts_passed"] = content.get("passed", False)
                        new_state["cover_prompts_status"] = "completed"

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
    """Display the final results."""
    print("\n✅ Design generation complete!")
    
    new_state = state.copy()
    
    # Display results
    display_results.invoke({
        "title": state.get("title", ""),
        "description": state.get("description", ""),
        "midjourney_prompts": state.get("midjourney_prompts", []),
        "seo_keywords": state.get("seo_keywords", [])
    })
    
    # Note: Saving is handled by the UI via save_workflow_state() to saved_designs folder
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
        "cover_prompts": [],
        "seo_keywords": [],
        # Attempt history
        "title_attempts": [],
        "prompts_attempts": [],
        "cover_prompts_attempts": [],
        "keywords_attempts": [],
        # Quality scores
        "title_score": 0,
        "prompts_score": 0,
        "cover_prompts_score": 0,
        "keywords_score": 0,
        "title_passed": False,
        "prompts_passed": False,
        "cover_prompts_passed": False,
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
        "cover_prompts_status": "pending",
        "keywords_status": "pending"
    }

    # Create and run the graph
    app = create_coloring_book_graph()
    final_state = app.invoke(initial_state)

    print("\n" + "=" * 60)
    print("🎉 Workflow complete!")
    print("=" * 60)
    
    return final_state


def run_design_for_concept(concept: dict) -> ColoringBookState:
    """
    Run full design generation for a single pre-defined concept.
    Skips theme expansion and uses the concept directly as theme context.

    Args:
        concept: Dict with theme, style (or theme_concept, art_style), and optional
                 style_description, unique_angle, mixable_components.

    Returns:
        The final state with all generated content.
    """
    theme = concept.get("theme") or concept.get("theme_concept", "")
    style = concept.get("style") or concept.get("art_style", "")
    mixable = concept.get("mixable_components", {})
    if not theme and mixable:
        theme = mixable.get("theme", "")
    if not style and mixable:
        style = mixable.get("style", "")
    user_request = f"{theme} in {style} style" if (theme or style) else str(concept)

    print("🎨 Starting Concept-Based Design Generator")
    print("=" * 60)
    print(f"Concept: {theme} | Style: {style}")
    print("=" * 60)

    initial_state: ColoringBookState = {
        "user_request": user_request,
        "concept": concept,
        "concept_source": concept,
        "expanded_theme": {},
        "theme_attempts": [],
        "theme_score": 0,
        "theme_passed": False,
        "style_research": {},
        "title": "",
        "description": "",
        "midjourney_prompts": [],
        "cover_prompts": [],
        "seo_keywords": [],
        "title_attempts": [],
        "prompts_attempts": [],
        "cover_prompts_attempts": [],
        "keywords_attempts": [],
        "title_score": 0,
        "prompts_score": 0,
        "cover_prompts_score": 0,
        "keywords_score": 0,
        "title_passed": False,
        "prompts_passed": False,
        "cover_prompts_passed": False,
        "keywords_passed": False,
        "messages": [],
        "status": "generating",
        "pending_question": "",
        "user_answer": "",
        "images_folder_path": "",
        "uploaded_images": [],
        "images_ready": False,
        "workflow_stage": "design",
        "completed_stages": [],
        "theme_status": "pending",
        "title_status": "pending",
        "prompts_status": "pending",
        "cover_prompts_status": "pending",
        "keywords_status": "pending",
    }

    app = create_coloring_book_graph()
    final_state = app.invoke(initial_state)
    final_state["concept_source"] = concept

    print("\n" + "=" * 60)
    print("🎉 Concept design complete!")
    print("=" * 60)

    return final_state


DESIGN_STEPS = ["theme_context", "title", "prompts", "cover_prompts", "keywords"]


def run_design_step_for_concept(
    concept: dict,
    step_name: str,
    previous_state: ColoringBookState | None = None,
) -> ColoringBookState:
    """
    Run a single step of design generation for a concept.
    Used for step-by-step UI progress with checklist.

    Args:
        concept: Dict with theme, style (or theme_concept, art_style).
        step_name: One of "theme_context", "title", "prompts", "cover_prompts", "keywords".
        previous_state: State from previous step (required for title, prompts, keywords).

    Returns:
        Updated state with generation_log including completed steps.
    """
    theme = concept.get("theme") or concept.get("theme_concept", "")
    style = concept.get("style") or concept.get("art_style", "")
    mixable = concept.get("mixable_components", {})
    if not theme and mixable:
        theme = mixable.get("theme", "")
    if not style and mixable:
        style = mixable.get("style", "")
    user_request = f"{theme} in {style} style" if (theme or style) else str(concept)

    if previous_state:
        new_state = dict(previous_state)
        generation_log = list(new_state.get("generation_log", []))
    else:
        new_state = {
            "user_request": user_request,
            "concept": concept,
            "concept_source": concept,
            "expanded_theme": {},
            "theme_attempts": [],
            "theme_score": 0,
            "theme_passed": False,
            "style_research": {},
            "title": "",
            "description": "",
            "midjourney_prompts": [],
            "cover_prompts": [],
            "seo_keywords": [],
            "title_attempts": [],
            "prompts_attempts": [],
            "cover_prompts_attempts": [],
            "keywords_attempts": [],
            "title_score": 0,
            "prompts_score": 0,
            "cover_prompts_score": 0,
            "keywords_score": 0,
            "title_passed": False,
            "prompts_passed": False,
            "cover_prompts_passed": False,
            "keywords_passed": False,
            "messages": [],
            "status": "generating",
            "pending_question": "",
            "user_answer": "",
            "images_folder_path": "",
            "uploaded_images": [],
            "images_ready": False,
            "workflow_stage": "design",
            "completed_stages": [],
            "theme_status": "pending",
            "title_status": "pending",
            "prompts_status": "pending",
            "cover_prompts_status": "pending",
            "keywords_status": "pending",
        }
        generation_log = []

    if step_name == "theme_context":
        theme_context = _build_theme_context_from_concept(concept)
    else:
        theme_context = new_state.get("expanded_theme") or _build_theme_context_from_concept(concept)

    if step_name == "theme_context":
        generation_log.append({"step": "concept", "message": "Building theme context from concept..."})
        new_state["expanded_theme"] = theme_context
        new_state["theme_attempts"] = [{"attempt": 1, "content": theme_context, "evaluation": {"score": 100, "passed": True}, "feedback": ""}]
        new_state["theme_score"] = 100
        new_state["theme_passed"] = True
        new_state["theme_status"] = "completed"
        new_state["style_research"] = {}

    elif step_name == "title":
        generation_log.append({"step": "title", "message": "Generating title and description..."})
        title_result = generate_and_refine_title_description.invoke(
            {"user_input": theme_context.get("original_input", user_request), "theme_context": theme_context}
        )
        if isinstance(title_result, dict) and "final_content" in title_result:
            fc = title_result["final_content"]
            new_state["title"] = fc.get("title", "")
            new_state["description"] = fc.get("description", "")
            new_state["title_attempts"] = title_result.get("attempts", [])
            new_state["title_score"] = title_result.get("final_score", 0)
            new_state["title_passed"] = title_result.get("passed", False)
        new_state["title_status"] = "completed"
        new_state["expanded_theme"] = theme_context

    elif step_name == "prompts":
        generation_log.append({"step": "prompts", "message": "Generating MidJourney prompts..."})
        prompts_result = generate_and_refine_prompts.invoke(
            {"description": new_state.get("description", ""), "theme_context": theme_context}
        )
        if isinstance(prompts_result, dict) and "final_content" in prompts_result:
            new_state["midjourney_prompts"] = prompts_result["final_content"]
            new_state["prompts_attempts"] = prompts_result.get("attempts", [])
            new_state["prompts_score"] = prompts_result.get("final_score", 0)
            new_state["prompts_passed"] = prompts_result.get("passed", False)
        new_state["prompts_status"] = "completed"

    elif step_name == "cover_prompts":
        generation_log.append({"step": "cover_prompts", "message": "Generating cover prompts..."})
        cover_result = generate_and_refine_cover_prompts.invoke(
            {"description": new_state.get("description", ""), "theme_context": theme_context}
        )
        if isinstance(cover_result, dict) and "final_content" in cover_result:
            new_state["cover_prompts"] = cover_result["final_content"]
            new_state["cover_prompts_attempts"] = cover_result.get("attempts", [])
            new_state["cover_prompts_score"] = cover_result.get("final_score", 0)
            new_state["cover_prompts_passed"] = cover_result.get("passed", False)
        new_state["cover_prompts_status"] = "completed"

    elif step_name == "keywords":
        generation_log.append({"step": "keywords", "message": "Generating SEO keywords..."})
        keywords_result = generate_and_refine_keywords.invoke(
            {"description": new_state.get("description", ""), "theme_context": theme_context}
        )
        if isinstance(keywords_result, dict) and "final_content" in keywords_result:
            new_state["seo_keywords"] = keywords_result["final_content"]
            new_state["keywords_attempts"] = keywords_result.get("attempts", [])
            new_state["keywords_score"] = keywords_result.get("final_score", 0)
            new_state["keywords_passed"] = keywords_result.get("passed", False)
        new_state["keywords_status"] = "completed"
        generation_log.append({"step": "complete", "message": "Design package complete!"})
        new_state["status"] = "complete"

    new_state["generation_log"] = generation_log
    new_state["concept_source"] = concept
    return new_state


def rerun_design_with_modifications(
    existing_state: ColoringBookState,
    modifications: dict,
) -> ColoringBookState:
    """
    Rerun design generation with partial modifications.
    modifications can include:
      - art_style: str - new style hint; cascades to title, prompts, keywords
      - regenerate: list - ["title", "prompts", "keywords"] or ["all"] for full rerun
      - custom_instructions: str - free text instructions for the AI (e.g., "make it more playful")

    Args:
        existing_state: Current workflow state.
        modifications: Dict with art_style, regenerate, and/or custom_instructions keys.

    Returns:
        Updated state with regenerated content.
    """
    new_state = dict(existing_state)
    theme_context = new_state.get("expanded_theme") or {}
    if isinstance(theme_context, dict):
        theme_context = dict(theme_context)
    else:
        theme_context = {}

    regenerate_list = modifications.get("regenerate", [])
    if isinstance(regenerate_list, str):
        regenerate_list = [regenerate_list]
    art_style_hint = modifications.get("art_style", "")
    custom_instructions = modifications.get("custom_instructions", "")

    # If art_style changed, update theme_context first (cascades to all)
    if art_style_hint:
        print(f"   🎨 Updating art style to: {art_style_hint}")
        theme_context = regenerate_art_style(theme_context, art_style_hint)
        new_state["expanded_theme"] = theme_context
        regenerate_list = ["title", "prompts", "cover_prompts", "keywords"]  # Cascade to all

    if custom_instructions:
        print(f"   📝 Custom instructions: {custom_instructions[:50]}...")

    if "all" in regenerate_list:
        # Full rerun from concept or user_request
        concept = new_state.get("concept_source") or new_state.get("concept")
        if concept:
            return run_design_for_concept(concept)
        user_request = new_state.get("user_request", "")
        return run_coloring_book_agent(user_request)

    user_input = theme_context.get("original_input", new_state.get("user_request", ""))
    description = new_state.get("description", "")

    if "title" in regenerate_list:
        print("   📝 Regenerating title and description...")
        result = regenerate_title_description(theme_context, user_input, custom_instructions)
        if isinstance(result, dict) and "final_content" in result:
            fc = result["final_content"]
            new_state["title"] = fc.get("title", "")
            new_state["description"] = fc.get("description", "")
            new_state["title_attempts"] = result.get("attempts", [])
            new_state["title_score"] = result.get("final_score", 0)
            new_state["title_passed"] = result.get("passed", False)
        description = new_state.get("description", description)

    if "prompts" in regenerate_list:
        print("   🎨 Regenerating MidJourney prompts...")
        result = regenerate_prompts(theme_context, description, custom_instructions)
        if isinstance(result, dict) and "final_content" in result:
            new_state["midjourney_prompts"] = result["final_content"]
            new_state["prompts_attempts"] = result.get("attempts", [])
            new_state["prompts_score"] = result.get("final_score", 0)
            new_state["prompts_passed"] = result.get("passed", False)

    if "cover_prompts" in regenerate_list:
        print("   📖 Regenerating cover prompts...")
        result = regenerate_cover_prompts(theme_context, description, custom_instructions)
        if isinstance(result, dict) and "final_content" in result:
            new_state["cover_prompts"] = result["final_content"]
            new_state["cover_prompts_attempts"] = result.get("attempts", [])
            new_state["cover_prompts_score"] = result.get("final_score", 0)
            new_state["cover_prompts_passed"] = result.get("passed", False)

    if "keywords" in regenerate_list:
        print("   🔍 Regenerating SEO keywords...")
        result = regenerate_keywords(theme_context, description, custom_instructions)
        if isinstance(result, dict) and "final_content" in result:
            new_state["seo_keywords"] = result["final_content"]
            new_state["keywords_attempts"] = result.get("attempts", [])
            new_state["keywords_score"] = result.get("final_score", 0)
            new_state["keywords_passed"] = result.get("passed", False)

    new_state["status"] = "complete"
    return new_state
