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
    .tier-card { padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; background-color: #262730; margin-bottom: 10px; }
    .champ-board { padding: 20px; border-radius: 10px; border: 2px solid #ffd700; background-color: #332b00; text-align: center; margin-bottom: 25px; box-shadow: 0px 4px 15px rgba(255, 215, 0, 0.15); }
    </style>
    """, unsafe_allow_html=True)

st.title("🏆 Iron Leaderboard")

# --- 1. CONNECT TO GOOGLE SHEETS ---
# Load the secret JSON key we saved in Streamlit Settings
scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(st.secrets["gcp_json"])
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
client = gspread.authorize(creds)

# Open the sheet (Make sure this matches your Google Sheet name exactly!)
sheet = client.open("Gym Leaderboard DB").sheet1

# Helper function to save DataFrames to Google Sheets
def save_to_sheet(dataframe):
    sheet.clear()
    sheet.update(values=[dataframe.columns.values.tolist()] + dataframe.values.tolist(), range_name="A1")

# Load existing data
data = sheet.get_all_records()
if not data:
    # If the sheet is totally blank, create the columns
    df = pd.DataFrame(columns=["Name", "Exercise", "Weight", "Quote", "Passcode"])
    save_to_sheet(df)
else:
    df = pd.DataFrame(data)

# Ensure Passcode and Quote columns exist as text
for col in ["Quote", "Passcode"]:
    if col not in df.columns:
        df[col] = ""
df["Quote"] = df["Quote"].fillna("").astype(str)
df["Passcode"] = df["Passcode"].fillna("").astype(str)

# --- YOUR MASTER ADMIN PASSWORD ---
ADMIN_PASSWORD = "boss123"

default_exercises = ["Bench Press", "Squat", "Deadlift"]
existing_exercises = df['Exercise'].dropna().unique().tolist()
all_exercises = list(set(default_exercises + existing_exercises))

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
            new_row = pd.DataFrame({"Name": ["Admin"], "Exercise": [new_exercise], "Weight": [0], "Quote": [""], "Passcode": [""]})
            df = pd.concat([df, new_row], ignore_index=True)
            save_to_sheet(df)
            st.sidebar.success(f"{new_exercise} added!")
            st.rerun()
            
    st.sidebar.markdown("**Force Delete a Record**")
    force_name = st.sidebar.selectbox("Select Any Name", df[df['Name'] != 'Admin']['Name'].unique(), key="force_name")
    force_ex = st.sidebar.selectbox("Select Lift", df[df['Name'] == force_name]['Exercise'].unique() if force_name else [], key="force_ex")
    if st.sidebar.button("Force Delete", type="primary"):
        df = df[~((df['Name'] == force_name) & (df['Exercise'] == force_ex))]
        save_to_sheet(df)
        st.sidebar.success("Record annihilated.")
        st.rerun()

# --- MAIN PAGE: LOG PR ---
with st.expander("➕ Log a New PR", expanded=True):
    with st.form("pr_form"):
        col1, col2 = st.columns(2)
        with col1:
            user_name = st.text_input("Enter your name")
            exercise = st.selectbox("Select Lift", all_exercises)
            weight = st.number_input("Max Weight (lbs)", min_value=0.0, step=5.0)
        with col2:
            quote = st.text_input("Champion's Quote (Only shows if you hit #1!)")
            user_pin = st.text_input("Create/Enter your PIN (4 digits)", type="password")
            st.caption("First time? Create a PIN. Updating? Use your existing PIN.")
            
        if st.form_submit_button("Update Leaderboard"):
            if user_name and user_pin:
                existing_user = df[df['Name'] == user_name]
                if not existing_user.empty:
                    correct_pin = str(existing_user.iloc[0]['Passcode'])
                    if user_pin != correct_pin and correct_pin != "":
                        st.error("❌ That name is taken, and your PIN is incorrect!")
                        st.stop()
                
                mask = (df['Name'] == user_name) & (df['Exercise'] == exercise)
                if mask.any():
                    df.loc[mask, 'Weight'] = weight
                    df.loc[mask, 'Quote'] = quote
                else:
                    new_row = pd.DataFrame({"Name": [user_name], "Exercise": [exercise], "Weight": [weight], "Quote": [quote], "Passcode": [user_pin]})
                    df = pd.concat([df, new_row], ignore_index=True)
                
                save_to_sheet(df)
                st.success(f"Boom! {user_name} updated to {weight} lbs.")
                st.rerun()
            else:
                st.warning("Please enter your name and a PIN!")

# --- TIER LIST LOGIC ---
st.divider()
selected_lift = st.selectbox("View Rankings For:", all_exercises)

display_df = df[df['Name'] != 'Admin']
filtered_df = display_df[display_df['Exercise'] == selected_lift].sort_values(by="Weight", ascending=False).reset_index(drop=True)

if filtered_df.empty:
    st.info("No records for this lift yet. Be the first!")
else:
    champ_row = filtered_df.iloc[0]
    if str(champ_row['Quote']).strip() != "":
        st.markdown(f'''
            <div class="champ-board">
                <h2 style="color: #ffd700; margin-bottom: 5px;">👑 S-Tier Champion: {selected_lift} 👑</h2>
                <h3 style="font-style: italic;">"{champ_row['Quote']}"</h3>
                <p style="margin-top: 10px; font-size: 18px;">- <b>{champ_row['Name']}</b></p>
            </div>
        ''', unsafe_allow_html=True)

    for index, row in filtered_df.iterrows():
        rank = index + 1
        tier_label = "🥇 S-Tier" if rank == 1 else "🥈 A-Tier" if rank == 2 else "🥉 B-Tier" if rank == 3 else f"Rank {rank}"
        
        st.markdown(f"""
            <div class="tier-card">
                <h4>{tier_label}: {row['Name']}</h4>
                <p style="font-size: 20px;"><b>{row['Weight']} lbs</b></p>
            </div>
        """, unsafe_allow_html=True)
