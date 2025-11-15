import pandas as pd
import plotly.express as px
import streamlit as st

st.title("Cloud Cost and Tagging Analysis Dashboard")

# Read the CSV file properly with correct separator and quote handling
try:
    # First, try reading with standard settings
    df = pd.read_csv(r"cloudmart_multi_account.csv", sep=',', quotechar='"', skipinitialspace=True)
    
    # If the header was incorrectly parsed as a single column, fix it manually
    if len(df.columns) == 1:
        st.warning("CSV has unusual formatting. Attempting to fix...")
        
        # Read the file as raw text and process it
        with open(r"cloudmart_multi_account.csv", 'r') as f:
            lines = f.readlines()
        
        # Process each line to remove surrounding quotes
        processed_lines = []
        for line in lines:
            line = line.strip()
            # Remove quotes that wrap the entire line
            if line.startswith('"') and line.endswith('"'):
                line = line[1:-1]
            processed_lines.append(line)
        
        # Create a temporary string with processed content
        from io import StringIO
        csv_string = '\n'.join(processed_lines)
        
        # Read from the processed string
        df = pd.read_csv(StringIO(csv_string), sep=',')
    
except FileNotFoundError:
    st.error("File 'cloudmart_multi_account.csv' not found. Please place it in the working directory.")
    st.stop()

# Strip whitespace from column headers and remove any quotes
df.columns = df.columns.str.strip().str.replace('"', '')

# Debug: Show what columns were detected
st.subheader("Detected Columns")
st.write(f"Number of columns: {len(df.columns)}")
st.write(f"Column names: {list(df.columns)}")
st.write(f"Column data types: {df.dtypes}")

# Display first few rows to verify correct loading
st.subheader("First 5 Rows of Dataset")
st.dataframe(df.head())

# Check for missing values
st.subheader("Missing Values per Column")
st.write(df.isnull().sum())

# Count tagged vs untagged
st.subheader("Tagged vs Untagged Resource Counts")
tagged_counts = df['Tagged'].value_counts()
st.write(tagged_counts)

# Percentage untagged
percent_untagged = (tagged_counts.get('No', 0) / len(df)) * 100
st.write(f"Percentage of Untagged Resources: {percent_untagged:.2f}%")

# Cost visibility - total cost by tag
cost_by_tag = df.groupby('Tagged')['MonthlyCostUSD'].sum()
total_cost = df['MonthlyCostUSD'].sum()
untagged_cost = cost_by_tag.get('No', 0)
percent_untagged_cost = (untagged_cost / total_cost) * 100

st.subheader("Cost by Tagging Status")
st.write(cost_by_tag)
st.write(f"Percentage of Total Cost that is Untagged: {percent_untagged_cost:.2f}%")

# Department with highest untagged cost
untagged_dept_cost = df[df['Tagged'] == 'No'].groupby('Department')['MonthlyCostUSD'].sum()
dept_most_untagged_cost = untagged_dept_cost.idxmax() if not untagged_dept_cost.empty else "N/A"
st.write(f"Department with Most Untagged Cost: {dept_most_untagged_cost}")

# Project consuming most cost
project_cost = df.groupby('Project')['MonthlyCostUSD'].sum()
project_most_cost = project_cost.idxmax() if not project_cost.empty else "N/A"
st.write(f"Project with Highest Total Cost: {project_most_cost}")

# Environments cost and tagging quality
env_tag_summary = df.groupby(['Environment', 'Tagged'])['MonthlyCostUSD'].sum()
st.subheader("Cost by Environment and Tagging Status")
st.write(env_tag_summary)

# Tag completeness score
tag_fields = ['Department', 'Project', 'Owner', 'CostCenter']
df['TagCompletenessScore'] = df[tag_fields].notnull().sum(axis=1)

st.subheader("Top 5 Resources with Lowest Tag Completeness Score")
st.dataframe(df.nsmallest(5, 'TagCompletenessScore'))

# Most frequently missing tag fields
missing_by_tag = df[tag_fields].isnull().sum()
st.subheader("Missing Tags Frequency")
st.write(missing_by_tag)

