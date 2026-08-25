import streamlit as st
import pandas as pd
import plotly.express as px
from functools import reduce

# Page Configuration
st.set_page_config(
    page_title="Student Performance & Exam Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Student Performance & Exam Analytics Dashboard")
st.markdown("Upload one or multiple exam Excel reports to instantly analyze student performance, track average rankings, and identify trend shifts.")
# Helper function to parse exam Excel sheets
def parse_exam_file(file):
    excel_file = pd.ExcelFile(file)
    
    # Read the raw file with NO headers to find the exact row index
    df_raw = pd.read_excel(excel_file, sheet_name=0, header=None)
    
    header_idx = 0
    # Scan every row until we find the column names
    for idx, row in df_raw.iterrows():
        # Convert row values to uppercase strings for safe matching
        row_str = [str(val).upper().strip() for val in row.values]
        if "STUDENT NAME" in row_str or "OMR NUMBER" in row_str:
            header_idx = idx
            break
            
    # Re-read the file using the correctly identified row as the header
    df = pd.read_excel(excel_file, sheet_name=0, header=header_idx)
    
    # Clean up column names (remove extra spaces)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Convert score/rank columns to numbers so we can do math on them
    numeric_keywords = ['Marks', 'Rank', 'Correct', 'Incorrect', 'Unattended']
    for col in df.columns:
        if any(kw.lower() in col.lower() for kw in numeric_keywords):
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df
    

# Calculate average student rankings across all uploaded exams
def calculate_average_rankings(exam_data):
    rank_dfs = []
    
    for exam_name, df in exam_data.items():
        # Identify student name and rank columns
        name_col = next((c for c in df.columns if 'STUDENT NAME' in c.upper()), None)
        rank_col = next((c for c in df.columns if 'RANK' in c.upper()), None)
        
        if name_col and rank_col:
            temp_df = df[[name_col, rank_col]].dropna(subset=[name_col]).copy()
            # Clean up student names for consistent merging
            temp_df[name_col] = temp_df[name_col].astype(str).str.strip().str.upper()
            temp_df.columns = ['STUDENT NAME', f'Rank ({exam_name})']
            rank_dfs.append(temp_df)
            
    if not rank_dfs:
        return None
        
    # Merge all exam rankings together by student name
    merged_ranks = reduce(lambda left, right: pd.merge(left, right, on='STUDENT NAME', how='outer'), rank_dfs)
    
    # Get all individual exam rank columns
    rank_cols = [c for c in merged_ranks.columns if c.startswith('Rank (')]
    
    # Calculate key metrics
    merged_ranks['Exams Attempted'] = merged_ranks[rank_cols].notna().sum(axis=1)
    merged_ranks['Average Rank'] = merged_ranks[rank_cols].mean(axis=1).round(2)
    
    # Sort by Average Rank ascending (Rank 1 is top)
    merged_ranks = merged_ranks.sort_values(by='Average Rank', ascending=True).reset_index(drop=True)
    
    # Rearrange columns
    ordered_cols = ['STUDENT NAME', 'Average Rank', 'Exams Attempted'] + rank_cols
    return merged_ranks[ordered_cols]

