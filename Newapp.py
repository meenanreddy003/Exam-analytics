import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import StandardScaler, LabelEncoder
import warnings
warnings.filterwarnings('ignore')

class ComprehensiveDataAnalyzer:
    def __init__(self, dataframe):
        """Initialize with a pandas DataFrame."""
        self.df = dataframe.copy()
        self.num_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        self.cat_cols = self.df.select_dtypes(include=['object', 'category']).columns.tolist()

    def basic_profiling(self):
        """1. Structural and Statistical Summary"""
        print("--- SHAPE & DATA TYPES ---")
        print(f"Rows: {self.df.shape[0]}, Columns: {self.df.shape[1]}\n")
        print(self.df.info())
        
        print("\n--- MISSING VALUES ---")
        missing = self.df.isnull().sum()
        print(missing[missing > 0])
        
        print("\n--- NUMERICAL SUMMARY ---")
        display(self.df.describe().T)
        
        print("\n--- CATEGORICAL SUMMARY ---")
        if self.cat_cols:
            display(self.df.describe(include=['object', 'category']).T)

    def univariate_analysis(self):
        """2. Analyze individual variables (Distributions & Frequencies)"""
        # Numerical Distributions
        if self.num_cols:
            fig = plt.figure(figsize=(15, len(self.num_cols) * 4))
            for i, col in enumerate(self.num_cols):
                plt.subplot(len(self.num_cols), 2, 2*i + 1)
                sns.histplot(self.df[col], kde=True, bins=30)
                plt.title(f'Distribution of {col}')
                
                plt.subplot(len(self.num_cols), 2, 2*i + 2)
                sns.boxplot(x=self.df[col])
                plt.title(f'Boxplot of {col}')
            plt.tight_layout()
            plt.show()

        # Categorical Frequencies
        if self.cat_cols:
            for col in self.cat_cols:
                plt.figure(figsize=(8, 4))
                self.df[col].value_counts().nlargest(10).plot(kind='bar', color='skyblue')
                plt.title(f'Top 10 Categories in {col}')
                plt.ylabel('Count')
                plt.show()

    def bivariate_multivariate_analysis(self):
        """3. Analyze relationships between multiple variables"""
        if len(self.num_cols) > 1:
            print("\n--- CORRELATION MATRIX ---")
            plt.figure(figsize=(10, 8))
            corr = self.df[self.num_cols].corr()
            sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", linewidths=0.5)
            plt.title('Numerical Features Correlation')
            plt.show()

            print("\n--- PAIRPLOT (Sampled for performance) ---")
            sample_df = self.df.sample(min(500, len(self.df))) # Sample to avoid crashing
            sns.pairplot(sample_df[self.num_cols])
            plt.show()

    def outlier_detection_iqr(self):
        """4. Detect outliers using the Interquartile Range (IQR) method"""
        print("\n--- OUTLIER DETECTION (IQR) ---")
        outlier_summary = {}
        for col in self.num_cols:
            Q1 = self.df[col].quantile(0.25)
            Q3 = self.df[col].quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = self.df[(self.df[col] < lower_bound) | (self.df[col] > upper_bound)]
            outlier_summary[col] = len(outliers)
            
        print(pd.Series(outlier_summary, name="Outlier Count").to_frame())

    def basic_preprocessing(self):
        """5. Basic data cleaning and preparation"""
        cleaned_df = self.df.copy()
        
        # Fill missing values: Median for numerical, Mode for categorical
        for col in self.num_cols:
            cleaned_df[col].fillna(cleaned_df[col].median(), inplace=True)
        for col in self.cat_cols:
            cleaned_df[col].fillna(cleaned_df[col].mode()[0], inplace=True)
            
        # Label Encoding for categoricals
        le = LabelEncoder()
        for col in self.cat_cols:
            cleaned_df[col] = le.fit_transform(cleaned_df[col].astype(str))
            
        # Scale numericals
        scaler = StandardScaler()
        cleaned_df[self.num_cols] = scaler.fit_transform(cleaned_df[self.num_cols])
        
        print("\n--- PREPROCESSING COMPLETE ---")
        print("Missing values imputed, categoricals encoded, numericals scaled.")
        return cleaned_df

    def run_all(self):
        """Execute the full analysis pipeline"""
        self.basic_profiling()
        self.univariate_analysis()
        self.bivariate_multivariate_analysis()
        self.outlier_detection_iqr()
        return self.basic_preprocessing()

# ==========================================
# HOW TO USE IT:
# ==========================================
# df = pd.read_csv('your_data.csv')
# analyzer = ComprehensiveDataAnalyzer(df)
# processed_data = analyzer.run_all()
