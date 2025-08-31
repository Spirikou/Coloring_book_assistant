import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser

# Load environment variables
load_dotenv()

def create_coloring_book_design():
    """Generate an innovative coloring book design based on user input."""
    
    # Initialize the language model
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.8,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Create the prompt template
    prompt = ChatPromptTemplate.from_template("""
    You are a creative coloring book designer. Create an innovative coloring book design based on this user request:
    
    User Request: {user_input}
    
    Please provide:
    1. A creative title for the design
    2. A detailed description of the design elements and patterns
    3. Suggested color palette ideas
    4. Difficulty level (Beginner/Intermediate/Advanced)
    5. Any special features or unique aspects
    
    Keep your response clean, inspiring, and suitable for a coloring book.
    """)
    
    # Create the chain
    chain = prompt | llm | StrOutputParser()
    
    # Get user input
    print("🎨 Welcome to the Coloring Book Design Generator! 🎨")
    print("=" * 50)
    
    user_input = input("Describe the coloring book design you'd like to create: ")
    
    if not user_input.strip():
        print("Please provide a description. Using default creative prompt...")
        user_input = "a magical forest with hidden creatures and geometric patterns"
    
    print("\n🔄 Generating your coloring book design...\n")
    
    try:
        # Generate the design
        result = chain.invoke({"user_input": user_input})
        
        # Display the result
        print("✨ Your Coloring Book Design ✨")
        print("=" * 50)
        print(result)
        print("\n" + "=" * 50)
        print("🎉 Design generated successfully! Happy coloring! 🎉")
        
    except Exception as e:
        print(f"❌ Error generating design: {e}")
        print("Please check your OpenAI API key and try again.")

def main():
    """Main function to run the coloring book design generator."""
    try:
        create_coloring_book_design()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye! Thanks for using the Coloring Book Design Generator!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()
