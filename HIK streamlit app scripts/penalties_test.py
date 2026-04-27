import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

# -----------------------------------
# LOAD DATA FROM GITHUB
# -----------------------------------
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/Vangelis19/DBU-Divisionen/main/Penalties_App/Penalty_project_HIK.csv"
    df = pd.read_csv(url, sep=",", encoding="utf-8")

    # CLEAN COLUMN NAMES
    df.columns = df.columns.str.strip()        # remove spaces
    df.columns = df.columns.str.upper()        # make all uppercase
    return df

df = load_data()
st.write(df.columns.tolist())

# -----------------------------------
# CLEAN DATA
# -----------------------------------
df["PLAYER"] = df["FIRSTNAME"] + " " + df["LASTNAME"]
df["GK"] = df["GK_FIRSTNAME"] + " " + df["GK_LASTNAME"]

# Standardize goal outcome
df["IS_GOAL"] = df["SHOTISGOAL"].astype(bool)

# Identify misses (post hits)
post_values = ["pl", "pr", "pt", "pbr", "plb", "ptl", "ptr"]
df["IS_MISS"] = df["SHOTGOALZONE"].isin(post_values)

# -----------------------------------
# SIDEBAR NAVIGATION
# -----------------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Penalty Takers", "Goalkeepers"])

# -----------------------------------
# HOME
# -----------------------------------
if page == "Home":
    st.title("⚽ Penalty Analysis Platform")
    st.write("Use the menu to explore penalty data.")

# -----------------------------------
# PENALTY TAKERS
# -----------------------------------
elif page == "Penalty Takers":

    st.title("⚽ Penalty Takers")

    teams = df["TEAMNAME"].dropna().unique()
    selected_team = st.selectbox("Select Team", teams)

    team_df = df[df["TEAMNAME"] == selected_team]

    # Player stats
    player_stats = team_df.groupby("PLAYER").agg(
        penalties_taken=("IS_GOAL", "count"),
        scored=("IS_GOAL", "sum")
    ).reset_index()

    player_stats["conversion_rate"] = (
        player_stats["scored"] / player_stats["penalties_taken"]
    ).round(2)

    st.dataframe(player_stats)

    selected_player = st.selectbox("Select Player", player_stats["PLAYER"])

    player_df = team_df[team_df["PLAYER"] == selected_player]

    st.header(selected_player)

    # FOOT FILTER
    foot = st.selectbox(
        "Select Foot",
        player_df["SHOTBODYPART"].dropna().unique()
    )

    foot_df = player_df[player_df["SHOTBODYPART"] == foot]

    # ZONE STATS
    zone_stats = foot_df.groupby("SHOTGOALZONE").agg(
        shots=("IS_GOAL", "count"),
        goals=("IS_GOAL", "sum")
    ).reset_index()

    zone_stats["conversion_rate"] = (
        zone_stats["goals"] / zone_stats["shots"]
    ).round(2)

    st.subheader("Zone Stats")
    st.dataframe(zone_stats)

# -----------------------------------
# GOALKEEPERS
# -----------------------------------
elif page == "Goalkeepers":

    st.title("🧤 Goalkeepers")

    teams = df["GK_TEAMNAME"].dropna().unique()
    selected_team = st.selectbox("Select Team", teams)

    team_df = df[df["GK_TEAMNAME"] == selected_team]

    # GK stats
    gk_stats = team_df.groupby("GK").agg(
        faced=("IS_GOAL", "count"),
        conceded=("IS_GOAL", "sum")
    ).reset_index()

    gk_stats["saved"] = gk_stats["faced"] - gk_stats["conceded"]
    gk_stats["save_rate"] = (
        gk_stats["saved"] / gk_stats["faced"]
    ).round(2)

    st.dataframe(gk_stats)

    selected_gk = st.selectbox("Select Goalkeeper", gk_stats["GK"])

    gk_df = team_df[team_df["GK"] == selected_gk]

    # ZONE STATS
    zone_stats = gk_df.groupby("SHOTGOALZONE").agg(
        shots=("IS_GOAL", "count"),
        goals=("IS_GOAL", "sum")
    ).reset_index()

    zone_stats["saved"] = zone_stats["shots"] - zone_stats["goals"]
    zone_stats["save_rate"] = (
        zone_stats["saved"] / zone_stats["shots"]
    ).round(2)

    st.subheader("Zone Performance")
    st.dataframe(zone_stats)