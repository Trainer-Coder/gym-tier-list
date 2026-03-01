import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime

# Page Config
st.set_page_config(page_title="Gym Tier List", page_icon="💪", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .tier-card { padding: 15px; border-radius: 10px; background-color: #262730; margin-bottom: 10px; border-left: 5px solid #ff4b4b;}
    .champ-board { padding: 20px; border-radius: 10px; border: 2px solid #ffd700; background-color: #332b00; text-align: center; margin-bottom: 25px; box-shadow: 0px 4px 15px rgba(255, 215, 0, 0.15); }
    .hype-feed { padding: 10px; border-radius: 5px; background-color: #1e1e24; color: #00ffcc; font-family: monospace; text-align: center; margin-bottom: 20px;}
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
    df = pd.DataFrame(columns=["Name", "Exercise", "Weight", "BodyWeight", "Quote", "Passcode", "Timestamp"])
    df.loc[0] = ["Admin", "Bench Press", 0, 0, "", "", str(datetime.datetime.now())]
    save_to_sheet(df)
else:
    df = pd.DataFrame(data)

# Auto-upgrade database for new features
for col in ["Quote", "Passcode", "Timestamp"]:
    if col not in df.columns:
        if col == "Timestamp":
            df[col] = str(datetime.datetime.now())
        else:
            df[col] = ""
if "BodyWeight" not in df.columns:
    df["BodyWeight"] = 150.0

df["Quote"] = df["Quote"].fillna("").astype(str)
df["Passcode"] = df["Passcode"].fillna("").astype(str)
df["Timestamp"] = df["Timestamp"].fillna(str(datetime.datetime.now())).astype(str)

ADMIN_PASSWORD = "boss123"

all_exercises = sorted(df[df['Exercise'] != "No Exercises Found"]['Exercise'].dropna().unique().tolist())
if not all_exercises:
    all_exercises = ["Bench Press", "Squat", "Deadlift"]

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
    
    # 1. Add Exercise
    new_exercise = st.sidebar.text_input("Type new exercise name")
    if st.sidebar.button("Add to List") and new_exercise:
        if new_exercise not in all_exercises:
            new_row = pd.DataFrame({"Name": ["Admin"], "Exercise": [new_exercise], "Weight": [0], "BodyWeight": [0], "Quote": [""], "Passcode": [""], "Timestamp": [str(datetime.datetime.now())]})
            df = pd.concat([df, new_row], ignore_index=True)
            save_to_sheet(df)
            st.sidebar.success(f"{new_exercise} added!")
            st.rerun()
            
    st.sidebar.divider()
    
    # 2. Force Delete ANY Record
    st.sidebar.markdown("**Force Delete a PR Record**")
    admin_display_df = df[df['Name'] != 'Admin']
    if not admin_display_df.empty:
        force_name = st.sidebar.selectbox("Select Any Name", admin_display_df['Name'].unique(), key="force_name")
        force_ex = st.sidebar.selectbox("Select Lift", admin_display_df[admin_display_df['Name'] == force_name]['Exercise'].unique() if force_name else [], key="force_ex")
        if st.sidebar.button("Delete PR", type="primary"):
            df = df[~((df['Name'] == force_name) & (df['Exercise'] == force_ex))]
            save_to_sheet(df)
            st.sidebar.success("Record annihilated.")
            st.rerun()
    else:
        st.sidebar.info("No user records to delete yet.")
    
    st.sidebar.divider()
    
    # 3. Nuke Entire Exercise
    st.sidebar.markdown("**NUKE AN ENTIRE EXERCISE**")
    nuke_ex = st.sidebar.selectbox("Select Exercise to Destroy", all_exercises, key="nuke_ex")
    if st.sidebar.button("Nuke Exercise", type="primary"):
        df = df[df['Exercise'] != nuke_ex]
        save_to_sheet(df)
        st.sidebar.success(f"{nuke_ex} completely removed.")
        st.rerun()

# --- THE HYPE FEED ---
if not df[df['Name'] != 'Admin'].empty:
    recent_lifts = df[df['Name'] != 'Admin'].sort_values(by="Timestamp", ascending=False).head(3)
    feed_text = " | ".join([f"🔥 {row['Name']} hit {row['Weight']}lbs on {row['Exercise']}!" for _, row in recent_lifts.iterrows()])
    st.markdown(f"<div class='hype-feed'>📢 LIVE ACTIVITY: {feed_text}</div>", unsafe_allow_html=True)

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
            if user_name and user_pin:
                existing_user = df[df['Name'] == user_name]
                if not existing_user.empty:
                    correct_pin = str(existing_user.iloc[0]['Passcode'])
                    if user_pin != correct_pin and correct_pin != "":
                        st.error("❌ That name is taken, and your PIN is incorrect!")
                        st.stop()
                
                # Append the new lift instead of overwriting, to build history!
                timestamp = str(datetime.datetime.now())
                new_row = pd.DataFrame({"Name": [user_name], "Exercise": [exercise], "Weight": [weight], "BodyWeight": [body_weight], "Quote": [quote], "Passcode": [user_pin], "Timestamp": [timestamp]})
                df = pd.concat([df, new_row], ignore_index=True)
                save_to_sheet(df)
                
                st.balloons() # 🎉 CONFETTI EFFECT 🎉
                st.success(f"Boom! {user_name} updated to {weight} lbs.")
            else:
                st.warning("Please enter your name and a PIN!")

# --- ORGANIZE PRs (Get only the highest weight per person per exercise) ---
display_df = df[df['Name'] != 'Admin'].copy()
display_df['BodyWeight'] = pd.to_numeric(display_df['BodyWeight'], errors='coerce').fillna(150.0)
display_df['Weight'] = pd.to_numeric(display_df['Weight'], errors='coerce').fillna(0.0)
display_df['Multiplier'] = display_df['Weight'] / display_df['BodyWeight']

# This isolates everyone's all-time max for the leaderboard
pr_df = display_df.sort_values('Weight', ascending=False).drop_duplicates(subset=['Name', 'Exercise'])

# --- APP TABS ---
tab1, tab2, tab3 = st.tabs(["🏆 Leaderboard", "📈 Gains Chart", "🔥 1000 lb Club"])

with tab1:
    col_a, col_b = st.columns(2)
    with col_a:
        selected_lift = st.selectbox("View Rankings For:", all_exercises, key="rank_lift")
    with col_b:
        ranking_style = st.radio("Rank By:", ["Max Weight (lbs)", "Pound-for-Pound (Multiplier)"])

    if ranking_style == "Max Weight (lbs)":
        filtered_df = pr_df[pr_df['Exercise'] == selected_lift].sort_values(by="Weight", ascending=False).reset_index(drop=True)
    else:
        filtered_df = pr_df[pr_df['Exercise'] == selected_lift].sort_values(by="Multiplier", ascending=False).reset_index(drop=True)

    if filtered_df.empty:
        st.info("No records for this lift yet. Be the first!")
    else:
        champ_row = filtered_df.iloc[0]
        
        # Determine the stat text for the Champion based on the toggle
        if ranking_style == "Max Weight (lbs)":
            champ_stat = f"{champ_row['Weight']} lbs"
        else:
            champ_stat = f"{champ_row['Multiplier']:.2f}x Bodyweight <span style='font-size: 16px; color: #ffffff;'>({champ_row['Weight']} lbs)</span>"
            
        # Display the quote only if they wrote one
        quote_html = f'<h3 style="font-style: italic;">"{champ_row["Quote"]}"</h3>' if str(champ_row['Quote']).strip() != "" else ""
        
        st.markdown(f'''
            <div class="champ-board">
                <h2 style="color: #ffd700; margin-bottom: 5px;">👑 True Gym Rat: {selected_lift} 👑</h2>
                {quote_html}
                <p style="font-size: 26px; margin: 10px 0px; color: #00ffcc;"><b>{champ_stat}</b></p>
                <p style="font-size: 18px; margin-bottom: 0px;">- <b>{champ_row['Name']}</b></p>
            </div>
        ''', unsafe_allow_html=True)

        for index, row in filtered_df.iterrows():
            rank = index + 1
            if rank == 1:
                continue # Skip #1 because they are the Champion box above!
            elif rank == 2:
                tier_label = "🥈 CBUM Enthusiast"
            elif rank == 3:
                tier_label = "🥉 The real gym bro"
            elif rank == 4:
                tier_label = "HTN bro"
            elif rank == 5:
                tier_label = "Avocado Joe"
            elif rank == 6:
                tier_label = "gym kid"
            else:
                tier_label = "gym bud (Needs more pre)"
                
            stat_text = f"<b>{row['Weight']} lbs</b>" if ranking_style == "Max Weight (lbs)" else f"<b>{row['Multiplier']:.2f}x Bodyweight</b> <span style='font-size: 14px;'>({row['Weight']} lbs)</span>"
            
            st.markdown(f"""
                <div class="tier-card">
                    <h4>{tier_label}: {row['Name']}</h4>
                    <p style="font-size: 20px;">{stat_text}</p>
                </div>
            """, unsafe_allow_html=True)

with tab2:
    st.subheader("📈 Progress Over Time")
    chart_lift = st.selectbox("Select Lift to Graph:", all_exercises, key="chart_lift")
    chart_data = display_df[display_df['Exercise'] == chart_lift].copy()
    
    if not chart_data.empty:
        chart_data['Timestamp'] = pd.to_datetime(chart_data['Timestamp'], errors='coerce')
        pivot_df = chart_data.pivot_table(index='Timestamp', columns='Name', values='Weight', aggfunc='max')
        pivot_df = pivot_df.ffill() # Connects the dots if someone skips a day
        st.line_chart(pivot_df)
    else:
        st.info("Log some lifts to see the chart grow!")

with tab3:
    st.subheader("🔥 The 1,000 lb Club")
    st.markdown("Your total is the sum of your all-time Max **Bench Press**, **Squat**, and **Deadlift**.")
    
    # Calculate Powerlifting Totals
    sbd_df = pr_df[pr_df['Exercise'].isin(["Bench Press", "Squat", "Deadlift"])]
    totals = sbd_df.groupby('Name')['Weight'].sum().reset_index()
    totals = totals.sort_values(by='Weight', ascending=False).reset_index(drop=True)
    
    if totals.empty:
        st.info("Nobody has logged Bench, Squat, and Deadlift yet!")
    else:
        for index, row in totals.iterrows():
            if row['Weight'] >= 1000:
                st.success(f"👑 **{row['Name']}** is in the club! Total: **{row['Weight']} lbs**")
            else:
                st.info(f"💪 **{row['Name']}** is on the grind. Total: **{row['Weight']} lbs** (Needs {1000 - row['Weight']} lbs more)")
