# test/fixtures — the source of each fixture's shape

Every value is synthetic, and no real ledger is included. The shapes (column order, keys, how lines are grouped, and the format of dates and amounts) follow the sources below, as checked on 2026-10-22.

| File | Shape source |
|---|---|
| `parity.edn` | kaikei's own table. The guest's `test-*` copy the same rows. |
| `xero-accounts.json` | XeroAPI/Xero-OpenAPI `5a115f3`, `xero_accounting.yaml`: the `GET /Accounts` example and the `Account` schema (`Type` and `Class`). |
| `xero-manual-journals.json` | Same yaml: the `GET /ManualJournals/{ManualJournalID}` example (L10477), with `Status` values `POSTED`, `DRAFT` and `VOIDED`, and `LineAmountTypes` values `NoTax` and `Exclusive`. |
| `xero-journals.json` | Same yaml: the `GET /Journals` example (L9417). `NetAmount` is positive for a debit and negative for a credit. |
| `qbo-accounts.json` | intuit/QuickBooks-V3-Java-SDK `c4d5dfa` (`Finance.xsd`), plus the Account query response sample in Intuit's developer docs. The sub-account `Truck:Original Cost` comes from the JournalEntry sample in the same docs. |
| `qbo-journal-entries.json` | The JournalEntry query response sample in Intuit's developer docs, plus `Finance.xsd`: `PostingType` and `Entity`/`DepartmentRef`. |
| `yayoi.csv` | Yayoi support "仕訳データの項目と記述形式" (page_id=18545): 25 fields, no header row, `#` comment lines, and the flags 2000, 2110, 2100, 2101 and 2111. Invoice qualifiers in 税区分 follow the 税区分 記述形式 page (page_id=18111). |
| `yayoi-sjis.txt` | The same text as `yayoi.csv`, encoded with Python's `cp932` codec. Used to compare kaikei's Shift_JIS encoder and decoder against an independent implementation. |
| `mf.csv` | MoneyForward Cloud Accounting guide "「仕訳帳」をインポートする" (import-books/ib01): 27 columns A–AA, and a compound entry with the same 取引No and 取引日. The invoice value `80％控除` uses a full-width ％. |
| `freee.csv` | The freee import template attached to help article 204847430: the 33-column header verbatim, and `[表題行]`/`[明細行]`. The first data row follows the template's own first row, with the trading partner's name changed. |
| `qbo-journal.csv` | QuickBooks Help "Import journal entries" (US). Columns are Journal No., Journal Date, Account Name, Debits, Credits, Description, Name and Location; the sub-account is written `Parent:Sub`. Dates are US mm/dd/yyyy. |
| `xero-manual-journal.csv` | Xero Central "Add, import and post manual journals" (UK). Only the first row of a journal has Narration and Date, the Amount is signed, and dates are dd/mm/yyyy. Whether the header has the `*` prefix is unverified. |

Line endings are CRLF.
