from datetime import datetime

import pandas as pd
from flask import Flask
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

from autolocal import DocumentManager

DATETIME_VARS = ['date']
CATEGORICAL_VARS = ['city', 'committee', 'doc_type']
HYPERLINK_VARS = ['url']

FILTER_LABELS = ['City', 'Committee', 'Date', 'Document Type', 'Keywords']
PAGE_TITLE = 'City Meeting Database'

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
        filter_labels=FILTER_LABELS,
        page_title=PAGE_TITLE,
        ):
        
        # store arguments
        if documents is None:
            self.documents = DocumentManager()
        else:
            self.documents = documents
        self.categorical_vars = categorical_vars
        self.datetime_vars = datetime_vars
        self.hyperlink_columns = hyperlink_columns
        self.disp_columns = disp_columns
        self.filter_labels = filter_labels

        # get data to display
        self.table_data = self.documents.get_metadata()

        # initialize server and app
        self.server = Flask(__name__)
        self.app = dash.Dash(__name__, server=self.server)
        self.app.scripts.config.serve_locally = True
        self.app.title = page_title

        # set page layout
        self._generate_page_layout()

        # initialize callback function
        self._init_dash_callbacks(self.app)

        pass

    def run(self):
        # function to launch webapp
        self.app.run_server()
        pass
    
    def _generate_page_layout(self):
        # Function to generate page layout in HTML
        self.app.layout = html.Div(
            className='content-wrapper',
            children=[
                *self._generate_filters(),
                html.Div(        
                    id='table_container',
                    className='table-wrapper',
                    children=self._generate_table(self.table_data)
                )
            ]
        )
        pass

    def _generate_filters(
        self
        ):
        # Function to generate the HTML for the input portion of the app

        filter_layouts = {
            'City': html.Div(
                id='container_city_filter',
                    children=dcc.Dropdown(
                    id='city_filter',
                    multi=True,
                    options=self._calc_data_ranges('city')
                )
            ),               
            'Committee': html.Div(
                id='container_committee_filter',
                children=dcc.Dropdown(
                    id='committee_filter',
                    multi=True,
                    options=self._calc_data_ranges('committee')
                )
            ),
            'Document Type': html.Div(
                id='container_doctype_filter',
                children=dcc.Dropdown(
                    id='doctype_filter',
                    multi=True,
                    options=self._calc_data_ranges('doc_type')
                )
            ),            
            'Date': html.Div(
                id='container_date_filter',
                children=dcc.DatePickerRange(
                    id='date_filter',
                    start_date=self._calc_data_ranges('date')[0],
                    end_date=self._calc_data_ranges('date')[1],
                    initial_visible_month=self._calc_data_ranges('date')[1],
                )         
            ),
            'Keywords': html.Div(
                id='container_keyword_filter',
                children=dcc.Input(id='keyword_filter')
            )
        }

        layout = []
        for label in self.filter_labels:            
            layout.append(
                html.Div(
                    className='filter_container',
                    children=[
                        html.Div(
                            className='filter_label',
                            children=label
                        ),
                        html.Div(filter_layouts[label])
                    ]
                )
            )

        return layout
    
    def _generate_table(
        self,
        df,
        id='table',
        className='fl-table',
        **kwargs):
        # function for generating the HTML for the data table

        header = html.Tr([html.Th(c) for c in self.disp_columns])
        rows = []
        for r in range(len(df)):
            row = []
            for c in self.disp_columns:
                value = df.iloc[r][c]
                if c in self.hyperlink_columns and not pd.isnull(value):
                    cell_content = html.A('PDF', href=value, target="_blank")
                elif c in self.datetime_vars:
                    try:
                        cell_content = pd.to_datetime(value).strftime('%B %d, %Y')
                    except:
                        cell_content = ''
                else:
                    cell_content = value
                row.append(html.Td(cell_content))
            rows.append(html.Tr(row))
            
        layout = html.Table(
            [
                html.Thead(header),
                html.Tbody(rows)
            ],
            className=className,
            **kwargs)
        return layout


    def _calc_data_ranges(self, var):
        # calculates the ranges of certain variables
        
        if var in self.categorical_vars:
            vals = self.table_data.loc[:, var].dropna().unique() 
            return [{'label': _, 'value': _} for _ in vals]
        elif var in self.datetime_vars:
            return (self.table_data.loc[:, var].min(), datetime.now())


    
    def _init_dash_callbacks(self, app):
        # function to instantiate the responsive portion of the site (via Dash callbacks)

        @app.callback(
            [
                Output('table_container', 'children'),
                Output('city_filter', 'options'),
                Output('doctype_filter', 'options'),
                Output('committee_filter', 'options'),
            ],
            [
                Input('committee_filter', 'value'),
                Input('city_filter', 'value'),
                Input('doctype_filter', 'value'),
                Input('date_filter', 'start_date'),
                Input('date_filter', 'end_date'),
                Input('keyword_filter', 'value')
            ])    
        def filter_table(
            committee,
            city,
            doc_type,
            start_date,
            end_date,
            keyword):
            # on user input, automatically update table
            
            # don't update if there's nothing to do
            all_params = [committee, city, doc_type, start_date, end_date, keyword]
            if all([param is None for param in all_params]):
                raise PreventUpdate

            # refresh data using thread-safe function
            self.table_data = self.documents.get_metadata()

            # initially select all rows
            idx = pd.Series([True]*len(self.table_data), dtype=bool)

            # winnow down rows based on selections
            if committee:
                idx = idx & self.table_data.loc[:,'committee'].isin(committee)
            if city:
                idx = idx & self.table_data.loc[:,'city'].isin(city)
            if doc_type:
                idx = idx & self.table_data.loc[:,'doc_type'].isin(doc_type)
            if start_date and end_date:
                idx = idx & self.table_data.loc[:,'date'].between(start_date, end_date)
            if keyword:
                idx = idx & (self.documents.get_count_vector(keyword, 'keyword') > 0)
            df = self.table_data.loc[idx,:]

            res = (
                self._generate_table(df), \
                self._calc_data_ranges('city'), \
                self._calc_data_ranges('doc_type'), \
                self._calc_data_ranges('committee')
                )

            return res

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
    WebApp().run(debug=True)


                # html.Div(
                #     className='filter_container',            
                #     children=[
                #         html.Div(
                #             className='filter_label',
                #             children='City:'
                #         ),
                #         html.Div(
                #             id='container_city_filter',
                #                 children=dcc.Dropdown(
                #                 id='city_filter',
                #                 multi=True,
                #                 options=self._calc_data_ranges('City')
                #             )
                #         )    
                #     ]
                # ),
                # html.Div(
                #     className='filter_container',            
                #     children=[
                #         html.Div(
                #             className='filter_label',
                #             children='Committee:'
                #         ),
                #         html.Div(
                #             id='container_committee_filter',
                #             children=dcc.Dropdown(
                #                 id='committee_filter',
                #                 multi=True,
                #                 options=self._calc_data_ranges('Committee')
                #             )
                #         )
                #     ]
                # ),
                # html.Div(
                #     className='filter_container',
                #     children=[
                #         html.Div(
                #             className='filter_label',
                #             children='Date range:'
                #         ),    
                #         html.Div(
                #             id='container_date_filter',
                #             children=dcc.DatePickerRange(
                #                 id='date_filter',
                #                 start_date=self._calc_data_ranges('Date')[0],
                #                 end_date=self._calc_data_ranges('Date')[1],
                #                 initial_visible_month=self._calc_data_ranges('Date')[1],
                #             )         
                #         ),
                #     ]
                # ),
                # html.Div(
                #     className='filter_container',            
                #     children=[
                #         html.Div(
                #             className='filter_label',
                #             children='Keywords:'
                #         ),
                #         html.Div(
                #             id='container_keyword_query', children=dcc.Input(id='keyword_filter')
                #         )
                #     ]
                # ),
