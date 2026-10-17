"""Deterministic ledger: all trades settle against the cash account."""
from datetime import date, timedelta
import math


def replay(initial, start, assets, events, end=None):
    end = end or date.today()
    start = date.fromisoformat(start)
    if start > end:
        raise ValueError('起始日期不能晚于今天')
    positions = {a['id']: dict(a, units=0., cost=0., price=0., realized=0.) for a in assets}
    cash = float(initial)
    interest = 0.
    curve, ledger = [], []
    ordered = sorted(events, key=lambda e: (e['day'], e['id']))
    idx = 0
    day = start
    while day <= end:
        if day > start:
            earned = cash * (1.01 ** (1 / 365) - 1)
            cash += earned
            interest += earned
        while idx < len(ordered) and ordered[idx]['day'] == day.isoformat():
            e = ordered[idx]
            p = positions[e['asset_id']]
            amount, price, fee = float(e['amount']), float(e['price']), float(e['fee'])
            realized = 0.
            if e['kind'] == 'buy':
                if amount + fee > cash + 1e-7:
                    raise ValueError(f"{e['day']} 可用现金不足（买入及费用共 {amount + fee:.2f} 元）")
                p['units'] += amount / price
                p['cost'] += amount + fee
                cash -= amount + fee
            elif e['kind'] == 'sell':
                units = amount / price
                if units > p['units'] and not math.isclose(units, p['units'], rel_tol=1e-12, abs_tol=0):
                    raise ValueError(f"{e['day']} 卖出份额超过持仓")
                basis = p['cost'] * min(1., units / p['units']) if p['units'] else 0.
                p['units'] = max(0., p['units'] - units)
                p['cost'] = max(0., p['cost'] - basis)
                realized = amount - fee - basis
                p['realized'] += realized
                cash += amount - fee
                if cash < -1e-7:
                    raise ValueError('现金不足以支付卖出手续费')
            p['price'] = price
            total = cash + sum(x['units'] * x['price'] for x in positions.values())
            ledger.append(dict(e, name=p['name'], cash=cash, units=p['units'], holding=p['units'] * price,
                               total=total, profit=total-initial, return_pct=(total/initial-1)*100,
                               realized=realized))
            idx += 1
        values = {str(k): p['units'] * p['price'] for k,p in positions.items()}
        total = cash + sum(values.values())
        curve.append(dict(day=day.isoformat(), total=total, cash=cash, profit=total-initial, values=values,
                          asset_profit={str(k): p['units']*p['price']-p['cost']+p['realized'] for k,p in positions.items()}))
        day += timedelta(days=1)
    peak = initial
    drawdown = 0.
    for row in curve:
        peak = max(peak, row['total'])
        drawdown = min(drawdown, row['total']/peak-1)
    holdings = []
    for p in positions.values():
        value = p['units'] * p['price']
        profit = value - p['cost'] + p['realized']
        invested = sum(e['amount']+e['fee'] for e in events if e['asset_id']==p['id'] and e['kind']=='buy')
        holdings.append(dict(p, value=value, unrealized=value-p['cost'], profit=profit,
                             return_pct=profit/invested*100 if invested else 0))
    total = curve[-1]['total']
    elapsed = (end-start).days
    exponent = math.log(total/initial)*365/elapsed if elapsed and total>0 else None
    annual = math.expm1(exponent)*100 if exponent is not None and exponent<700 else None
    return dict(initial=initial, start=start.isoformat(), total=total, cash=cash, interest=interest,
                profit=total-initial, return_pct=(total/initial-1)*100, annualized=annual,
                drawdown=drawdown*100, holdings=holdings, curve=curve, ledger=ledger)
