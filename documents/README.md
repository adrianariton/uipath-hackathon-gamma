# SEC Filings Snapshot

This folder contains the most recent 10-K and 10-Q filings pulled directly from the SEC EDGAR archive for:
- Apple (AAPL)
- Amazon (AMZN)
- Microsoft (MSFT)
- Alphabet/Google (GOOGL)
- NVIDIA (NVDA)

For each company you get two files per form:
- `<FORM>-<FILING_DATE>-raw.html` — the original filing from EDGAR.
- `<FORM>-<FILING_DATE>.txt` — a lightly cleaned text version for quick inspection/RAG ingestion. The HTML-to-text pass is intentionally minimal; consider a richer cleaner if you need better structure.

To refresh everything, run from the repo root:
```
python documents/fetch_filings.py
```
The script respects SEC User-Agent guidance and waits between requests. If you have trouble reaching EDGAR, update the contact email in the script header to something appropriate for your team.
