import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import date, timedelta, datetime

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

# --- SHOPPING LIST LOGIC (Same as before) ---
if page == "Shopping List":
    st.header("🛒 Shopping List")
    try:
        df = conn.read(worksheet="Shopping", ttl=0)
        if df is not None and not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            if "Store" in df.columns and "Item" in df.columns:
                df = df.sort_values(by=["Store", "Item"])
            store_list = ["All Stores"] + sorted(df["Store"].dropna().unique().tolist())
            selected_filter = st.selectbox("🔍 Filter by Store", store_list)
            display_df = df[df["Store"] == selected_filter].copy() if selected_filter != "All Stores" else df.copy()
            if "Quantity" in display_df.columns:
                display_df["Quantity"] = pd.to_numeric(display_df["Quantity"], errors='coerce').fillna(0).astype(int).astype(str)
            cols_to_show = [c for c in display_df.columns if c.lower() not in ['status', 'price']]
            st.dataframe(display_df[cols_to_show], use_container_width=True, hide_index=True)

            st.subheader("Update List")
            item_to_remove = st.selectbox("Select item to mark as bought:", ["Select..."] + sorted(display_df["Item"].tolist()))
            if st.button("Mark as Bought (Remove)"):
                if item_to_remove != "Select...":
                    updated_df = df[df["Item"] != item_to_remove]
                    conn.update(worksheet="Shopping", data=updated_df)
                    st.success(f"Removed {item_to_remove}!")
                    st.rerun()
        
        st.divider()
        st.subheader("➕ Add New Item")
        with st.form("add_shopping_item", clear_on_submit=True):
            new_item = st.text_input("Item Name")
            c1, c2 = st.columns([1, 2])
            with c1: new_qty = st.number_input("Quantity", min_value=1, step=1, value=1)
            with c2: new_store = st.selectbox("Store", ["", "Aldi", "Bunnings", "Butcher", "Costco", "Fruit&Veg", "Harris Farm", "Health Foods", "Mountain Creek", "Woolies", "Other"])
            new_comment = st.text_input("Comment")
            if st.form_submit_button("Add to List"):
                if new_item and new_store:
                    new_row = pd.DataFrame([{"Item": new_item, "Quantity": int(new_qty), "Store": new_store, "Comment": new_comment, "Status": "Pending", "Price": 0}])
                    updated_df = pd.concat([df, new_row], ignore_index=True)
                    conn.update(worksheet="Shopping", data=updated_df)
                    st.success("Added!")
                    st.rerun()
                else: st.warning("Item Name and Store are required.")
    except: st.error("Shopping tab error.")

