import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io


# Page Configuration
st.set_page_config(
    page_title="Student Performance & Exam Analytics",
    page_icon="📊",
    layout="wide"
)


st.title("📊 Student Performance & Exam Analytics Dashboard")
st.markdown("Upload one or multiple exam Excel reports to instantly analyze student performance, identify struggling students, and track multi-exam trends.")


# Helper function to parse exam Excel sheets
def parse_exam_file(file):
    excel_file = pd.ExcelFile(file)
    df_raw = pd.read_excel(excel_file, sheet_name=0)
    
    # Locate header row containing 'STUDENT NAME' or 'OMR NUMBER'
    header_idx = 0
    for idx, row in df_raw.iterrows():
        row_str = [str(val).upper() for val in row.values]
        if any("STUDENT NAME" in s or "OMR" in s for s in row_str):
            header_idx = idx
            break
            
    df = pd.read_excel(excel_file, sheet_name=0, header=header_idx)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Clean numeric columns
    numeric_keywords = ['Marks', 'Rank', 'Correct', 'Incorrect', 'Unattended']
    for col in df.columns:
        if any(kw.lower() in col.lower() for kw in numeric_keywords):
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df


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


    # Tabs for single or multi-test analysis
    tab1, tab2 = st.tabs(["📌 Exam Overview & Risk Analysis", "📈 Multi-Exam Trend & Comparative Analysis"])


    with tab1:
        selected_exam_name = st.selectbox("Select Exam to Analyze:", list(exam_data.keys()))
        df_exam = exam_data[selected_exam_name]


        # Key Metrics
        total_students = len(df_exam)
        total_marks_col = [c for c in df_exam.columns if 'Total Marks' in c][0] if any('Total Marks' in c for c in df_exam.columns) else None
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Students Evaluated", total_students)
        if total_marks_col:
            avg_score = df_exam[total_marks_col].mean()
            max_score = df_exam[total_marks_col].max()
            below_40pct = (df_exam[total_marks_col] < 120).sum() # Assuming 120/300 (40%)
            col2.metric("Class Average Marks", f"{avg_score:.1f}")
            col3.metric("Highest Score", f"{max_score}")
            col4.metric("Students Below 40%", f"{below_40pct}")


        st.markdown("---")


        # 1. High Priority Attention List
        st.subheader("🚨 High Priority Attention Needed (Bottom Performers)")
        bottom_cutoff = st.slider("Select Bottom N Students to Display:", 5, 25, 10)
        
        if total_marks_col:
            df_sorted = df_exam.sort_values(by=total_marks_col, ascending=True).head(bottom_cutoff)
            display_cols = [c for c in ['Rank', 'STUDENT NAME', total_marks_col, 'MATHEMATICS (Total Marks)', 'PHYSICS (Total Marks)', 'CHEMISTRY (Total Marks)'] if c in df_exam.columns]
            st.dataframe(df_sorted[display_cols].reset_index(drop=True), use_container_width=True)


        # 2. Subject Weakness & Negative Marking
        st.subheader("⚠️ Negative Marking & Subject Vulnerability")
        subj_cols = [c for c in df_exam.columns if 'Total Marks' in c and c != total_marks_col]
        
        if subj_cols:
            neg_conditions = [df_exam[sc] < 0 for sc in subj_cols]
            combined_neg = neg_conditions[0]
            for cond in neg_conditions[1:]:
                combined_neg = combined_neg | cond
            
            df_negatives = df_exam[combined_neg]
            if not df_negatives.empty:
                st.warning(f"Found {len(df_negatives)} student(s) with negative marks in one or more subjects:")
                st.dataframe(df_negatives[['STUDENT NAME'] + subj_cols].reset_index(drop=True), use_container_width=True)
            else:
                st.success("No negative subject marks recorded in this exam.")


        # 3. Class Score Distribution
        if total_marks_col:
            st.subheader("📊 Marks Distribution Across Class")
            fig_dist = px.histogram(df_exam, x=total_marks_col, nbins=20, title="Class Score Distribution", color_discrete_sequence=['#3366cc'])
            st.plotly_chart(fig_dist, use_container_width=True)


    with tab2:
        if len(exam_data) < 2:
            st.info("ℹ️ Upload **two or more exam reports** to unlock comparative trends and performance drop tracking.")
        else:
            st.subheader("📉 Multi-Exam Comparative Analytics")
            
            # Select 2 exams to compare
            file_names = list(exam_data.keys())
            e1 = st.selectbox("Select Baseline Exam (e.g., Exam 1 / PTM-2):", file_names, index=0)
            e2 = st.selectbox("Select Latest Exam (e.g., Exam 2 / PTM-3):", file_names, index=min(1, len(file_names)-1))


            df1 = exam_data[e1]
            df2 = exam_data[e2]


            # Merge on OMR NUMBER or STUDENT NAME
            merge_key = 'OMR NUMBER' if 'OMR NUMBER' in df1.columns and 'OMR NUMBER' in df2.columns else 'STUDENT NAME'
            merged = pd.merge(df1, df2, on=merge_key, suffixes=('_Baseline', '_Latest'))


            name_col = 'STUDENT NAME_Latest' if 'STUDENT NAME_Latest' in merged.columns else 'STUDENT NAME'
            m1_col = [c for c in merged.columns if 'Total Marks' in c and '_Baseline' in c][0]
            m2_col = [c for c in merged.columns if 'Total Marks' in c and '_Latest' in c][0]


            merged['Marks_Change'] = merged[m2_col] - merged[m1_col]


            # Major Drops Table
            st.markdown("**Major Score Declines (Performance Drops)**")
            drop_threshold = st.number_input("Filter Drops Greater Than (Marks):", min_value=5, max_value=100, value=20)
            
            df_drops = merged[merged['Marks_Change'] <= -drop_threshold].sort_values(by='Marks_Change', ascending=True)
            
            drop_display_cols = [merge_key, name_col, m1_col, m2_col, 'Marks_Change']
            st.dataframe(df_drops[drop_display_cols].rename(columns={m1_col: 'Baseline Marks', m2_col: 'Latest Marks', 'Marks_Change': 'Score Shift'}), use_container_width=True)


            # Scatter Plot: Baseline vs Latest
            fig_scatter = px.scatter(
                merged, x=m1_col, y=m2_col, hover_data=[name_col],
                labels={m1_col: "Baseline Exam Marks", m2_col: "Latest Exam Marks"},
                title="Student Movement: Baseline vs Latest Exam"
            )
            fig_scatter.add_shape(type="line", x0=0, y0=0, x1=300, y1=300, line=dict(color="Red", dash="dash"))
            st.plotly_chart(fig_scatter, use_container_width=True)