"""
Coloring Book Design Generator - Multi-Agent System

This application uses a LangGraph-based multi-agent architecture with:
- Executor Agent: Generates coloring book content (title, description, prompts, keywords)
- Evaluator Agent: Reviews content quality and provides feedback for improvements

Run with: uv run python main.py
"""

import sys
from features.design_generation.workflow import run_coloring_book_agent


def main():
    """Main entry point for the Coloring Book Design Generator."""
    print("🎨 Welcome to the Advanced Coloring Book Design Generator! 🎨")
    print("=" * 60)
    print("This tool uses AI agents to create complete coloring book")
    print("design packages with quality assurance.")
    print("=" * 60)
    
    # Get user input
    if len(sys.argv) > 1:
        # Allow passing request as command line argument
        user_request = " ".join(sys.argv[1:])
        print(f"\nUsing command line input: {user_request}")
    else:
        user_request = input("\nDescribe the coloring book design you'd like to create: ")
    
    if not user_request.strip():
        print("No input provided. Using default example...")
        user_request = "a forest animals coloring book for adults with intricate patterns"
    
    print()
    
    try:
        # Run the multi-agent workflow
        final_state = run_coloring_book_agent(user_request)
        
        # Show final status
        if final_state.get("status") == "complete":
            print("\n✅ Your coloring book design package is ready!")
            
            # Show evaluation summary if available
            eval_result = final_state.get("evaluation_result", {})
            if eval_result:
                score = eval_result.get("overall_score", "N/A")
                print(f"   Final Quality Score: {score}/100")
                iterations = final_state.get("iteration", 1)
                print(f"   Iterations needed: {iterations}")
        else:
            print("\n⚠️ Workflow completed with status:", final_state.get("status"))
            
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Thanks for using the Coloring Book Assistant!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please check your OpenAI API key and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
