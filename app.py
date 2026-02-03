import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 1. Page Setup
st.set_page_config(page_title="Family Hub", layout="wide")
st.title("🦘 Family Life Hub")

# 2. Connection Setup
# This connects to the secrets.toml file automatically
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error loading secrets.toml. Please check your Private Key format.")
    st.stop()

# 3. Sidebar Navigation
page = st.sidebar.radio("Menu", ["Shopping List", "Bills Tracker"])

# --- SHOPPING LIST PAGE ---
if page == "Shopping List":
    st.header("🛒 Shopping List")
    df = conn.read(worksheet="Shopping", ttl=0)
    
    # 1. Dynamically get stores from your actual data
    # This looks at your 'Store' column and finds unique names
    if not df.empty and "Store" in df.columns:
        existing_stores = sorted(df["Store"].dropna().unique().tolist())
    else:
        existing_stores = ["Coles", "Woolworths", "PetStock"]

    # 2. Add New Item Form
    with st.expander("➕ Add New Item"):
        with st.form("add_form", clear_on_submit=True):
            new_item = st.text_input("Item Name")
            
            # Dropdown for existing stores + "New Store..." option
            store_options = existing_stores + ["Add New Store..."]
            selected_store = st.selectbox("Select Store", store_options)
            
            # Only show this text box if "Add New Store..." is selected
            custom_store = st.text_input("Type new store name (if not in list above)")
            
            new_price = st.number_input("Price ($)", min_value=0.0)
            
            if st.form_submit_button("Add to List"):
                # Determine which store name to use
                final_store = custom_store if selected_store == "Add New Store..." else selected_store
                
                if new_item and final_store:
                    new_row = pd.DataFrame([{"Item": new_item, "Store": final_store, "Status": "Pending", "Price": new_price}])
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet="Shopping", data=updated_df)
                    st.success(f"Added {new_item} for {final_store}!")
                    st.rerun()

# --- BILLS TRACKER LOGIC ---
elif page == "Bills Tracker":
    st.header("💸 Bills & Expenses")
    
    try:
        df_bills = conn.read(worksheet="Bills", ttl=0)
    except:
        st.error("Could not read 'Bills' tab.")
        st.stop()
    
    if not df_bills.empty:
        st.dataframe(df_bills, use_container_width=True, hide_index=True)
        
        # Calculate Total Outstanding
        # Checks if 'Paid' column exists and counts anything that isn't 'Yes'
        if "Paid" in df_bills.columns and "Amount" in df_bills.columns:
            unpaid_mask = df_bills["Paid"].astype(str).str.lower() != "yes"
            total_due = df_bills[unpaid_mask]["Amount"].sum()
            st.metric("Total Outstanding", f"${total_due:,.2f}")
    else:

        st.info("No bills found.")

