
import streamlit as st
import pandas as pd
import joblib
import os
import altair as alt # Added Altair import

# Load the saved data and models
@st.cache_data
def load_data():
    df_predictions = pd.read_csv('predicted_salaries_50th_percentile.csv')
    return df_predictions

@st.cache_resource
def load_models():
    le = joblib.load('label_encoder.joblib')
    model = joblib.load('random_forest_model.joblib')
    return le, model

# Load data and models
df_predictions = load_data()
le, model = load_models()

# Streamlit App Title
st.title('Predicted Salary Comparison Tool')

# Get unique school names for selection
available_schools = sorted(df_predictions['LABEL_INSTITUTION'].unique())

# School selection widgets
st.subheader('Select Schools for Comparison')

# Text input for searching schools
search_query = st.text_input('Search for a school (e.g., "University of")')

# Filter available schools based on search query
if search_query:
    filtered_schools = [s for s in available_schools if search_query.lower() in s.lower()]
else:
    filtered_schools = available_schools

# Multiselect for primary and comparison schools
# Ensure that the options are from the filtered schools
selected_schools = st.multiselect(
    'Choose up to 3 schools:',
    options=filtered_schools,
    default=[],
    max_selections=3
)

# Validation for unique selections
if len(selected_schools) > len(set(selected_schools)):
    st.warning('Duplicate schools selected! Please choose unique schools.')
    selected_schools = list(set(selected_schools)) # This will remove duplicates but won't update the widget directly until rerun

# Year selection widget
st.subheader('Select Year for Comparison')
selected_year = st.selectbox(
    'Choose a year after graduation:',
    options=[1, 5, 10],
    index=2 # Default to 10 years
)

# Filter and retrieve predicted salaries
if selected_schools:
    filtered_predictions = df_predictions[
        (df_predictions['LABEL_INSTITUTION'].isin(selected_schools)) &
        (df_predictions['Year'] == selected_year)
    ]

    # Sort by Predicted_Salary in descending order for ranking
    filtered_predictions = filtered_predictions.sort_values(by='Predicted_Salary', ascending=False)

    # Display predicted salaries in a table
    st.subheader(f'Predicted Salaries for Year {selected_year}')
    st.dataframe(filtered_predictions[['LABEL_INSTITUTION', 'Predicted_Salary']].reset_index(drop=True))

    # Create and display Altair bar chart
    chart = alt.Chart(filtered_predictions).mark_bar().encode(
        x=alt.X('Predicted_Salary', title='Predicted Salary'),
        y=alt.Y('LABEL_INSTITUTION', sort='-x', title='Institution'),
        tooltip=['LABEL_INSTITUTION', alt.Tooltip('Predicted_Salary', format='$,.2f')]
    ).properties(
        title=f'Predicted Salary Comparison (Year {selected_year})'
    )
    st.altair_chart(chart, use_container_width=True)
else:
    st.info('Please select at least one school to see predictions.')
