import time


# ORDER MANAGEMENT SYSTEM CLASS

class OrderManagementSystem:
    """
    The OMS sits between the Trader and the Exchange.
    - The Trader tells the OMS what to do
    - The OMS validates it (enough cash? enough shares?) and forwards to the Exchange
    - The Exchange executes it and notifies the OMS back via on_fill() / on_cancel()
    - The OMS keeps its own internal record of cash and portfolio (source of truth for the Trader)
    """

    def __init__(self, trader_name, initial_cash):
        self.trader_name = trader_name


        # a. Cash tracking — the amount available for trading

        self.cash = initial_cash         # Current available cash
        self.total_deposited = initial_cash  # Track total deposits for P&L calculation


        # Portfolio: tracks shares owned across ALL exchanges
        self.portfolio = {}


        # Order log: keeps a record of every order placed

        self.order_log = []


        # Fill log: records every confirmed trade execution
        # This comes from the exchange calling on_fill()

        self.fill_log = []


        # Pending orders: orders sent but not yet filled
        # If an order gets cancelled, we remove it from here
        # Format: { order_id: {details} }

        self.pending_orders = {}
        self._order_counter = 0  # Simple incrementing ID for each order

        # Portfolio value history: recorded at each time step for the P&L graph
        # Format: [(timestamp, portfolio_value), ...]
        self.value_history = []

        print(f"[OMS] Initialized for {self.trader_name} | Starting Cash: ${self.cash}")


    # INTERNAL HELPER: Generate a unique order ID

    def _new_order_id(self):
        self._order_counter += 1
        return f"{self.trader_name}_ORD_{self._order_counter}"


    # b. CASH MANAGEMENT


    def get_cash_balance(self):
        """Returns current available cash."""
        return self.cash

    def deposit_cash(self, amount, exchange=None):
        """
        Adds cash to the trading account.
        Optionally also deposits into the exchange ledger so the exchange
        knows this trader has funds (required for settlement).
        """
        if amount <= 0:
            print(f"[OMS:{self.trader_name}] Deposit rejected: amount must be positive.")
            return

        self.cash += amount
        self.total_deposited += amount

        # Also fund the exchange ledger so trades can settle there
        if exchange:
            exchange.deposit(self.trader_name, amount)

        print(f"[OMS:{self.trader_name}] Deposited ${amount} | New Balance: ${self.cash}")

    def withdraw_cash(self, amount):
        """
        Withdraws cash from the trading account.
        Cannot withdraw more than available balance.
        """
        if amount <= 0:
            print(f"[OMS:{self.trader_name}] Withdrawal rejected: amount must be positive.")
            return
        if amount > self.cash:
            print(f"[OMS:{self.trader_name}] Withdrawal rejected: only ${self.cash} available.")
            return

        self.cash -= amount
        print(f"[OMS:{self.trader_name}] Withdrew ${amount} | Remaining Balance: ${self.cash}")


    # c. PORTFOLIO VALUE


    def get_portfolio_value(self, exchanges):
        """
        Calculates total current value = cash + market value of all shares.

        Parameters:
            exchanges: list of StockExchange instances
                       We check both exchanges for last traded price and use
                       the most recent one available.
        """
        total_value = self.cash

        for stock, qty in self.portfolio.items():
            # Find the most recent last traded price across all exchanges
            best_price = None
            for ex in exchanges:
                ltp = ex.last_price.get(stock, None)
                if ltp is not None:
                    # Use whichever exchange has a price (or the higher one as a conservative estimate)
                    if best_price is None or ltp > best_price:
                        best_price = ltp

            if best_price is not None:
                total_value += qty * best_price
            else:
                # No trades have happened yet — shares have unknown market value
                print(f"[OMS:{self.trader_name}] Warning: No LTP for {stock}, excluding from valuation.")

        return total_value

    def snapshot_value(self, exchanges):
      
        #Records current portfolio value at this point in time,called at each time step so we can plot P&L over time later.
      
        value = self.get_portfolio_value(exchanges)
        self.value_history.append((time.time(), value))
        return value

    def get_pnl(self, exchanges):
        """
        Profit and Loss = Current Portfolio Value - Total Cash Deposited
        """
        current_value = self.get_portfolio_value(exchanges)
        pnl = current_value - self.total_deposited
        return pnl


    # d. PLACE BUY ORDER

    def buy_stock(self, target_exchange, stock, price, qty):
        """
        Places a buy order via the target exchange.

        Steps:
        1. Check trader has enough cash (pre-trade check)
        2. Register trader with the exchange (so it can notify us back)
        3. Log the pending order
        4. Send order to exchange
        5. Deduct cash optimistically (will be reconciled on fill/cancel)
        """

        total_cost = price * qty

        # Pre-trade validation: do we have enough cash?
        if total_cost > self.cash:
            print(f"[OMS:{self.trader_name}] BUY REJECTED: Need ${total_cost}, only have ${self.cash}.")
            return None

        # Make sure exchange knows about us (idempotent — safe to call multiple times)
        if self.trader_name not in target_exchange.oms_registry:
            target_exchange.register_oms(self.trader_name, self)
            target_exchange.deposit(self.trader_name, self.cash)  # Fund the exchange account

        # Generate an order ID for tracking
        order_id = self._new_order_id()

        # Log this as a pending order
        order_details = {
            "order_id": order_id,
            "stock": stock,
            "side": "buy",
            "price": price,
            "qty": qty,
            "exchange": target_exchange.name,
            "timestamp": time.time(),
            "status": "pending"
        }
        self.pending_orders[order_id] = order_details
        self.order_log.append(order_details)

        # Optimistically deduct cash so we don't double-spend while order is pending
        self.cash -= total_cost

        print(f"[OMS:{self.trader_name}] BUY ORDER sent | {qty} {stock} @ ${price} on {target_exchange.name} | Order ID: {order_id}")

        # Send to exchange — exchange will call on_fill() when matched
        target_exchange.place_order(self.trader_name, stock, "buy", price, qty)

        return order_id


    # e. PLACE SELL ORDER


    def sell_stock(self, target_exchange, stock, price, qty):
        """
        Places a sell order via the target exchange.

        Steps:
        1. Check trader owns enough shares (pre-trade check)
        2. Register with exchange if needed
        3. Log pending order
        4. Send to exchange
        5. Optimistically reduce portfolio count
        """

        current_qty = self.portfolio.get(stock, 0)

        # Pre-trade validation: do we own enough shares?
        if current_qty < qty:
            print(f"[OMS:{self.trader_name}] SELL REJECTED: Need {qty} {stock}, only own {current_qty}.")
            return None

        # Register with exchange if needed
        if self.trader_name not in target_exchange.oms_registry:
            target_exchange.register_oms(self.trader_name, self)
            target_exchange.deposit(self.trader_name, self.cash)

        order_id = self._new_order_id()

        order_details = {
            "order_id": order_id,
            "stock": stock,
            "side": "sell",
            "price": price,
            "qty": qty,
            "exchange": target_exchange.name,
            "timestamp": time.time(),
            "status": "pending"
        }
        self.pending_orders[order_id] = order_details
        self.order_log.append(order_details)

        # Optimistically reduce portfolio so we don't double-sell
        self.portfolio[stock] = current_qty - qty

        print(f"[OMS:{self.trader_name}] SELL ORDER sent | {qty} {stock} @ ${price} on {target_exchange.name} | Order ID: {order_id}")

        target_exchange.place_order(self.trader_name, stock, "sell", price, qty)

        return order_id


    # CALLBACK: Called BY the Exchange when a trade is filled
    # This is how the exchange "notifies the OMS when an order is fulfilled"


    def on_fill(self, stock, side, price, qty, exchange_name):
        """
        The Exchange calls this method when our order gets matched.
        We use this to:
        - Update portfolio (for buys)
        - Add cash (for sells)
        - Move order from pending to filled in our log
        """

        fill_record = {
            "stock": stock,
            "side": side,
            "price": price,
            "qty": qty,
            "exchange": exchange_name,
            "timestamp": time.time()
        }
        self.fill_log.append(fill_record)

        if side == "buy":
            # We already deducted cash in buy_stock() — now add the shares
            self.portfolio[stock] = self.portfolio.get(stock, 0) + qty
            print(f"[OMS:{self.trader_name}] FILL CONFIRMED: Bought {qty} {stock} @ ${price} on {exchange_name}")

        elif side == "sell":
            # We already reduced shares in sell_stock() — now add the cash
            self.cash += price * qty
            print(f"[OMS:{self.trader_name}] FILL CONFIRMED: Sold {qty} {stock} @ ${price} on {exchange_name}")


    # CALLBACK: Called BY the Exchange when an order is cancelled


    def on_cancel(self, stock, side, price, qty, reason):
        """
        The Exchange calls this when our order is cancelled
        (either outside Top 5, or market close).
        We reverse the optimistic deduction we made.
        """

        if side == "buy":
            # Refund the cash we reserved
            self.cash += price * qty
            print(f"[OMS:{self.trader_name}] ORDER CANCELLED ({reason}): Refunding ${price * qty} for {qty} {stock} bid @ ${price}")

        elif side == "sell":
            # Restore the shares we removed
            self.portfolio[stock] = self.portfolio.get(stock, 0) + qty
            print(f"[OMS:{self.trader_name}] ORDER CANCELLED ({reason}): Restoring {qty} {stock} to portfolio")


    # UTILITY: Print a summary of the trader's current state


    def print_summary(self, exchanges):
        print(f"\n{'='*50}")
        print(f"  OMS SUMMARY: {self.trader_name}")
        print(f"{'='*50}")
        print(f"  Cash Available : ${self.cash:,.2f}")
        print(f"  Portfolio      : {self.portfolio}")
        print(f"  Total Value    : ${self.get_portfolio_value(exchanges):,.2f}")
        print(f"  P&L            : ${self.get_pnl(exchanges):,.2f}")
        print(f"  Orders Placed  : {len(self.order_log)}")
        print(f"  Fills Received : {len(self.fill_log)}")
        print(f"{'='*50}\n")

"""
---

## How It All Connects
```
Trader
  └── calls oms.buy_stock(exchange, stock, price, qty)
        └── OMS validates (cash check)
        └── OMS sends to exchange.place_order(...)
              └── Exchange._match() executes the trade
              └── Exchange._settle() calls oms.on_fill() ← exchange notifies OMS
        └── OMS updates portfolio / cash in on_fill()
```
"""