# List untagged resources with costs
untagged_resources = df[df['Tagged'] == 'No'][['ResourceID', 'MonthlyCostUSD']]
st.subheader("Untagged Resources and Costs")
st.dataframe(untagged_resources)

# Export untagged resources CSV for download
st.download_button("Download Untagged Resources CSV", 
                   data=untagged_resources.to_csv(index=False), 
                   file_name="untagged_resources.csv", 
                   mime="text/csv")

# Visualization dashboard
fig_pie = px.pie(df, names='Tagged', title="Tagged vs Untagged Resources")
st.plotly_chart(fig_pie)

fig_bar_dept = px.bar(df, x='Department', y='MonthlyCostUSD', color='Tagged', barmode='group',
                      title="Cost per Department by Tagging Status")
st.plotly_chart(fig_bar_dept)

cost_per_service = df.groupby('Service')['MonthlyCostUSD'].sum().reset_index()
fig_bar_service = px.bar(cost_per_service, x='MonthlyCostUSD', y='Service', orientation='h',
                         title="Total Cost per Service")
st.plotly_chart(fig_bar_service)

env_cost = df.groupby('Environment')['MonthlyCostUSD'].sum().reset_index()
fig_pie_env = px.pie(env_cost, names='Environment', values='MonthlyCostUSD', title="Cost by Environment")
st.plotly_chart(fig_pie_env)

# Interactive filters
st.subheader("Filter Data")
selected_service = st.selectbox("Select Service", options=["All"] + sorted(df['Service'].dropna().unique().tolist()))
selected_region = st.multiselect("Select Region(s)", options=sorted(df['Region'].dropna().unique().tolist()))
selected_department = st.multiselect("Select Department(s)", options=sorted(df['Department'].dropna().unique().tolist()))

filtered_df = df.copy()
if selected_service != "All":
    filtered_df = filtered_df[filtered_df['Service'] == selected_service]
if selected_region:
    filtered_df = filtered_df[filtered_df['Region'].isin(selected_region)]
if selected_department:
    filtered_df = filtered_df[filtered_df['Department'].isin(selected_department)]

st.write(f"Filtered Data: {len(filtered_df)} resources")
st.dataframe(filtered_df.head(10))

# Tag remediation workflow
st.subheader("Tag Remediation Editor for Untagged Resources")
untagged_df = df[df['Tagged'] == 'No'].copy()

if not untagged_df.empty:
    edited_df = st.data_editor(untagged_df, num_rows="dynamic")

    if st.button("Download Remediated Dataset"):
        tagged_df = df[df['Tagged'] == 'Yes']
        combined_df = pd.concat([tagged_df, edited_df], ignore_index=True)
        csv = combined_df.to_csv(index=False)
        st.download_button("Download CSV", data=csv, file_name="remediated_cloud_costs.csv", mime="text/csv")

    edited_df['Tagged'] = edited_df[tag_fields].notnull().all(axis=1).map({True: 'Yes', False: 'No'})
    updated_df = pd.concat([df[df['Tagged'] == 'Yes'], edited_df], ignore_index=True)

    st.write("Cost Summary After Remediation")
    updated_cost_by_tag = updated_df.groupby('Tagged')['MonthlyCostUSD'].sum()
    st.write(updated_cost_by_tag)

    total_updated_cost = updated_df['MonthlyCostUSD'].sum()
    updated_untagged_cost = updated_cost_by_tag.get('No', 0)
    updated_percent_untagged_cost = (updated_untagged_cost / total_updated_cost) * 100
    st.write(f"Percentage of Untagged Cost After Remediation: {updated_percent_untagged_cost:.2f}%")
else:
    st.info("No untagged resources found.")

# Reflection on improved tagging
st.subheader("Reflection on Tagging Improvements")
st.write("""
Improved tagging enhances financial accountability by enabling precise cost allocation to departments, projects, and owners.
This leads to better budget management, reduced orphan costs, and cleaner reporting.
Tag remediation workflows support ongoing governance and cloud cost optimization strategies.
""")