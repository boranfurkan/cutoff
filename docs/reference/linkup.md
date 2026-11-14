# Linkup reference

Condensed from `docs/vendor/linkup/` (fetched 14 Nov 2026). Where this file and the vendor docs differ, the vendor docs win.

## Basics
- Base URL `https://api.linkup.so`, endpoints `POST /v1/search` and `POST /v1/fetch`. Auth: `Authorization: Bearer <key>`.
- Python: `pip install linkup-sdk`, `from linkup import LinkupClient`, `LinkupClient()` reads `LINKUP_API_KEY`.
- Rate limit: 10 queries per second per organization.
- Errors are not billed. Out of credit returns HTTP 429.

## Search: `client.search(...)`

| Parameter | Values | Notes |
|---|---|---|
| `query` | str | required |
| `depth` | `"flash"`, `"fast"`, `"standard"`, `"deep"` | required |
| `output_type` | `"searchResults"`, `"sourcedAnswer"`, `"structured"` | required |
| `structured_output_schema` | pydantic model or JSON-schema string | required for `structured`; root must be an object; keep it shallow |
| `include_domains` / `exclude_domains` | list of str | up to 100 include domains |
| `from_date` / `to_date` | `datetime.date` | prefer these over dates in the query |
| `include_inline_citations` | bool | for `sourcedAnswer`: adds [1], [2] markers |
| `include_sources` | bool | for `structured`: wraps the result with its sources |
| `max_results` | int | limits result count |
| `include_images` | bool | |

Depths:
- `flash` (alpha): under 200 ms, keyword only, no LLM, no scraping.
- `fast`: about 1 s, keyword only.
- `standard`: 1–3 s, one agentic pass; can scrape **one** URL given in the query.
- `deep`: 5–30 s, up to 10 iterations; can chain search → scrape → search.

Output types:
- `searchResults`: list of `{name, url, content}`. Best when Claude reasons over the sources.
- `sourcedAnswer`: `.answer` plus sources. Best for showing a person.
- `structured`: JSON matching the schema. Best for code.

## Fetch: `client.fetch(url=..., mode=None, render_js=None, include_raw_html=None)`
Returns the page as cleaned markdown. `mode="pro"` for hard pages; `render_js=True` for JavaScript-rendered pages. The HTTP API also accepts `schema` (+ `instructions`) for structured extraction from a known page.

## Cost (from $20 of credit)

| Call | Cost |
|---|---|
| search, flash/fast/standard, `searchResults` | $0.005 |
| search, flash/fast/standard, `sourcedAnswer`/`structured` | $0.006 |
| search, deep, `searchResults` | $0.05 |
| search, deep, `sourcedAnswer`/`structured` | $0.055 |
| fetch standard | $0.001 ($0.005 with `render_js`) |
| fetch pro | $0.005 ($0.01 with `render_js`) |

$20 is roughly 4,000 standard searches or 360 deep ones. Default to `standard` + `fetch`; reserve `deep` for when a standard search fails to find the changelog.

## Query writing
- Keyword style for flash/fast; instruction style for standard/deep: "Find the changelog for X 2.0. Scrape it. Extract breaking changes."
- Say what to **find**, not what to conclude. Reasoning stays on our side.
- For chains, state the order: "First find X. Then scrape X. Then extract Y."

## How Cutoff uses it
1. `search(query="<package> <new version> changelog breaking changes migration guide", depth="standard", output_type="searchResults", include_domains=[project docs, github.com, pypi.org])` to locate the page.
2. `fetch(url)` to read the full changelog as markdown.
3. Keep the URL and a short supporting quote with every extracted rule; these become the pull-request citations.

## MCP server and skills (for development, not the product)
- Hosted MCP: `claude mcp add --transport http linkup https://mcp.linkup.so/mcp --header "Authorization: Bearer YOUR_API_KEY"`. Tools: `linkup-search`, `linkup-fetch`.
- Local MCP: `npx -y linkup-mcp-server apiKey=YOUR_API_KEY`.
- Skills: `npx skills add LinkupPlatform/skills` (five skills; source at github.com/LinkupPlatform/skills).

The product calls the Python SDK directly. The MCP server is only useful for exploring Linkup from a Claude Code session.
