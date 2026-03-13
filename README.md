# JPMC-all-the-money-is-mine

## Project Overview

This project simulates a high-frequency stock market microstructure environment. It models two independent, identical stock exchanges and evaluates the Profit and Loss (P&L) dynamics of different market participants over a standard 6.5-hour trading day. The simulation strictly adheres to price-time priority for order matching and features an integrated Order Management System (OMS).

## Core Architecture
1. Stock Exchanges & Matching Engine: Implements dual exchanges that independently maintain Limit Order Books (bids and asks). The matching engine processes incoming buy/sell orders using price-time priority, immediately settling trades and updating top-of-book data.

2. Order Management System (OMS): Acts as the intermediary for all traders, tracking cash balances, portfolio holdings, and routing orders to the exchanges. It handles trade fills, order cancellations (e.g., end-of-day or falling out of the top 5 bids/asks), and calculates real-time portfolio value.

Market Participants (Agents)
3. Standard Traders (Noise Traders): Five distinct trading agents that operate at integer-second frequencies. They simulate retail or algorithmic noise trading by making random directional bets (buy/sell) and randomizing their limit prices around the Best Bid, Best Offer, or Mid-price.

4. Fast Trader (HFT/Arbitrageur): A specialized high-frequency trader operating at half-second intervals. This agent continuously monitors the order books of both exchanges to identify and exploit risk-free arbitrage opportunities (buying low on one exchange and selling high on the other simultaneously), maintaining zero net inventory.

## Simulation & Analytics
The main simulation loop runs for 46,800 steps (0.5-second increments) across multiple securities (AAPL, GOOG, MSFT, AMZN, TSLA). It captures the real-time portfolio value of all agents and utilizes matplotlib to generate graphical P&L comparisons, highlighting the stark contrast between the random walk returns of standard traders and the step-function growth of the arbitrageur.

## Technical Implementation
Language: Python 3.x
Libraries: matplotlib (Visualization), random (Stochastic modeling), typing (Type hinting).
Logic: 
1. Price-Time Priority: Orders at the same price are filled based on arrival time.
2. Order Pruning: Bids or offers outside the top 5 levels are automatically cancelled to simulate exchange bandwidth limits.
3. Settlement: Immediate transfer of funds and shares upon trade execution.

