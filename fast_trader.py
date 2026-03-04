import time

class FastTrader: #information into fast trader required to operate in market
    def __init__(self, order_manager, balance, exchange_0, exchange_1):
        self.bank_balance = balance
        self.order_manager = order_manager
        
        #the Fast Trader needs direct access of the exchanges to spot arbitrage
        self.exchange_0 = exchange_0
        self.exchange_1 = exchange_1
        
        #default order size so that we prevent infinite shares, though we will dynamically adjust this based on available liquidity
        self.max_quantity = 1000 

    def take_action(self, stock): #checks for arbitrage opportunities across both exchanges

        #fetch the OrderBooks for the given stock from both exchanges
        book_0 = self.exchange_0.order_books.get(stock)
        book_1 = self.exchange_1.order_books.get(stock)

        #if the stock hasn't been traded or doesn't exist in one of the books, we can't arbitrage
        if not book_0 or not book_1:
            return

#here on we have to deal with 2 arbitrage possibilities, a vice versa case on both exchanges

        #get the best available prices (top of the book)
        best_bid_0 = book_0.best_bid() 
        best_ask_0 = book_0.best_ask()
        
        best_bid_1 = book_1.best_bid() 
        best_ask_1 = book_1.best_ask() 

        #check for arbitrage 
        #someone on Exchange 0 is willing to BUY at a higher price than someone on Exchange 1 is willing to SELL
        if best_bid_0 is not None and best_ask_1 is not None and best_bid_0 > best_ask_1:
            self._execute_arbitrage(
                stock=stock, 
                buy_exchange=self.exchange_1, 
                sell_exchange=self.exchange_0, 
                buy_price=best_ask_1, 
                sell_price=best_bid_0,
                buy_book=book_1, 
                sell_book=book_0
            )

        #someone on Exchange 1 is willing to BUY at a higher price than someone on Exchange 0 is willing to SELL.
        elif best_bid_1 is not None and best_ask_0 is not None and best_bid_1 > best_ask_0:
            self._execute_arbitrage(
                stock=stock, 
                buy_exchange=self.exchange_0, 
                sell_exchange=self.exchange_1, 
                buy_price=best_ask_0, 
                sell_price=best_bid_1,
                buy_book=book_0, 
                sell_book=book_1
            )

    def _execute_arbitrage(self, stock, buy_exchange, sell_exchange, buy_price, sell_price, buy_book, sell_book):
#simultaneous execution of buy and trade once arbitrage is spotted

        #calculate the maximum size we can trade
        #a trade can only occur if the relevant size exists at those exact price levels
        #we fetch the list of orders sitting at the best ask and best bid
        ask_orders = buy_book.asks.get(buy_price, [])
        bid_orders = sell_book.bids.get(sell_price, [])
        
        if not ask_orders or not bid_orders:
            return #liquidity disappeared, cancel the trade
            
        #sum the quantities of all resting orders at those price levels
        available_ask_qty = sum(order.quantity for order in ask_orders)
        available_bid_qty = sum(order.quantity for order in bid_orders)

        trade_qty = min(available_ask_qty, available_bid_qty, self.max_quantity)
        
        if trade_qty <= 0:
            return

        #checks: ensure we have enough cash in the OMS to execute the buy 
        required_cash = buy_price * trade_qty
        current_cash = self.order_manager.get_cash_balance()
        
        if current_cash < required_cash:
            #calculate shortfall and try to deposit from bank balance
            shortfall = required_cash - current_cash
            if self.bank_balance >= shortfall:
                self.order_manager.deposit_cash(shortfall)
                self.bank_balance -= shortfall
            else:
                #if we don't have enough bank balance, scale down the trade quantity to what we can afford
                trade_qty = int(current_cash // buy_price)
                if trade_qty <= 0:
                    return #still can't afford a single share, cancel trade

        print(f"\n[FAST TRADER] ARBITRAGE DETECTED for {stock}")
        print(f"   -> Buying {trade_qty} @ ${buy_price} on Exchange {buy_exchange.exchange_id}")
        print(f"   -> Selling {trade_qty} @ ${sell_price} on Exchange {sell_exchange.exchange_id}")
        print(f"   -> Instant Risk-Free Profit: ${(sell_price - buy_price) * trade_qty}\n")

        #execute the trades
        self.order_manager.buy_stock(
            target_exchange=buy_exchange, 
            stock=stock, 
            price=buy_price, 
            qty=trade_qty
        )
        
        self.order_manager.sell_stock(
            target_exchange=sell_exchange, 
            stock=stock, 
            price=sell_price, 
            qty=trade_qty
        )
