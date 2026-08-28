import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# Page Configuration
st.set_page_config(
    page_title="Student Performance & Exam Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Student Performance & Exam Analytics Dashboard")
st.markdown("Upload one or multiple exam Excel reports to analyze student performance, subject-wise averages, and overall rankings.")

# Helper to find specific total marks column while excluding subject total columns
def find_total_column(columns):
    # Priority 1: Exact matches for grand total
    priority_1 = ['TOTAL MARKS', 'GRAND TOTAL', 'TOTAL SCORE', 'OVERALL TOTAL', 'TOTAL']
    for col in columns:
        col_clean = str(col).upper().replace("_", " ").strip()
        if any(kw == col_clean for kw in priority_1):
            return col

    # Priority 2: Contains TOTAL or SCORE but excludes subject names
    subjects = ['PHYSIC', 'CHEMIST', 'MATH', 'BOTANY', 'ZOOLOGY', 'BIO']
    for col in columns:
        col_clean = str(col).upper().replace("_", " ").strip()
        if ('TOTAL' in col_clean or 'SCORE' in col_clean) and not any(s in col_clean for s in subjects):
            return col

    # Priority 3: Fallback 'MARKS' without subject names
    for col in columns:
        col_clean = str(col).upper().replace("_", " ").strip()
        if 'MARKS' in col_clean and not any(s in col_clean for s in subjects):
            return col
            
    return None

def find_name_column(columns):
    name_keywords = ['STUDENT NAME', 'CANDIDATE NAME', 'STUDENT', 'NAME']
    for kw in name_keywords:
        for col in columns:
            if kw == str(col).upper().replace("_", " ").strip():
                return col
    for col in columns:
        col_clean = str(col).upper()
        if 'NAME' in col_clean or 'STUDENT' in col_clean:
            return col
    return None

def find_rank_column(columns):
    for col in columns:
        col_clean = str(col).upper().replace("_", " ").strip()
        if 'RANK' in col_clean and 'AIR' not in col_clean:
            return col
    return None

def clean_subject_name(col_name):
    clean = str(col_name).replace("_", " ").strip()
    for w in [" Marks", " MARKS", " Total", " TOTAL", " Score", " SCORE"]:
        clean = clean.replace(w, "")
    return clean.strip().title()

def extract_subject_columns(df, name_col, total_col, rank_col):
    ignore_keywords = ['OMR', 'RANK', 'SL', 'S.NO', 'SNO', 'TOTAL', 'PERCENT', 'ATTENDANCE', 'ROLL', 'MOBILE', 'PHONE', 'DOB', 'SECTION']
    subject_cols = []
    for col in df.columns:
        if col in [name_col, total_col, rank_col]:
            continue
        col_u = str(col).upper()
        if any(ig in col_u for ig in ignore_keywords):
            continue
        if pd.api.types.is_numeric_dtype(df[col]) or pd.to_numeric(df[col], errors='coerce').notna().sum() > 0:
            subject_cols.append(col)
    return subject_cols

def parse_exam_file(file):
    excel_file = pd.ExcelFile(file)
    df_raw = pd.read_excel(excel_file, sheet_name=0, header=None)
    
    header_idx = 0
    for idx, row in df_raw.iterrows():
        row_str = [str(val).upper().strip() for val in row.values]
        if any("STUDENT" in s or "OMR" in s or "NAME" in s for s in row_str):
            header_idx = idx
            break
            
    df = pd.read_excel(excel_file, sheet_name=0, header=header_idx)
    df.columns = [str(c).strip() for c in df.columns]
    
    numeric_keywords = ['marks', 'rank', 'correct', 'incorrect', 'unattended', 'score', 'total']
    for col in df.columns:
        if any(kw in col.lower() for kw in numeric_keywords):
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

