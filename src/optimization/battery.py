def dispatch(action, soc, price, capacity=100, max_rate=25, efficiency=0.85):
    # action: 'charge', 'discharge', 'idle'
    # soc: current state of charge in MWh
    # price: current market price $/MWh
    # returns: new_soc, cash_flow

    if action == 'charge':
        # available room in battery
        available_capacity = capacity - soc
        
        # actual amount we can charge this hour
        charge_amount = min(max_rate, available_capacity)
        
        # efficiency loss while charging
        energy_stored = charge_amount * efficiency
        
        # update SOC
        new_soc = soc + energy_stored
        
        # buying electricity = negative cash flow
        cash_flow = -charge_amount * price
        
        return new_soc, cash_flow

    elif action == 'discharge':
        # actual amount we can discharge
        discharge_amount = min(max_rate, soc)
        
        # usable energy delivered after efficiency loss
        energy_sold = discharge_amount * efficiency
        
        # update SOC
        new_soc = soc - discharge_amount
        
        # selling electricity = positive cash flow
        cash_flow = energy_sold * price
        
        return new_soc, cash_flow

    else:  # idle
        return soc, 0



def naive_strategy(hour, soc):
    # hour is 0-23
    if hour <=5:
        return 'charge'
    elif hour>=16 and hour<=21:
        return 'discharge'
    else:
        return 'idle'


def smart_strategy(current_price, q10, q50, q90, soc, recent_prices, capacity=100):
    # current_price: actual price this hour
    if len(recent_prices) < 2:
        return 'idle'
    p30 = np.percentile(recent_prices, 30)
    p70 = np.percentile(recent_prices, 70)

    soc_ratio = soc / capacity

    can_charge = soc_ratio < 0.90
    can_discharge = soc_ratio > 0.10

    #QRF based decision 

    strong_upside = (q90 - current_price) > 10

    if (current_price < p30 and strong_upside and can_charge):
        return 'charge'
    elif (current_price > p70 and can_discharge):
        return 'discharge'
    else:
        return 'idle'
    



def backtest(test_df, predictions, initial_soc=50):
    soc_naive = initial_soc
    soc_smart = initial_soc
    
    revenue_naive = 0
    revenue_smart = 0
    
    # store results for analysis
    results = []
    
    for i in range(len(test_df)):
        current_price = test_df['settlementPointPrice'].iloc[i]
        hour = test_df['timestamp'].iloc[i].hour
        
        q10, q50, q90 = predictions[i, 0], predictions[i, 1], predictions[i, 2]
        
        # recent prices for dynamic threshold
        recent_prices = test_df['settlementPointPrice'].iloc[max(0, i-24):i].values
        
        # naive decision
        action_naive = naive_strategy(hour, soc_naive)
        soc_naive, cf_naive = dispatch(action_naive, soc_naive, current_price)
        revenue_naive += cf_naive
        # smart decision
        action_smart = smart_strategy(current_price, q10, q50, q90, soc_smart, recent_prices)
        soc_smart, cf_smart = dispatch(action_smart, soc_smart, current_price)
        revenue_smart += cf_smart
        
        # dispatch both
        results.append({
            'timestamp': test_df['timestamp'].iloc[i],
            'actual_price': current_price,
            'predicted_price': q50,
            'soc_naive': soc_naive,
            'soc_smart': soc_smart,
            'action_naive': action_naive,
            'action_smart': action_smart,
            'cashflow_naive': cf_naive,
            'cashflow_smart': cf_smart
        })      
        # track results
        
    return pd.DataFrame(results)