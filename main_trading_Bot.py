import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import ta
from binance.client import Client
import numpy as np
symbol="BTCTUSD"
timeframe="5m"
starting_date="10 april 2023"

#get the data
info = Client().get_historical_klines(symbol,timeframe,starting_date)
dataframe_df = pd.DataFrame(info, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore'])

data=dataframe_df.copy() #make a copy of the data

#leave only ohlcv columns in the data
data.drop(columns=data.columns.difference(['timestamp', 'open', 'high', 'low', 'close', 'volume']), inplace=True)

#make time in miliseconds
data.set_index(data['timestamp'], inplace=True)
data.index=pd.to_datetime(data.index, unit='ms')
del data['timestamp']

data['open'] = pd.to_numeric(data['open'])
data['high'] = pd.to_numeric(data['high'])
data['low'] = pd.to_numeric(data['low'])
data['close'] = pd.to_numeric(data['close'])

ema12 = data['close'].ewm(span=12, adjust=False).mean()
ema26 = data['close'].ewm(span=26, adjust=False).mean()
macd = ema12 - ema26
macdsignal = macd.ewm(span=9, adjust=False).mean()
macdhist = macd - macdsignal


###############  Wallet
wallet = 10000


trading_fees = 0.00
trade=[]
########### Profit/Loss
profit = 0
loss = 0

profit_ratio = 1.5
percentage_of_stop_loss= 0.01

total_p=0
total_l=0

########## Keeping track of the asset
in_position = False

buying_btc=0
btc_bought = 0
purchase_price = 0
last_purchase_price = 0  # keep track of the last purchase price
highest_candle_price=0
num_buys = 0


count_wins=0
count_loss=0
print(data)

def Supertrend(data, atr_period, multiplier):

    high = data['high']
    low = data['low']
    close = data['close']

    # calculate ATR
    price_diffs = [high - low,
                   high - close.shift(),
                   close.shift() - low]
    true_range = pd.concat(price_diffs, axis=1)
    true_range = true_range.abs().max(axis=1)
    # default ATR calculation in supertrend indicator
    atr = true_range.ewm(alpha=1/atr_period,min_periods=atr_period).mean()
    # data['atr'] = data['tr'].rolling(atr_period).mean()

    # HL2 is simply the average of high and low prices
    hl2 = (high + low) / 2
    # upperband and lowerband calculation
    # notice that final bands are set to be equal to the respective bands
    final_upperband = upperband = hl2 + (multiplier * atr)
    final_lowerband = lowerband = hl2 - (multiplier * atr)

    # initialize Supertrend column to True
    supertrend = [True] * len(data)

    for i in range(1, len(data.index)):
        curr, prev = i, i-1

        # if current close price crosses above upperband
        if close[curr] > final_upperband[prev]:
            supertrend[curr] = True

        # if current close price crosses below lowerband
        elif close[curr] < final_lowerband[prev]:
            supertrend[curr] = False

        # else, the trend continues
        else:
            supertrend[curr] = supertrend[prev]

            # adjustment to the final bands
            if supertrend[curr] == True and final_lowerband[curr] < final_lowerband[prev]:
                final_lowerband[curr] = final_lowerband[prev]
            if supertrend[curr] == False and final_upperband[curr] > final_upperband[prev]:
                final_upperband[curr] = final_upperband[prev]

        # to remove bands according to the trend direction
        if supertrend[curr] == True:
            final_upperband[curr] = np.nan
        else:
            final_lowerband[curr] = np.nan

    return pd.DataFrame({
        'Supertrend': supertrend,
        'Final Lowerband': final_lowerband,
        'Final Upperband': final_upperband
    }, index=data.index),


atr_period = 10
atr_multiplier = 1

supertrend,  = Supertrend(data, atr_period, atr_multiplier,)
data = data.join(supertrend)


# print(data)

for i in range(len(data)):
   
    buy_percent_of_trade = 0.3 * wallet
    trend_up=False
    trend_down=False
   
    if data['Supertrend'][i] == True:
        trend_up=True
    else:
        trend_down=True

    if data['high'][i] > highest_candle_price:
        highest_candle_price = data['high'][i]

  
    # Check if MACD and signal lines have crossed above the zero line to indicate a bullish trend
    if macd[i] < 0 and macdsignal[i] < 0 and macd[i] > macdsignal[i] and macd[i-1] < macdsignal[i-1] : # and data['open'][i] > ema_200[i]
        # 

        #stop_loss_price = purchase_price - (0.01 * purchase_price)
        # keep track of the highest candle price since the bu
        if trend_up and not in_position:
            purchase_price = data['open'][i]            
           # Stop loss is 2% below 50 day EMA
            target_price = (1 + (profit_ratio/100)) * purchase_price
            
            purchase_amount = buy_percent_of_trade/purchase_price
            #calculate_trading_fee= purchase_amount*(1-trading_fees)
            purchase_amount = purchase_amount*(1-trading_fees)
            btc_bought += purchase_amount
            
            hold_the_fee = buy_percent_of_trade-(purchase_amount*purchase_price)

            wallet -= (purchase_amount * purchase_price) + hold_the_fee
            last_purchase_price = purchase_price
            
            #print(f'This is what it would look like with a fee: {calculate_trading_fee}')
            print(f"Purchased {purchase_amount} BTC at {purchase_price:.2f} USDT each")
            trade.append({'date':data.index[i], 'side':'buy', 'price': purchase_price, 'amount': purchase_amount, 'usdt':buy_percent_of_trade, 'wallet':wallet})
            num_buys+=1
            in_position = True
            highest_candle_price=purchase_price
            
            if wallet != 0 and trend_up:
                    purchase_amount = buy_percent_of_trade/purchase_price
                    purchase_amount= purchase_amount*(1-trading_fees)
                    btc_bought += purchase_amount

                    # Deduct purchased amount from max_buy_percentage
                    hold_the_fee = buy_percent_of_trade-(purchase_amount*purchase_price)

                    wallet -= (purchase_amount * purchase_price) + hold_the_fee

                    last_purchase_price = purchase_price
                    
                    print(f"Purchased {purchase_amount} BTC at {purchase_price:.2f} USDT each")
                    trade.append({'date':data.index[i], 'side':'buy', 'price': purchase_price, 'amount': purchase_amount, 'usdt':buy_percent_of_trade, 'wallet':wallet})
                    
                    num_buys+=1
                    in_position = True
                    highest_candle_price=purchase_price



       
        stop_loss_price = highest_candle_price - (percentage_of_stop_loss * highest_candle_price)
        #stop_loss_price = ema_50[i] - percentage_of_stop_loss * ema_50[i]
    elif in_position and ((data['high'][i] >= target_price) or (data['low'][i] <= stop_loss_price) or data['Supertrend'][i]==False):
        sell_price = data['high'][i]
        btc_sold = btc_bought
        btc_bought = 0
        if data['Supertrend'][i]==False and in_position:
            if data['high'][i]>purchase_price:
                profit = btc_sold * (sell_price - purchase_price)
                wallet += ((btc_sold*sell_price) )
                wallet*=(1-trading_fees)
                total_p += profit
   
                count_wins+=1
            
                print(f"Sold {btc_sold:.8f} BTC at {sell_price:.2f} USDT  for a profit of: {profit:.2f}. - Supertrend Succeded ")
                trade.append({'date':data.index[i], 'side':'sell', 'price': sell_price, 'amount': num_buys*purchase_amount, 'usdt':btc_sold*sell_price, 'wallet':wallet})
            else:
                loss = btc_sold * (purchase_price - sell_price)
                wallet += ((btc_sold*sell_price) )
                wallet*=(1-trading_fees)
                total_l -= loss
                
                count_loss+=1

                print(f"Sold {btc_sold:.8f} BTC at {sell_price:.2f} USDT for a loss of {loss:.2f}. - Supertrend failed")
                trade.append({'date':data.index[i], 'side':'sell', 'price': sell_price, 'amount': num_buys*purchase_amount, 'usdt':btc_sold*sell_price, 'wallet':wallet})
             
        if data['high'][i] >= target_price:
            profit = btc_sold * (sell_price - purchase_price)
            wallet += ((btc_sold*sell_price) )
            wallet*=(1-trading_fees)
            total_p += profit

            count_wins+=1

            print(f"Sold {btc_sold:.8f} BTC at {sell_price:.2f} USDT for a profit of: {profit:.2f}. - Reached 1.5 profit")
            trade.append({'date':data.index[i], 'side':'sell', 'price': sell_price, 'amount': num_buys*purchase_amount, 'usdt':btc_sold*sell_price, 'wallet':wallet})
            
        elif data['high'][i]<stop_loss_price:
            loss = btc_sold * (purchase_price - sell_price)
            wallet += ((btc_sold*sell_price) )
            wallet*=(1-trading_fees)
            total_l -= loss
            
            count_loss+=1

            print(f"Sold {btc_sold:.8f} BTC at {sell_price:.2f} USDT for a loss of {loss:.2f}. - Activated Stop Loss")
            trade.append({'date':data.index[i], 'side':'sell', 'price': sell_price, 'amount': num_buys*purchase_amount, 'usdt':btc_sold*sell_price, 'wallet':wallet})
           
        # Set profit_to_next_trade to the total profit/loss
        in_position = False

        num_buys=0
        # Reset last_purchase_price to allow buying at the same price after selling

        print(f'THE HIGHEST CANDLE WAS: {highest_candle_price}')
        print(' ')
        last_purchase_price = 0
        #highest_candle_price=0




print(f'total profit: {total_p:.2f}')
print(f'total loss: {total_l:.2f}')
print(f'money in the wallet: {wallet:.2f}')

print('')
print(f'W:{count_wins}')
print(f'L:{count_loss}')
trade = pd.DataFrame(trade,columns=['date', 'side', 'price', 'amount', 'usdt', 'wallet'])
trade=trade.round(8)
print(trade)