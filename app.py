import json
import time
import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

# ------------------------------
# 1. Connect to Google Sheets
# ------------------------------
if 'gs_client' not in st.session_state:
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"],
        ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    )
    st.session_state.gs_client = gspread.authorize(creds)
    time.sleep(1)

    spreadsheet = st.session_state.gs_client.open("User Study – All Evidence Examples")
    st.session_state.examples_df = pd.DataFrame(spreadsheet.worksheet("examples").get_all_records())
    st.session_state.assignments_df = pd.DataFrame(spreadsheet.worksheet("assignments").get_all_records())
    st.session_state.results_sheet = spreadsheet.worksheet("results")

# ------------------------------
# 2. User login
# ------------------------------
user_id = st.text_input("Enter your user ID (e.g., user_1):")

# Initialize session state
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "user_answers" not in st.session_state:
    st.session_state.user_answers = []

# ------------------------------
# 3. Prepare user examples once
# ------------------------------
if user_id:
    row = st.session_state.assignments_df[st.session_state.assignments_df["user_id"] == user_id]
    if row.empty:
        st.write("User not found.")
    else:
        example_ids = row.iloc[0]["example_ids"].strip("[]")
        example_ids = [x.strip() for x in example_ids.split(",")]
        if "example_ids" not in st.session_state:
            st.session_state.example_ids = example_ids

# ------------------------------
# 4. Show example (ALL evidence at once)
# ------------------------------
def show_example():
    example_id = int(st.session_state.example_ids[st.session_state.current_index])
    row = st.session_state.examples_df[st.session_state.examples_df["example_id"] == example_id].iloc[0]

    st.write("## Claim:")
    st.write(row["claim"])

    st.write("---")
    st.write("## Evidence Sentences:")

    # Collect all non-empty sentences
    sentences = [
        row[f"sentence_{i}"]
        for i in range(1, 51)
        if f"sentence_{i}" in row and row[f"sentence_{i}"]
    ]

    # Show all sentences with numbering
    for idx, sent in enumerate(sentences, start=1):
        st.write(f"**{idx}.** {sent}")

    st.write("---")

    # Decision buttons
    col1, col2, col3 = st.columns(3)

    def save(decision):
        st.session_state.user_answers.append({
            "user_id": user_id,
            "example_id": example_id,
            "claim": row["claim"],
            "decision": decision,
            "timestamp": str(datetime.now())
        })
        st.session_state.current_index += 1

    with col1:
        if st.button("Support", key=f"support_{example_id}"):
            save("support")
    with col2:
        if st.button("Refute", key=f"refute_{example_id}"):
            save("refute")
    with col3:
        if st.button("Can't Decide", key=f"cannot_decide_{example_id}"):
            save("cannot_decide")

# ------------------------------
# 5. Main logic
# ------------------------------
if user_id and "example_ids" in st.session_state:
    st.write("### Instructions")
    st.write("""
    You will receive a claim and **all the evidence sentences at once**.

    Your task:
    - Read the claim.
    - Read all evidence sentences.
    - Then decide:

      **Support** → The evidence fully supports the claim.  
      **Refute** → At least one evidence sentence contradicts the claim.  
      **Can't Decide** → The evidence is insufficient or unclear.  

    After you choose, the next example will appear automatically.  
    After finishing all examples, click **Finish Session** to save your answers.
    """)

    if st.session_state.current_index < len(st.session_state.example_ids):
        show_example()
    else:
        st.write("🎉 You have completed all examples!")

# ------------------------------
# 6. Finish Session
# ------------------------------
if st.session_state.user_answers:
    if st.button("Finish Session"):
        rows = [
            [
                ans["user_id"],
                ans["example_id"],
                ans["claim"],
                ans["decision"],
                ans["timestamp"]
            ]
            for ans in st.session_state.user_answers
        ]
        st.session_state.results_sheet.append_rows(rows)
        st.success("All answers saved!")
        st.session_state.user_answers = []
