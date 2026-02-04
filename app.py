import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, timedelta

# 1. Page Setup
st.set_page_config(page_title="Family Hub", layout="wide")
st.title("😍 Family Life Hub")

# 2. Connection Setup
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Error loading secrets.toml. Please check your Private Key format.")
    st.stop()

# 3. Sidebar Navigation
page = st.sidebar.radio("Menu", ["Shopping List", "Calendar", "Bills Tracker", "Pizza's Growth", "Water Tests"])

# --- SHOPPING LIST LOGIC ---
if page == "Shopping List":
    st.header("🛒 Shopping List")
    
    try:
        df = conn.read(worksheet="Shopping", ttl=0)
    except Exception as e:
        st.error(f"Could not read 'Shopping' tab. Error: {e}")
        st.stop()
    
    if df is not None and not df.empty:
        df.columns = [str(c).strip() for c in df.columns]

        # Sorting: Store first, then Item
        if "Store" in df.columns and "Item" in df.columns:
            df = df.sort_values(by=["Store", "Item"])

        # Filter Logic
        if "Store" in df.columns:
            store_list = ["All Stores"] + sorted(df["Store"].dropna().unique().tolist())
            selected_filter = st.selectbox("🔍 Filter by Store", store_list)
            
            if selected_filter != "All Stores":
                display_df = df[df["Store"] == selected_filter].copy()
            else:
                display_df = df.copy()
        else:
            display_df = df.copy()

        # UI FIX: Ensure Quantity is a whole number string
        if "Quantity" in display_df.columns:
            display_df["Quantity"] = pd.to_numeric(display_df["Quantity"], errors='coerce').fillna(0).astype(int).astype(str)

        cols_to_hide = ['status', 'price']
        cols_to_show = [c for c in display_df.columns if c.lower() not in cols_to_hide]
        
        st.dataframe(display_df[cols_to_show], use_container_width=True, hide_index=True)

        # Mark as Bought
        st.subheader("Update List")
        if "Item" in display_df.columns:
            item_list = sorted(display_df["Item"].tolist())
            item_to_remove = st.selectbox("Select item to mark as bought:", ["Select..."] + item_list)
            if st.button("Mark as Bought (Remove)"):
                if item_to_remove != "Select...":
                    updated_df = df[df["Item"] != item_to_remove]
                    conn.update(worksheet="Shopping", data=updated_df)
                    st.success(f"Removed {item_to_remove} from list!")
                    st.rerun()
    else:
        st.info("Your shopping list is empty. Add something below!")

    st.divider()
    st.subheader("➕ Add New Item")
    with st.form("add_shopping_item", clear_on_submit=True):
        new_item = st.text_input("Item Name")
        col1, col2 = st.columns([1, 2])
        with col1:
            new_qty = st.number_input("Quantity", min_value=1, step=1, value=1)
        with col2:
            store_options = [""] + ["Aldi", "Bunnings", "Butcher", "Costco", "Fruit&Veg", "Harris Farm", "Health Foods", "Mountain Creek", "Woolies", "Other"]
            new_store = st.selectbox("Store", store_options, index=0)
        
        new_comment = st.text_input("Comment (e.g. 'On Special', 'Half Price')")
        
        if st.form_submit_button("Add to List"):
            if not new_item:
                st.warning("Please enter an item name.")
            elif not new_store:
                st.warning("Please select a store.")
            else:
                new_row = pd.DataFrame([{
                    "Item": new_item, 
                    "Quantity": int(new_qty), 
                    "Store": new_store, 
                    "Comment": new_comment,
                    "Status": "Pending", 
                    "Price": 0
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Shopping", data=updated_df)
                st.success(f"Added {int(new_qty)}x {new_item}!")
                st.rerun()

# --- CALENDAR LOGIC ---
elif page == "Calendar":
    st.header("📅 Family Calendar")
    
    try:
        df_cal = conn.read(worksheet="Calendar", ttl=0)
    except:
        st.error("Missing 'Calendar' tab. Please add it to Google Sheets with columns: Date, Event, Time, Who")
        st.stop()

    # --- INPUT FORM ---
    with st.expander("➕ Add New Event"):
        with st.form("add_event", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                e_date = st.date_input("Date", value=date.today())
                e_time = st.time_input("Time", value=None) # Optional time
            with c2:
                e_who = st.selectbox("Who is this for?", ["Family", "Me", "Partner", "Kids", "Pets"])
                e_desc = st.text_input("Event Description")
            
            if st.form_submit_button("Save Event"):
                if e_desc:
                    # Convert time to string if exists
                    time_str = e_time.strftime("%H:%M") if e_time else ""
                    new_evt = pd.DataFrame([{
                        "Date": e_date.strftime("%Y-%m-%d"),
                        "Event": e_desc,
                        "Time": time_str,
                        "Who": e_who
                    }])
                    updated_cal = pd.concat([df_cal, new_evt], ignore_index=True)
                    conn.update(worksheet="Calendar", data=updated_cal)
                    st.success("Event Added!")
                    st.rerun()
                else:
                    st.warning("Please describe the event.")

    # --- DISPLAY LOGIC ---
    if not df_cal.empty:
        # Ensure Date is datetime object for filtering
        df_cal["Date"] = pd.to_datetime(df_cal["Date"])
        df_cal = df_cal.sort_values("Date")
        
        # Calculate Date Ranges
        today = pd.Timestamp(date.today())
        four_weeks_out = today + timedelta(days=28)

        # 1. UPCOMING (Next 4 Weeks)
        st.subheader("Next 4 Weeks")
        # Filter: Date is today or future, AND Date is before 4 weeks from now
        mask_upcoming = (df_cal["Date"] >= today) & (df_cal["Date"] <= four_weeks_out)
        df_upcoming = df_cal[mask_upcoming].copy()

        if not df_upcoming.empty:
            # Format date to look nice (e.g., "Fri 06 Feb")
            df_upcoming["Formatted Date"] = df_upcoming["Date"].dt.strftime("%a %d %b")
            
            # Show a clean table
            st.dataframe(
                df_upcoming[["Formatted Date", "Time", "Event", "Who"]], 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("Nothing scheduled for the next 4 weeks! 🎉")

        # 2. ALL EVENTS (The Master List)
        st.divider()
        with st.expander("📂 View All Calendar Entries (Future & Past)"):
            # Show everything, just sorted
            df_display_all = df_cal.copy()
            df_display_all["Formatted Date"] = df_display_all["Date"].dt.strftime("%Y-%m-%d")
            st.dataframe(
                df_display_all[["Formatted Date", "Time", "Event", "Who"]], 
                use_container_width=True, 
                hide_index=True
            )

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
        st.error("Missing 'Growth' tab.")
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
        st.error("Missing 'Water' tab.")
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
