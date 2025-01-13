import dash
from dash import dcc, html, Input, Output, State, callback_context
import webbrowser
from datetime import timedelta
from python_project_alban_magerand_203.utils import *
import plotly.graph_objs as go
from threading import Timer
from dash import dash_table
from python_project_alban_magerand_203.portfolio import PortfolioOptimizer
from pybacktestchain.broker import Broker, Backtest, StopLoss, EndOfMonth
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

            html.Div([
                html.Div([
                    html.Label("Select a way to estimate returns and a lookback period (days):"),
                    dcc.RadioItems(
                        id='rtn_estimates',
                        options=[{'label': option, 'value': option} for option in rtns_estimates_options],
                        value=rtns_estimates_options[0],  # Default value
                        style={'display': 'inline-block', 'margin-right': '5px'}
                    ),
                    html.Div("over", style={'font-weight': 'bold', 'margin': '0 10px'}),
                    dcc.Input(id='lookback_period', type='number', value=360, style={'width': '80px', 'padding': '4px'}),
                    html.Div(" days", style={'font-weight': 'bold', 'margin': '0 10px'}),

                ], style={'display': 'flex', 'align-items': 'flex-start', 'margin-right': '40px'}),

                html.Div([
                    html.Label("Select an objective function:"),
                    dcc.RadioItems(
                        id='obj_fct',
                        options=[{'label': option, 'value': option} for option in opt_fcts.keys()],
                        # placeholder="Choose a utility function",
                        value=list(opt_fcts.keys())[0],  # Default value
                        style={'display': 'inline-block'}
                    )
                ], style={'display': 'flex', 'align-items': 'flex-start', 'margin-right': '40px'})
            ]),

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
                ],
                    id='stoploss_container', style={'display': 'none', 'margin-left': '20px'})  # Hidden initially
            ], style={'margin-bottom': '20px'}),
            # Handling the choice of the country
            html.Div([
                html.Label("Select a country and one/several stock(s):"),

                html.Div([
                    dcc.Dropdown(
                        id='country-dropdown',
                        options=[{'label': country, 'value': country} for country in universe_options.keys()],
                        value=list(universe_options.keys())[-1],  # Default to the last country in the dictionary
                        style={'width': '200px', 'display': 'inline-block'}
                    ),

                    dcc.Dropdown(
                        id='stock-dropdown',
                        multi=True,
                        placeholder="Choose a stock",
                        style={'width': '200px', 'display': 'inline-block', 'margin-left': '20px'}
                    )
                ])
            ]),

            # Initial Cash Input
            html.Div([
                html.Label("Initial Cash Value:", style={'color': '#ecf0f1'}),
                dcc.Input(
                    id='initial_cash',
                    type='number',
                    value=1_000_000,  # Default to 1 million
                    style={'width': '80px', 'padding': '5px'}
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

        @self.app.callback(
            Output('stock-dropdown', 'options'),
            Output('stock-dropdown', 'value'),
            Input('country-dropdown', 'value')
        )
        def update_stock_dropdown(selected_country):
            if selected_country is None:
                return [], None  # No options if country isn't selected

            stock_options = [{'label': stock, 'value': stock} for stock in universe_options[selected_country]]
            default_stock = stock_options[0]['value'] if stock_options else None  # Select first stock by default

            return stock_options, default_stock

        # Callback to update the graph of the backtest + show stats when the button is clicked
        @self.app.callback(
            Output('graph_backtest', 'figure'),
            Output('perf_table', 'data'),
            Output('daily_pnl_figure', 'figure'),

            Input('launch_backtest', 'n_clicks'),
            State('start_date', 'date'),
            State('end_date', 'date'),
            State('rtn_estimates', 'value'),
            State('lookback_period', 'value'),
            State('obj_fct', 'value'),
            State('rebalancing-flag', 'value'),
            State('risk_model', 'value'),
            State('stoploss', 'value'),
            State('stock-dropdown', 'value'),
            State('initial_cash', 'value')
        )
        def update_graphs(
                n_clicks, start_date, end_date, rtn_estimates, lookback_period, obj_fct, rebalancing_flag, str_risk_model, pct_sl, universe,
                initial_cash
        ):
            if n_clicks > 0 and universe:
                start_date , end_date = datetime.strptime(start_date, "%Y-%m-%d"), datetime.strptime(end_date, "%Y-%m-%d")
                #   ALL THE PARAMS IN THIS CLASS COULD BE VARIABLES SELECTED BY THE USER
                if type(universe) == str: #means only one stock selected
                    universe = [universe]

                if str_risk_model != 'None':
                    risk_model = StopLoss
                    risk_model.threshold = pct_sl / 100
                else:
                    risk_model = None

                backtest = Backtest(
                    initial_date=start_date,
                    final_date=end_date,
                    s=timedelta(days=lookback_period),
                    information_class=PortfolioOptimizer,
                    rtn_estimates=rtn_estimates,
                    obj_fct=opt_fcts.get(obj_fct),
                    universe=universe,
                    risk_model=risk_model,
                    rebalance_flag=rebal_flags.get(rebalancing_flag),
                    name_blockchain='dash_backtest',
                    verbose=True,
                    initial_cash=initial_cash,
                    broker=Broker(cash=initial_cash, verbose=True)  # re-instantiate to clean positions
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
                del backtest
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

    @staticmethod
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:8050")

    def run(self):
        Timer(1, self.open_browser).start()
        self.app.run_server()


if __name__ == '__main__':
    app = BacktestApp()
    app.run()
