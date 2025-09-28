import streamlit as st
import pandas as pd
import requests
import base64
import plotly.graph_objects as go

# Cache helper functions
@st.cache_data
def get_base64_of_bin_file(bin_file):
    response = requests.get(bin_file)
    data = response.content
    return base64.b64encode(data).decode()

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

# Fetch CSV from GitHub API or raw link
@st.cache_data
def load_csv_from_github(url):
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Could not load {url}. Error: {e}")
        return None

# Fetch all available files in a folder using GitHub API
@st.cache_data
def get_available_files(team_choice):
    api_url = f"https://api.github.com/repos/Vangelis19/DBU-Divisionen/contents/25_26/Matchdays/{team_choice}"
    response = requests.get(api_url)
    if response.status_code == 200:
        files = response.json()
        csv_files = [f["name"] for f in files if f["name"].endswith(".csv") and f["name"].startswith("#")]
        return csv_files
    else:
        st.error(f"Could not access GitHub API for {team_choice}. Error code: {response.status_code}")
        return []

# Page 1: Match Analysis Stats
def match_analysis_page():
    st.subheader("Match Analysis Stats")

    team_choice = st.selectbox("Select Team", ["U17", "U19"])
    round_options = list(range(1, 31)) + ["All rounds"]
    round_choice = st.selectbox("Select Round", round_options)

    base_url = f"https://raw.githubusercontent.com/Vangelis19/DBU-Divisionen/main/25_26/Matchdays/{team_choice}"
    dfs = []

    if round_choice == "All rounds":
        available_files = get_available_files(team_choice)
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

    def compute_sequence_time(df, sequence_type):
        seq_df = df[df["code"] == sequence_type].copy()
        seq_df["DURATION"] = seq_df["end"] - seq_df["start"]
        return seq_df.groupby("ROUND")["DURATION"].sum()

    active_times = compute_sequence_time(combined_df, "Active")
    dead_times = compute_sequence_time(combined_df, "Dead")

    if round_choice == "All rounds":
        n_files = len(get_available_files(team_choice))
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
        title="Total Active vs Dead Sequence Time per Round (minutes)",
        xaxis_title="Round",
        yaxis_title="Time (minutes)",
        barmode="group",
        template="plotly_white"
    )
    st.plotly_chart(fig1)

    total_times = active_times.add(dead_times, fill_value=0)
    active_pct = [100 * active_times.get(r, 0)/total_times.get(r, 1) for r in rounds]
    dead_pct = [100 * dead_times.get(r, 0)/total_times.get(r, 1) for r in rounds]

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=rounds,
        y=active_pct,
        name="Active",
        marker_color="green",
        text=[f"{round(p,1)}%" for p in active_pct],
        textposition='inside'
    ))
    fig2.add_trace(go.Bar(
        x=rounds,
        y=dead_pct,
        name="Dead",
        marker_color="lightcoral",
        text=[f"{round(p,1)}%" for p in dead_pct],
        textposition='inside'
    ))
    fig2.update_layout(
        title="Percentage of Active vs Dead Sequence Time per Round",
        xaxis_title="Round",
        yaxis_title="Percentage (%)",
        barmode="stack",
        template="plotly_white"
    )
    st.plotly_chart(fig2)

    def active_time_distribution(df):
        sequence_codes = [
            "Build Up", "Breakthrough", "Afslutningsspillet", "Off Transition",
            "Defend the box", "Low", "Medium", "High", "Def Transition"
        ]
        active_df = df[df["code"].isin(sequence_codes)].copy()
        active_df["DURATION"] = active_df["end"] - active_df["start"]
        distribution = active_df.groupby("code")["DURATION"].sum() / 60
        fig = go.Figure(go.Pie(labels=distribution.index, values=distribution.values))
        fig.update_layout(title="Active Time Distribution (minutes)", template="plotly_white")
        st.plotly_chart(fig)

    active_time_distribution(combined_df)

    def on_off_total_time(df):
        on_ball_codes = ["Build Up", "Breakthrough", "Afslutningsspillet"]
        off_ball_codes = ["Defend the box", "Low", "Medium", "High", "Def Transition"]
        df["DURATION"] = df["end"] - df["start"]
        on_ball_time = df[df["code"].isin(on_ball_codes)]["DURATION"].sum() / 60
        off_ball_time = df[df["code"].isin(off_ball_codes)]["DURATION"].sum() / 60
        fig = go.Figure(go.Pie(labels=["On the Ball", "Off the Ball"], values=[on_ball_time, off_ball_time]))
        fig.update_layout(title="On vs Off the Ball Total Time (minutes)", template="plotly_white")
        st.plotly_chart(fig)

    on_off_total_time(combined_df)

    def on_ball_distribution(df):
        on_ball_codes = ["Build Up", "Breakthrough", "Afslutningsspillet"]
        df["DURATION"] = df["end"] - df["start"]
        on_df = df[df["code"].isin(on_ball_codes)].copy()
        distribution = on_df.groupby("code")["DURATION"].sum() / 60
        fig = go.Figure(go.Pie(labels=distribution.index, values=distribution.values))
        fig.update_layout(title="On the Ball Time Distribution (minutes)", template="plotly_white")
        st.plotly_chart(fig)

    on_ball_distribution(combined_df)

    def off_ball_distribution(df):
        off_ball_codes = ["Defend the box", "Low", "Medium", "High", "Def Transition"]
        df["DURATION"] = df["end"] - df["start"]
        off_df = df[df["code"].isin(off_ball_codes)].copy()
        distribution = off_df.groupby("code")["DURATION"].sum() / 60
        fig = go.Figure(go.Pie(labels=distribution.index, values=distribution.values))
        fig.update_layout(title="Off the Ball Time Distribution (minutes)", template="plotly_white")
        st.plotly_chart(fig)

    off_ball_distribution(combined_df)

