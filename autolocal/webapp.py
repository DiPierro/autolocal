import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
import pandas as pd
from datetime import datetime
from flask import Flask
from document_manager import DocumentManager

# set columns to filter
DATETIME_VARS = [
    'Date'
]

CATEGORICAL_VARS = [
    'City',
    'Committee',
]

# set columns to hyperlink
HYPERLINK_VARS = [
    'Agendas',
    'Minutes'
]


class WebApp(object):
    """
    Class for web app (front end) code.
    """

    def __init__(        
        self,
        documents=None, # should be an instance of DocumentManager
        categorical_vars=CATEGORICAL_VARS,
        datetime_vars=DATETIME_VARS,
        hyperlink_columns=HYPERLINK_VARS,
        disp_columns=DATETIME_VARS + CATEGORICAL_VARS + HYPERLINK_VARS,
        ):
        
        if documents is None:
            self.documents = DocumentManager()

        # store arguments
        self.documents = documents        
        self.categorical_vars = categorical_vars
        self.datetime_vars = datetime_vars
        self.hyperlink_columns = hyperlink_columns
        self.disp_columns = disp_columns

        # get data to display
        self.table_data = self.documents.get_metadata()

        # initialize server and app
        self.server = Flask(__name__)
        self.app = dash.Dash(__name__, server=self.server)
        self.app.scripts.config.serve_locally = True
        self.app.title = 'City Meeting Database'

        # specify page layout
        self.set_page_layout()

        pass

    def run(self, **kwargs):
        self.app.run_server(**kwargs)
        pass

    def calc_data_ranges(self, var):
        # calculates the ranges of certain variables
        if var in self.categorical_vars:
            vals = self.table_data.loc[:, var].dropna().unique() 
            return [{'label': _, 'value': _} for _ in vals]
        elif var in self.datetime_vars:
            return (self.table_data.loc[:, var].min(), datetime.now())

    # specify page layout
    def set_page_layout(self):
        self.app.layout = html.Div(
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
                                options=self.calc_data_ranges('City')
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
                                options=self.calc_data_ranges('Committee')
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
                            children=dcc.DatePickerRange(
                                id='date_filter',
                                start_date=self.calc_data_ranges('Date')[0],
                                end_date=self.calc_data_ranges('Date')[1],
                                initial_visible_month=self.calc_data_ranges('Date')[1],
                            )         
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
                    children=self.format_table(self.table_data),
                )
            ]
        )
        pass


    # function for formatting the dataframe into an HTML table
    def format_table(
        self,
        df,
        id='table',
        className='fl-table',
        **kwargs):
        header = html.Tr([html.Th(c) for c in self.disp_columns])
        rows = []
        for r in range(len(df)):
            row = []
            for c in self.disp_columns:
                value = df.iloc[r][c]
                if c in self.hyperlink_columns and not pd.isnull(value):
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


    # on user input, automatically update table
    @self.app.callback(
        [
            Output('table_container', 'children'),
            Output('city_filter', 'options'),
            Output('committee_filter', 'options'),
        ]
        [
            Input('committee_filter', 'value'),
            Input('city_filter', 'value'),
            Input('date_filter', 'start_date'),
            Input('date_filter', 'end_date'),
            Input('keyword_query', 'value')
        ])    
    def filter_table(
        self,
        committee,
        city,
        start_date,
        end_date,
        keyword_query):
        
        # don't update if there's nothing to do
        all_params = [committee, city, start_date, end_date, keyword_query]
        if all([param is None for param in all_params]):
            raise PreventUpdate

        # refresh data using thread-safe function
        self.table_data = self.documents.get_metadata()

        # initially select all rows
        idx = pd.Series([True]*len(self.table_data), dtype=bool)

        # winnow down rows based on selections
        if committee:
            idx = idx & self.table_data.loc[:,'Committee'].isin(committee)
        if city:
            idx = idx & self.table_data.loc[:,'City'].isin(city)
        if start_date and end_date:
            idx = idx & self.table_data.loc[:,'Date'].between(start_date, end_date)
        if keyword_query:
            idx = idx & (self.documents.get_count_vector('Keyword', keyword_query) > 0)
        df = self.table_data.loc[idx,:]

        # update categorical input options
        city_filter_options = self.calc_data_ranges('City')
        committee_filter_options = self.calc_data_ranges('Committee') 

        return self.format_table(df), city_filter_options, committee_filter_options

        # # intersect selection with index queries
        # index_queries =  {
        #     'Committee': committee,
        #     'City': city,
        #     'Keyword': keyword
        # }
        # for index_var, query in index_queries.items():
        #     if query:
        #         idx = idx & documents.index[index_var][query]
        
        # # intersect selection with date query
        # if start_date and end_date:
        #     idx = idx & table_data.loc[:,'Date'].between(start_date, end_date)
        # df = table_data.loc[idx,:]


if __name__ == '__main__':    
    WebApp().deploy(debug=True)

