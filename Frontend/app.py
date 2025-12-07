"""
Streamlit Frontend for Customer Support Multi-Agent Framework
User-friendly interface for interacting with the backend API
"""

import streamlit as st
import requests
import json
from typing import Optional
from datetime import datetime

# ============== Page Configuration ==============

st.set_page_config(
    page_title="Customer Support AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== Custom CSS ==============

st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton > button {
        width: 100%;
        padding: 0.75rem;
        font-size: 1rem;
        font-weight: bold;
        border-radius: 0.5rem;
    }
    .response-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #e8f4f8;
        border-left: 4px solid #0066cc;
        color: #1a1a1a;
    }
    .error-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #ffe6e6;
        border-left: 4px solid #cc0000;
        color: #660000;
    }
    .success-box {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #e6ffe6;
        border-left: 4px solid #00cc00;
        color: #003300;
    }
    .info-card {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# ============== Constants ==============

API_BASE_URL = "http://localhost:8000"
HEALTH_CHECK_INTERVAL = 60  # seconds

# ============== Session State ==============

if "api_available" not in st.session_state:
    st.session_state.api_available = False

if "query_history" not in st.session_state:
    st.session_state.query_history = []

if "last_response" not in st.session_state:
    st.session_state.last_response = None

# ============== Helper Functions ==============

def check_api_health():
    """Check if the backend API is available"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            st.session_state.api_available = True
            return data
    except requests.exceptions.RequestException:
        st.session_state.api_available = False
    return None

def process_query(question: str) -> Optional[dict]:
    """Send query to backend API and get response"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/query",
            json={"question": question},
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            if response.text:
                st.error(response.text)
            return None
    except requests.exceptions.Timeout:
        st.error("Request timed out. The query may be taking too long. Please try again.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the backend API. Please ensure the server is running.")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def format_response(response: dict) -> str:
    """Format API response for display"""
    output = ""
    if response.get("response"):
        output += response["response"]
    
    # Add metadata if available
    if response.get("database") or response.get("query") or response.get("num_rows"):
        output += "\n\n---\n"
        if response.get("database"):
            output += f"\n**Database Used:** {response['database']}"
        if response.get("query"):
            output += f"\n\n**SQL Query:**\n```sql\n{response['query']}\n```"
        if response.get("num_rows"):
            output += f"\n**Rows Retrieved:** {response['num_rows']}"
    
    return output

# ============== Header ==============

col1, col2 = st.columns([3, 1])

with col1:
    st.title("🤖 Customer Support AI Assistant")
    st.markdown("*Powered by Multi-Agent AI Framework*")

with col2:
    health_status = check_api_health()
    if st.session_state.api_available:
        st.success("✅ Backend Connected", icon="✅")
        if health_status:
            st.caption(f"API v{health_status.get('status', 'unknown')}")
    else:
        st.error("❌ Backend Offline", icon="❌")
        st.caption("Please start the backend server")

# ============== Sidebar ==============

with st.sidebar:
    st.header("⚙️ Configuration")
    
    st.markdown("### API Settings")
    api_url = st.text_input(
        "Backend API URL",
        value=API_BASE_URL,
        key="api_url_input"
    )
    
    if api_url != API_BASE_URL:
        globals()["API_BASE_URL"] = api_url
    
    st.markdown("### About")
    st.info("""
    This AI-powered customer support assistant:
    
    1. **Understands** your natural language query
    2. **Selects** the appropriate database
    3. **Generates** safe SQL queries
    4. **Validates** queries for security
    5. **Executes** queries and retrieves data
    6. **Formats** results into helpful responses
    
    All interactions are logged for quality assurance.
    """)
    
    st.markdown("### Query History")
    if st.session_state.query_history:
        st.text(f"Total Queries: {len(st.session_state.query_history)}")
        if st.button("Clear History"):
            st.session_state.query_history = []
            st.rerun()
    else:
        st.text("No queries yet")

# ============== Main Content ==============

st.markdown("---")

# Create tabs for different sections
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📋 History", "ℹ️ Help"])

# ============== Tab 1: Chat ==============

with tab1:
    st.markdown("### Ask Your Question")
    
    # Input area
    col1, col2 = st.columns([4, 1])
    
    with col1:
        question = st.text_area(
            "Enter your question:",
            placeholder="e.g., 'Give me the ticket details for customer John Smith'",
            height=100,
            key="query_input"
        )
    
    with col2:
        st.markdown("")
        st.markdown("")
        submit_button = st.button("🚀 Submit", use_container_width=True)
    
    # Process query
    if submit_button:
        if not st.session_state.api_available:
            st.error("❌ Backend API is not available. Please start the server.")
        elif not question.strip():
            st.warning("⚠️ Please enter a question.")
        else:
            with st.spinner("🔄 Processing your query..."):
                response = process_query(question)
                
                if response:
                    st.session_state.last_response = response
                    
                    # Add to history
                    st.session_state.query_history.append({
                        "question": question,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "response": response
                    })
                    
                    # Display response
                    st.markdown("### 📝 Response")
                    
                    if response.get("status") == "success":
                        st.markdown(f"""
                        <div class="response-box">
                        {format_response(response)}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error(f"Error: {response.get('response', 'Unknown error')}")
    
    # Display last response if available
    if st.session_state.last_response and not submit_button:
        st.markdown("### 📝 Last Response")
        last_response = st.session_state.last_response
        if last_response.get("status") == "success":
            st.markdown(f"""
            <div class="response-box">
            {format_response(last_response)}
            </div>
            """, unsafe_allow_html=True)

# ============== Tab 2: History ==============

with tab2:
    st.markdown("### Query History")
    
    if st.session_state.query_history:
        for idx, item in enumerate(reversed(st.session_state.query_history), 1):
            with st.expander(f"**Query {len(st.session_state.query_history) - idx + 1}:** {item['question'][:50]}... ({item['timestamp']})"):
                st.markdown("**Question:**")
                st.text(item['question'])
                
                st.markdown("**Response:**")
                response = item['response']
                if response.get("status") == "success":
                    st.markdown(format_response(response))
                else:
                    st.error(response.get("response", "Error"))
    else:
        st.info("No query history yet. Start by asking a question!")

# ============== Tab 3: Help ==============

with tab3:
    st.markdown("### How to Use")
    
    st.markdown("""
    #### 📌 Getting Started
    
    1. **Type Your Question**: Ask any question about your database in natural language
    2. **Click Submit**: The AI will process your query through multiple agents
    3. **Get Results**: View the friendly response with data from your database
    
    #### 🔍 Example Queries
    
    - "Show me all tickets for customer John Smith"
    - "What are the top 10 products by sales?"
    - "List all open orders from the last 7 days"
    - "Give me customer details for email john@example.com"
    - "How many employees work in the Sales department?"
    
    #### ⚙️ How It Works
    
    The system uses a Multi-Agent Framework that:
    
    1. **Database Selector**: Determines which database has the information you need
    2. **SQL Generator**: Converts your question to a database query
    3. **Validator**: Ensures the query is safe and read-only
    4. **Executor**: Runs the query and retrieves results
    5. **Response Generator**: Formats results into a friendly response
    
    #### ❓ FAQ
    
    **Q: Can I modify data?**  
    A: No, all queries are read-only for security.
    
    **Q: How long does processing take?**  
    A: Usually 5-30 seconds depending on query complexity.
    
    **Q: Are my queries stored?**  
    A: Yes, in the session history for this browser tab.
    
    **Q: What if I get an error?**  
    A: Check that the backend server is running and the question is clear.
    """)

# ============== Footer ==============

st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.caption("🔒 All queries are secure and read-only")

with col2:
    if st.session_state.api_available:
        st.caption("✅ Backend: Connected")
    else:
        st.caption("❌ Backend: Offline")

with col3:
    st.caption(f"📊 Queries processed: {len(st.session_state.query_history)}")
