import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, callback_context
import webbrowser
from utils import *
import plotly.graph_objs as go
from dash import dash_table
from pybacktestchain.data_module import FirstTwoMoments
from pybacktestchain.broker import Backtest, StopLoss, EndOfMonth
from datetime import datetime
from backtest import Backtest

last_bd_date = (datetime.today() - pd.offsets.BusinessDay(n=1)).strftime('%Y-%m-%d') # -1 bd to have close prices
rebal_flags = {
    'Daily': EndOfDay,
    'Weekly': EndOfWeek,
    'Monthly': EndOfMonth
}

class BacktestApp:
    def __init__(self, title='Backtester'):
        # suppressing call back exceptions otherwise error messages due to the hidden stoploss box- not an issue since
        # we use it only if it has been instantiated
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.app.title = title
        self.default_risk_model = risk_models[0]  # Stoploss by default
        self.app.layout = self.create_layout()
        self.register_callbacks()

    def create_layout(self):
        layout = html.Div([
            html.H1("Parameters of the portfolio", style={'text-align': 'center'}),

            # Row with Start Date and End Date selection
            html.Div([
                html.Div([
                    html.Label("Start Date of the backtest:", style={'color': '#ecf0f1'}),
                    dcc.DatePickerSingle(
                        id='start_date',
                        min_date_allowed='2010-01-01',
                        max_date_allowed=last_bd_date,
                        initial_visible_month='2019-01-01',
                        date='2024-01-01',
                        style={'width': '100%'}
                    )
                ], style={'display': 'inline-block', 'width': '48%', 'padding-right': '10px'}),

                html.Div([
                    html.Label("End Date of the backtest:", style={'color': '#ecf0f1'}),
                    dcc.DatePickerSingle(
                        id='end_date',
                        min_date_allowed='2010-01-01',
                        max_date_allowed=last_bd_date,
                        initial_visible_month=last_bd_date,
                        date=last_bd_date,
                        style={'width': '100%'}
                    )
                ], style={'display': 'inline-block', 'width': '48%'}),
            ], style={'display': 'flex', 'justify-content': 'space-between', 'margin-bottom': '20px',
                      'background-color': '#34495e', 'padding': '10px', 'border-radius': '5px'}),

            # Single selection for 'ptf construction'
            html.Div([
                html.Label("Select Portfolio Construction:", ),
                dcc.RadioItems(
                    id='ptf-construction',
                    options=[{'label': option, 'value': option} for option in ptf_construction_options],
                    value=ptf_construction_options[0],  # Default value
                )
            ], style={'margin-bottom': '20px'}),

            # Single selection for 'rebalancing flag'
            html.Div([
                html.Label("Select Rebalancing Flag:"),
                dcc.RadioItems(
                    id='rebalancing-flag',
                    options=[{'label': option, 'value': option} for option in rebalancing_flag_options],
                    value=rebalancing_flag_options[-1],  # Default value
                )
            ], style={'margin-bottom': '20px'}),

            # Choice of a stoploss or not
            html.Div([
                html.Label("Select risk model:"),
                dcc.RadioItems(
                    id='risk_model',
                    options=[{'label': option, 'value': option} for option in risk_models],
                    value=self.default_risk_model,
                ),
                html.Div([
                    html.Label("Set stop-loss level (%):"),
                    dcc.Input(id='stoploss', type='number', min=0, max=100, step=0.01, value=10,
                              placeholder="Enter stop-loss", style={'width': '150px'})
                ], id='stoploss_container', style={'display': 'none', 'margin-left': '20px'})  # Hidden initially
            ]),

            # Multi-selection for 'universe'
            html.Div([
                html.Label("Select Universe:"),
                dcc.Dropdown(
                    id='universe',
                    options=[{'label': option, 'value': option} for option in universe_options],
                    multi=True
                )
            ], style={'margin-bottom': '20px'}),

            # Initial Cash Input
            html.Div([
                html.Label("Initial Cash Value:", style={'color': '#ecf0f1'}),
                dcc.Input(
                    id='initial_cash',
                    type='number',
                    value=1_000_000,  # Default to 1 million
                    style={'width': '100%', 'padding': '5px'}
                )
            ], style={'margin-bottom': '20px', 'background-color': '#34495e', 'padding': '10px',
                      'border-radius': '5px'}),

            # Button to start the backtest
            html.Div([
                html.Button('Launch Backtest', id='launch_backtest', n_clicks=0)
            ], style={'margin-top': '20px'}),

            # First row: Graph of the backtest inside a loading component
            html.Div([
                html.Label("Performance of the strategy:", style={'color': '#ecf0f1'}),

                dcc.Loading(
                    id="loading-backtest",
                    type="circle",
                    children=[dcc.Graph(id='graph_backtest', figure=go.Figure())]
                )
            ], style={'margin-top': '40px', 'background-color': '#34495e', 'padding': '20px', 'border-radius': '5px'}),

            # Metrics summary & daily PnL
            html.Div([
                html.Div([
                    html.Label("Performance metrics of the strategy:", style={'color': '#ecf0f1'}),

                    dcc.Loading(
                        id="loading-metrics",
                        type="circle",
                        children=[
                            dash_table.DataTable(
                                id='perf_table',
                                columns=[{'name': col, 'id': col} for col in ['Metric', 'Value']],
                                data=[],
                                style_table={'height': '400px', 'overflowY': 'auto'},
                                style_header={'backgroundColor': '#2c3e50', 'color': 'white'},
                                style_cell={'backgroundColor': '#34495e', 'color': 'white', 'textAlign': 'center'}
                            )
                        ]
                    )
                ], style={'width': '48%', 'padding-right': '10px', 'display': 'inline-block'}),

                html.Div([
                    html.Label("Evolution of the daily PnL:", style={'color': '#ecf0f1'}),
                    dcc.Loading(
                        id="loading-daily-pnl",
                        type="circle",
                        children=[
                            dcc.Graph(id='daily_pnl_figure', figure=go.Figure(), style={'background-color': '#2c3e50'})
                        ]
                    )
                ], style={'width': '48%', 'display': 'inline-block'})
            ], style={'display': 'flex', 'justify-content': 'space-between', 'margin-top': '40px',
                      'background-color': '#34495e', 'padding': '10px', 'border-radius': '5px'})

        ])
        return layout

    def register_callbacks(self):
        @self.app.callback(
            Output('stoploss_container', 'style'),
            Input('risk_model', 'value')
        )
        def toggle_stoploss_visibility(selected_model):
            return {'display': 'inline-block', 'margin-left': '20px'} if selected_model != self.default_risk_model else {
                'display': 'none'}

        # Callback to update the graph of the backtest + show stats when the button is clicked
        @self.app.callback(
            Output('graph_backtest', 'figure'),
            Output('perf_table', 'data'),
            Output('daily_pnl_figure', 'figure'),
            Input('launch_backtest', 'n_clicks'),
            State('start_date', 'date'),
            State('end_date', 'date'),
            State('ptf-construction', 'value'),
            State('rebalancing-flag', 'value'),
            State('risk_model', 'value'),
            State('stoploss', 'value'),
            State('universe', 'value'),
            State('initial_cash', 'value')
        )
        def update_graphs(
                n_clicks, start_date, end_date, ptf_construction, rebalancing_flag, str_risk_model, pct_sl, universe,
                initial_cash
        ):
            print(pct_sl)
            if n_clicks > 0 and universe:
                start_date , end_date = datetime.strptime(start_date, "%Y-%m-%d"), datetime.strptime(end_date, "%Y-%m-%d")
                #   ALL THE PARAMS IN THIS CLASS COULD BE VARIABLES SELECTED BY THE USER
                if str_risk_model != 'None':
                    risk_model = StopLoss
                    risk_model.threshold = pct_sl / 100
                else:
                    risk_model = None
                backtest = Backtest(
                    initial_date=start_date,
                    final_date=end_date,
                    information_class=FirstTwoMoments,
                    universe=universe,
                    risk_model=risk_model,
                    rebalance_flag=rebal_flags.get(rebalancing_flag),
                    name_blockchain='dash_backtest',
                    verbose=True,
                    initial_cash=initial_cash
                )
                df_backtest = backtest.get_df_backtest()

                # Updating the backtest figure
                backtest_fig = go.Figure(
                    data=[go.Scatter(x=df_backtest.date, y=df_backtest['ptf_value'])],
                    layout=go.Layout(title=f"Backtest Equity curve", xaxis_title="Date", yaxis_title="Portfolio value($)")
                )
                df_perf = backtest.get_backtest_metrics(df_backtest)
                daily_pnl_fig = go.Figure(
                    data=[go.Scatter(x=df_backtest.date, y=df_backtest['daily_pnl'])],
                    layout=go.Layout(title=f"Daily PnL", xaxis_title="Date", yaxis_title="PnL($)")
                )
                return backtest_fig, df_perf.to_dict(orient='records'), daily_pnl_fig
            else:
                empty_fig = go.Figure()
                empty_fig.update_layout(
                    annotations=[
                        dict(
                            text="Please select a universe and start the backtest.", x=0.5, y=0.5, showarrow=False,
                            font=dict(size=16, color="red"), xref="paper", yref="paper"
                        )
                    ],
                    xaxis=dict(visible=False),yaxis=dict(visible=False), plot_bgcolor='#2c3e50', paper_bgcolor='#34495e'
                )
                return empty_fig, [], empty_fig

    def run(self):
        self.app.run_server(debug=True)


if __name__ == '__main__':
    app = BacktestApp()
    app.run()


# def open_browser():
#     webbrowser.open_new("http://127.0.0.1:8050")
# # Run the app
# if __name__ == '__main__':
#     # Timer(1, open_browser).start()
#     app.run_server(debug=True)
