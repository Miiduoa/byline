# Byline

[![ci](https://github.com/Miiduoa/byline/actions/workflows/ci.yml/badge.svg)](https://github.com/Miiduoa/byline/actions/workflows/ci.yml)

資料檔改了，報表還能不能照跑？

Byline 是一個小型 CSV contract checker。它把資料集的欄位、型別、缺值率與檔案指紋存成 manifest；之後資料更新時，可以在 pipeline 真正執行前先檢查是否出現 breaking change。

我做這個工具的原因很單純：很多分析錯誤不是模型造成的，而是上游 CSV 悄悄改欄名、型別或資料內容，直到報表壞掉才被發現。

## 目前做得到

- 建立 CSV manifest：row count、欄位、推斷型別、null rate、unique count、SHA-256
- 比較新資料與既有 contract
- 區分 breaking / warning
  - 欄位消失：breaking
  - 欄位型別改變：breaking
  - 新增欄位：warning
  - 缺值率明顯上升：warning
- CLI 以 exit code 回報結果，方便接 CI
- manifest 是普通 JSON，可直接 code review

## Quick start

```bash
python -m pip install -e .

byline snapshot examples/orders_v1.csv --out contracts/orders.json
byline check examples/orders_v2.csv --contract contracts/orders.json
```

成功時 exit code 是 `0`；偵測到 breaking change 時是 `2`。

## Example

```text
$ byline check examples/orders_v2.csv --contract contracts/orders.json

contract: contracts/orders.json
dataset:  examples/orders_v2.csv

BREAKING
- column removed: customer_id
- type changed: amount (float -> text)

WARNING
- new column: coupon_code
```

## 設計取捨

Byline 不做 schema registry，也不假裝自己是完整 data observability 平台。它只處理「進 repo 的小型表格資料，能不能在 PR / CI 階段先擋掉明顯破壞」這件事。

型別推斷刻意保持簡單：`integer`、`float`、`boolean`、`date`、`datetime`、`text`。如果同一欄出現互相衝突的值，會退回 `text`，避免過度猜測。

## Test

```bash
python -m unittest discover -s tests -v
```

## Repo structure

```text
src/byline/        core + CLI
tests/             contract comparison tests
examples/          small reproducible fixtures
.github/workflows  CI
```

## License

MIT
