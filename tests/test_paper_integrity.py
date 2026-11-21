import json
import tempfile
import unittest
from pathlib import Path
from tradingagents.agents.paper_integrity import audit

class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "strategy.json").write_text(json.dumps({"mode":"PAPER_ONLY","season":"2026-11-05-paper-game-100k"}))
        (self.root / "portfolio.json").write_text(json.dumps({"mode":"PAPER_ONLY","transactions":[{"trade_id":"t1","date":"2026-11-12","ticker":"VWCE.DE"}]}))
    def tearDown(self):
        self.temp.cleanup()
    def test_missing_receipt_blocks(self):
        result=audit(self.root)
        self.assertEqual(result["status"],"BLOCKED_LEDGER_INCONSISTENCY")
        self.assertFalse(result["new_orders_allowed"])
        self.assertEqual(len(result["missing_receipts"]),1)
    def test_valid_receipt_passes(self):
        (self.root / "receipts").mkdir()
        (self.root / "receipts/2026-11-12.json").write_text(json.dumps({
            "session_date":"2026-11-12",
            "fills":[{"trade_id":"t1","date":"2026-11-12","ticker":"VWCE.DE",
                      "status":"PAPER_FILL_EOD_PROXY_NOT_EXECUTABLE","broker_order_sent":False,
                      "quote_and_fx":{"quote":{"date":"2026-11-12","executable":False,"source":"https://example.org/price"},
                                      "fx":{"date":"2026-11-12","source":"https://example.org/fx"}}}]}))
        self.assertTrue(audit(self.root)["new_orders_allowed"])
    def test_bad_evidence_blocks(self):
        (self.root / "receipts").mkdir()
        (self.root / "receipts/2026-11-12.json").write_text(json.dumps({
            "session_date":"2026-11-12","fills":[{"trade_id":"t1","date":"2026-11-12","ticker":"VWCE.DE"}]}))
        self.assertEqual(audit(self.root)["status"],"BLOCKED_LEDGER_INCONSISTENCY")

if __name__ == "__main__":
    unittest.main()
