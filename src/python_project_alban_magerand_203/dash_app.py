import dash
from dash import dcc, html, Input, Output, State
import webbrowser
from threading import Timer
from utils import *
import plotly.graph_objs as go
import random
from pybacktestchain.data_module import FirstTwoMoments
from pybacktestchain.broker import Backtest, StopLoss
from datetime import datetime
from backtest import BacktestAugmented

# Initialize the Dash app
app = dash.Dash(__name__)

# App layout
app.layout = html.Div([
    html.H1("Portfolio Settings", style={'text-align': 'center'}),

    # Single selection for 'ptf construction'
    html.Div([
        html.Label("Select Portfolio Construction:"),
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
            value=rebalancing_flag_options[0],  # Default value
        )
    ], style={'margin-bottom': '20px'}),

    # Multi-selection for 'universe'
    html.Div([
        html.Label("Select Universe:"),
        dcc.Dropdown(
            id='universe',
            options=[{'label': option, 'value': option} for option in universe_options],
            multi=True
        )
    ], style={'margin-bottom': '20px'}),

    # Button to start the backtest
    html.Div([
        html.Button('Launch Backtest', id='launch_backtest', n_clicks=0)
    ], style={'margin-top': '20px'}),

    # Adding the graph of the backtest
    html.Div([
            dcc.Graph(
                id='graph_backtest',
                figure=go.Figure(),  # Empty figure
            )
        ], style={'margin-top': '40px'}),
    # Output display
    html.Div(id='output', style={'margin-top': '20px', 'font-weight': 'bold'})
    ])

# Callback to update the graph of the backtest + show stats when the button is clicked
@app.callback(
    Output('graph_backtest', 'figure'),
    Input('launch_backtest', 'n_clicks'),
    State('ptf-construction', 'value'),
    State('rebalancing-flag', 'value'),
    State('universe', 'value')
)
def update_graph(n_clicks, ptf_construction, rebalancing_flag, universe):
    if n_clicks > 0 and universe:
        # Mock data generation
        x = universe  # Use selected universe as x-axis labels
        y = [random.randint(10, 100) for _ in universe]  # Random mock values for y-axis

        #   ALL THE PARAMS IN THIS CLASS COULD BE VARIABLES SELECTED BY THE USER
        raw_backtest = Backtest(
            initial_date=datetime(2019, 6, 1),
            final_date=datetime(2020, 1, 1),
            information_class=FirstTwoMoments,
            risk_model=StopLoss,
            name_blockchain='test',
            verbose=True
        )
        raw_backtest.universe = ['AAPL']  # univers is a class level attribute, can't give it as an input
        aug_backtest = BacktestAugmented(raw_backtest)
        df_backtest = aug_backtest.get_df_backtest()
        print(1)


        figure = go.Figure(
            data=[go.Bar(x=x, y=y, marker_color='blue')],
            layout=go.Layout(
                title=f"Mock Backtest Results: {ptf_construction} | {rebalancing_flag}",
                xaxis_title="Universe",
                yaxis_title="Performance Metric",
            )
        )
        return figure
    else:
        return go.Figure()  # Return empty figure if no data

# Callback to display the selected values
# @app.callback(
#     Output('output', 'children'),
#     Input('ptf-construction', 'value'),
#     Input('rebalancing-flag', 'value'),
#     Input('universe', 'value')
# )
# def update_output(ptf_construction, rebalancing_flag, universe):
#     return f"Selected Portfolio Construction: {ptf_construction}, Rebalancing Flag: {rebalancing_flag}, Universe: {universe or 'None'}"
#

def open_browser():
    webbrowser.open_new("http://127.0.0.1:8050")
# Run the app
if __name__ == '__main__':
    # Timer(1, open_browser).start()
    app.run_server(debug=True)
