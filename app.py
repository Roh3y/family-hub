import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date

# 1. Page Setup
st.set_page_config(page_title="Family Hub", layout="wide")
st.title("🦘 Family Life Hub")

# 2. Connection Setup
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error loading secrets.toml. Please check your Private Key format.")
    st.stop()

# 3. Sidebar Navigation
# Added new pages for Pizza and Water Tests
page = st.sidebar.radio("Menu", ["Shopping List", "Bills Tracker", "Pizza's Growth", "Water Tests"])

# --- SHOPPING LIST LOGIC ---
if page == "Shopping List":
    st.header("🛒 Shopping List")
    
    try:
        df = conn.read(worksheet="Shopping", ttl=0)
    except Exception as e:
        st.error(f"Could not read 'Shopping' tab. Check if the tab exists in Google Sheets. Error: {e}")
        st.stop()
    
    if df is not None and not df.empty:
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

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.subheader("Update List")
        if "Item" in display_df.columns:
            item_to_remove = st.selectbox("Select item to mark as bought:", ["Select..."] + display_df["Item"].tolist())
            if st.button("Mark as Bought (Remove)"):
                if item_to_remove != "Select...":
                    updated_df = df[df["Item"] != item_to_remove]
                    conn.update(worksheet="Shopping", data=updated_df)
                    st.success(f"Removed {item_to_remove}!")
                    st.rerun()
    else:
        st.info("Your shopping list is empty. Add something below!")

    st.divider()
    st.subheader("➕ Add New Item")
    with st.form("add_shopping_item", clear_on_submit=True):
        new_item = st.text_input("Item Name")
        # Your specific manual store list
        new_store = st.selectbox("Store", ["Aldi", "Bunnings", "Butcher", "Costco", "Fruit&Veg", "Harris Farm", "Health Foods", "Mountain Creek", "Woolies", "Other"])
        new_price = st.number_input("Estimated Price ($)", min_value=0.0, step=0.50)
        
        submitted = st.form_submit_button("Add to List")
        
        if submitted:
            if new_item:
                new_data = pd.DataFrame([{"Item": new_item, "Store": new_store, "Status": "Pending", "Price": new_price}])
                updated_df = pd.concat([df, new_data], ignore_index=True)
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
        
        if "Paid" in df_bills.columns and "Amount" in df_bills.columns:
            unpaid_mask = df_bills["Paid"].astype(str).str.lower() != "yes"
            total_due = df_bills[unpaid_mask]["Amount"].sum()
            st.metric("Total Outstanding", f"${total_due:,.2f}")
    else:
        st.info("No bills found.")

# --- PIZZA'S GROWTH CHART ---
elif page == "Pizza's Growth":
    st.header("🐟 Pizza's Growth Chart")
    
    # Read the Growth tab
    try:
        df_growth = conn.read(worksheet="Growth", ttl=0)
    except:
        st.error("Could not find 'Growth' tab. Please create a tab in your sheet named 'Growth' with columns: Date, Length")
        st.stop()

    # Form to add new measurement
    with st.expander("📏 Add New Measurement"):
        with st.form("pizza_growth"):
            measure_date = st.date_input("Date", value=date.today())
            measure_len = st.number_input("Length (mm)", min_value=0.0, step=1.0)
            
            if st.form_submit_button("Log Growth"):
                new_row = pd.DataFrame([{"Date": measure_date.strftime("%Y-%m-%d"), "Length": measure_len}])
                updated_growth = pd.concat([df_growth, new_row], ignore_index=True)
                conn.update(worksheet="Growth", data=updated_growth)
                st.success("Logged!")
                st.rerun()

    # Display Chart
    if not df_growth.empty:
        # Ensure data is sorted by date for the chart
        df_growth["Date"] = pd.to_datetime(df_growth["Date"])
        df_growth = df_growth.sort_values("Date")
        
        st.line_chart(df_growth, x="Date", y="Length")
        
        # Show recent stats
        latest = df_growth.iloc[-1]
        st.info(f"Current Size: {latest['Length']}mm (recorded {latest['Date'].date()})")
        
        # Reference Note
        st.caption("Pizza started at 43mm on 1 Feb 2026.")
    else:
        st.info("No growth data yet. Add the first entry (43mm on Feb 1st) above!")

# --- WATER TESTS LOGIC ---
elif page == "Water Tests":
    st.header("💧 Aquarium Water Tests")
    
    # Read the Water tab
    try:
        df_water = conn.read(worksheet="Water", ttl=0)
    except:
        st.error("Could not find 'Water' tab. Please create a tab in your sheet named 'Water' with columns: Date, Tank, pH, Ammonia, Nitrite, Nitrate")
        st.stop()

    # Input Form
    with st.expander("🧪 Log New Test"):
        with st.form("water_test"):
            test_date = st.date_input("Date", value=date.today())
            selected_tank = st.selectbox("Tank", ["154L", "20L"])
            
            # Columns for inputs to save space
            c1, c2 = st.columns(2)
            with c1:
                # Values based on your Aqua One kit info
                ph_val = st.selectbox("pH", [6.0, 6.3, 6.6, 7.0, 7.3, 7.5, 7.8])
                ammonia_val = st.selectbox("Ammonia (ppm)", [0.0, 0.5, 1.0, 5.0, 10.0])
            with c2:
                nitrite_val = st.selectbox("Nitrite (ppm)", [0.0, 0.1, 0.25, 0.5, 1.0, 2.0])
                nitrate_val = st.selectbox("Nitrate (ppm)", [0.0, 2.5, 5.0, 10.0, 20.0, 40.0])

            if st.form_submit_button("Save Results"):
                new_water = pd.DataFrame([{
                    "Date": test_date.strftime("%Y-%m-%d"),
                    "Tank": selected_tank,
                    "pH": ph_val,
                    "Ammonia": ammonia_val,
                    "Nitrite": nitrite_val,
                    "Nitrate": nitrate_val
                }])
                updated_water = pd.concat([df_water, new_water], ignore_index=True)
                conn.update(worksheet="Water", data=updated_water)
                st.success(f"Logged tests for {selected_tank}!")
                st.rerun()

    # Display History
    if not df_water.empty:
        # Filter by Tank
        tank_filter = st.radio("Show History For:", ["154L", "20L"], horizontal=True)
        tank_data = df_water[df_water["Tank"] == tank_filter]
        
        if not tank_data.empty:
            st.dataframe(tank_data.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info(f"No records yet for {tank_filter} tank.")
