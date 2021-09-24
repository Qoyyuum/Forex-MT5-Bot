# Trading ML Experiment

This is a study on how different Neural Networks would be able to find the right way of modelling and finding a pattern through limited past or backtests before attempting to place a trade.

Develop in Python 🐍 with all of the packages mentioned in the `requirements.txt`. Primarily using Pytorch to model a Neural Network.

Actually, Pytorch is a bit advanced for a noob like me. So I used sci-kit learn and just get a working model with the defaults first.

## Usage

Other than the required pip to install, the Metatrader client must have "Autotrading" mode enabled.

Copy and paste the `config.sample.py` file to `config.py` and change the contents to fit for your account and pairs that you want to trade.

Then run,

`python3 app.py`

## Development and Contribution

This repo utilises [pre-commit](https://pre-commit.com/) and manages package management with `pipenv`.

To set up the dev environment, `pipenv install -d` and `pre-commit install`.
