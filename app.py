import streamlit as st
import streamlit.components.v1 as stc
import networkx as nx
from pyvis.network import Network
import pandas as pd
from neo4j import GraphDatabase
import matplotlib.pyplot as plt

from Neo4jConnectionManager import Neo4jConnectionManager

# # Neo4j Connection (same as previous implementation)
# @st.cache_resource
# def init_neo4j_connection():
#     uri = st.secrets["NEO4J_URI"]
#     username = st.secrets["NEO4J_USERNAME"]
#     password = st.secrets["NEO4J_PASSWORD"]
    
#     try:
#         driver = GraphDatabase.driver(uri, auth=(username, password))
#         return driver
#     except Exception as e:
#         st.error(f"Connection Error: {e}")
#         return None

def create_tool_visualization(order_by='category'):
    """Query to fetch all Tool nodes and group them (order by)
    
    Args:
        order_by (str): The property to order the tools by; must be one of ['category', 'owner']
    """
    assert order_by in ['category', 'owner'], "order_by must be one of ['category', 'owner']"
    
    query = f"""
    MATCH (t:Tools)
    RETURN t.title_abbreviated AS tool_name, 
           t.category AS category_name,
           t.owner_abbreviated AS owner_name,
           labels(t) AS labels,
           properties(t) AS tool_properties
    ORDER BY {order_by}_name
    """
    
    properties_to_display = ['title', 'owner_abbreviated', 'category',
                             'description', 'link_dashboard']
    
    # Execute query
    result = Neo4jConnectionManager.run_query(query)
    tools = list(result)
    
    # Create NetworkX graph
    G = nx.Graph()
    
    # Track unique characteristics
    categories = {}
    owners = {}
    characteristics = {
        'category': categories,
        'owner': owners
    }
    
    
    # Add nodes and edges
    for record in tools:
        tool_name = record['tool_name']
        category_name = record['category_name']
        owner_name = record['owner_name']
        tool_properties = record['tool_properties']
        
        # Add category node if not exists
        if category_name not in categories.keys():
            if order_by == 'category':
                G.add_node(category_name, node_type='category')
            categories[category_name] = 1
        else:
            categories[category_name] += 1
            
        # Add owner node if not exists
        if owner_name not in owners.keys():
            if order_by == 'owner':
                G.add_node(owner_name, node_type='owner')
            owners[owner_name] = 1
        else:
            owners[owner_name] += 1
        
        # Add tool node
        G.add_node(tool_name, node_type='tool', category=category_name, owner=owner_name, properties=tool_properties)
        
        # Connect tool to category
        if order_by == 'category':
            G.add_edge(tool_name, category_name)
        # Connect tool to owner
        if order_by == 'owner':
            G.add_edge(tool_name, owner_name)
    
    # Convert to Pyvis Network with increased height and width
    net = Network(height="800px", width="100%", 
                  bgcolor="#222222", 
                  font_color="white", 
                  directed=False)
    
    # Color palette
    colors = ['#0072B2',  # Blue
              '#E69F00',  # Orange
              '#009E73',  # Bluish Green
              '#CC79A7',  # Pink
              '#56B4E9',  # Sky Blue
              '#F0E442']  # Yellow
    category_colors = {ordby: colors[i % len(colors)] 
                       for i, ordby in enumerate(characteristics[order_by].keys())}
    category_colors['Uncategorized'] = '#GRAY'
    
    # Add grouping characteristic nodes with custom styling
    for node in G.nodes():
        node_type = G.nodes[node].get('node_type')
        if node_type == order_by:
            # Larger nodes for grouping attribute
            net.add_node(node, 
                         color=category_colors.get(node, '#GRAY'), 
                         size=50,
                         label=node, 
                         title=node)
        else:
            # Smaller nodes for tools, colored by grouping characteristic
            category = G.nodes[node].get(order_by, 'Uncategorized')
            popup_title = ""
            props = G.nodes[node].get('properties', {})
            for property_name in properties_to_display:
                if property_name in props.keys():
                    popup_title += f"{property_name.split('_')[0]}: {props[property_name]}\n"
            net.add_node(node, 
                         color=category_colors[category], 
                         size=30,
                         label=node,
                         title=popup_title)
    
    # Add edges
    for edge in G.edges():
        net.add_edge(edge[0], edge[1])
    
    # Physics options for better layout
    net.set_options('''
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.15
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      },
      "nodes": {
        "font": {
          "size": 26,
          "color": "white",
          "face": "Arial, sans-serif"
        },
        "scaling": {
          "min": 30,
          "max": 50
        }
      }
    }
    ''')
    
    return net, categories, owners

