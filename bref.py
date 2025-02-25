import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from bs4 import BeautifulSoup
import re
import matplotlib.pyplot as plt
import seaborn as sns
import unicodedata

# Define the function to get NBA teams
def get_nba_teams():
    """Retrieve current NBA teams from Basketball-Reference"""
    url = "https://www.basketball-reference.com/leagues/NBA_2025.html"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    teams = []
    # Find all team links in the standings tables
    team_links = soup.select('table a[href*="/teams/"]')
    
    for link in team_links:
        team_name = link.text
        team_abbr = link['href'].split('/')[2]
        if [team_name, team_abbr] not in teams:
            teams.append([team_name, team_abbr])
    
    # Remove duplicates and return as DataFrame
    teams_df = pd.DataFrame(teams, columns=['Team', 'Abbreviation']).drop_duplicates()
    return teams_df

st.set_page_config(
    page_title="Basketball Analyzer",
    page_icon="🏀",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .subheader {
        font-size: 1.5rem;
        color: #424242;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .stat-card {
        background-color: #f8f9fa;
        border-radius: 5px;
        padding: 1rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .highlight-value {
        font-size: 1.2rem;
        font-weight: bold;
        color: #1E88E5;
    }
    .player-card {
        display: flex;
        align-items: center;
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1.5rem;
    }
    .player-image {
        width: 120px;
        height: 120px;
        border-radius: 60px;
        object-fit: cover;
        margin-right: 1.5rem;
        border: 3px solid #1E88E5;
    }
    .player-info {
        flex: 1;
    }
    .player-name {
        font-size: 1.8rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
        color: #1E88E5;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">Basketball Analyzer</h1>', unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'current_view' not in st.session_state:
    st.session_state.current_view = 'team_selection'
if 'selected_team_url' not in st.session_state:
    st.session_state.selected_team_url = None
if 'selected_player_url' not in st.session_state:
    st.session_state.selected_player_url = None
if 'hide_sidebar' not in st.session_state:
    st.session_state.hide_sidebar = False

# Sidebar for team selection
with st.sidebar:
    st.markdown("### 🏀 Team Selection")
    
    try:
        teams_df = get_nba_teams()
        selected_team = st.selectbox("Select NBA Team:", teams_df['Team'].tolist())
        team_abbr = teams_df[teams_df['Team'] == selected_team]['Abbreviation'].values[0]
        team_url = f"https://www.basketball-reference.com/teams/{team_abbr}/2025.html"
        
        if st.button("View Team"):
            st.session_state.current_view = 'team_roster'
            st.session_state.selected_team_url = team_url
            st.rerun()
            
        # Hide sidebar option
        if st.button("Hide Sidebar"):
            st.session_state.hide_sidebar = True
            st.rerun()
    except Exception as e:
        st.error(f"Error loading teams: {e}")

# Hide sidebar if button was clicked
if st.session_state.hide_sidebar:
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"][aria-expanded="true"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Add button to show sidebar again
    if st.button("Show Sidebar"):
        st.session_state.hide_sidebar = False
        st.rerun()

# Main content area - handle different views
if st.session_state.current_view == 'team_selection':
    st.info("Please select a team from the sidebar to view their roster.")

elif st.session_state.current_view == 'team_roster':
    # Display team roster
    try:
        url = st.session_state.selected_team_url
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Improved team name extraction with multiple fallback options
            team_name = "NBA Team"  # Default fallback
            
            # Try different selectors to find team name
            selectors = [
                'h1[itemprop="name"] span',
                'h1[data-testid="entity-name"]',
                'h1.teamname',
                'h1',
                'div#meta div h1'
            ]
            
            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    # Clean up the text to get just the team name
                    full_text = element.text.strip()
                    # Remove year information if present
                    team_name = re.sub(r'\s+\d{4}-\d{2,4}.*$', '', full_text)
                    break
            
            # If still not found, try to extract from title
            if team_name == "NBA Team" and soup.title:
                title_text = soup.title.text
                # Extract team name from title (usually in format "Team Name Roster...")
                title_match = re.search(r'^(.*?)\s+Roster', title_text)
                if title_match:
                    team_name = title_match.group(1).strip()
            
            st.markdown(f"## {team_name} Roster")
            
            # Extract roster table
            tables = pd.read_html(response.text)
            roster_table = None
            
            # Find the roster table (usually has 'Player' column)
            for table in tables:
                if 'Player' in table.columns:
                    roster_table = table
                    break
            
            if roster_table is not None:
                # Add player URLs to the roster table
                player_links = {}
                for link in soup.select('table#roster a[href*="/players/"]'):
                    # Get player name directly from the HTML
                    player_name = link.text
                    player_url = "https://www.basketball-reference.com" + link['href']
                    player_links[player_name] = player_url
                
                # Create a new column for player URLs
                if player_links and 'Player' in roster_table.columns:
                    # Create a mapping function that tries different ways to match names
                    def find_player_url(player_name):
                        # Try direct match
                        if player_name in player_links:
                            return player_links[player_name]
                        
                        # Try normalized version (remove accents, etc.)
                        normalized_player_name = unicodedata.normalize('NFKD', player_name).encode('ASCII', 'ignore').decode('ASCII')
                        
                        # Find closest match
                        for name in player_links:
                            normalized_name = unicodedata.normalize('NFKD', name).encode('ASCII', 'ignore').decode('ASCII')
                            if normalized_name == normalized_player_name:
                                return player_links[name]
                        
                        return "N/A"
                    
                    # Apply the mapping function
                    roster_table['Profile URL'] = roster_table['Player'].apply(find_player_url)
                
                # Display roster with URLs
                st.dataframe(roster_table, use_container_width=True)
                
                # Allow selecting a player from roster
                st.subheader("Select Player for Game Log")
                
                # Use the already extracted player links
                if player_links:
                    selected_player = st.selectbox("Select Player:", list(player_links.keys()))
                    player_url = player_links[selected_player]
                    
                    # Add year selection for game logs
                    current_year = 2025  # Default to current season
                    available_years = list(range(current_year, current_year-10, -1))  # Last 10 years
                    selected_year = st.selectbox("Select Season:", available_years)
                    
                    if st.button("View Player Game Log"):
                        # Modify URL to point to game log with selected year
                        gamelog_url = player_url.replace(".html", f"/gamelog/{selected_year}")
                        st.session_state.selected_player_url = gamelog_url
                        st.session_state.current_view = 'player_gamelog'
                        st.rerun()
            else:
                st.error("Could not find roster table on the team page.")
        else:
            st.error(f"Failed to retrieve team data. HTTP Status Code: {response.status_code}")
    except Exception as e:
        st.error(f"An error occurred loading team roster: {e}")

elif st.session_state.current_view == 'player_gamelog':
    # Display player game log
    try:
        url = st.session_state.selected_player_url
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            # Parse the HTML content to create the soup object
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract player ID from URL for headshot image
            player_id = None
            if "/players/" in url:
                url_parts = url.split("/players/")
                if len(url_parts) > 1:
                    player_path = url_parts[1].split("/")
                    if len(player_path) > 1:
                        player_id = player_path[1]
            
            # Add "Back to Team Roster" button
            if st.button("← Back to Team Roster"):
                st.session_state.current_view = 'team_roster'
                st.rerun()
            
            # Extract current season from URL
            current_season = "2025"  # Default
            if "/gamelog/" in url:
                url_parts = url.split("/gamelog/")
                if len(url_parts) > 1 and url_parts[1].isdigit():
                    current_season = url_parts[1]
            
            # Season selector
            available_seasons = list(range(int(current_season), int(current_season)-10, -1))  # Last 10 years
            selected_season = st.selectbox("Select Season:", available_seasons, 
                                          index=available_seasons.index(int(current_season)) if int(current_season) in available_seasons else 0)
            
            # Change season button
            if selected_season != int(current_season):
                if st.button(f"View {selected_season} Season"):
                    # Create new URL with selected season
                    base_url = url.split("/gamelog/")[0] if "/gamelog/" in url else url.split("/")[:-1]
                    if isinstance(base_url, list):
                        base_url = "/".join(base_url)
                    new_url = f"{base_url}/gamelog/{selected_season}"
                    st.session_state.selected_player_url = new_url
                    st.rerun()
            
            # Load tables
            tables = pd.read_html(response.text)
            
            # Game log table (usually table 7)
            game_log = tables[7]
            
            # Remove unnamed columns and drop specific ones if they exist
            game_log = game_log.loc[:, ~game_log.columns.str.contains('Unnamed:', case=False)]
            columns_to_exclude = ['GmSc', '+/-', 'Date', 'Tm', 'Age']
            game_log = game_log.drop(columns=columns_to_exclude, errors='ignore')
            
            # Identify and drop columns that contain the string "none" (case-insensitive)
            columns_with_none = [
                col for col in game_log.columns 
                if game_log[col].astype(str).str.lower().eq('None').any()
            ]
            if columns_with_none:
                game_log = game_log.drop(columns=columns_with_none)
            
            # Convert columns to numeric if possible, but skip columns 'MP' and 'Opp'
            for col in game_log.columns:
                if col in ["MP", "Opp"]:
                    continue  # Do not convert these columns
                # Clean values: remove commas and percentage signs
                cleaned = game_log[col].astype(str).str.replace(',', '', regex=False).str.replace('%', '', regex=False)
                # Convert to numeric; non-convertible values will become NaN
                game_log[col] = pd.to_numeric(cleaned, errors='coerce')
            
            # Add opponent filter in sidebar
            with st.sidebar:
                if 'Opp' in game_log.columns:
                    opponents = ['All'] + sorted(game_log['Opp'].unique().tolist())
                    selected_opponent = st.selectbox("Select Opponent:", opponents)
            
            # Apply opponent filter if selected
            filtered_game_log = game_log
            if 'Opp' in game_log.columns and selected_opponent != 'All':
                filtered_game_log = game_log[game_log['Opp'] == selected_opponent]
            
            # Display player card with headshot if player_id is available
            if player_id:
                image_url = f"https://www.basketball-reference.com/req/202106291/images/headshots/{player_id}.jpg"
                
                # Try to get player name from the HTML content
                player_name = "Player"
                try:
                    # Try multiple selectors to find player name
                    player_name_element = soup.select_one('h1[itemprop="name"] span')
                    if player_name_element:
                        player_name = player_name_element.text
                    else:
                        # Alternative selector for player name
                        player_name_element = soup.select_one('h1')
                        if player_name_element:
                            # Clean up the text to get just the player name
                            full_text = player_name_element.text.strip()
                            # Remove "Game Log" and year information if present
                            player_name = re.sub(r'\s+Game Log.*$', '', full_text)
                        else:
                            # Try to extract from breadcrumbs
                            breadcrumb = soup.select_one('div.breadcrumbs')
                            if breadcrumb and breadcrumb.find_all('a'):
                                # Usually the last breadcrumb link is the player name
                                player_links = breadcrumb.find_all('a')
                                if len(player_links) > 0:
                                    player_name = player_links[-1].text
                except Exception as e:
                    st.warning(f"Could not extract player name: {e}")
                    # Fallback to extracting from URL if HTML parsing fails
                    if player_id:
                        # Convert player_id format (like "jamesle01") to a readable name
                        name_parts = re.findall(r'([a-z]+)([0-9]+)', player_id)
                        if name_parts:
                            player_name = name_parts[0][0].capitalize()
                
                if "gamelog" in url:
                    season = url.split("/")[-1] if url.split("/")[-1].isdigit() else "Current Season"
                else:
                    season = "Current Season"
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.image(image_url, width=150)
                with col2:
                    st.markdown(f"### {player_name}")
                    st.markdown(f"**Season**: {season}")
                    if 'Opp' in game_log.columns and selected_opponent != 'All':
                        st.markdown(f"**Filtered by opponent**: {selected_opponent}")
                    
                    # Show key stats summary
                    if 'PTS' in filtered_game_log.columns:
                        avg_pts = filtered_game_log['PTS'].mean()
                        st.markdown(f"**Avg Points**: {avg_pts:.1f}")
                    
                    if 'AST' in filtered_game_log.columns and 'TRB' in filtered_game_log.columns:
                        avg_ast = filtered_game_log['AST'].mean()
                        avg_trb = filtered_game_log['TRB'].mean()
                        st.markdown(f"**Avg Assists**: {avg_ast:.1f} | **Avg Rebounds**: {avg_trb:.1f}")
            
            tab1, tab2, tab3 = st.tabs(["Game Log", "Analysis", "Visualization"])

            with tab1:
                st.subheader("Game Log Data")
                st.dataframe(filtered_game_log, use_container_width=True)

            with tab2:
                st.markdown('<h2 class="subheader">Analysis Section</h2>', unsafe_allow_html=True)
                
                # Create two columns for better layout
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    # Provide a multi-select widget to choose headers (columns) to exclude from final display
                    all_columns = filtered_game_log.columns.tolist()
                    exclude_columns = st.multiselect("Select columns to exclude:", all_columns, key="exclude_columns")
                
                with col2:
                    # Dropdown for statistical analysis on numeric columns
                    numeric_columns = filtered_game_log.select_dtypes(include=['float64', 'int64']).columns
                    stat_column = st.selectbox("Select a column for statistical analysis:", numeric_columns, key="stat_column")
                
                # Remove the selected columns from the DataFrame
                modified_game_log = filtered_game_log.drop(columns=exclude_columns) if exclude_columns else filtered_game_log
                
                # Calculate and display statistics for the chosen column
                if stat_column:
                    try:
                        stats = modified_game_log[stat_column].describe()
                        st.subheader(f"Statistical Analysis for {stat_column}")
                        st.text(f"Average: {stats['mean']:.2f}")
                        st.text(f"Minimum: {stats['min']:.2f}")
                        st.text(f"Maximum: {stats['max']:.2f}")
                        st.text(f"Standard Deviation: {stats['std']:.2f}")

                        # Allow the user to enter a threshold value
                        threshold = st.number_input("Enter threshold value", value=20.5, step=0.5)
                        count_over = (modified_game_log[stat_column] > threshold).sum()
                        count_under = (modified_game_log[stat_column] < threshold).sum()
                        total_matches = count_over + count_under
                        
                        # Calculate percentages
                        pct_over = (count_over / total_matches * 100) if total_matches > 0 else 0
                        pct_under = (count_under / total_matches * 100) if total_matches > 0 else 0
                        
                        st.subheader("Stats Comparison")
                        st.write(f"Number of matches with {stat_column} over {threshold}: {count_over} ({pct_over:.1f}%)")
                        st.write(f"Number of matches with {stat_column} under {threshold}: {count_under} ({pct_under:.1f}%)")
                    
                    except Exception as e:
                        st.error(f"Could not calculate statistics for {stat_column}: {e}")

                with tab3:
                    st.subheader("Visualization Section")
                    # Line chart for selected stat over time
                    if stat_column:
                        fig = px.line(modified_game_log, x=modified_game_log.index, y=stat_column, 
                                     title=f"{stat_column} Over Time")
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True, key=f"line_chart_viz_{stat_column}")

                    # Bar chart comparing multiple stats
                    stats_to_compare = st.multiselect(
                        "Select stats to compare:", 
                        numeric_columns,
                        default=['PTS', 'AST', 'TRB'] if all(stat in numeric_columns for stat in ['PTS', 'AST', 'TRB']) else [],
                        key="stats_to_compare_viz"
                    )
                    
                    if stats_to_compare:
                        avg_stats = modified_game_log[stats_to_compare].mean()
                        fig = px.bar(avg_stats, title="Average Stats Comparison")
                        st.plotly_chart(fig, use_container_width=True, key="bar_chart_viz")
        else:
            st.error(f"Failed to retrieve player data. HTTP Status Code: {response.status_code}")
    except Exception as e:
        st.error(f"An error occurred loading player game log: {e}")
