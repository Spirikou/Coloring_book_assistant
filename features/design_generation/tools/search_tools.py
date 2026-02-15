"""Web search tools for trend research."""

from langchain_core.tools import tool

try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False


@tool
def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web for information about coloring book trends, themes, or market research.
    
    Args:
        query: The search query to look up (e.g., "trending coloring book themes 2024").
        max_results: Maximum number of results to return (default 5).
        
    Returns:
        A formatted string containing search results with titles and snippets.
    """
    if not DDGS_AVAILABLE:
        return "Web search is not available. Please install duckduckgo-search: uv add duckduckgo-search"
    
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        
        if not results:
            return f"No results found for: {query}"
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            body = result.get("body", "No description")
            href = result.get("href", "")
            formatted_results.append(f"{i}. **{title}**\n   {body}\n   URL: {href}")
        
        return "\n\n".join(formatted_results)
    
    except Exception as e:
        return f"Search error: {str(e)}"


@tool
def search_coloring_book_trends() -> str:
    """
    Search for current trending coloring book themes and styles.
    
    Returns:
        A formatted string with trending coloring book information.
    """
    if not DDGS_AVAILABLE:
        return "Web search is not available. Please install duckduckgo-search: uv add duckduckgo-search"
    
    queries = [
        "best selling coloring books 2024",
        "trending coloring book themes adults",
    ]
    
    all_results = []
    
    try:
        with DDGS() as ddgs:
            for query in queries:
                results = list(ddgs.text(query, max_results=3))
                for result in results:
                    title = result.get("title", "No title")
                    body = result.get("body", "No description")
                    all_results.append(f"- **{title}**: {body}")
        
        if not all_results:
            return "No trending information found."
        
        return "Current Coloring Book Trends:\n\n" + "\n\n".join(all_results)
    
    except Exception as e:
        return f"Search error: {str(e)}"
