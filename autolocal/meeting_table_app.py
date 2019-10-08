
import random
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash_table import DataTable
from dash.exceptions import PreventUpdate
import pandas as pd

# read data
example_data_path = 'example_data.csv'
date_cols = ['Date']
raw_df = pd.read_csv(example_data_path, parse_dates=date_cols)
column_dtypes = {'Committee': 'category'}


categorical_col = 'Committee'
for c in [categorical_col]:
    raw_df.loc[:,c] = raw_df.loc[:,c].astype('category')
    categorical_vals = raw_df.loc[:,c].dropna().unique()

datetime_col = 'Date'
datetime_range = (raw_df.loc[:,datetime_col].min(), raw_df.loc[:,datetime_col].max())

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

def make_hyperlinked_columns(df):
    rows = []
    for r in range(len(df)):
        row = {}
        for c in disp_columns:
            value = df.loc[:,c].iloc[r]
            if c in hyperlink_columns and not pd.isnull(value):
                row[c] = value #dcc.Link('Link', href=value) #html.Td(html.A('Link', href=value))
            else:
                row[c] = value
        rows.append(row)
    df_out = pd.DataFrame(rows, columns=disp_columns)
    for c in [categorical_col]:
        df_out.loc[:,c] = df_out.loc[:,c].astype('category')
    return df_out

sample_df = make_hyperlinked_columns(raw_df)

# sample_df = pd.DataFrame({
#     'int': [random.randint(1, 100) for i in range(20)],
#     'float': [random.random() * x for x in random.choices(range(100), k=20)],
#     'str(object)': ['one', 'one two', 'one two three', 'four'] * 5,
#     'category': random.choices(['Sat', 'Sun', 'Mon', 'Tue', 'Wed','Thu', 'Fri'], k=20),
#     'datetime': pd.date_range('2019-05-01', periods=20),
#     'bool': random.choices([True, False], k=20),
# })
# sample_df['category'] = sample_df['category'].astype('category')


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

app = dash.Dash(__name__)

app.layout = html.Div([
    html.Div([
        html.Div(id='container_col_select',
                 children=dcc.Dropdown(id='col_select',
                                       options=[{
                                           'label': c.replace('_', ' ').title(),
                                           'value': c}
                                           for c in filter_columns]),
                 style={'display': 'inline-block', 'width': '30%', 'margin-left': '7%'}),
        # DataFrame filter containers
        html.Div(
            [
                html.Div(children=dcc.RangeSlider(id='num_filter', updatemode='drag')),
                html.Div(children=html.Div(id='rng_slider_vals'), ),
            ],
            id='container_num_filter', ),
        html.Div(
            id='container_str_filter', children=dcc.Input(id='str_filter')),
        html.Div(id='container_cat_filter',
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
        ], id='container_date_filter'),
    ]),
    DataTable(
        id='table',
        sort_action='native',
        sort_mode='multi',
        columns=[{"name": _, "id": _} for _ in sample_df.columns],
        style_cell={'maxWidth': '400px', 'whiteSpace': 'normal'},
        data=sample_df.to_dict("rows"))
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
    Output('table', 'data'),
    [
        Input('col_select', 'value'),
        Input('cat_filter', 'value'),
        Input('str_filter', 'value'),
        Input('date_filter', 'start_date'),
        Input('date_filter', 'end_date')
    ])
def filter_table(
    col,
    categories,
    string,
    start_date,
    end_date):
    if all([param is None for param in [
            col, categories, string, start_date, end_date]]):
        raise PreventUpdate
    elif categories and (get_str_dtype(sample_df, col) == 'category'):
        df = sample_df[sample_df.loc[:,col].isin(categories)]
        return df.to_dict('rows')    
    elif string and get_str_dtype(sample_df, col) == 'object':
        df = sample_df[sample_df.loc[:,col].str.contains(string, case=False)]
        return df.to_dict('rows')
    elif start_date and end_date and (get_str_dtype(sample_df, col) == 'datetime'):
        df = sample_df[sample_df.loc[:,col].between(start_date, end_date)]
        return df.to_dict('rows')
    else:
        return sample_df.to_dict('rows')

if __name__ == '__main__':
    app.run_server(debug=True)