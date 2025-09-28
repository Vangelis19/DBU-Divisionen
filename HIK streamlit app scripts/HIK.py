import streamlit as st
import pandas as pd
import requests
import base64
import plotly.graph_objects as go

# ------------------------------
# Cache helper functions
# ------------------------------
@st.cache_data
def get_base64_of_bin_file(bin_file):
    response = requests.get(bin_file)
    data = response.content
    return base64.b64encode(data).decode()

@st.cache_data
def load_csv_from_github(url):
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Could not load {url}. Error: {e}")
        return None

# Background styling
def set_png_as_page_bg(png_file):
    bin_str = get_base64_of_bin_file(png_file)
    page_bg_img = f'''
    <style>
    .stApp {{
        background: linear-gradient(rgba(255,255,255,0.8), rgba(255,255,255,0.8)), 
                    url("data:image/png;base64,{bin_str}") no-repeat center center fixed;
        background-size: contain;
    }}
    </style>
    '''
    st.markdown(page_bg_img, unsafe_allow_html=True)

# Fetch available files from GitHub folder
@st.cache_data
def get_available_files_from_github(folder_url):
    response = requests.get(folder_url)
    if response.status_code == 200:
        files = response.json()
        csv_files = [f["name"] for f in files if f["name"].endswith(".csv")]
        return csv_files
    else:
        st.error(f"Could not access GitHub folder. Error code: {response.status_code}")
        return []

# ------------------------------
# Page 1: Match Analysis Stats
# ------------------------------
def match_analysis_page():
    st.subheader("📊 Match Analysis Stats")

    team_choice = st.selectbox("Select Team", ["U17", "U19"])
    round_options = list(range(1, 31)) + ["All rounds"]
    round_choice = st.selectbox("Select Round", round_options)

    base_url = f"https://raw.githubusercontent.com/Vangelis19/DBU-Divisionen/main/25_26/Matchdays/{team_choice}"

    dfs = []
    if round_choice == "All rounds":
        available_files = get_available_files_from_github(
            f"https://api.github.com/repos/Vangelis19/DBU-Divisionen/contents/25_26/Matchdays/{team_choice}"
        )
        if not available_files:
            st.warning("No CSV files found in the GitHub repo for this team.")
            return

        for file in available_files:
            file_url = f"{base_url}/{file.replace('#','%23')}"
            df = load_csv_from_github(file_url)
            if df is not None:
                df["ROUND"] = int(file.strip(".csv").replace("#",""))
                dfs.append(df)
        
        if dfs:
            combined_df = pd.concat(dfs, ignore_index=True)
            st.dataframe(combined_df)
        else:
            st.warning("No valid CSV files could be loaded.")
            return
    else:
        csv_url = f"{base_url}/%23{round_choice}.csv"
        df = load_csv_from_github(csv_url)
        if df is not None:
            df["ROUND"] = round_choice
            combined_df = df
            st.dataframe(combined_df)
        else:
            return

    # --- Visualization 1: Total Active vs Dead Time ---
    def compute_sequence_time(df, sequence_type):
        seq_df = df[df["code"] == sequence_type].copy()
        seq_df["DURATION"] = seq_df["end"] - seq_df["start"]
        return seq_df.groupby("ROUND")["DURATION"].sum()

    active_times = compute_sequence_time(combined_df, "Active")
    dead_times = compute_sequence_time(combined_df, "Dead")

    if round_choice == "All rounds":
        n_files = len(get_available_files_from_github(
            f"https://api.github.com/repos/Vangelis19/DBU-Divisionen/contents/25_26/Matchdays/{team_choice}"
        ))
        active_times = active_times / n_files
        dead_times = dead_times / n_files

    rounds = sorted(combined_df["ROUND"].unique())

    fig1 = go.Figure()
    fig1.add_trace(go.Bar(
        x=rounds,
        y=[active_times.get(r, 0)/60 for r in rounds],
        name="Active",
        marker_color="green",
        text=[f"{round(active_times.get(r, 0)/60, 1)} min" for r in rounds],
        textposition='auto'
    ))
    fig1.add_trace(go.Bar(
        x=rounds,
        y=[dead_times.get(r, 0)/60 for r in rounds],
        name="Dead",
        marker_color="lightcoral",
        text=[f"{round(dead_times.get(r, 0)/60, 1)} min" for r in rounds],
        textposition='auto'
    ))

    fig1.update_layout(
        title="⏱️ Total Active vs Dead Sequence Time per Round (minutes)",
        xaxis_title="Round",
        yaxis_title="Time (minutes)",
        barmode="group",
        template="plotly_white"
    )
    st.plotly_chart(fig1)

# ------------------------------
# Page 2: Training Analysis Stats
# ------------------------------
def training_analysis_page():
    st.subheader("📈 Training Analysis Stats")

    team = st.selectbox("Select a team", ["U17", "U19"])

    # List CSV files in the selected folder
    api_url = f"https://api.github.com/repos/Vangelis19/DBU-Divisionen/contents/25_26/Training_Sessions/{team}"
    csv_files = get_available_files_from_github(api_url)

    if not csv_files:
        st.warning("No CSV files found for this team.")
        return

    # File selection
    file_choice = st.selectbox("Select a file", csv_files)
    base_url = f"https://raw.githubusercontent.com/Vangelis19/DBU-Divisionen/main/25_26/Training_Sessions/{team}"
    csv_url = f"{base_url}/{file_choice.replace(' ', '%20')}"
    df = load_csv_from_github(csv_url)

    if df is not None:
        st.dataframe(df)
        training_visualizations(df)

