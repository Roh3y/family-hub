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
page = st.sidebar.radio("Menu", ["Shopping List", "Bills Tracker", "Pizza's Growth", "Water Tests"])

# --- SHOPPING LIST LOGIC ---
if page == "Shopping List":
    st.header("🛒 Shopping List")
    
    try:
        df = conn.read(worksheet="Shopping", ttl=0)
    except Exception as e:
        st.error(f"Could not read 'Shopping' tab. Error: {e}")
        st.stop()
    
    if df is not None and not df.empty:
        # FILTER LOGIC: Get unique stores for the dropdown
        if "Store" in df.columns:
            store_list = ["All Stores"] + sorted(df["Store"].dropna().unique().tolist())
            selected_filter = st.selectbox("🔍 Filter by Store", store_list)
            
            # Apply Filter
            if selected_filter != "All Stores":
                display_df = df[df["Store"] == selected_filter]
            else:
                display_df = df
        else:
            display_df = df
            st.warning("Column 'Store' not found in spreadsheet.")

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # Mark as Bought
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
        new_store = st.selectbox("Store", ["Aldi", "Bunnings", "Butcher", "Costco", "Fruit&Veg", "Harris Farm", "Health Foods", "Mountain Creek", "Woolies", "Other"])
        new_price = st.number_input("Estimated Price ($)", min_value=0.0, step=0.50)
        
        if st.form_submit_button("Add to List"):
            if new_item:
                new_row = pd.DataFrame([{"Item": new_item, "Store": new_store, "Status": "Pending", "Price": new_price}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Shopping", data=updated_df)
                st.success(f"Added {new_item}!")
                st.rerun()

# --- BILLS TRACKER LOGIC ---
elif page == "Bills Tracker":
    st.header("💸 Bills & Expenses")
    try:
        df_bills = conn.read(worksheet="Bills", ttl=0)
        if not df_bills.empty:
            st.dataframe(df_bills, use_container_width=True, hide_index=True)
            if "Paid" in df_bills.columns and "Amount" in df_bills.columns:
                unpaid_mask = df_bills["Paid"].astype(str).str.lower() != "yes"
                total_due = df_bills[unpaid_mask]["Amount"].sum()
                st.metric("Total Outstanding", f"${total_due:,.2f}")
    except:
        st.error("Could not read 'Bills' tab.")

# --- PIZZA'S GROWTH CHART ---
elif page == "Pizza's Growth":
    st.header("🐟 Pizza's Growth Chart")
    try:
        df_growth = conn.read(worksheet="Growth", ttl=0)
    except:
        st.error("Missing 'Growth' tab in Google Sheets.")
        st.stop()

    with st.expander("📏 Log New Measurement"):
        with st.form("pizza_form"):
            m_date = st.date_input("Date", value=date.today())
            m_len = st.number_input("Length (mm)", min_value=0.0, step=1.0)
            if st.form_submit_button("Log Growth"):
                new_entry = pd.DataFrame([{"Date": m_date.strftime("%Y-%m-%d"), "Length": m_len}])
                updated_g = pd.concat([df_growth, new_entry], ignore_index=True)
                conn.update(worksheet="Growth", data=updated_g)
                st.success("Logged!")
                st.rerun()

    if not df_growth.empty:
        df_growth["Date"] = pd.to_datetime(df_growth["Date"])
        st.line_chart(df_growth.sort_values("Date"), x="Date", y="Length")
        st.info(f"Started at 43mm on 1 Feb 2026.")

# --- WATER TESTS LOGIC ---
elif page == "Water Tests":
    st.header("💧 Aquarium Water Tests")
    try:
        df_water = conn.read(worksheet="Water", ttl=0)
    except:
        st.error("Missing 'Water' tab in Google Sheets.")
        st.stop()

    with st.expander("🧪 Log New Test"):
        with st.form("water_form"):
            t_date = st.date_input("Date", value=date.today())
            tank = st.selectbox("Tank", ["154L", "20L"])
            c1, c2 = st.columns(2)
            with c1:
                ph = st.selectbox("pH", [6.0, 6.3, 6.6, 7.0, 7.3, 7.5, 7.8])
                am = st.selectbox("Ammonia (ppm)", [0.0, 0.5, 1.0, 5.0, 10.0])
            with c2:
                ni = st.selectbox("Nitrite (ppm)", [0.0, 0.1, 0.25, 0.5, 1.0, 2.0])
                na = st.selectbox("Nitrate (ppm)", [0.0, 2.5, 5.0, 10.0, 20.0, 40.0])
            if st.form_submit_button("Save Results"):
                new_w = pd.DataFrame([{"Date": t_date.strftime("%Y-%m-%d"), "Tank": tank, "pH": ph, "Ammonia": am, "Nitrite": ni, "Nitrate": na}])
                updated_w = pd.concat([df_water, new_w], ignore_index=True)
                conn.update(worksheet="Water", data=updated_w)
                st.success("Results Saved!")
                st.rerun()

    if not df_water.empty:
        t_filter = st.radio("View Tank:", ["154L", "20L"], horizontal=True)
        st.dataframe(df_water[df_water["Tank"] == t_filter].sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
