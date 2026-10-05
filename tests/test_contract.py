from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from byline.contract import compare_contract
from byline.profile import infer_type, load_contract, profile_csv, save_contract


class TypeInferenceTests(unittest.TestCase):
    def test_infers_common_types(self) -> None:
        self.assertEqual(infer_type(["1", "2", ""]), "integer")
        self.assertEqual(infer_type(["1.5", "2"]), "float")
        self.assertEqual(infer_type(["true", "false"]), "boolean")
        self.assertEqual(infer_type(["2026-10-05", "2026-10-06"]), "date")
        self.assertEqual(infer_type(["A12", "B15"]), "text")


class ContractTests(unittest.TestCase):
    def _write(self, root: Path, name: str, body: str) -> Path:
        path = root / name
        path.write_text(body, encoding="utf-8")
        return path

    def test_removed_column_and_type_change_are_breaking(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = self._write(
                root,
                "old.csv",
                "id,amount,customer_id\n1,10.5,c1\n2,11.0,c2\n",
            )
            new = self._write(
                root,
                "new.csv",
                "id,amount,coupon_code\n1,free,X\n2,12.0,\n",
            )
            contract_path = root / "contract.json"
            save_contract(profile_csv(old), contract_path)

            result = compare_contract(load_contract(contract_path), profile_csv(new))
            self.assertIn("column removed: customer_id", result.breaking)
            self.assertIn("type changed: amount (float -> text)", result.breaking)
            self.assertIn("new column: coupon_code", result.warnings)

    def test_null_rate_jump_warns(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            old = self._write(
                root,
                "old.csv",
                "id,city\n1,Taipei\n2,Taichung\n3,Tainan\n4,Kaohsiung\n",
            )
            new = self._write(
                root,
                "new.csv",
                "id,city\n1,\n2,\n3,Tainan\n4,\n",
            )
            result = compare_contract(
                profile_csv(old).to_dict(),
                profile_csv(new),
                null_rate_delta=0.20,
            )
            self.assertTrue(
                any("null rate increased: city" in w for w in result.warnings)
            )

    def test_contract_is_plain_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self._write(root, "data.csv", "id,value\n1,3\n2,4\n")
            target = root / "contract.json"
            save_contract(profile_csv(source), target)
            parsed = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(parsed["version"], 1)
            self.assertEqual(parsed["dataset"]["row_count"], 2)


if __name__ == "__main__":
    unittest.main()
