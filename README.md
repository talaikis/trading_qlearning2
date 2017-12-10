# Trading with Q-Learning

## Note

This fork uses great code and research from [QLearning_Trading](https://github.com/ucaiado/QLearning_Trading), which uses adaptive learning model for single stock trading.

## Differences from original

- Works with Python 3.6+
- Efficiency improvements

## How to use

Install dependencies:

    $ pip install -r requirements.txt

Run:

    $ python qtrader/agent.py <OPTION> <filename> # filename without extenstion
    $ python -m qtrader.agent <OPTION>

*OPTION*:

- train_learner
- test_learner
- test_random
- optimize_k
- optimize_gamma

Example:

    $ python qtrader/agent.py train_learner EURUSD-2016-01