# Sidebar File Uploader
st.sidebar.header("📁 File Upload")
uploaded_files = st.sidebar.file_uploader(
    "Upload Excel Exam Reports (.xlsx)", 
    type=["xlsx", "xls"], 
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("👈 Please upload one or more Excel files from the sidebar to start the analysis.")
else:
    exam_data = {}
    for file in uploaded_files:
        try:
            exam_data[file.name] = parse_exam_file(file)
        except Exception as e:
            st.error(f"Error parsing file '{file.name}': {e}")

    # Tabs for different view modes
    tab1, tab2, tab3 = st.tabs([
        "📌 Single Exam Analysis", 
        "🏆 Overall Average Rankings", 
        "📈 Multi-Exam Trend & Comparisons"
    ])

    # TAB 1: Single Exam Overview
    with tab1:
        selected_exam_name = st.selectbox("Select Exam to Analyze:", list(exam_data.keys()))
        df_exam = exam_data[selected_exam_name]

        total_students = len(df_exam)
        total_marks_col = next((c for c in df_exam.columns if 'Total Marks' in c), None)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Students Evaluated", total_students)
        if total_marks_col:
            col2.metric("Class Average Marks", f"{df_exam[total_marks_col].mean():.1f}")
            col3.metric("Highest Score", f"{df_exam[total_marks_col].max()}")

        st.markdown("---")

        # Bottom Performers
        st.subheader("🚨 Bottom Performers Attention List")
        bottom_cutoff = st.slider("Select Bottom N Students to Display:", 5, 25, 10)
        
        if total_marks_col:
            df_sorted = df_exam.sort_values(by=total_marks_col, ascending=True).head(bottom_cutoff)
            display_cols = [c for c in ['Rank', 'STUDENT NAME', total_marks_col, 'MATHEMATICS (Total Marks)', 'PHYSICS (Total Marks)', 'CHEMISTRY (Total Marks)'] if c in df_exam.columns]
            st.dataframe(df_sorted[display_cols].reset_index(drop=True), use_container_width=True)

        # Marks Distribution
        if total_marks_col:
            st.subheader("📊 Marks Distribution Across Class")
            fig_dist = px.histogram(df_exam, x=total_marks_col, nbins=20, title="Class Score Distribution", color_discrete_sequence=['#3366cc'])
            st.plotly_chart(fig_dist, use_container_width=True)
            
    # TAB 2: Average Ranking Leaderboard
    with tab2:
        st.subheader("🏆 Overall Average Rank Leaderboard")
        st.markdown("This table calculates the mean rank of each student across all uploaded exam reports (Rank 1.0 = Highest Performance).")
        
        df_avg_rank = calculate_average_rankings(exam_data)
        
        if df_avg_rank is not None and not df_avg_rank.empty:
            max_exams = int(df_avg_rank['Exams Attempted'].max())
            
            # Show the slider only if multiple exams exist
            if max_exams > 1:
                min_exams = st.slider("Filter students who took at least N exams:", 1, max_exams, 1)
            else:
                min_exams = 1
            
            filtered_rank_df = df_avg_rank[df_avg_rank['Exams Attempted'] >= min_exams]
            
            # Display Table
            st.dataframe(
                filtered_rank_df,
                column_config={
                    "Average Rank": st.column_config.NumberColumn("Average Rank 🏆", format="%.2f"),
                    "Exams Attempted": st.column_config.NumberColumn("Exams Taken 📝"),
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("Could not find 'STUDENT NAME' or 'Rank' columns across the uploaded files.")
            

    # TAB 3: Multi-Exam Comparisons & Drop Tracker
    with tab3:
        if len(exam_data) < 2:
            st.info("ℹ️ Upload **two or more exam reports** to compare trends and track performance drops.")
        else:
            st.subheader("📉 Performance Shift & Score Drop Tracker")
            
            file_names = list(exam_data.keys())
            e1 = st.selectbox("Select Baseline Exam (e.g., Test 1):", file_names, index=0)
            e2 = st.selectbox("Select Comparison Exam (e.g., Test 2):", file_names, index=min(1, len(file_names)-1))

            df1, df2 = exam_data[e1], exam_data[e2]
            
            name1 = next((c for c in df1.columns if 'STUDENT NAME' in c.upper()), 'STUDENT NAME')
            name2 = next((c for c in df2.columns if 'STUDENT NAME' in c.upper()), 'STUDENT NAME')
            
            df1[name1] = df1[name1].astype(str).str.strip().str.upper()
            df2[name2] = df2[name2].astype(str).str.strip().str.upper()

            merged = pd.merge(df1, df2, left_on=name1, right_on=name2, suffixes=('_Baseline', '_Latest'))

            m1_col = next((c for c in merged.columns if 'Total Marks' in c and '_Baseline' in c), None)
            m2_col = next((c for c in merged.columns if 'Total Marks' in c and '_Latest' in c), None)

            if m1_col and m2_col:
                merged['Marks_Change'] = merged[m2_col] - merged[m1_col]

                # Filter Major Drops
                drop_threshold = st.number_input("Filter Score Drops Greater Than (Marks):", min_value=1, max_value=100, value=15)
                df_drops = merged[merged['Marks_Change'] <= -drop_threshold].sort_values(by='Marks_Change', ascending=True)
                
                st.markdown(f"**Students with Score Drop ≥ {drop_threshold} Marks:**")
                st.dataframe(df_drops[[name1, m1_col, m2_col, 'Marks_Change']].rename(
                    columns={m1_col: 'Baseline Marks', m2_col: 'Latest Marks', 'Marks_Change': 'Score Shift'}
                ), use_container_width=True)