# Streamlit Pages
def overview_page():
    st.title("Environmental Monitoring and Modeling Ecosystem Overview")
    
        # Initialize session state for selected node
    if 'selected_node' not in st.session_state:
        print("no selected node")
        st.session_state.selected_node = None
    
    # Create two columns
    col1, col2 = st.columns(2)
    
    with col1:
        # Node details display
        st.header("Tools by Category")
        
        # Create graph visualization
        graph_net, categories, owners = create_tool_visualization(order_by='category')
        
        # Display graph using Streamlit's HTML component
        html_file_path = "tool_graph_byCategory.html"
        graph_net.save_graph(html_file_path)
        
        with open(html_file_path, 'r') as f:
            graph_html = f.read()
        
        # Modify HTML to include click handling
        click_script = """
        <script>
        network.on("click", function(params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                var nodeName = network.body.data.nodes.get(nodeId).title;
                
                if (window.streamlitToken) {
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue', 
                        args: [nodeName],
                        token: window.streamlitToken
                    }, '*');
                    
                    // Trigger Streamlit rerun
                    window.parent.postMessage({
                        type: 'streamlit:rerun',
                        token: window.streamlitToken
                    }, '*');
                }
            }
        });
        </script>
        """
        
        # Inject the click handler into the HTML
        graph_html_with_click = graph_html.replace('</body>', click_script + '</body>')
        
        # Display the graph
        stc.html(graph_html_with_click, height=800, scrolling=True)
        # st.html(graph_html_with_click)
        # stc.iframe(graph_html_with_click, height=800)
        
        # Additional overview statistics
        # st.subheader("Quick Stats")
        df = pd.DataFrame.from_dict(categories, orient='index', columns=['Frequency'])
        df.reset_index(names='Owner', inplace=True)
        st.bar_chart(df, x='Owner', y='Frequency')
        
    # with col2:
    #     # Node details display
    #     st.header("Node Details")
        
    #     # Fetch and display node details
    #     if st.session_state.selected_node:
    #         # Query for full node details
    #         match_string = "{title: " + f"{st.session_state.selected_node}" + "}"
    #         query = f"""
    #         MATCH (t:Tools {match_string})
    #         RETURN properties(t) AS properties
    #         """
            
    #         # with driver.session() as session:
    #         #     result = session.run(query, {"node_name": st.session_state.selected_node})
    #         #     node_details = result.single()['properties']
    #         result = Neo4jConnectionManager.run_query(query)
    #         node_details = result.single()['properties']
            
    #         node_details
    #         # # Display node details
    #         # for key, value in node_details.items():
    #         #     print(f"{key}: {value}")
    #         #     st.write(f"**{key}**: {value}")
    #     else:
    #         st.write("Click a node to see details")    
    
    with col2:
        # Node details display
        st.header("Tools by Owner")
        
        # Create graph visualization
        graph_net, categories, owners = create_tool_visualization(order_by='owner')
        
        # Display graph using Streamlit's HTML component
        html_file_path = "tool_graph_byOwner.html"
        graph_net.save_graph(html_file_path)
        
        with open(html_file_path, 'r') as f:
            graph_html = f.read()
        
        # Modify HTML to include click handling
        click_script = """
        <script>
        network.on("click", function(params) {
            if (params.nodes.length > 0) {
                var nodeId = params.nodes[0];
                var nodeName = network.body.data.nodes.get(nodeId).title;
                
                if (window.streamlitToken) {
                    window.parent.postMessage({
                        type: 'streamlit:setComponentValue', 
                        args: [nodeName],
                        token: window.streamlitToken
                    }, '*');
                    
                    // Trigger Streamlit rerun
                    window.parent.postMessage({
                        type: 'streamlit:rerun',
                        token: window.streamlitToken
                    }, '*');
                }
            }
        });
        </script>
        """
        
        # Inject the click handler into the HTML
        graph_html_with_click = graph_html.replace('</body>', click_script + '</body>')
        
        # Display the graph
        stc.html(graph_html_with_click, height=800, scrolling=True)
        
        # Additional overview statistics
        # st.subheader("Quick Stats")
        df = pd.DataFrame.from_dict(owners, orient='index', columns=['Frequency'])
        df.reset_index(names='Owner', inplace=True)
        st.bar_chart(df, x='Owner', y='Frequency')

def explore_page():
    st.title("Explore Tools")
    # Placeholder for more detailed exploration features

def custom_query_page():
    st.title("Custom Cypher Query")
    # Placeholder for custom query interface
    

# Declare and initialize session state variables
def initialize_session_state():
    # Define all state variables with default values
    default_states = {
        'selected_node': None,
        'current_page': 'overview',
        'graph_layout': 'force-directed',
        'node_details': {},
        'search_query': '',
        'filter_categories': []
    }
    
    state_var_names = ['selected_node', 'current_page', 'graph_layout', 'node_details', 'search_query', 'filter_categories']

    # Initialize only if not already present
    for key in state_var_names:
        if key not in st.session_state:
            st.session_state[key] = default_states[key]
            

# Main App
def main():
    # Streamlit page configuration
    st.set_page_config(page_title="Tool Ecosystem", layout="wide")
    
    # Initialize all state variables at the start
    if 'selected_node' not in st.session_state:
        initialize_session_state()
    
    # Page selection
    page = st.sidebar.selectbox("Navigate", 
        ["Overview", "Explore", "Custom Query"]
    )
    
    if page == "Overview":
        overview_page()
    elif page == "Explore":
        explore_page()
    else:
        custom_query_page()

if __name__ == "__main__":
    main()