import streamlit as st
from neo4j import GraphDatabase
import pandas as pd

# Neo4j Connection Configuration
@st.cache_resource
def init_neo4j_connection():
    # Secrets file (.streamlit/secrets.toml) should look like:
    # NEO4J_URI = "neo4j+s://your-aura-instance.databases.neo4j.io"
    # NEO4J_USERNAME = "neo4j"
    # NEO4J_PASSWORD = "your-password"
    uri = st.secrets["NEO4J_URI"]
    username = st.secrets["NEO4J_USERNAME"]
    password = st.secrets["NEO4J_PASSWORD"]
        
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        return driver
    except Exception as e:
        st.error(f"Connection Error: {e}")
        return None

# Function to run Cypher query
def run_query(driver, query, params=None):
    with driver.session() as session:
        result = session.run(query, params or {})
        return pd.DataFrame([record.data() for record in result])

# Streamlit App
def main():
    st.title("Neo4j Graph Database Explorer")
    
    # Initialize connection
    driver = init_neo4j_connection()
    
    if driver:
        # Example query selection
        query_type = st.selectbox("Choose a Query", [
            "Show All Nodes",
            "Node Count by Type",
            "Custom Query"
        ])
        
        # Predefined queries
        if query_type == "Show All Nodes":
            query = "MATCH (n) RETURN n LIMIT 25"
            df = run_query(driver, query)
            st.dataframe(df)
        
        elif query_type == "Node Count by Type":
            query = "MATCH (n) RETURN labels(n) as NodeType, count(*) as Count"
            df = run_query(driver, query)
            st.dataframe(df)
        
        # Custom query input
        elif query_type == "Custom Query":
            custom_query = st.text_area("Enter Cypher Query")
            if st.button("Run Custom Query"):
                try:
                    df = run_query(driver, custom_query)
                    st.dataframe(df)
                except Exception as e:
                    st.error(f"Query Error: {e}")
    
    else:
        st.warning("Could not connect to Neo4j database")

if __name__ == "__main__":
    main()