# Page 2: Training Analysis Stats
def training_analysis_page():
    st.subheader("Training Analysis Stats")

    team_choice = st.selectbox("Select Team", ["U17", "U19"])
    base_url = f"https://raw.githubusercontent.com/Vangelis19/DBU-Divisionen/main/25_26/Training_Sessions/{team_choice}"

    available_files = get_available_files_training(team_choice)
    if not available_files:
        st.warning("No training session CSV files found.")
        return

    file_choice = st.selectbox("Select Training File", available_files)
    file_url = f"{base_url}/{file_choice.replace(' ', '%20')}"
    df = load_csv_from_github(file_url)
    if df is None:
        return

    st.dataframe(df)

    training_visualizations(df)

@st.cache_data
def get_available_files_training(team_choice):
    api_url = f"https://api.github.com/repos/Vangelis19/DBU-Divisionen/contents/25_26/Training_Sessions/{team_choice}"
    response = requests.get(api_url)
    if response.status_code == 200:
        files = response.json()
        csv_files = [f["name"] for f in files if f["name"].endswith(".csv")]
        return csv_files
    else:
        return []

def training_visualizations(df):
    blocks = ["Warm Up (S)", "Block 1 (S)", "Block 2 (S)", "Block 3 (S)", "Block 4 (S)", "Block 5 (S)", "Individual (S)"]
    durations_minutes = {}
    for block in blocks:
        block_df = df[df["code"] == block].copy()
        block_df["duration_sec"] = block_df["end"] - block_df["start"]
        durations_minutes[block] = block_df["duration_sec"].sum() / 60

    fig_pie = go.Figure(go.Pie(labels=list(durations_minutes.keys()), values=list(durations_minutes.values())))
    fig_pie.update_layout(title="Training Time Distribution by Block (minutes)", template="plotly_white")
    st.plotly_chart(fig_pie)

    total_blocks_time = sum(durations_minutes.values())
    session_df = df[df["code"] == "Session (S)"].copy()
    session_df["duration_sec"] = session_df["end"] - session_df["start"]
    session_time = session_df["duration_sec"].sum() / 60

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(x=["Blocks Total"], y=[total_blocks_time], text=[f"{round(total_blocks_time,1)} min"], textposition="auto"))
    fig_bar.add_trace(go.Bar(x=["Session (S)"], y=[session_time], text=[f"{round(session_time,1)} min"], textposition="auto"))
    fig_bar.update_layout(title="Total Blocks Time vs Session Time (minutes)", template="plotly_white")
    st.plotly_chart(fig_bar)

    categories = ["Organization", "Coaching", "Active"]
    category_minutes = {}
    for cat in categories:
        cat_df = df[df["code"] == cat].copy()
        cat_df["duration_sec"] = cat_df["end"] - cat_df["start"]
        category_minutes[cat] = cat_df["duration_sec"].sum() / 60

    fig_cat = go.Figure(go.Bar(
        x=list(category_minutes.keys()),
        y=list(category_minutes.values()),
        text=[f"{round(v,1)} min" for v in category_minutes.values()],
        textposition="auto",
        marker_color=["orange", "blue", "green"]
    ))
    fig_cat.update_layout(title="Organization vs Coaching vs Active Time (minutes)", yaxis_title="Minutes", template="plotly_white")
    st.plotly_chart(fig_cat)

    # Grouped bar chart
    categories = ["Organization", "Coaching", "Active"]
    data_by_block = {cat: [] for cat in categories}
    for block in blocks:
        for cat in categories:
            block_cat_df = df[(df["parent"] == block) & (df["code"] == cat)].copy()
            block_cat_df["duration_sec"] = block_cat_df["end"] - block_cat_df["start"]
            data_by_block[cat].append(block_cat_df["duration_sec"].sum() / 60)

    fig_grouped = go.Figure()
    for cat in categories:
        fig_grouped.add_trace(go.Bar(x=blocks, y=data_by_block[cat], name=cat))
    fig_grouped.update_layout(
        title="Organization, Coaching, and Active Time per Block (minutes)",
        yaxis_title="Minutes",
        barmode="group",
        template="plotly_white"
    )
    st.plotly_chart(fig_grouped)    # --- Grouped Bar Chart: Organization, Coaching, Active by Block ---
    blocks = [
        "Warm Up (S)", "Block 1 (S)", "Block 2 (S)",
        "Block 3 (S)", "Block 4 (S)", "Block 5 (S)",
        "Individual (S)"
    ]
    categories = ["Organization", "Coaching", "Active"]

    data_by_block = {cat: [] for cat in categories}

    for block in blocks:
        for cat in categories:
            block_cat_df = df[df["code"].str.contains(block) & df["code"].str.contains(cat)].copy()
            if not block_cat_df.empty:
                block_cat_df["duration_sec"] = block_cat_df["end"] - block_cat_df["start"]
                data_by_block[cat].append(block_cat_df["duration_sec"].sum() / 60)
            else:
                data_by_block[cat].append(0)

    fig_grouped = go.Figure()
    for cat in categories:
        fig_grouped.add_trace(go.Bar(x=blocks, y=data_by_block[cat], name=cat))

    fig_grouped.update_layout(
        title="Organization, Coaching, and Active Time per Block (minutes)",
        yaxis_title="Minutes",
        barmode="group",
        template="plotly_white"
    )
    st.plotly_chart(fig_grouped)


# Page 3: Player Data Explorer
def player_data_page():
    st.subheader("Player Data Explorer")
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

# Main App
def main():
    st.title("Automated Report")
    set_png_as_page_bg("https://www.hik.dk/media/4216/korrekt-farve-logo-hik-maj-2025.png")
    page = st.sidebar.selectbox("Select a page", ("Match Analysis Stats", "Training Analysis Stats", "Player Data Explorer"))
    if page == "Match Analysis Stats":
        match_analysis_page()
    elif page == "Training Analysis Stats":
        training_analysis_page()
    elif page == "Player Data Explorer":
        player_data_page()

if __name__ == "__main__":
    main()
