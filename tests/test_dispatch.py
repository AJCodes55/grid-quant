from optimization.battery import dispatch, naive_strategy


def test_charge_empty_battery():
    new_soc, cash_flow = dispatch('charge', soc=0, price=20)
    assert new_soc == 21.25
    assert cash_flow == -500

def test_discharge_full_battery():
    new_soc, cash_flow = dispatch('discharge', soc=100, price=50)
    assert new_soc == 75
    assert cash_flow == 1062.50

def test_charge_hits_capacity():
    new_soc, cash_flow = dispatch('charge', soc=90, price=20)
    assert new_soc == 98.5
    assert cash_flow == -200

def test_idle_battery():
    new_soc, cash_flow = dispatch('idle', soc=50, price=20)
    assert new_soc == 50
    assert cash_flow == 0


def test_naive_charges_at_midnight():
    # hour 0, any SOC
    assert naive_strategy(0, 50) == "charge"


def test_naive_discharges_evening():
    # hour 18, any SOC
    assert naive_strategy(18, 50) == "discharge"


def test_naive_idles_midday():
    # hour 12, any SOC
    assert naive_strategy(12, 50) == "idle"