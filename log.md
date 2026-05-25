This file logs the time we spend working on this backtesting project.


Week 0. 4 - 10 May 2026

Accomplished
- Decided project direction
- Created basic django models. 
- Created backtester performance metrics calculating functions and\ 
corresponding unit tests for them

Week 1. 11 - 17 May 2026

Accomplished
- 

Time Contributions

Week 2. 18 - 24 May 2026
Accomplished
- 

Time Contributions
21 May had discussion on deadlines.
23rd may finish events.py and dataloader.py and have a discussion

22 May (~4h)
Mervin finishes updated version of dataloader.py. Added initial prototype of test_data_loader that initializes a test database 

23 May 3 pm meeting
Discussion of events.py and determining direction from here.
Classes to implement
strategy => Take in MarketEvent create SignalEvent
portfolio => Take in SignalEvent maybe create OrderEvent, take in FillEvent and generate MarketEvent
execution => Take in OrderEvent maybe create FillEvent.

performance => necessary to update methods for strategy?

25 Monday, finish up initial portfolio and backtesting by Mervin, look into metrics for strategy

finish up execution, strategy(one), initial portfolio, (unit testing for dataloader maybe)

By Tuesday we should have finished up after call on Monday 
Then the following days we finish up UI stuffs. 


25 May
12 pm Mervin works on Backtest.py
- Ask Ryan and agree on adding docstring to classes
- I should stop editing to the log.md directly and instead push and commit
- 1 pm finished Backtest.py, Looking into portfolio.py 
- Portfolio has many more advanced features that can be implemented after the basic
 version has been implemented
- E.g estimation of holdings using seconds, minutes, hourly bars => our current daily
  bar is not that accurate
  - Risk factors => How much risk the strategy is taking
  - Position sizing => How much capital is the strategy allocating to each trade
  - For our initial working prototype, we will go with a simple version which ignores risk factors
    and position sizing
- Ask ryan is comission should be in portfolio or in execution
- Ask Ryan why his indention for Types is 8 spaces
- Is get_latest_bar_value the close value of the latest bar?





