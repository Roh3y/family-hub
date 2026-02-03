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

# --- SHOPPING LIST LOGIC ---
if page == "Shopping List":
    st.header("🛒 Shopping List")
    
    # Read Data (ttl=0 means 'don't cache, reload every time')
    try:
        df = conn.read(worksheet="Shopping", ttl=0)
    except Exception as e:
        st.error(f"Could not read 'Shopping' tab. Check if the tab exists in Google Sheets. Error: {e}")
        st.stop()
    
    # Check if dataframe is valid
    if df is not None and not df.empty:
        # Filter by Store
        # We ensure 'Store' column exists to avoid crash
        if "Store" in df.columns:
            stores = ["All"] + sorted(df["Store"].dropna().unique().tolist())
            selected_store = st.selectbox("Filter by Store", stores)
            
            if selected_store != "All":
                display_df = df[df["Store"] == selected_store]
            else:
                display_df = df
        else:
            display_df = df
            st.warning("Column 'Store' not found in spreadsheet.")

        # Show the Data
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # "Mark as Bought" Feature
        st.subheader("Update List")
        if "Item" in display_df.columns:
            item_to_remove = st.selectbox("Select item to mark as bought:", ["Select..."] + display_df["Item"].tolist())
            if st.button("Mark as Bought (Remove)"):
                if item_to_remove != "Select...":
                    # Filter out the item to remove
                    updated_df = df[df["Item"] != item_to_remove]
                    conn.update(worksheet="Shopping", data=updated_df)
                    st.success(f"Removed {item_to_remove}!")
                    st.rerun()

    else:
        st.info("Your shopping list is empty. Add something below!")

    # Add New Item Form
    st.divider()
    st.subheader("➕ Add New Item")
    with st.form("add_shopping_item", clear_on_submit=True):
        new_item = st.text_input("Item Name")
        new_store = st.selectbox("Store", ["Coles", "Woolworths", "PetStock", "Bunnings", "Other"])
        new_price = st.number_input("Estimated Price ($)", min_value=0.0, step=0.50)
        
        submitted = st.form_submit_button("Add to List")
        
        if submitted:
            if new_item:
                # Create a new row
                new_data = pd.DataFrame([{"Item": new_item, "Store": new_store, "Status": "Pending", "Price": new_price}])
                # Combine old data with new row
                updated_df = pd.concat([df, new_data], ignore_index=True)
                # Save back to Google Sheets
                conn.update(worksheet="Shopping", data=updated_df)
                st.success(f"Added {new_item}!")
                st.rerun()
            else:
                st.warning("Please enter an item name.")

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