# --- CALENDAR LOGIC ---
elif page == "Calendar":
    st.header("📅 Family Calendar")
    try:
        df_cal = conn.read(worksheet="Calendar", ttl=0)
    except:
        st.error("Missing 'Calendar' tab. Columns needed: Date, Event, Start Time, End Time, Who")
        st.stop()

    # --- INPUT FORM ---
    with st.expander("➕ Add New Event"):
        with st.form("add_event", clear_on_submit=True):
            e_desc = st.text_input("Event Description")
            c1, c2, c3 = st.columns(3)
            with c1: e_date = st.date_input("Date", value=date.today())
            with c2: e_start = st.time_input("Start Time", value=None)
            with c3: e_end = st.time_input("End Time", value=None)
            
            # Multi-select for Who
            e_who_list = st.multiselect("Who is this for? (Select at least one)", ["Me", "Partner", "Kids", "Pets", "Other"])
            
            if st.form_submit_button("Save Event"):
                if e_desc and e_who_list:
                    start_str = e_start.strftime("%H:%M") if e_start else ""
                    end_str = e_end.strftime("%H:%M") if e_end else ""
                    who_str = ", ".join(e_who_list)
                    
                    new_evt = pd.DataFrame([{
                        "Date": e_date.strftime("%Y-%m-%d"),
                        "Event": e_desc,
                        "Start Time": start_str,
                        "End Time": end_str,
                        "Who": who_str
                    }])
                    updated_cal = pd.concat([df_cal, new_evt], ignore_index=True)
                    conn.update(worksheet="Calendar", data=updated_cal)
                    st.success("Event Added!")
                    st.rerun()
                else:
                    st.warning("Please provide a description and select at least one person.")

    # --- DISPLAY LOGIC ---
    if not df_cal.empty:
        df_cal["Date"] = pd.to_datetime(df_cal["Date"])
        df_cal = df_cal.sort_values("Date")
        
        today = pd.Timestamp(date.today())
        two_weeks_out = today + timedelta(days=14)

        # 1. NEXT 2 WEEKS
        st.subheader("Next 2 Weeks")
        mask_upcoming = (df_cal["Date"] >= today) & (df_cal["Date"] <= two_weeks_out)
        df_upcoming = df_cal[mask_upcoming].copy()

        if not df_upcoming.empty:
            df_upcoming["Date"] = df_upcoming["Date"].dt.strftime("%d/%m/%y")
            st.dataframe(df_upcoming[["Date", "Start Time", "End Time", "Event", "Who"]], use_container_width=True, hide_index=True)
        else:
            st.info("Nothing scheduled for the next 2 weeks! 🎉")

        # 2. EDIT/DELETE SECTION (The "Don't go to Google Sheets" feature)
        st.divider()
        with st.expander("📝 Edit or Delete Entries"):
            # Create a unique label for the selectbox
            df_cal["Edit_Label"] = df_cal["Date"].dt.strftime("%d/%m/%y") + " - " + df_cal["Event"]
            choice = st.selectbox("Select an entry to modify:", ["Select..."] + df_cal["Edit_Label"].tolist())
            
            if choice != "Select...":
                # Get the specific row
                row_idx = df_cal[df_cal["Edit_Label"] == choice].index[0]
                row_data = df_cal.loc[row_idx]
                
                with st.form("edit_form"):
                    u_desc = st.text_input("Edit Description", value=row_data["Event"])
                    u_date = st.date_input("Edit Date", value=row_data["Date"])
                    
                    # Time parsing logic
                    def parse_t(t_str):
                        try: return datetime.strptime(t_str, "%H:%M").time()
                        except: return None

                    u_start = st.time_input("Edit Start", value=parse_t(row_data["Start Time"]))
                    u_end = st.time_input("Edit End", value=parse_t(row_data["End Time"]))
                    u_who = st.text_input("Edit Who (comma separated)", value=row_data["Who"])
                    
                    col_save, col_del = st.columns(2)
                    if col_save.form_submit_button("Update Entry"):
                        df_cal.loc[row_idx, "Event"] = u_desc
                        df_cal.loc[row_idx, "Date"] = u_date.strftime("%Y-%m-%d")
                        df_cal.loc[row_idx, "Start Time"] = u_start.strftime("%H:%M") if u_start else ""
                        df_cal.loc[row_idx, "End Time"] = u_end.strftime("%H:%M") if u_end else ""
                        df_cal.loc[row_idx, "Who"] = u_who
                        
                        # Cleanup and save
                        final_df = df_cal.drop(columns=["Edit_Label"])
                        final_df["Date"] = pd.to_datetime(final_df["Date"]).dt.strftime("%Y-%m-%d")
                        conn.update(worksheet="Calendar", data=final_df)
                        st.success("Updated!")
                        st.rerun()
                        
                    if col_del.form_submit_button("🗑️ Delete Permanently"):
                        final_df = df_cal.drop(row_idx).drop(columns=["Edit_Label"])
                        final_df["Date"] = pd.to_datetime(final_df["Date"]).dt.strftime("%Y-%m-%d")
                        conn.update(worksheet="Calendar", data=final_df)
                        st.success("Deleted!")
                        st.rerun()

        # 3. MASTER LIST
        with st.expander("📂 View All Calendar Entries"):
            df_all = df_cal.copy()
            df_all["Date"] = df_all["Date"].dt.strftime("%d/%m/%y")
            st.dataframe(df_all[["Date", "Start Time", "End Time", "Event", "Who"]], use_container_width=True, hide_index=True)

# --- OTHER PAGES (Remain same as previous version) ---
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
    except: st.error("Bills error.")

elif page == "Pizza's Growth":
    st.header("🐟 Pizza's Growth Chart")
    try:
        df_growth = conn.read(worksheet="Growth", ttl=0)
        with st.expander("📏 Log Measurement"):
            with st.form("pizza_form"):
                m_date = st.date_input("Date")
                m_len = st.number_input("Length (mm)", min_value=0.0)
                if st.form_submit_button("Log"):
                    new_e = pd.DataFrame([{"Date": m_date.strftime("%Y-%m-%d"), "Length": m_len}])
                    conn.update(worksheet="Growth", data=pd.concat([df_growth, new_e]))
                    st.rerun()
        if not df_growth.empty:
            df_growth["Date"] = pd.to_datetime(df_growth["Date"])
            st.line_chart(df_growth.sort_values("Date"), x="Date", y="Length")
    except: st.error("Growth error.")

elif page == "Water Tests":
    st.header("💧 Aquarium Water Tests")
    try:
        df_water = conn.read(worksheet="Water", ttl=0)
        with st.expander("🧪 Log Test"):
            with st.form("water_form"):
                tank = st.selectbox("Tank", ["154L", "20L"])
                # ... (rest of water form)
                if st.form_submit_button("Save"):
                    # ... save logic
                    st.rerun()
        if not df_water.empty:
            t_filter = st.radio("View Tank:", ["154L", "20L"], horizontal=True)
            st.dataframe(df_water[df_water["Tank"] == t_filter].sort_values("Date", ascending=False), hide_index=True)
    except: st.error("Water error.")
