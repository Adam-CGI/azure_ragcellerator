"""
Azure RAGcelerator - Streamlit Chat Interface

A conversational interface for RAG-powered document Q&A.
"""

import logging
from typing import Optional

import streamlit as st
from openai import AzureOpenAI

from .config import get_settings
from .search_service import SearchService, SearchResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Azure RAGcelerator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
<style>
    .stApp {
        max-width: 1400px;
        margin: 0 auto;
    }
    
    .citation-box {
        background-color: #1E1E2E;
        border-left: 4px solid #0078D4;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
        font-size: 0.9em;
    }
    
    .citation-header {
        color: #0078D4;
        font-weight: 600;
        margin-bottom: 6px;
    }
    
    .citation-content {
        color: #CCCCCC;
        line-height: 1.5;
    }
    
    .score-badge {
        background-color: #0078D4;
        color: white;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        margin-left: 8px;
    }
    
    .source-tag {
        color: #888888;
        font-size: 0.85em;
    }
    
    .chat-message {
        padding: 16px;
        border-radius: 12px;
        margin-bottom: 12px;
    }
    
    .header-container {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 24px;
    }
    
    .header-icon {
        font-size: 2.5em;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "search_service" not in st.session_state:
        st.session_state.search_service = None
    if "openai_client" not in st.session_state:
        st.session_state.openai_client = None


def get_search_service() -> Optional[SearchService]:
    """Get or create the search service."""
    if st.session_state.search_service is None:
        try:
            settings = get_settings()
            missing = settings.validate_required()
            if missing:
                st.error(f"Missing configuration: {', '.join(missing)}")
                return None
            st.session_state.search_service = SearchService()
        except Exception as e:
            st.error(f"Failed to initialize search service: {e}")
            return None
    return st.session_state.search_service


def get_openai_client() -> Optional[AzureOpenAI]:
    """Get or create the Azure OpenAI client."""
    if st.session_state.openai_client is None:
        try:
            settings = get_settings()
            st.session_state.openai_client = AzureOpenAI(
                azure_endpoint=settings.openai_endpoint,
                api_key=settings.openai_api_key,
                api_version=settings.openai_api_version,
            )
        except Exception as e:
            st.error(f"Failed to initialize OpenAI client: {e}")
            return None
    return st.session_state.openai_client


def build_rag_prompt(query: str, search_results: list[SearchResult]) -> str:
    """
    Build a RAG prompt with context from search results.
    
    Args:
        query: User's question.
        search_results: Relevant document chunks.
    
    Returns:
        str: The constructed prompt.
    """
    settings = get_settings()
    
    # Limit context to top N results
    context_results = search_results[:settings.max_context_chunks]
    
    # Build context string
    context_parts = []
    for i, result in enumerate(context_results, 1):
        context_parts.append(
            f"[Source {i}: {result.file_name}]\n{result.content}"
        )
    
    context = "\n\n---\n\n".join(context_parts)
    
    prompt = f"""You are a helpful assistant that answers questions based on the provided document context.
Use the following context to answer the user's question. If the answer cannot be found in the context, 
say so clearly. Always cite which source(s) you used to answer.

Context:
{context}

Question: {query}

Instructions:
- Answer based on the provided context only
- Cite sources using [Source N] format
- If information is not in the context, say "I don't have enough information to answer this"
- Be concise but thorough
"""
    
    return prompt


def generate_response(
    query: str,
    search_results: list[SearchResult],
) -> tuple[str, list[SearchResult]]:
    """
    Generate a response using RAG.
    
    Args:
        query: User's question.
        search_results: Search results for context.
    
    Returns:
        tuple: (response_text, used_sources)
    """
    client = get_openai_client()
    if not client:
        return "Error: OpenAI client not available", []
    
    settings = get_settings()
    prompt = build_rag_prompt(query, search_results)
    
    try:
        response = client.chat.completions.create(
            model=settings.chat_model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions based on document context."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
        )
        
        answer = response.choices[0].message.content
        used_sources = search_results[:settings.max_context_chunks]
        
        return answer, used_sources
    
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return f"Error generating response: {str(e)}", []


def display_citations(sources: list[SearchResult]):
    """Display source citations in an expandable section."""
    if not sources:
        return
    
    with st.expander(f"📚 Sources ({len(sources)} documents)", expanded=False):
        for i, source in enumerate(sources, 1):
            st.markdown(f"""
<div class="citation-box">
    <div class="citation-header">
        [{i}] {source.file_name}
        <span class="score-badge">Score: {source.score:.2f}</span>
    </div>
    <div class="citation-content">
        {source.content[:300]}{'...' if len(source.content) > 300 else ''}
    </div>
    <div class="source-tag">Chunk {source.chunk_id} • {source.source_path}</div>
</div>
            """, unsafe_allow_html=True)


def render_sidebar():
    """Render the sidebar with app info and controls."""
    with st.sidebar:
        st.markdown("## ⚙️ Settings")
        
        # Clear conversation button
        if st.button("🗑️ Clear Conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        st.divider()
        
        # Search settings
        st.markdown("### Search Options")
        settings = get_settings()
        
        use_semantic = st.checkbox("Semantic Ranking", value=True, 
                                   help="Use Azure Cognitive Search semantic ranking")
        use_vector = st.checkbox("Vector Search", value=True,
                                help="Include vector similarity in search")
        
        st.session_state.use_semantic = use_semantic
        st.session_state.use_vector = use_vector
        
        st.divider()
        
        # App info
        st.markdown("### About")
        st.markdown("""
        **Azure RAGcelerator** is a document Q&A system powered by:
        - Azure Cognitive Search
        - Azure OpenAI
        - Streamlit
        
        Upload PDFs to the storage account and ask questions!
        """)
        
        # Status indicators
        st.divider()
        st.markdown("### Status")
        
        search_service = get_search_service()
        if search_service:
            st.success("✅ Search Service Connected")
        else:
            st.error("❌ Search Service Unavailable")
        
        openai_client = get_openai_client()
        if openai_client:
            st.success("✅ OpenAI Connected")
        else:
            st.error("❌ OpenAI Unavailable")


def render_chat():
    """Render the chat interface."""
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if "sources" in message and message["sources"]:
                display_citations(message["sources"])
    
    # Chat input
    if prompt := st.chat_input("Ask a question about your documents..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching documents..."):
                search_service = get_search_service()
                if not search_service:
                    st.error("Search service unavailable")
                    return
                
                # Search for relevant documents
                use_semantic = getattr(st.session_state, 'use_semantic', True)
                use_vector = getattr(st.session_state, 'use_vector', True)
                
                search_results = search_service.search(
                    prompt,
                    top_k=get_settings().max_search_results,
                    use_semantic=use_semantic,
                    use_vector=use_vector,
                )
            
            if not search_results:
                response = "I couldn't find any relevant documents to answer your question. Please make sure documents have been uploaded and processed."
                sources = []
            else:
                with st.spinner("Generating answer..."):
                    response, sources = generate_response(prompt, search_results)
            
            st.markdown(response)
            display_citations(sources)
            
            # Save assistant message
            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "sources": sources,
            })


def main():
    """Main application entry point."""
    init_session_state()
    
    # Header
    st.markdown("""
    <div class="header-container">
        <span class="header-icon">🔍</span>
        <div>
            <h1 style="margin: 0;">Azure RAGcelerator</h1>
            <p style="margin: 0; color: #888;">AI-powered document Q&A</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Render sidebar and chat
    render_sidebar()
    render_chat()


if __name__ == "__main__":
    main()