def aggregate_multi_exam_data(exam_data):
    records = []
    
    for exam_name, df in exam_data.items():
        name_col = find_name_column(df.columns)
        total_col = find_total_column(df.columns)
        rank_col = find_rank_column(df.columns)
        subject_cols = extract_subject_columns(df, name_col, total_col, rank_col)
        
        if name_col and total_col:
            for _, row in df.iterrows():
                raw_name = str(row[name_col]).strip()
                if not raw_name or raw_name.upper() in ['NAN', 'NONE', '']:
                    continue
                
                tot_val = pd.to_numeric(row[total_col], errors='coerce')
                if pd.isna(tot_val):
                    continue
                    
                entry = {
                    'STUDENT NAME': raw_name.upper(),
                    'Exam': exam_name,
                    'Total Marks': float(tot_val)
                }
                
                for sc in subject_cols:
                    s_clean = clean_subject_name(sc)
                    val = pd.to_numeric(row[sc], errors='coerce')
                    entry[s_clean] = float(val) if pd.notna(val) else np.nan
                    
                records.append(entry)
                
    if not records:
        return None, None
        
    flat_df = pd.DataFrame(records)
    subject_names = [c for c in flat_df.columns if c not in ['STUDENT NAME', 'Exam', 'Total Marks']]
    
    # Aggregating Average Total Marks & Subject Averages across all exams
    agg_dict = {'Total Marks': ['count', 'mean']}
    for sub in subject_names:
        agg_dict[sub] = 'mean'
        
    summary = flat_df.groupby('STUDENT NAME').agg(agg_dict)
    
    summary.columns = [
        'Exams Taken' if col == ('Total Marks', 'count') else
        'Avg Total Marks' if col == ('Total Marks', 'mean') else
        f'Avg {col[0]}' for col in summary.columns
    ]
    
    summary = summary.reset_index()
    summary['Avg Total Marks'] = summary['Avg Total Marks'].round(2)
    for sub in subject_names:
        summary[f'Avg {sub}'] = summary[f'Avg {sub}'].round(2)
        
    # Rank directly based on Avg Total Marks descending
    summary['Overall Rank'] = summary['Avg Total Marks'].rank(ascending=False, method='min').astype(int)
    summary = summary.sort_values(by='Overall Rank', ascending=True).reset_index(drop=True)
    
    subj_avg_cols = [f'Avg {sub}' for sub in subject_names]
    ordered_cols = ['Overall Rank', 'STUDENT NAME', 'Avg Total Marks'] + subj_avg_cols + ['Exams Taken']
    
    return summary[ordered_cols], flat_df

