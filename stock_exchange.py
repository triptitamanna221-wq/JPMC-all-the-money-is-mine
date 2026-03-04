from typing import Dict, List, Optional
import heapq
import time

class Order:   #placing an order- placed an order(order_id by trader_id) to buy/sell(side) a stock at a certain price and quantity
    def __init__(
        self,
        order_id: int,
        trader_id: int,
        stock: str,
        side: str,              # 'BUY' or 'SELL'
        price: float,
        quantity: int,
        timestamp: float
    ):
        self.order_id = order_id
        self.trader_id = trader_id
        self.stock = stock
        self.side = side
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp

class Trade:   #execution of trade- when a buy and sell order match, a trade is executed with details of the stock, price, quantity, buyer/seller ids and timestamp
    def __init__(
        self,
        stock: str,
        price: float,
        quantity: int,
        buyer_id: int,
        seller_id: int,
        timestamp: float
    ):
        self.stock = stock
        self.price = price
        self.quantity = quantity
        self.buyer_id = buyer_id
        self.seller_id = seller_id
        self.timestamp = timestamp

class OrderBook: 
    def __init__(self): 
        self.bids: Dict[float, List[Order]] = {}  #buy orders
        self.asks: Dict[float, List[Order]] = {}  #sell orders

    def best_bid(self) -> Optional[float]:  #highest buy price
        if not self.bids:
            return None
        return max(self.bids.keys())

    def best_ask(self) -> Optional[float]:  #lowest sell price
        if not self.asks:
            return None
        return min(self.asks.keys())

    #use only top 5 values- given in Q
    def top_5_bids(self) -> List[float]:
        return sorted(self.bids.keys(), reverse=True)[:5]

    def top_5_asks(self) -> List[float]:
        return sorted(self.asks.keys())[:5]

    def add_order(self, order: Order):  #add to order book (FIFO- for same price level, choose the one with earlier timestamp)
        book = self.bids if order.side == 'BUY' else self.asks
        book.setdefault(order.price, []).append(order)

    def remove_empty_levels(self):
        self.bids = {p: q for p, q in self.bids.items() if q}
        self.asks = {p: q for p, q in self.asks.items() if q}

class MatchingEngine:
    def match(
        self,
        incoming_order: Order,
        order_book: OrderBook
    ) -> List[Trade]:
        trades: List[Trade] = []

        if incoming_order.side == 'BUY':
            trades = self._match_buy(incoming_order, order_book)
        else:
            trades = self._match_sell(incoming_order, order_book)

        return trades

    def _match_buy(self, buy_order: Order, book: OrderBook) -> List[Trade]:
        trades = []
        # Matches a buy order against existing sell orders (asks)
        # Bids match with the lowest asks first
        while buy_order.quantity > 0 and book.asks:
            best_ask_price = book.best_ask()
            if best_ask_price is None or buy_order.price < best_ask_price:
                break  # Buy price doesn't cross the best ask

            # Get the orders at the best ask price (they are already sorted by time if appended chronologically)
            ask_orders = book.asks[best_ask_price]
            
            while buy_order.quantity > 0 and ask_orders:
                resting_ask = ask_orders[0]
                
                trade_qty = min(buy_order.quantity, resting_ask.quantity)
                
                # Trade happens at the resting order's price
                trade = Trade(
                    stock=buy_order.stock,
                    price=resting_ask.price,
                    quantity=trade_qty,
                    buyer_id=buy_order.trader_id,
                    seller_id=resting_ask.trader_id,
                    timestamp=time.time()
                )
                trades.append(trade)
                
                buy_order.quantity -= trade_qty
                resting_ask.quantity -= trade_qty
                
                if resting_ask.quantity == 0:
                    ask_orders.pop(0)
            
            if not ask_orders:
                del book.asks[best_ask_price]
                
        return trades

    def _match_sell(self, sell_order: Order, book: OrderBook) -> List[Trade]:
        trades = []
        # Matches a sell order against existing buy orders (bids)
        # Asks match with the highest bids first
        while sell_order.quantity > 0 and book.bids:
            best_bid_price = book.best_bid()
            if best_bid_price is None or sell_order.price > best_bid_price:
                break  # Sell price doesn't cross the best bid
                
            bid_orders = book.bids[best_bid_price]
            
            while sell_order.quantity > 0 and bid_orders:
                resting_bid = bid_orders[0]
                
                trade_qty = min(sell_order.quantity, resting_bid.quantity)
                
                # Trade happens at the resting order's price
                trade = Trade(
                    stock=sell_order.stock,
                    price=resting_bid.price,
                    quantity=trade_qty,
                    buyer_id=resting_bid.trader_id,
                    seller_id=sell_order.trader_id,
                    timestamp=time.time()
                )
                trades.append(trade)
                
                sell_order.quantity -= trade_qty
                resting_bid.quantity -= trade_qty
                
                if resting_bid.quantity == 0:
                    bid_orders.pop(0)
                    
            if not bid_orders:
                del book.bids[best_bid_price]
                
        return trades
    
