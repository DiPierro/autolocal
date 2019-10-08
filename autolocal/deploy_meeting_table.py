import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash_table import DataTable
from dash.exceptions import PreventUpdate
import pandas as pd
from datetime import datetime

import pdf2txt
import os
import urllib

data_dir = '../data/'

# load data
example_data_path = '../data/meeting_database/example_meeting_database.csv'
datetime_cols = ['Date']
categorical_vars = ['Committee', 'City']
column_dtypes = {v: 'category' for v in categorical_vars}
data = pd.read_csv(example_data_path, parse_dates=datetime_cols, dtype=column_dtypes)

# get range of values of each column
categorical_vals = {v: data.loc[:,v].dropna().unique() for v in categorical_vars}
datetime_range = (data.loc[:,'Date'].min(), datetime.now())

def process_pdf_url(pdf_url, city):
    # city = df["City"]
    # pdf_url = df["Agendas"]
    if not isinstance(pdf_url, str):
        return ""
    citydir = os.path.join(data_dir, city)
    pdfdir = os.path.join(citydir, "pdf")
    txtdir = os.path.join(citydir, 'txt')
    pdfname = os.path.basename(pdf_url)
    local_pdf_path = os.path.join(pdfdir, pdfname)
    txtname = pdfname[:-4] + '.txt'
    txt_path = os.path.join(txtdir, txtname)
    if not os.path.exists(local_pdf_path):
        if not os.path.exists(citydir):
            os.mkdir(citydir)
        if not os.path.exists(pdfdir):
            os.mkdir(pdfdir)
        urllib.request.urlretrieve(pdf_url.replace(" ", "%20"), local_pdf_path)
    if not os.path.exists(txt_path):
        if not os.path.exists(txtdir):
            os.mkdir(txtdir)
        args = [local_pdf_path, '-o', txt_path]
        pdf2txt.main(args)
    with open(txt_path, 'r') as f:
        return f.read()

def add_text_column(df):
    df["txt"] = df.apply(lambda x: process_pdf_url(x.Agendas, x.City), axis=1)
    return df

sample_df = add_text_column(data)

# set columns to filter
filter_columns = [
    'City',
    'Date',
    'Committee'
]

# set columns to hyperlink
hyperlink_columns = [
    'Agendas',
    'Minutes'
]

# set columns to display
disp_columns = filter_columns + hyperlink_columns

# initialize app
app = dash.Dash(__name__)
app.title = 'City Meeting Database'

# function for formatting the dataframe into an HTML table
def format_table(df, id='table', className='fl-table', **kwargs):
    header = html.Tr([html.Th(c) for c in disp_columns])
    rows = []
    for r in range(len(df)):
        row = []
        for c in disp_columns:
            value = df.iloc[r][c]
            if c in hyperlink_columns and not pd.isnull(value):
                cell_content = html.A('PDF', href=value, target="_blank")
            elif c in datetime_cols:
                cell_content = value.strftime('%B %d, %Y')
            else:
                cell_content = value
            row.append(html.Td(cell_content))
        rows.append(html.Tr(row))
    table = html.Table(
        [html.Thead(header), html.Tbody(rows)],
        className=className,
        **kwargs)
    return table

# specify page layout
app.layout = html.Div(
    className='content-wrapper',
    children=[
        html.Div(
            className='filter_container',            
            children=[
                html.Div(
                    className='filter_label',
                    children='City:'
                ),
                html.Div(
                    id='container_city_filter',
                        children=dcc.Dropdown(
                        id='city_filter',
                        multi=True,
                        options=[{'label': _, 'value': _} for _ in categorical_vals['City']]
                    )
                ) 
            ]
        ),
        html.Div(
            className='filter_container',            
            children=[
                html.Div(
                    className='filter_label',
                    children='Committee:'
                ),
                html.Div(
                    id='container_committee_filter',
                    children=dcc.Dropdown(
                        id='committee_filter',
                        multi=True,
                        options=[{'label': _, 'value': _} for _ in categorical_vals['Committee']]
                    )
                )
            ]
        ),
        html.Div(
            className='filter_container',
            children=[
                html.Div(
                    className='filter_label',
                    children='Date range:'
                ),    
                html.Div(
                    id='container_date_filter',
                    children=[
                        dcc.DatePickerRange(
                            id='date_filter',
                            start_date=datetime_range[0],
                            end_date=datetime_range[1],
                            initial_visible_month=datetime_range[1],
                            )
                    ],             
                ),
            ]
        ),
        html.Div(
            className='filter_container',            
            children=[
                html.Div(
                    className='filter_label',
                    children='Keywords:'
                ),
                html.Div(
                    id='container_keyword_query', children=dcc.Input(id='keyword_query')
                )
            ]
        ),
        html.Div(        
            id='table_container',
            className='table-wrapper',
            children=format_table(data),
        )
    ]
)



@app.callback(
    Output('table_container', 'children'),
    [
        Input('committee_filter', 'value'),
        Input('city_filter', 'value'),
        Input('date_filter', 'start_date'),
        Input('date_filter', 'end_date'),
        Input('keyword_query', 'value')
    ])
def filter_table(
    committee,
    city,
    start_date,
    end_date,
    keyword_query):
    
    # don't update if there's nothing to do
    all_params = [committee, city, start_date, end_date]
    if all([param is None for param in all_params]):
        raise PreventUpdate
    
    # initially select all rows
    idx = pd.Series([True]*len(data), dtype=bool)
    
    # winnow down rows based on selections
    if committee:
        idx = idx & data.loc[:,'Committee'].isin(committee)
    if city:
            idx = idx & data.loc[:,'City'].isin(city)
    if start_date and end_date:
        idx = idx & data.loc[:,'Date'].between(start_date, end_date)
    if keyword_query:
        idx = idx & data.loc[:,'txt'].str.contains(keyword_query, case=False, na=False)
    df = data.loc[idx,:]
    return format_table(df)

if __name__ == '__main__':
    app.run_server(debug=True)