import random
from typing import Dict,Optional
from order_management_system import OrderManagementSystem
#Requirements  
class Action(Exception):
    pass
# class OrderManagementSystem:
#     def __init__(self,trading_acc_balance):
#         self.trading_acc_bal=trading_acc_balance

       
#     def get_global_best_bid(self,stock: str) -> Optional[int]: 
#         return 2000
#         #Returns the highest bid across both exchanges.
#     def get_global_best_ask(self,stock: str) -> Optional[int]: 
#         return 1500
#         #Returns the lowest offer across both exchanges.
#     def get_last_traded_price(self,stock: str) -> float: 
#         return 3000
#         #Fetches the most recent price a trade occurred at.
#     def price_exists_at_exchange(self,stock: str, price: float, side: str, exchange_id: int) -> bool: 
#         return True
#         #Checks if a bid (if BUY) or ask (if SELL) already exists at that specific price level on the specified exchange.
#     def trading_acc_balance(self) -> float:
#         return self.trading_acc_bal
#         #Tracks the trader's currently available cash in the trading account.
#     def deposit_cash(self,amount: float): 
#         self.trading_acc_bal+=amount
#         #Transfers cash from the bank to the trading account.
#     def buy(self,stock: str, price: float, quantity: int, exchange: int):
#         print(f"received buy order for price: {price}, quantity: {quantity}, exchange:{exchange}, stock:{stock}\n")
#         self.trading_acc_bal-=price*quantity
#         #Places the order; must handle notification if order is cancelled (e.g., if outside top 5).
#     def sell(self,stock: str, price: float, quantity: int, exchange: int):
#         print(f"received buy order for price: {price}, quantity: {quantity}, exchange:{exchange}, stock:{stock}\n")
#         self.trading_acc_bal+=price*quantity
#         #Similar to buy, updates portfolio value.

class Trader:
    def __init__(self,order_manager,balance):
        self.bank_balance: float=balance
        self.quantity: int=1000

        self.order_manager=order_manager

    def decide_price(self,stock,action):
        best_bid=self.order_manager.get_global_best_bid(stock) #->returns top bid for both echanges
        best_ask=self.order_manager.get_global_best_ask(stock) #->returns top ask for both echanges
        
        if(best_bid is None or best_ask is None):
            last_traded_price=self.order_manager.get_last_prices(stock) #->return the most recent(last traded) price of a stock by comparing both exchanges
            return 1.05*last_traded_price if action=='BUY' else 0.95*last_traded_price
        mid_price=(best_bid+best_ask)/2
        price=random.choice([best_ask,best_bid,mid_price])
        return price
        
    def decide_exchange(self,stock,price,action):
        
        exists_at_ex0 = self.order_manager.price_exists_at_exchange(stock, price, action, exchange_id=0) #return if bid/ask is present in given exchange
        exists_at_ex1 = self.order_manager.price_exists_at_exchange(stock, price, action, exchange_id=1) #return if bid/ask is present in given exchange
        if((exists_at_ex0 and exists_at_ex1)or(not exists_at_ex0 and not exists_at_ex1)):
            return random.choice([0,1])
        return 0 if exists_at_ex1 else 1


    def take_action(self, stock):
        action=random.choice(['BUY','SELL'])
        price=self.decide_price(stock,action)
        exchange=self.decide_exchange(stock,price,action)
        #based on exchange, price and action we call 
        trading_acc_balance=self.order_manager.get_cash_balance()
        if(action=='BUY'):
            if(trading_acc_balance<price*self.quantity):
                amount_to_add= price*self.quantity-trading_acc_balance#amount to be added assuming bank balance is greater than this otherwise no actions can be taken this is upto trader
                if(amount_to_add>self.bank_balance):
                    raise Action('Insufficient Balance!') 
                self.order_manager.deposit_cash(amount_to_add)
                # print(f"added {amount_to_add} to portfolio\n")
                self.bank_balance -= amount_to_add
            self.order_manager.buy_stock(exchange,stock,price,self.quantity) 
        elif (action=='SELL'):
            if(self.order_manager.get_holdings[stock]<self.quantity):
                raise Action('Not enough holdings!')
            self.order_manager.sell_stock(exchange,stock,price,self.quantity)

oms=OrderManagementSystem('1',500000,{'a':2000,'b':4000,'c':5000})
available_stocks=['a','b','c']
trader1=Trader(oms,100000000)
for stock in available_stocks:
    trader1.take_action(stock)




        

        