import unittest
from datetime import date
from finance import replay

ASSETS=[{'id':1,'name':'纳斯达克'}]
def event(i,day,kind,amount,price,fee=0):
    return dict(id=i,asset_id=1,day=day,kind=kind,amount=amount,price=price,fee=fee,note='')

class LedgerTests(unittest.TestCase):
    def test_cash_one_year(self):
        s=replay(10000,'2025-01-01',ASSETS,[],date(2026,1,1))
        self.assertAlmostEqual(s['total'],10100,places=6)
        self.assertAlmostEqual(s['annualized'],1,places=6)

    def test_buy_quote_partial_sell_cost_and_fees(self):
        events=[event(1,'2026-01-01','buy',1000,10,10),event(2,'2026-01-01','quote',0,12),event(3,'2026-01-01','sell',600,12,5)]
        s=replay(2000,'2026-01-01',ASSETS,events,date(2026,1,1)); p=s['holdings'][0]
        self.assertEqual(p['units'],50)
        self.assertEqual(p['cost'],505)
        self.assertEqual(p['realized'],90)
        self.assertEqual(p['unrealized'],95)
        self.assertEqual(s['cash'],1585)
        self.assertEqual(s['profit'],185)
        self.assertEqual(s['total'],2185)
        self.assertAlmostEqual(s['return_pct'],9.25)

    def test_overspend_and_oversell(self):
        for e in [event(1,'2026-01-01','buy',1001,1),event(1,'2026-01-01','sell',1,1)]:
            with self.assertRaises(ValueError): replay(1000,'2026-01-01',ASSETS,[e],date(2026,1,1))

    def test_tiny_positions_cannot_be_oversold(self):
        events=[event(1,'2026-01-01','buy',1,1e12),event(2,'2026-01-01','sell',2,1e12)]
        with self.assertRaises(ValueError): replay(1000,'2026-01-01',ASSETS,events,date(2026,1,1))

    def test_backdated_replay_invalidates_later_trade(self):
        events=[event(2,'2026-01-01','buy',800,10),event(1,'2026-01-02','buy',500,10)]
        with self.assertRaises(ValueError): replay(1000,'2026-01-01',ASSETS,events,date(2026,1,2))

    def test_daily_carry_and_drawdown(self):
        events=[event(1,'2026-01-01','buy',1000,10),event(2,'2026-01-02','quote',0,8)]
        s=replay(1000,'2026-01-01',ASSETS,events,date(2026,1,3))
        self.assertEqual(s['total'],800)
        self.assertAlmostEqual(s['drawdown'],-20)
        self.assertEqual(s['curve'][-1]['values']['1'],800)

if __name__=='__main__': unittest.main()
