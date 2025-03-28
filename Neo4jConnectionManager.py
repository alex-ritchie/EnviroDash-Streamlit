import streamlit as st
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

class Neo4jConnectionManager:
    @staticmethod
    def get_connection():
        try:
            uri = st.secrets["NEO4J_URI"]
            username = st.secrets["NEO4J_USERNAME"]
            password = st.secrets["NEO4J_PASSWORD"]
            
            driver = GraphDatabase.driver(
                uri, 
                auth=(username, password),
                connection_timeout=10,  # 10-second timeout
                max_connection_lifetime=300  # 5-minute max connection time
            )
            return driver
        except Exception as e:
            st.error(f"Database Connection Error: {e}")
            return None

    @staticmethod
    def run_query(query, params=None):
        driver = None
        try:
            # Establish connection
            driver = Neo4jConnectionManager.get_connection()
            
            if not driver:
                st.error("Could not establish database connection")
                return None
            
            # Run query
            with driver.session() as session:
                result = session.run(query, params or {})
                # Convert to list to ensure connection closes
                return list(result)
        
        except Neo4jError as e:
            st.error(f"Cypher Query Error: {e}")
            return None
        
        except Exception as e:
            st.error(f"Unexpected Error: {e}")
            return None
        
        finally:
            # Ensure connection is closed
            if driver:
                driver.close()