# ------------------------------
# Training visualizations helper
# ------------------------------
def training_visualizations(df):
    st.subheader("⏱️ Block Durations (minutes)")
    blocks = ["Warm Up (S)", "Block 1 (S)", "Block 2 (S)", "Block 3 (S)", "Block 4 (S)", "Block 5 (S)", "Individual (S)"]

    durations_minutes = {}
    for block in blocks:
        block_df = df[df["code"] == block].copy()
        if not block_df.empty:
            block_df["duration_sec"] = block_df["end"] - block_df["start"]
            durations_minutes[block] = block_df["duration_sec"].sum() / 60
        else:
            durations_minutes[block] = 0

    session_df = df[df["code"] == "Session (S)"].copy()
    session_minutes = 0
    if not session_df.empty:
        session_df["duration_sec"] = session_df["end"] - session_df["start"]
        session_minutes = session_df["duration_sec"].sum() / 60

    # Pie chart
    fig_pie = go.Figure(data=[go.Pie(
        labels=list(durations_minutes.keys()),
        values=list(durations_minutes.values()),
        hole=.3
    )])
    fig_pie.update_layout(title="🥧 Distribution of Training Blocks (minutes)")

    # Bar chart total vs session
    fig_bar = go.Figure(data=[
        go.Bar(name="Sum of Blocks", x=["Total"], y=[sum(durations_minutes.values())]),
        go.Bar(name="Session", x=["Total"], y=[session_minutes])
    ])
    fig_bar.update_layout(title="📊 Total Training Time: Sum of Blocks vs Session", barmode="group")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_pie, use_container_width=True)
    with col2:
        st.plotly_chart(fig_bar, use_container_width=True)

    # Organization vs Coaching vs Active
    st.subheader("📊 Organization vs Coaching vs Active")
    categories = ["Organization", "Coaching", "Active"]
    category_minutes = {}
    for cat in categories:
        cat_df = df[df["code"] == cat].copy()
        if not cat_df.empty:
            cat_df["duration_sec"] = cat_df["end"] - cat_df["start"]
            category_minutes[cat] = cat_df["duration_sec"].sum() / 60
        else:
            category_minutes[cat] = 0

    fig_cat = go.Figure(go.Bar(
        x=list(category_minutes.keys()),
        y=list(category_minutes.values()),
        text=[f"{round(v,1)} min" for v in category_minutes.values()],
        textposition="auto",
        marker_color=["orange", "blue", "green"]
    ))
    fig_cat.update_layout(title="📊 Organization vs Coaching vs Active Time (minutes)", yaxis_title="Minutes", template="plotly_white")
    st.plotly_chart(fig_cat, use_container_width=True)

    # Grouped bar chart per block — FIXED
    st.subheader("📊 Organization, Coaching, and Active per Block")
    data_by_block = {cat: [] for cat in categories}

    for i, block in enumerate(blocks):
        # Find start index of this block
        block_indices = df.index[df["code"] == block].tolist()
        if not block_indices:
            for cat in categories:
                data_by_block[cat].append(0)
            continue

        start_idx = block_indices[0]
        # Determine end index (either next block or end of dataframe)
        if i + 1 < len(blocks):
            next_block_indices = df.index[df["code"] == blocks[i + 1]].tolist()
            end_idx = next_block_indices[0] if next_block_indices else len(df)
        else:
            end_idx = len(df)

        block_df = df.iloc[start_idx:end_idx].copy()
        block_df["duration_sec"] = block_df["end"] - block_df["start"]

        for cat in categories:
            cat_duration = block_df[block_df["code"] == cat]["duration_sec"].sum() / 60
            data_by_block[cat].append(cat_duration)

    fig_grouped = go.Figure()
    for cat in categories:
        fig_grouped.add_trace(go.Bar(
            x=blocks,
            y=data_by_block[cat],
            name=cat
        ))

    fig_grouped.update_layout(
        title="📊 Organization, Coaching, and Active Time per Block (minutes)",
        yaxis_title="Minutes",
        barmode="group",
        template="plotly_white"
    )
    st.plotly_chart(fig_grouped, use_container_width=True)

# ------------------------------
# Page 3: Player Data Explorer
# ------------------------------
def player_data_page():
    st.subheader("🧑‍💻 Player Data Explorer")

    csv_file = st.file_uploader("Upload a CSV file", type=["csv"])
    if csv_file is not None:
        df = pd.read_csv(csv_file)
        df["TEAM_FILTER"] = df["TEAMNAME"].str.replace("U17", "", regex=False).str.strip()
        team_options = ["ALL"] + sorted(df["TEAM_FILTER"].unique().tolist())
        team_choice = st.selectbox("Select Team", team_options)
        position_options = ["ALL"] + sorted(df["POSITION"].unique().tolist())
        position_choice = st.selectbox("Select Position", position_options)

        filtered_df = df.copy()
        if team_choice != "ALL":
            filtered_df = filtered_df[filtered_df["TEAM_FILTER"] == team_choice]
        if position_choice != "ALL":
            filtered_df = filtered_df[filtered_df["POSITION"] == position_choice]

        st.dataframe(filtered_df)

# ------------------------------
# Main App
# ------------------------------
def main():
    st.title("📑 Automated Report")
    set_png_as_page_bg("https://www.hik.dk/media/4216/korrekt-farve-logo-hik-maj-2025.png")

    page = st.sidebar.selectbox("Select a page", (
        "Match Analysis Stats",
        "Training Analysis Stats",
        "Player Data Explorer"
    ))

    if page == "Match Analysis Stats":
        match_analysis_page()
    elif page == "Training Analysis Stats":
        training_analysis_page()
    elif page == "Player Data Explorer":
        player_data_page()

if __name__ == "__main__":
    main()
