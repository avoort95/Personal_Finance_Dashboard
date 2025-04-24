import streamlit as st
import plotly.express as px
import pandas as pd
import json
import os
import numpy as np

st.set_page_config(page_title='Personal Finance App', page_icon='💰💳💲', layout='wide')

category_file = 'categories.json'

if "categories" not in st.session_state:
    st.session_state["categories"] = {'Uncategorized': []}

if os.path.exists(category_file):
    with open(category_file, 'r') as f:
        st.session_state['categories'] = json.load(f)

def save_categories():
    with open(category_file, 'w') as f:
        json.dump(st.session_state.categories, f)

def categorize_transaction(df):
    df['Category'] = 'Uncategorized'

    for category, keywords in st.session_state.categories.items():
        if category == 'Uncategorized' or not keywords:
            continue

        lowered_keywords = [keyword.lower() for keyword in keywords]

        for idx, row in df.iterrows():
            details = row[['Details', 'Details4', 'Details5', 'Details6']].astype(
                str).str.lower().tolist()
            if any(keyword in detail for detail in details for keyword in lowered_keywords):
                df.at[idx, 'Category'] = category

    return df

def load_transactions(file):
    try:
        df = pd.read_csv(file)

        df = df.drop(columns=['Rentedatum', 'Beginsaldo', 'Eindsaldo'])
        df['Transactiedatum'] = pd.to_datetime(df['Transactiedatum'], format='%Y%m%d').dt.date
        df['Type'] = np.where(df['Transactiebedrag'] > 0, 'debit', 'credit')
        df['Bedrag'] = df['Transactiebedrag'].abs()
        df.drop(columns='Transactiebedrag', inplace=True)
        df[['Details1', 'Details2', 'Details3', 'Details4', 'Details5', 'Details6', 'Details7']] = df[
            'Omschrijving'].str.split(r'\s{2,}', expand=True)
        df['Details'] = df['Details1'] + df['Details2']
        df = df.drop(columns=['Omschrijving', 'Details3', 'Details7'])

        df_categorized = categorize_transaction(df.copy())
        return df_categorized

        if df.empty:
            st.warning('The uploaded file appears to be empty')
            return None

        st.success(f"Succesfully loaded file with {len(df)} rows")
        return df

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True
    return False

def main():
    st.title('Personal Finance Dashboard VLK')
    uploaded_file = st.file_uploader('Upload your transaction CSV file', type=['csv'])
    if uploaded_file is not None:
        df = load_transactions(uploaded_file)
        if df is not None:
            st.subheader('Preview of uploaded data:')

            debit_df = df[df['Type'] == 'debit'].copy()
            credit_df = df[df['Type'] == 'credit'].copy()

            st.session_state.debit_df = debit_df.copy()
            st.session_state.credit_df = credit_df.copy()

            tab1, tab2 = st.tabs(['Bijschrijving', 'Afschrijvingen'])
            with tab1:
                new_category = st.text_input('New Category Name', key='new_category_tab1')
                add_button = st.button('Add Category', key='add_button_tab1')

                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()

                st.subheader('CashMoneyHoes')
                edited_df = st.data_editor(
                    st.session_state.debit_df[['Transactiedatum', 'Details', 'Details4', 'Details5', 'Details6', 'Bedrag', 'Category']],
                    column_config={'Category': st.column_config.SelectboxColumn(
                        'Category', options=list(st.session_state.categories.keys()))},
                    hide_index=True, use_container_width=True, key='category_editor_tab1')

                save_button = st.button('Apply Changes', type='primary', key='save_button_tab1')
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new_category = row['Category']
                        if new_category == st.session_state.debit_df.at[idx, 'Category']:
                            continue

                        details = row["Details"]
                        st.session_state.debit_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, details)

                st.subheader('Income Summary')
                total_income = debit_df['Bedrag'].sum().round(2)
                st.metric(f"Total income is: ", f"€{total_income}")

            with tab2:
                new_category = st.text_input('New Category Name', key='new_category_tab2')
                add_button = st.button('Add Category', key='add_button_tab2')

                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()

                st.subheader('MoBitchesMoProblems')
                edited_df = st.data_editor(
                    st.session_state.credit_df[['Transactiedatum', 'Details', 'Details4', 'Details5', 'Details6', 'Bedrag', 'Category']],
                    column_config={'Category': st.column_config.SelectboxColumn(
                        'Category', options=list(st.session_state.categories.keys()))},
                    hide_index=True, use_container_width=True, key='category_editor_tab2')

                save_button = st.button('Apply Changes', type='primary', key='save_button_tab2+')
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new_category = row['Category']
                        if new_category == st.session_state.credit_df.at[idx, 'Category']:
                            continue

                        details = row["Details"]
                        st.session_state.credit_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, details)

                st.subheader('Expense Summary')
                total_expenses = credit_df['Bedrag'].sum().round(2)
                st.metric(f"Total expenses are: ", f"€{total_expenses}")
                category_totals = st.session_state.credit_df.groupby('Category')['Bedrag'].sum().reset_index()
                category_totals = category_totals.sort_values('Bedrag', ascending=False)

                st.dataframe(
                    category_totals,
                    column_config={
                        'Bedrag': st.column_config.NumberColumn('Bedrag', format='%.2f EUR')
                    },
                    use_container_width=True,
                    hide_index=True
                )

                fig = px.pie(category_totals, values='Bedrag', names='Category', title='Expenses by Category')
                st.plotly_chart(fig, use_container_width=True)

            if df.empty:
                st.warning('This file contains no data')
            else:
                st.write(f"DataFrame shape: {df.shape}")
                st.dataframe(df)

main()