class StockExchange:  #one exchange
    def __init__(self, exchange_id: int, trading_start: float, trading_end: float):
        self.exchange_id = exchange_id
        self.trading_start = trading_start
        self.trading_end = trading_end

        self.order_books: Dict[str, OrderBook] = {}
        self.last_traded_price: Dict[str, float] = {}

        self.matching_engine = MatchingEngine()
        self.order_id_counter = 0

    def accept_order(self, order: Order) -> bool:
        if not self._is_trading_open():
            self._notify_cancel(order, reason="Market closed")
            return False

        book = self.order_books.setdefault(order.stock, OrderBook())

        trades = self.matching_engine.match(order, book)

        for trade in trades:
            self.last_traded_price[trade.stock] = trade.price
            self._settle_trade(trade)

        if order.quantity > 0:
            book.add_order(order)

            if not self._is_within_top_5(order, book):
                self._cancel_order(order, book)
                self._notify_cancel(order, reason="Outside top 5")

        self._prune_order_book(book)
        return True
    
    def _is_trading_open(self) -> bool:
        now = time.time()
        return self.trading_start <= now <= self.trading_end

    def _is_within_top_5(self, order: Order, book: OrderBook) -> bool:
        if order.side == 'BUY':
            return order.price in book.top_5_bids()
        return order.price in book.top_5_asks()

    def _cancel_order(self, order: Order, book: OrderBook):
        levels = book.bids if order.side == 'BUY' else book.asks
        if order.price in levels:
            levels[order.price] = [
                o for o in levels[order.price] if o.order_id != order.order_id
            ]
        book.remove_empty_levels()

    def _prune_order_book(self, book: OrderBook):
        #Removes orders outside the top 5 levels and notifies traders.
        top_bids = book.top_5_bids()
        prices_to_remove = [p for p in book.bids if p not in top_bids]
        for p in prices_to_remove:
            for order in book.bids[p]:
                self._notify_cancel(order, "Fell outside top 5 bids")
            del book.bids[p]
            
        top_asks = book.top_5_asks()
        prices_to_remove = [p for p in book.asks if p not in top_asks]
        for p in prices_to_remove:
            for order in book.asks[p]:
                self._notify_cancel(order, "Fell outside top 5 asks")
            del book.asks[p]

    def _settle_trade(self, trade: Trade):
        # Exchange notifies OMS involved
        print(f"[EXCHANGE {self.exchange_id}] Trade executed: {trade.quantity}x {trade.stock} @ {trade.price}. Buyer: {trade.buyer_id}, Seller: {trade.seller_id}")

    def _notify_cancel(self, order: Order, reason: str):
        # Notify OMS of cancellation
        print(f"[EXCHANGE {self.exchange_id}] Order {order.order_id} cancelled: {reason}")

