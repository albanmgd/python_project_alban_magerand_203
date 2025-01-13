# python_project_alban_magerand_203

Final Project of the Python Programming course of the MSc 203. By following the Usage section below, the user:
- is able to perform backtests by adjusting several parameters (universe, objective function, length of the EWMA, ...)
- visualize equity curves and metrics related the strategy (Sharpe, drawdown, ...)
- export graphs thanks to the integration within the Plotly framework

## Installation

```bash
$ pip install python_project_alban_magerand_203
```

## Usage

```python
from python_project_alban_magerand_203.dash_app import BacktestApp
app = BacktestApp()
app.run()
```

## Contributing

Interested in contributing? Check out the contributing guidelines. Please note that this project is released with a Code of Conduct. By contributing to this project, you agree to abide by its terms.

## License

`python_project_alban_magerand_203` was created by Alban Magerand. It is licensed under the terms of the MIT license.

## Credits

`python_project_alban_magerand_203` was created with [`cookiecutter`](https://cookiecutter.readthedocs.io/en/latest/) and the `py-pkgs-cookiecutter` [template](https://github.com/py-pkgs/py-pkgs-cookiecutter).
