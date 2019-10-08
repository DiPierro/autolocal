import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash_table import DataTable
from dash.exceptions import PreventUpdate
import pandas as pd
import pdf2txt

import os
import urllib

# read data
data_dir = '../data/'
example_data_path = '../data/meeting_database/example_meeting_database.csv'
date_cols = ['Date']
raw_df = pd.read_csv(example_data_path, parse_dates=date_cols)
column_dtypes = {'Committee': 'category'}


categorical_col = 'Committee'
for c in [categorical_col]:
    raw_df.loc[:,c] = raw_df.loc[:,c].astype('category')
    categorical_vals = raw_df.loc[:,c].dropna().unique()

datetime_col = 'Date'
datetime_range = (raw_df.loc[:,datetime_col].min(), raw_df.loc[:,datetime_col].max())

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

sample_df = add_text_column(raw_df)

filter_columns = [
    'City',
    'Date',
    'Committee'
]

hyperlink_columns = [
    'Agendas',
    'Minutes'
]

disp_columns = filter_columns + hyperlink_columns

def format_table(df, id='table', className='fl-table', **kwargs):
    header = html.Tr([html.Th(c) for c in disp_columns])
    rows = []
    for r in range(len(df)):
        row = []
        for c in disp_columns:
            value = df.iloc[r][c]
            if c in hyperlink_columns and not pd.isnull(value):
                cell_content = html.A('PDF', href=value, target="_blank")
            elif c==datetime_col:
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

def get_str_dtype(df, col):
    """Return dtype of col in df"""
    dtypes = ['datetime', 'bool', 'int', 'float',
              'object', 'category']
    for d in dtypes:
        try:
            if d in str(df.dtypes.loc[col]).lower():
                return d
        except KeyError:
            return None

# initialize app
app = dash.Dash(__name__)

# specify page layout
app.layout = html.Div([
    html.Div([
        html.Div(
            [
                dcc.Dropdown(
                    id='col_select',
                    options=[
                        {
                            'label': c.replace('_', ' ').title(),
                            'value': c
                        } for c in filter_columns
                    ]
                ),
                html.Div(
                    id='container_keyword_query', children=dcc.Input(id='keyword_query')
                )
            ],
            id='container_col_select',
            style={'display': 'inline-block', 'width': '30%', 'margin-left': '7%'}
        ),
        html.Div(
            [
                html.Div(children=dcc.RangeSlider(id='num_filter', updatemode='drag')),
                html.Div(children=html.Div(id='rng_slider_vals'), ),
            ],
            id='container_num_filter',
        ),
        html.Div(
            id='container_str_filter', children=dcc.Input(id='str_filter')
        ),
        html.Div(
            id='container_cat_filter',
                 children=dcc.Dropdown(
                    id='cat_filter',
                    multi=True,
                    options=[
                        {'label': _, 'value': _} for _ in categorical_vals]
                    )
        ),
        html.Div([
            dcc.DatePickerRange(id='date_filter',

                                start_date=datetime_range[0],
                                end_date=datetime_range[1],
                                initial_visible_month=pd.datetime(2019, 10, 1)
                                ),
        ], id='container_date_filter'
        ),
    ]),
    html.Div(
        format_table(sample_df),
        id='table_container',
        className='table-wrapper',
    )
    # DataTable(
    #     id='table',
    #     sort_action='native',
    #     sort_mode='multi',
    #     columns=[{"name": _, "id": _} for _ in sample_df.columns],
    #     style_cell={'maxWidth': '400px', 'whiteSpace': 'normal'},
    #     data=sample_df.to_dict("rows"))
])


@app.callback(
    [
        Output(x, 'style') for x in 
        [
            'container_num_filter',
            'container_str_filter',
            'container_cat_filter',
            'container_date_filter'
        ]
    ],
    [
        Input('col_select', 'value')
    ])
def display_relevant_filter_container(col):
    if col is None:
        return [{'display': 'none'} for i in range(4)]
    dtypes = [['int', 'float'], ['object'], ['category'], ['datetime']]
    result = [{'display': 'none'} if get_str_dtype(sample_df, col) not in d
              else {'display': 'inline-block',
                    'margin-left': '7%',
                    'width': '400px'} for d in dtypes]
    return result


@app.callback(
    Output('rng_slider_vals', 'children'),
    [
        Input('num_filter', 'value')
    ])
def show_rng_slider_max_min(numbers):
    if numbers is None:
        raise PreventUpdate
    return 'from:' + ' to: '.join([str(numbers[0]), str(numbers[-1])])


@app.callback(
    [
        Output('num_filter', 'min'),
        Output('num_filter', 'max'),
        Output('num_filter', 'value')
    ],
    [
        Input('col_select', 'value')
    ])
def set_rng_slider_max_min_val(column):
    if column is None:
        raise PreventUpdate
    if column and (get_str_dtype(sample_df, column) in ['int', 'float']):
        minimum = sample_df[column].min()
        maximum = sample_df[column].max()
        return minimum, maximum, [minimum, maximum]
    else:
        return None, None, None


@app.callback(
    Output('table_container', 'children'),
    [
        Input('col_select', 'value'),
        Input('cat_filter', 'value'),
        Input('str_filter', 'value'),
        Input('date_filter', 'start_date'),
        Input('date_filter', 'end_date'),
        Input('keyword_query', 'value')
    ])
def filter_table(
    col,
    categories,
    string,
    start_date,
    end_date,
    keyword_query):
    if all([param is None for param in [
            col, categories, string, start_date, end_date]]):
        raise PreventUpdate
    elif categories and (get_str_dtype(sample_df, col) == 'category'):
        df = sample_df[sample_df.loc[:,col].isin(categories)]        
    elif string and get_str_dtype(sample_df, col) == 'object':
        df = sample_df[sample_df.loc[:,col].str.contains(string, case=False)]
    elif start_date and end_date and (get_str_dtype(sample_df, col) == 'datetime'):
        df = sample_df[sample_df.loc[:,col].between(start_date, end_date)]
    elif keyword_query:
        print(keyword_query)
        print(sample_df.loc[:,'txt'])
        print(sample_df.loc[:,'txt'].str.contains(keyword_query, case=False, na=False))
        df = sample_df[sample_df.loc[:,'txt'].str.contains(keyword_query, case=False, na=False)]
    else:
        df = sample_df
    return format_table(df)

if __name__ == '__main__':
    app.run_server(debug=True)