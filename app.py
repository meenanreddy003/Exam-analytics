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

# Flexible helper to find matching column names ignoring case & extra characters
def find_column(columns, keywords):
    for col in columns:
        col_clean = str(col).upper().replace("_", " ").strip()
        if any(kw in col_clean for kw in keywords):
            return col
    return None

# Helper function to parse exam Excel sheets
def parse_exam_file(file):
    excel_file = pd.ExcelFile(file)
    df_raw = pd.read_excel(excel_file, sheet_name=0, header=None)
    
    # Locate header row containing 'STUDENT' or 'OMR'
    header_idx = 0
    for idx, row in df_raw.iterrows():
        row_str = [str(val).upper().strip() for val in row.values]
        if any("STUDENT" in s or "OMR" in s for s in row_str):
            header_idx = idx
            break
            
    df = pd.read_excel(excel_file, sheet_name=0, header=header_idx)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Convert mark/score/rank columns to numeric
    numeric_keywords = ['marks', 'rank', 'correct', 'incorrect', 'unattended', 'score', 'total']
    for col in df.columns:
        if any(kw in col.lower() for kw in numeric_keywords):
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

# Calculate average student rankings across all uploaded exams
def calculate_average_rankings(exam_data):
    rank_dfs = []
    
    for exam_name, df in exam_data.items():
        name_col = find_column(df.columns, ['STUDENT NAME', 'STUDENT', 'CANDIDATE NAME', 'NAME'])
        rank_col = find_column(df.columns, ['RANK', 'AIR', 'TOTAL RANK', 'OVERALL RANK'])
        
        if name_col and rank_col:
            temp_df = df[[name_col, rank_col]].dropna(subset=[name_col]).copy()
            temp_df[name_col] = temp_df[name_col].astype(str).str.strip().str.upper()
            temp_df = temp_df[temp_df[name_col] != ''] # Remove empty name strings
            temp_df.columns = ['STUDENT NAME', f'Rank ({exam_name})']
            rank_dfs.append(temp_df)
            
    if not rank_dfs:
        return None
        
    # Merge rankings outer-style across all tests
    merged_ranks = reduce(lambda left, right: pd.merge(left, right, on='STUDENT NAME', how='outer'), rank_dfs)
    
    rank_cols = [c for c in merged_ranks.columns if c.startswith('Rank (')]
    
    merged_ranks['Exams Attempted'] = merged_ranks[rank_cols].notna().sum(axis=1)
    merged_ranks['Average Rank'] = merged_ranks[rank_cols].mean(axis=1).round(2)
    
    merged_ranks = merged_ranks.sort_values(by='Average Rank', ascending=True).reset_index(drop=True)
    
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
            parsed_df = parse_exam_file(file)
            if not parsed_df.empty:
                exam_data[file.name] = parsed_df
        except Exception as e:
            st.error(f"Error parsing file '{file.name}': {e}")

    if exam_data:
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
            total_marks_col = find_column(df_exam.columns, ['TOTAL MARKS', 'TOTAL SCORE', 'TOTAL', 'MARKS'])
            name_col = find_column(df_exam.columns, ['STUDENT NAME', 'STUDENT', 'NAME'])
            rank_col = find_column(df_exam.columns, ['RANK', 'OVERALL RANK'])

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Students Evaluated", total_students)
            if total_marks_col and not df_exam[total_marks_col].dropna().empty:
                col2.metric("Class Average Marks", f"{df_exam[total_marks_col].mean():.1f}")
                col3.metric("Highest Score", f"{df_exam[total_marks_col].max()}")

            st.markdown("---")

            # Bottom Performers with dynamic slider limits
            st.subheader("🚨 Bottom Performers Attention List")
            slider_max = max(5, total_students)
            default_val = min(10, total_students)
            bottom_cutoff = st.slider("Select Bottom N Students to Display:", 1, slider_max, default_val)
            
            if total_marks_col:
                df_sorted = df_exam.sort_values(by=total_marks_col, ascending=True).head(bottom_cutoff)
                cols_to_show = [c for c in [rank_col, name_col, total_marks_col] if c and c in df_exam.columns]
                
                # Add individual subject columns if present
                subject_cols = [c for c in df_exam.columns if 'TOTAL' in c.upper() and c != total_marks_col]
                cols_to_show.extend(subject_cols)
                
                st.dataframe(df_sorted[cols_to_show].reset_index(drop=True), use_container_width=True)

            # Subject Vulnerability & Negative Marks
            st.subheader("⚠️ Subject Vulnerability & Negative Scoring")
            subj_cols = [c for c in df_exam.columns if any(s in c.upper() for s in ['MATH', 'PHYSIC', 'CHEMIST', 'BOTANY', 'ZOOLOGY']) and 'MARK' in c.upper()]
            if subj_cols:
                neg_mask = (df_exam[subj_cols] < 0).any(axis=1)
                df_neg = df_exam[neg_mask]
                if not df_neg.empty and name_col:
                    st.warning(f"Found {len(df_neg)} student(s) with negative score in one or more subjects:")
                    st.dataframe(df_neg[[name_col] + subj_cols].reset_index(drop=True), use_container_width=True)
                else:
                    st.success("No negative subject scores detected in this exam.")

            # Score Distribution
            if total_marks_col:
                st.subheader("📊 Class Marks Distribution")
                fig_dist = px.histogram(df_exam, x=total_marks_col, nbins=20, title="Marks Distribution", color_discrete_sequence=['#3366cc'])
                st.plotly_chart(fig_dist, use_container_width=True)

        # TAB 2: Average Ranking Leaderboard
        with tab2:
            st.subheader("🏆 Overall Average Rank Leaderboard")
            st.markdown("Calculates the mean rank of each student across all uploaded exam reports (Rank 1.0 = Highest Performance).")
            
            df_avg_rank = calculate_average_rankings(exam_data)
            
            if df_avg_rank is not None and not df_avg_rank.empty:
                max_exams = int(df_avg_rank['Exams Attempted'].max())
                
                if max_exams > 1:
                    min_exams = st.slider("Filter students who took at least N exams:", 1, max_exams, 1)
                else:
                    min_exams = 1
                
                filtered_rank_df = df_avg_rank[df_avg_rank['Exams Attempted'] >= min_exams]
                
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
                st.warning("Could not identify both 'STUDENT NAME' and 'RANK' columns across the uploaded files.")

        # TAB 3: Multi-Exam Comparisons & Drop Tracker
        with tab3:
            if len(exam_data) < 2:
                st.info("ℹ️ Upload **two or more exam reports** to compare trends and track performance drops.")
            else:
                st.subheader("📉 Performance Shift & Score Drop Tracker")
                
                file_names = list(exam_data.keys())
                e1 = st.selectbox("Select Baseline Exam (e.g., Test 1):", file_names, index=0)
                e2 = st.selectbox("Select Comparison Exam (e.g., Test 2):", file_names, index=min(1, len(file_names)-1))

                df1 = exam_data[e1].copy()
                df2 = exam_data[e2].copy()
                
                name1 = find_column(df1.columns, ['STUDENT NAME', 'STUDENT', 'NAME'])
                name2 = find_column(df2.columns, ['STUDENT NAME', 'STUDENT', 'NAME'])
                
                if name1 and name2:
                    df1[name1] = df1[name1].astype(str).str.strip().str.upper()
                    df2[name2] = df2[name2].astype(str).str.strip().str.upper()

                    merged = pd.merge(df1, df2, left_on=name1, right_on=name2, suffixes=('_Baseline', '_Latest'))

                    m1_col = find_column(merged.columns, ['TOTAL MARKS_Baseline', 'MARKS_Baseline', 'TOTAL_Baseline'])
                    m2_col = find_column(merged.columns, ['TOTAL MARKS_Latest', 'MARKS_Latest', 'TOTAL_Latest'])

                    if m1_col and m2_col:
                        merged['Marks_Change'] = merged[m2_col] - merged[m1_col]

                        drop_threshold = st.number_input("Filter Score Drops Greater Than (Marks):", min_value=1, max_value=100, value=15)
                        df_drops = merged[merged['Marks_Change'] <= -drop_threshold].sort_values(by='Marks_Change', ascending=True)
                        
                        st.markdown(f"**Students with Score Drop ≥ {drop_threshold} Marks:**")
                        display_name = f"{name1}_Baseline" if f"{name1}_Baseline" in merged.columns else name1
                        st.dataframe(df_drops[[display_name, m1_col, m2_col, 'Marks_Change']].rename(
                            columns={display_name: 'Student Name', m1_col: 'Baseline Marks', m2_col: 'Latest Marks', 'Marks_Change': 'Score Shift'}
                        ), use_container_width=True)
                    else:
                        st.warning("Could not find matching Total Marks columns in both selected files.")
                else:
                    st.warning("Could not find Student Name columns in the selected files to perform comparison.")
                    
