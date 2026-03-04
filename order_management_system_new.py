import time
class OrderManagementSystem:

    def __init__(self, trader_name, initial_cash,portfolio):
        self.trader_name = trader_name
        self.cash = initial_cash
        
        self.portfolio = portfolio
        self.order_log = []
        self.fill_log = []
        self.pending_orders = {}
        self._order_counter = 0
        self.value_history = []

        print(f"[OMS] Initialized for {self.trader_name} | Starting Cash: ${self.cash}")
        
    def _new_order_id(self):
        self._order_counter += 1
        return f"{self.trader_name}_ORD_{self._order_counter}"
    def get_holdings(self):
        return self.portfolio
    def get_cash_balance(self):
        return self.cash

    def deposit_cash(self, amount, exchange=None):
        if amount <= 0:
            print(f"[OMS:{self.trader_name}] Deposit rejected: amount must be positive.")
            return

        self.cash += amount
        

        # if exchange:
        #     exchange.deposit(self.trader_name, amount) 

        print(f"[OMS:{self.trader_name}] Deposited ${amount} | New Balance: ${self.cash}")

    def withdraw_cash(self, amount):
        if amount <= 0:
            print(f"[OMS:{self.trader_name}] Withdrawal rejected: amount must be positive.")
            return

        if amount > self.cash:
            print(f"[OMS:{self.trader_name}] Withdrawal rejected: only ${self.cash} available.")
            return

        self.cash -= amount
        print(f"[OMS:{self.trader_name}] Withdrew ${amount} | Remaining Balance: ${self.cash}")

    def get_portfolio_value(self, exchanges):
        total_value = self.cash

        for stock, qty in self.portfolio.items():
            best_price = None

            for ex in exchanges:
                ltp = ex.last_price.get(stock, None)
                if ltp is not None:
                    if best_price is None or ltp > best_price:
                        best_price = ltp

            if best_price is not None:
                total_value += qty * best_price
            else:
                print(f"[OMS:{self.trader_name}] Warning: No LTP for {stock}, excluding from valuation.")

        return total_value

    def snapshot_value(self, exchanges):
        value = self.get_portfolio_value(exchanges)
        self.value_history.append((time.time(), value))
        return value

    def get_pnl(self, exchanges):
        current_value = self.get_portfolio_value(exchanges)
        pnl = current_value - self.cash
        return pnl

    def buy_stock(self, target_exchange, stock, price, qty):
        total_cost = price * qty

        if total_cost > self.cash:
            print(f"[OMS:{self.trader_name}] BUY REJECTED: Need ${total_cost}, only have ${self.cash}.")
            return None

        if self.trader_name not in target_exchange.oms_registry:
            target_exchange.register_oms(self.trader_name, self)
            target_exchange.deposit(self.trader_name, self.cash)

        order_id = self._new_order_id()

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

        self.cash -= total_cost

        print(
            f"[OMS:{self.trader_name}] BUY ORDER sent | "
            f"{qty} {stock} @ ${price} on {target_exchange.name} | "
            f"Order ID: {order_id}"
        )

        target_exchange.place_order(self.trader_name, stock, "buy", price, qty)

        return order_id

    def sell_stock(self, target_exchange, stock, price, qty):
        current_qty = self.portfolio.get(stock, 0)

        if current_qty < qty:
            print(
                f"[OMS:{self.trader_name}] SELL REJECTED: "
                f"Need {qty} {stock}, only own {current_qty}."
            )
            return None

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

        self.portfolio[stock] = current_qty - qty

        print(
            f"[OMS:{self.trader_name}] SELL ORDER sent | "
            f"{qty} {stock} @ ${price} on {target_exchange.name} | "
            f"Order ID: {order_id}"
        )

        target_exchange.place_order(self.trader_name, stock, "sell", price, qty)

        return order_id

    def on_fill(self, stock, side, price, qty, exchange_name):
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
            self.portfolio[stock] = self.portfolio.get(stock, 0) + qty
            print(
                f"[OMS:{self.trader_name}] FILL CONFIRMED: "
                f"Bought {qty} {stock} @ ${price} on {exchange_name}"
            )

        elif side == "sell":
            self.cash += price * qty
            print(
                f"[OMS:{self.trader_name}] FILL CONFIRMED: "
                f"Sold {qty} {stock} @ ${price} on {exchange_name}"
            )

    def on_cancel(self, stock, side, price, qty, reason):
        if side == "buy":
            self.cash += price * qty
            print(
                f"[OMS:{self.trader_name}] ORDER CANCELLED ({reason}): "
                f"Refunding ${price * qty} for {qty} {stock} bid @ ${price}"
            )

        elif side == "sell":
            self.portfolio[stock] = self.portfolio.get(stock, 0) + qty
            print(
                f"[OMS:{self.trader_name}] ORDER CANCELLED ({reason}): "
                f"Restoring {qty} {stock} to portfolio"
            )

    def print_summary(self, exchanges):
        print("\n" + "=" * 50)
        print(f"OMS SUMMARY: {self.trader_name}")
        print("=" * 50)

        print(f"Cash Available : ${self.cash:,.2f}")
        print(f"Portfolio      : {self.portfolio}")
        print(f"Total Value    : ${self.get_portfolio_value(exchanges):,.2f}")
        print(f"P&L            : ${self.get_pnl(exchanges):,.2f}")
        print(f"Orders Placed  : {len(self.order_log)}")
        print(f"Fills Received : {len(self.fill_log)}")

        print("=" * 50 + "\n")