from AlgorithmImports import *
from System import *
from QuantConnect import *
from QuantConnect.Algorithm import *
from QuantConnect.Indicators import *
from datetime import timedelta
from System.Linq import Enumerable

class BasicTemplateOptionsAlgorithm(QCAlgorithm):

    def Initialize(self):
        self.SetStartDate(2012,1,1)
        self.SetEndDate(2022,1,1)
        self.SetCash(10000)
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Cash)
        equity = self.AddEquity("SPY", Resolution.Minute)
        option = self.AddOption("SPY", Resolution.Minute)
        self.symbol = option.Symbol
        self.SetBenchmark("SPY")
        self.last_day = -1
        self.entry_price = None
        self.entry_time = None
        self.spy_close = RollingWindow[float](2)
        option.SetFilter(-2, +2, timedelta(0), timedelta(10))
    def OnData(self,slice):
        if self.Time.day == self.last_day:
            return
        
        self.last_day = self.Time.day
        
        # Update SPY close price
        if "SPY" in slice.Bars:
            self.spy_close.Add(slice.Bars["SPY"].Close)
        
        if not self.spy_close.IsReady:
            return
        if self.Portfolio.Invested:
            time_in_trade = self.Time - self.entry_time
            if self.Securities["SPY"].Price >= self.entry_price * 1.03 or time_in_trade >= timedelta(days=3):
                self.Liquidate()
                self.entry_time = None
            return
        
        # Buy call options if SPY ended red yesterday
        if ((self.spy_close[0] - self.spy_close[1]) / self.spy_close[1]) * 100 < -1:
            
            option_chain = slice.OptionChains.GetValue(self.symbol)
            
            if option_chain is None:
                return
            
            call_options = [x for x in option_chain if x.Right == OptionRight.Call]
            if not call_options:
                return
            # Sort by closest expiry
            call_options = sorted(call_options, key=lambda x: x.Expiry)
            #self.MarketOrder(call_options[0].Symbol, 5)
            available = self.Portfolio.Cash
            ask = call_options[0].AskPrice
            rounded_ask = round(ask * 1.3, 2)
            max_order = int((available * .4) / (ask * 100))
            self.Debug(f"Ask Price: {ask}, Max Order: {max_order}, Limit Price: {ask * 1.3}")
            self.Debug(f"Buying Power: {self.Portfolio.GetBuyingPower('SPY', OrderDirection.Buy)}")
            self.LimitOrder(call_options[0].Symbol, max_order, rounded_ask)
            # Record our entry price for SPY
            self.entry_price = self.Securities["SPY"].Price
            self.entry_time = self.Time
            self.Debug(f"Entry price for SPY: {self.entry_price}")
    def OnOrderEvent(self, orderEvent):
        if orderEvent.Status == OrderStatus.Filled:                
            self.Debug(f"Filled: {orderEvent}")
        elif orderEvent.Status == OrderStatus.Canceled:
            self.Debug(f"Canceled: {orderEvent}")
        else:
            self.Debug(f"Other status: {orderEvent.Status}")
