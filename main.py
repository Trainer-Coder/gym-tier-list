import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# Page Config
st.set_page_config(page_title="Gym Tier List", page_icon="💪", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .tier-card { padding: 15px; border-radius: 10px; background-color: #262730; margin-bottom: 10px; }
    .champ-board { padding: 20px; border-radius: 10px; border: 2px solid #ffd700; background-color: #332b00; text-align: center; margin-bottom: 25px; box-shadow: 0px 4px 15px rgba(255, 215, 0, 0.15); }
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 Iron Leaderboard")

# --- 1. CONNECT TO GOOGLE SHEETS ---
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["gcp_json"])
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

sheet = client.open("Gym Leaderboard DB").sheet1

def save_to_sheet(dataframe):
    sheet.clear()
    sheet.update(values=[dataframe.columns.values.tolist()] + dataframe.values.tolist(), range_name="A1")

data = sheet.get_all_records()
if not data:
    df = pd.DataFrame(columns=["Name", "Exercise", "Weight", "BodyWeight", "Quote", "Passcode"])
    df.loc[0] = ["Admin", "Bench Press", 0, 0, "", ""]
    save_to_sheet(df)
else:
    df = pd.DataFrame(data)

# Auto-upgrade the database columns if they are missing
for col in ["Quote", "Passcode"]:
    if col not in df.columns:
        df[col] = ""
if "BodyWeight" not in df.columns:
    df["BodyWeight"] = 150.0  # Default to avoid math errors on old entries

df["Quote"] = df["Quote"].fillna("").astype(str)
df["Passcode"] = df["Passcode"].fillna("").astype(str)

ADMIN_PASSWORD = "boss123"

all_exercises = sorted(df['Exercise'].dropna().unique().tolist())
if not all_exercises:
    all_exercises = ["No Exercises Found"]

# --- SIDEBAR: USER SETTINGS & ADMIN ---
st.sidebar.header("⚙️ Control Panel")

st.sidebar.subheader("🗑️ Delete My Record")
if not df.empty and len(df[df['Name'] != 'Admin']) > 0:
    del_name = st.sidebar.selectbox("Your Name", df[df['Name'] != 'Admin']['Name'].unique())
    del_exercise = st.sidebar.selectbox("Lift to Delete", df[df['Name'] == del_name]['Exercise'].unique())
    del_pin = st.sidebar.text_input("Your PIN", type="password", key="del_pin")
    
    if st.sidebar.button("Delete My Record"):
        user_records = df[df['Name'] == del_name]
        correct_pin = str(user_records.iloc[0]['Passcode'])
        
        if del_pin == correct_pin or correct_pin == "":
            df = df[~((df['Name'] == del_name) & (df['Exercise'] == del_exercise))]
            save_to_sheet(df)
            st.sidebar.success("Deleted successfully!")
            st.rerun()
        else:
            st.sidebar.error("❌ Incorrect PIN for this user.")

st.sidebar.divider()

st.sidebar.subheader("👑 Admin Zone")
admin_input = st.sidebar.text_input("Enter Admin Password", type="password")

if admin_input == ADMIN_PASSWORD:
    st.sidebar.success("Admin Unlocked")
    
    new_exercise = st.sidebar.text_input("Type new exercise name")
    if st.sidebar.button("Add to List") and new_exercise:
        if new_exercise not in all_exercises:
            new_row = pd.DataFrame({"Name": ["Admin"], "Exercise": [new_exercise], "Weight": [0], "BodyWeight": [0], "Quote": [""], "Passcode": [""]})
            df = pd.concat([df, new_row], ignore_index=True)
            save_to_sheet(df)
            st.sidebar.success(f"{new_exercise} added!")
            st.rerun()
            
    st.sidebar.markdown("**Force Delete a PR Record**")
    force_name = st.sidebar.selectbox("Select Any Name", df[df['Name'] != 'Admin']['Name'].unique(), key="force_name")
    force_ex = st.sidebar.selectbox("Select Lift", df[df['Name'] == force_name]['Exercise'].unique() if force_name else [], key="force_ex")
    if st.sidebar.button("Delete PR", type="primary"):
        df = df[~((df['Name'] == force_name) & (df['Exercise'] == force_ex))]
        save_to_sheet(df)
        st.sidebar.success("Record annihilated.")
        st.rerun()
        
    st.sidebar.divider()
    st.sidebar.markdown("**NUKE AN ENTIRE EXERCISE**")
    st.sidebar.caption("⚠️ This deletes the category AND all PRs inside it.")
    nuke_ex = st.sidebar.selectbox("Select Exercise to Destroy", all_exercises, key="nuke_ex")
    if st.sidebar.button("Nuke Exercise", type="primary"):
        df = df[df['Exercise'] != nuke_ex]
        save_to_sheet(df)
        st.sidebar.success(f"{nuke_ex} has been completely removed.")
        st.rerun()

# --- MAIN PAGE: LOG PR ---
with st.expander("➕ Log a New PR", expanded=True):
    with st.form("pr_form"):
        col1, col2 = st.columns(2)
        with col1:
            user_name = st.text_input("Enter your name")
            exercise = st.selectbox("Select Lift", all_exercises)
            weight = st.number_input("Max Weight (lbs)", min_value=0.0, step=5.0)
            body_weight = st.number_input("Your Body Weight (lbs)", min_value=50.0, value=150.0, step=1.0)
        with col2:
            quote = st.text_input("Champion's Quote (Only shows if you hit #1!)")
            user_pin = st.text_input("Create/Enter your PIN (4 digits)", type="password")
            st.caption("First time? Create a PIN. Updating? Use your existing PIN.")
            
        if st.form_submit_button("Update Leaderboard"):
            if user_name and user_pin and exercise != "No Exercises Found":
                existing_user = df[df['Name'] == user_name]
                if not existing_user.empty:
                    correct_pin = str(existing_user.iloc[0]['Passcode'])
                    if user_pin != correct_pin and correct_pin != "":
                        st.error("❌ That name is taken, and your PIN is incorrect!")
                        st.stop()
                
                mask = (df['Name'] == user_name) & (df['Exercise'] == exercise)
                if mask.any():
                    df.loc[mask, 'Weight'] = weight
                    df.loc[mask, 'BodyWeight'] = body_weight
                    df.loc[mask, 'Quote'] = quote
                else:
                    new_row = pd.DataFrame({"Name": [user_name], "Exercise": [exercise], "Weight": [weight], "BodyWeight": [body_weight], "Quote": [quote], "Passcode": [user_pin]})
                    df = pd.concat([df, new_row], ignore_index=True)
                
                save_to_sheet(df)
                st.success(f"Boom! {user_name} updated to {weight} lbs.")
                st.rerun()
            else:
                st.warning("Please enter your name, a PIN, and ensure there's a valid exercise selected!")

# --- TIER LIST LOGIC ---
st.divider()

col_a, col_b = st.columns(2)
with col_a:
    selected_lift = st.selectbox("View Rankings For:", all_exercises)
with col_b:
    ranking_style = st.radio("Rank By:", ["Max Weight (lbs)", "Pound-for-Pound (Multiplier)"])

display_df = df[df['Name'] != 'Admin'].copy()

# Ensure math works by converting to numbers
display_df['BodyWeight'] = pd.to_numeric(display_df['BodyWeight'], errors='coerce').fillna(150.0)
display_df['Weight'] = pd.to_numeric(display_df['Weight'], errors='coerce').fillna(0.0)
# The Pound-for-Pound formula!
display_df['Multiplier'] = display_df['Weight'] / display_df['BodyWeight']

# Sort based on the toggle switch
if ranking_style == "Max Weight (lbs)":
    filtered_df = display_df[display_df['Exercise'] == selected_lift].sort_values(by="Weight", ascending=False).reset_index(drop=True)
else:
    filtered_df = display_df[display_df['Exercise'] == selected_lift].sort_values(by="Multiplier", ascending=False).reset_index(drop=True)

if filtered_df.empty:
    st.info("No records for this lift yet. Be the first!")
else:
    champ_row = filtered_df.iloc[0]
    
    if str(champ_row['Quote']).strip() != "":
        st.markdown(f'''
            <div class="champ-board">
                <h2 style="color: #ffd700; margin-bottom: 5px;">👑 The Champion: {selected_lift} 👑</h2>
                <h3 style="font-style: italic;">"{champ_row['Quote']}"</h3>
                <p style="margin-top: 10px; font-size: 18px;">- <b>{champ_row['Name']}</b></p>
            </div>
        ''', unsafe_allow_html=True)

    # The Custom Joke Tiers!
    for index, row in filtered_df.iterrows():
        rank = index + 1
        
        if rank == 1:
            tier_label = "👑 True Gym Rat"
            border_color = "#ffd700" # Gold
        elif rank == 2:
            tier_label = "🥈 CBUM Enthusiast"
            border_color = "#C0C0C0" # Silver
        elif rank == 3:
            tier_label = "🥉 The real gym bro"
            border_color = "#CD7F32" # Bronze
        elif rank == 4:
            tier_label = "HTN bro"
            border_color = "#ff4b4b" # Red
        elif rank == 5:
            tier_label = "Avocado Joe"
            border_color = "#ff8c00" # Orange
        elif rank == 6:
            tier_label = "gym kid"
            border_color = "#8a2be2" # Purple
        else:
            tier_label = "gym bud (Needs more pre)"
            border_color = "#555555" # Dark Grey
            
        # Change text based on Absolute vs Pound-for-Pound
        if ranking_style == "Max Weight (lbs)":
            stat_text = f"<b>{row['Weight']} lbs</b>"
        else:
            stat_text = f"<b>{row['Multiplier']:.2f}x Bodyweight</b> <span style='font-size: 14px;'>({row['Weight']} lbs at {row['BodyWeight']} lbs bw)</span>"
        
        st.markdown(f"""
            <div class="tier-card" style="border-left: 5px solid {border_color};">
                <h4>{tier_label}: {row['Name']}</h4>
                <p style="font-size: 20px;">{stat_text}</p>
            </div>
        """, unsafe_allow_html=True)