# Sidebar
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
        summary_df, flat_df = aggregate_multi_exam_data(exam_data)

        tab1, tab2, tab3, tab4 = st.tabs([
            "📌 Single Exam Overview", 
            "🏆 Overall Leaderboard", 
            "📚 Subject-Wise Analytics",
            "📈 Multi-Exam Drop Tracker"
        ])

        # TAB 1: Single Exam Overview (Includes Single-Exam Subject Averages)
        with tab1:
            selected_exam_name = st.selectbox("Select Exam to Analyze:", list(exam_data.keys()))
            df_exam = exam_data[selected_exam_name]

            total_students = len(df_exam)
            name_col = find_name_column(df_exam.columns)
            total_marks_col = find_total_column(df_exam.columns)
            rank_col = find_rank_column(df_exam.columns)
            subject_cols = extract_subject_columns(df_exam, name_col, total_marks_col, rank_col)

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Students", total_students)
            if total_marks_col and not df_exam[total_marks_col].dropna().empty:
                col2.metric("Class Average Marks", f"{df_exam[total_marks_col].mean():.2f}")
                col3.metric("Highest Total Score", f"{df_exam[total_marks_col].max():.2f}")

            st.markdown("---")
            
            # Subject-Wise Averages Section for the Single Exam
            st.subheader("📊 Subject Performance Averages (Selected Exam)")
            if subject_cols:
                subj_avg_dict = {}
                for sc in subject_cols:
                    clean_s = clean_subject_name(sc)
                    mean_val = df_exam[sc].mean()
                    max_val = df_exam[sc].max()
                    min_val = df_exam[sc].min()
                    subj_avg_dict[clean_s] = {
                        "Subject Average": round(mean_val, 2),
                        "Highest Score": round(max_val, 2) if pd.notna(max_val) else "-",
                        "Lowest Score": round(min_val, 2) if pd.notna(min_val) else "-"
                    }
                
                subj_df = pd.DataFrame(subj_avg_dict).T
                st.dataframe(subj_df, use_container_width=True)

                fig_subj = px.bar(
                    subj_df.reset_index().rename(columns={"index": "Subject"}), 
                    x="Subject", 
                    y="Subject Average", 
                    title="Average Marks per Subject", 
                    color="Subject",
                    text_auto=True
                )
                st.plotly_chart(fig_subj, use_container_width=True)
            else:
                st.info("No individual subject columns detected.")

            st.markdown("---")

            # Bottom Performers
            st.subheader("🚨 Bottom Performers Attention List")
            slider_max = max(5, total_students)
            default_val = min(10, total_students)
            bottom_cutoff = st.slider("Select Bottom N Students to Display:", 1, slider_max, default_val)
            
            if total_marks_col:
                df_sorted = df_exam.sort_values(by=total_marks_col, ascending=True).head(bottom_cutoff)
                cols_to_show = [c for c in [rank_col, name_col, total_marks_col] if c and c in df_exam.columns]
                cols_to_show.extend(subject_cols)
                st.dataframe(df_sorted[cols_to_show].reset_index(drop=True), use_container_width=True)

            # Score Distribution
            if total_marks_col:
                st.subheader("📈 Score Distribution")
                fig_dist = px.histogram(df_exam, x=total_marks_col, nbins=20, title="Total Marks Distribution", color_discrete_sequence=['#3366cc'])
                st.plotly_chart(fig_dist, use_container_width=True)

        # TAB 2: Overall Leaderboard (Ranked by Average Total Marks)
        with tab2:
            st.subheader("🏆 Overall Leaderboard (Ranked by Average Total Marks)")
            st.markdown("Students are ranked based on their **Average Total Marks** calculated across all uploaded exams.")

            if summary_df is not None and not summary_df.empty:
                max_exams = int(summary_df['Exams Taken'].max())
                if max_exams > 1:
                    min_exams = st.slider("Filter students taking at least N exams:", 1, max_exams, 1)
                else:
                    min_exams = 1

                filtered_summary = summary_df[summary_df['Exams Taken'] >= min_exams]

                st.dataframe(
                    filtered_summary,
                    column_config={
                        "Overall Rank": st.column_config.NumberColumn("Overall Rank 🏆"),
                        "Avg Total Marks": st.column_config.NumberColumn("Avg Total Marks 📊", format="%.2f"),
                        "Exams Taken": st.column_config.NumberColumn("Exams Taken 📝")
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("Could not compute overall leaderboard. Please ensure 'STUDENT NAME' and 'TOTAL MARKS' columns exist.")

        # TAB 3: Separate Tabs for Subject-Wise Averages Across All Exams
        with tab3:
            st.subheader("📚 Subject-Wise Multi-Exam Performance & Rankings")
            
            if flat_df is not None and not flat_df.empty:
                subjects = [c for c in flat_df.columns if c not in ['STUDENT NAME', 'Exam', 'Total Marks']]
                
                if subjects:
                    subj_tabs = st.tabs([f"📖 {s}" for s in subjects])
                    
                    for idx, subject in enumerate(subjects):
                        with subj_tabs[idx]:
                            st.subheader(f"{subject} Detailed Analysis")
                            sub_df = flat_df.dropna(subset=[subject]).copy()
                            
                            if not sub_df.empty:
                                subj_summary = sub_df.groupby('STUDENT NAME').agg(
                                    Avg_Score=(subject, 'mean'),
                                    Highest_Score=(subject, 'max'),
                                    Lowest_Score=(subject, 'min'),
                                    Exams_Evaluated=('Exam', 'count')
                                ).reset_index()

                                subj_summary['Avg_Score'] = subj_summary['Avg_Score'].round(2)
                                subj_summary[f'{subject} Rank'] = subj_summary['Avg_Score'].rank(ascending=False, method='min').astype(int)
                                subj_summary = subj_summary.sort_values(by=f'{subject} Rank', ascending=True).reset_index(drop=True)

                                subj_summary = subj_summary.rename(columns={
                                    'Avg_Score': f'Avg {subject} Marks',
                                    'Highest_Score': f'Max {subject} Score',
                                    'Lowest_Score': f'Min {subject} Score'
                                })

                                c1, c2, c3 = st.columns(3)
                                c1.metric(f"Overall Class {subject} Avg", f"{sub_df[subject].mean():.2f}")
                                c2.metric(f"Top {subject} Score", f"{sub_df[subject].max():.2f}")
                                c3.metric(f"Lowest {subject} Score", f"{sub_df[subject].min():.2f}")

                                st.markdown(f"### 🏅 {subject} Subject Leaderboard")
                                st.dataframe(
                                    subj_summary[[f'{subject} Rank', 'STUDENT NAME', f'Avg {subject} Marks', f'Max {subject} Score', f'Min {subject} Score', 'Exams_Evaluated']],
                                    use_container_width=True,
                                    hide_index=True
                                )

                                fig_sub_dist = px.histogram(sub_df, x=subject, nbins=15, title=f"{subject} Marks Distribution Across Exams")
                                st.plotly_chart(fig_sub_dist, use_container_width=True)
                            else:
                                st.info(f"No score data available for {subject}.")
                else:
                    st.info("No subject-specific columns found across uploaded exam files.")

        # TAB 4: Multi-Exam Drop Tracker
        with tab4:
            if len(exam_data) < 2:
                st.info("ℹ️ Upload **two or more exam reports** to enable multi-exam drop tracking.")
            else:
                st.subheader("📉 Performance Drop Tracker")
                file_names = list(exam_data.keys())
                e1 = st.selectbox("Baseline Exam (e.g. Test 1):", file_names, index=0)
                e2 = st.selectbox("Comparison Exam (e.g. Test 2):", file_names, index=min(1, len(file_names)-1))

                df1 = exam_data[e1].copy()
                df2 = exam_data[e2].copy()

                name1 = find_name_column(df1.columns)
                name2 = find_name_column(df2.columns)
                tot1 = find_total_column(df1.columns)
                tot2 = find_total_column(df2.columns)

                if name1 and name2 and tot1 and tot2:
                    df1[name1] = df1[name1].astype(str).str.strip().str.upper()
                    df2[name2] = df2[name2].astype(str).str.strip().str.upper()

                    merged = pd.merge(
                        df1[[name1, tot1]], 
                        df2[[name2, tot2]], 
                        left_on=name1, 
                        right_on=name2, 
                        suffixes=('_Baseline', '_Comparison')
                    )

                    merged['Score Shift'] = merged[tot2] - merged[tot1]
                    drop_thresh = st.number_input("Threshold for Score Drop (Marks):", min_value=1, max_value=100, value=15)
                    
                    drops = merged[merged['Score Shift'] <= -drop_thresh].sort_values(by='Score Shift', ascending=True)

                    st.markdown(f"**Students with Score Drop ≥ {drop_thresh} Marks:**")
                    st.dataframe(
                        drops.rename(columns={name1: 'Student Name', tot1: f'Baseline ({e1})', tot2: f'Comparison ({e2})'}),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.warning("Could not match student name and total marks columns for comparison.")
                  
