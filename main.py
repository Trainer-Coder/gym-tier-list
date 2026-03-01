import streamlit as st
import pandas as pd
import os

# Page Config (Wide layout for PC)
st.set_page_config(page_title="Gym Tier List", page_icon="💪", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .tier-card { padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; background-color: #262730; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 Iron Leaderboard")

# 1. Load Data Safely (Creates the file if it got deleted)
if not os.path.exists("gym_data.csv"):
    pd.DataFrame(columns=["Name", "Exercise", "Weight"]).to_csv("gym_data.csv", index=False)
df = pd.read_csv("gym_data.csv")

# Get a list of all exercises currently in the file
default_exercises = ["Bench Press", "Squat", "Deadlift"]
existing_exercises = df['Exercise'].dropna().unique().tolist()
all_exercises = list(set(default_exercises + existing_exercises))

# --- SIDEBAR: ADMIN SETTINGS ---
st.sidebar.header("⚙️ Admin Settings")

# Admin Tool: Delete a Record
st.sidebar.subheader("Remove a Lifter's Record")
if not df.empty and len(df[df['Name'] != 'Admin']) > 0:
    del_name = st.sidebar.selectbox("Select Name", df[df['Name'] != 'Admin']['Name'].unique())
    del_exercise = st.sidebar.selectbox("Select Exercise", df[df['Name'] == del_name]['Exercise'].unique())
    
    if st.sidebar.button("Delete This Record"):
        # Keep everything EXCEPT the row that matches the name and exercise
        df = df[~((df['Name'] == del_name) & (df['Exercise'] == del_exercise))]
        df.to_csv("gym_data.csv", index=False)
        st.sidebar.success(f"Deleted!")
        st.rerun()

st.sidebar.divider()

# Admin Tool: Add a Custom Exercise
st.sidebar.subheader("Add Custom Exercise")
new_exercise = st.sidebar.text_input("Type new exercise name")
if st.sidebar.button("Add to List") and new_exercise:
    if new_exercise not in all_exercises:
        # Adds a hidden dummy row so the exercise saves to the CSV
        new_row = pd.DataFrame({"Name": ["Admin"], "Exercise": [new_exercise], "Weight": [0]})
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv("gym_data.csv", index=False)
        st.sidebar.success(f"{new_exercise} added to dropdowns!")
        st.rerun()

# --- MAIN PAGE: LOG PR ---
with st.expander("➕ Log a New PR", expanded=True):
    with st.form("pr_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            user_name = st.text_input("Enter your name")
        with col2:
            exercise = st.selectbox("Select Lift", all_exercises)
        with col3:
            weight = st.number_input("Max Weight (lbs)", min_value=0.0, step=5.0)
        
        if st.form_submit_button("Update Leaderboard"):
            if user_name:
                mask = (df['Name'] == user_name) & (df['Exercise'] == exercise)
                if mask.any():
                    df.loc[mask, 'Weight'] = weight
                else:
                    new_row = pd.DataFrame({"Name": [user_name], "Exercise": [exercise], "Weight": [weight]})
                    df = pd.concat([df, new_row], ignore_index=True)
                
                df.to_csv("gym_data.csv", index=False)
                st.success(f"Boom! {user_name} updated to {weight} lbs.")
                st.rerun()

# --- TIER LIST LOGIC ---
st.divider()
selected_lift = st.selectbox("View Rankings For:", all_exercises)

# Filter out the hidden Admin rows and sort
display_df = df[df['Name'] != 'Admin']
filtered_df = display_df[display_df['Exercise'] == selected_lift].sort_values(by="Weight", ascending=False).reset_index(drop=True)

if filtered_df.empty:
    st.info("No records for this lift yet. Be the first!")
else:
    for index, row in filtered_df.iterrows():
        rank = index + 1
        tier_label = "🥇 S-Tier" if rank == 1 else "🥈 A-Tier" if rank == 2 else "🥉 B-Tier" if rank == 3 else f"Rank {rank}"
        
        st.markdown(f"""
            <div class="tier-card">
                <h4>{tier_label}: {row['Name']}</h4>
                <p style="font-size: 20px;"><b>{row['Weight']} lbs</b></p>
            </div>

        """, unsafe_allow_html=True)
