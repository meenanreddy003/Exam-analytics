import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Set page layout
st.set_page_config(page_title="Data Analyzer", layout="wide")

st.title("Comprehensive Data Analyzer")

# 1. File Uploader accepting CSV and Excel
uploaded_file = st.file_uploader("Upload a CSV or Excel dataset to begin", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    # Read CSV or Excel depending on the file extension
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
        
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Rest of your app logic follows...

    # 2. Basic Profiling
    st.header("1. Data Overview")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Rows:** {df.shape[0]}")
        st.write(f"**Columns:** {df.shape[1]}")
    with col2:
        st.write("**Missing Values:**")
        missing = df.isnull().sum()
        st.dataframe(missing[missing > 0] if missing.sum() > 0 else "No missing values!")
        
    st.write("**Raw Data Preview:**")
    st.dataframe(df.head())
    
    # 3. Statistical Summary
    st.header("2. Numerical Summary")
    st.dataframe(df.describe())
    
    # 4. Univariate Analysis (Distributions)
    st.header("3. Distributions")
    if num_cols:
        selected_col = st.selectbox("Select a numerical column to visualize:", num_cols)
        
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.histplot(df[selected_col], kde=True, ax=ax)
        st.pyplot(fig)
    else:
        st.warning("No numerical columns found to plot.")
        
    # 5. Bivariate Analysis (Correlation)
    st.header("4. Correlation Heatmap")
    if len(num_cols) > 1:
        fig, ax = plt.subplots(figsize=(10, 8))
        corr = df[num_cols].corr()
        sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", ax=ax)
        st.pyplot(fig)
    else:
        st.warning("Need at least two numerical columns for correlation.")

else:
    st.info("Waiting for file upload...")
    
