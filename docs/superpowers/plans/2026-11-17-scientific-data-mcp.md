# scientific-data-mcp v0.1.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a free, keyless FastMCP server for scientific entity data across PubChem, ChEMBL, UniProt, RCSB PDB and PubMed E-utilities, maintained by DSH.

**Architecture:** One FastMCP server. Per-source providers own URL construction, pagination and field normalization; per-domain tool modules own the LLM-facing schema, validation and error wrapping. All HTTP goes through one `PoliteClient` with per-host pacing and retry; tools never raise.

**Tech Stack:** Python 3.10+, `mcp[cli]>=1.27,<2` (FastMCP 1.x), `httpx`, `respx` + `pytest` + `pytest-asyncio`, `ruff`, `hatchling` + `hatch-vcs`, Docker.

**Spec:** `docs/superpowers/specs/2026-11-17-scientific-data-mcp-design.md`

## Global Constraints

- Python `>=3.10`; every module starts with `from __future__ import annotations`.
- Distribution `scientific-data-mcp`, import package `scientific_data_mcp`, CLI `scientific-data-mcp`.
- No required API keys. `NCBI_API_KEY` is optional and only raises the E-utilities rate from 3/s to 10/s.
- Tools **never raise**: every failure path returns `{"error": str, "source": str, "hint"?: str}`.
- Responses only carry upstream fields; missing fields are omitted, never invented. No timestamps in payloads.
- Httpx calls only through `PoliteClient`; tests use `respx` and perform zero egress.
- `next_cursor`/`next_offset` are `None` when no further page exists.
- ruff: line-length 100, rules `E,F,I,UP,B`; ignore `E501`.
- Version comes only from git tags (`hatch-vcs`); never hardcode `version` in `pyproject.toml`.

## Review Focus

- Identifier containing `/`, `\`, `(`, `)`, `#`, `=`, `[`, `]` or `+` — must go through POST form for PubChem SMILES, URL-encoded path for others; a raw path segment must not 400 or silently mis-query.
- Upstream 404 (unknown CID/accession/PDB/PMID) — returns a `not_found` error dict, never an exception or a fabricated record.
- Upstream 429/503 with and without `Retry-After` — bounded retries, then a `rate_limited` error dict.
- Empty result sets (ChEMBL activity list, UniProt search, RCSB search, PubMed idconv miss) — `count: 0` with empty `items`, not an error, except an unresolvable DOI which is `not_found`.
- Both/neither of `chembl_id`/`target_chembl_id`, and both/neither of `pmid`/`doi` — a clear `error` dict naming the valid combinations.

---

### Task 1: Foundation — settings, errors, polite HTTP client

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/scientific_data_mcp/__init__.py`, `src/scientific_data_mcp/config.py`, `src/scientific_data_mcp/errors.py`, `src/scientific_data_mcp/http.py`
- Test: `tests/test_config.py`, `tests/test_http.py`

**Interfaces:**
- Produces: `Settings` dataclass with `ncbi_api_key: str | None`, `timeout: float = 20.0`, `max_retries: int = 3`, `user_agent: str`, `host_delays: dict[str, float]`; `Settings.from_env() -> Settings`.
- Produces: `ProviderError`, `RateLimited`, `AuthError`, `NotFound`, `UpstreamError` (each with `kind` and `retryable`), `tool_error(msg: object, hint: str | None = None, **extra: object) -> dict`, `scrub(text: str, *secrets: str) -> str`.
- Produces: `PoliteClient(settings: Settings)` with `async get_response(url, params=None, headers=None) -> httpx.Response`, `async get_json(...) -> Any`, `async get_text(...) -> str`, `async post_json(url, json_body, headers=None) -> Any`, `async post_form(url, fields, headers=None) -> Any`, `async aclose()`, async context manager.

- [ ] **Step 1: Write failing tests** — `tests/test_config.py`: `Settings.from_env()` with `NCBI_API_KEY="k"` set returns `ncbi_api_key == "k"`; with it blank returns `None`; `Settings().host_delays["eutils.ncbi.nlm.nih.gov"] == 0.34`. `tests/test_http.py`: respx 404 → `pytest.raises(NotFound)`; respx 429 then 200 → `get_json` returns the body and route called twice; 401 → `AuthError`; 500 → `UpstreamError`; pacing: `Settings(host_delays={"api.test": 0.05})`, two `get_json` calls take ≥0.04s.
- [ ] **Step 2: Run tests, confirm failure** — `pytest tests/test_config.py tests/test_http.py -q` fails on missing modules.
- [ ] **Step 3: Implement** — `PoliteClient` keeps one `httpx.AsyncClient(timeout=settings.timeout, headers={"User-Agent": settings.user_agent}, follow_redirects=True)`; per-host `asyncio.Lock`+`_last` pacing; retry loop on network errors and 429/503 honoring numeric `Retry-After` capped at 10s, else `0.5 * 2**attempt`; status map 401/403→`AuthError`, 404→`NotFound`, ≥400→`UpstreamError`; `tool_error` shape `{"error": ..., "hint"?: ...}`.
- [ ] **Step 4: Run tests, confirm pass** — `pytest tests/test_config.py tests/test_http.py -q` all pass.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: foundation — settings, error taxonomy, polite http client"`.

### Task 2: PubChem provider

**Files:**
- Create: `src/scientific_data_mcp/providers/__init__.py`, `src/scientific_data_mcp/providers/base.py`, `src/scientific_data_mcp/providers/pubchem.py`
- Test: `tests/test_pubchem.py`

**Interfaces:**
- Consumes: `PoliteClient`, `Settings`, `NotFound`.
- Produces: `class Provider: name: str; base_url: str; def __init__(self, http: PoliteClient, settings: Settings)`.
- Produces: `PubChemProvider(http, settings)` with `name = "pubchem"`, `base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"`, `async resolve_cid(identifier: str, id_type: str) -> int`, `async properties(cid: int, properties: list[str] | None = None) -> dict`, `async synonyms(cid: int, limit: int = 20) -> list[str]`, `async compound(identifier: str, id_type: str) -> dict`, `async similar_cids(smiles: str, threshold: int = 90, max_records: int = 20) -> list[int]`.
- Normalized compound keys: `cid`, `molecular_formula`, `molecular_weight`, `iupac_name`, `canonical_smiles`, `isomeric_smiles`, `inchikey`, `xlogp`, `tpsa`, `h_bond_donors`, `h_bond_acceptors`, `rotatable_bonds`, `heavy_atoms`, `charge`, `complexity`, `synonyms`.

- [ ] **Step 1: Write failing tests** — respx GET `.../compound/name/aspirin/cids/JSON` → `{"IdentifierList":{"CID":[2244]}}`; `.../compound/cid/2244/property/.../JSON` → `{"PropertyTable":{"Properties":[{"CID":2244,"MolecularFormula":"C9H8O4","MolecularWeight":"180.16","XLogP":1.2}]}}`; `.../compound/cid/2244/synonyms/JSON`; POST `.../compound/smiles/cids/JSON` (assert request body carries `smiles=C[C@H](N)C(=O)O`); similarity POST → 202 `{"Waiting":{"ListKey":"k1"}}`, then GET `.../compound/listkey/k1/cids/JSON` → `{"IdentifierList":{"CID":[1,2]}}`; missing CID → `NotFound`. Assert mapping drops absent fields (no `xlogp` key when upstream omits it).
- [ ] **Step 2: Run, confirm failure** — `pytest tests/test_pubchem.py -q`.
- [ ] **Step 3: Implement** — name/inchikey as GET path with `urllib.parse.quote(identifier, safe="")`; smiles via `post_form`; similarity via `post_form` with `{"smiles":..., "Threshold":..., "MaxRecords":...}`, then poll `listkey` up to 10 times with 0.5s sleep (cap 10s total), raising `NotFound` on exhausted polling; property whitelist constant `_PROPERTIES` mapping PubChem names → snake_case.
- [ ] **Step 4: Run, confirm pass** — `pytest tests/test_pubchem.py -q`.
- [ ] **Step 5: Commit** — `git commit -am "feat: pubchem provider"`.

### Task 3: Chemistry tools, server assembly and CLI

**Files:**
- Create: `src/scientific_data_mcp/runtime.py`, `src/scientific_data_mcp/server.py`, `src/scientific_data_mcp/__main__.py`, `src/scientific_data_mcp/tools/__init__.py`, `src/scientific_data_mcp/tools/chemistry.py`
- Test: `tests/test_server.py`, `tests/test_tools_chemistry.py`

**Interfaces:**
- Produces: `build_service(settings: Settings | None = None) -> Service` with fields `settings`, `http: PoliteClient`, `providers: dict[str, Provider]` (`"pubchem"` registered now).
- Produces: `build_server(service: Service | None = None) -> FastMCP` registering every tool in `tools.register_all`.
- Produces tools: `chem_compound(identifier: str, id_type: str = "name")`, `chem_compound_properties(cid: int, properties: list[str] | None = None)`, `chem_similar_compounds(smiles: str, threshold: int = 90, max_records: int = 20)`.
- Envelope: record tools return `{"source": "pubchem", "source_url": str, "record": dict}`; list tools return `{"source": "pubchem", "count": int, "items": list}`.

- [ ] **Step 1: Write failing tests** — `test_server.py`: `await build_server().list_tools()` names include the three `chem_*` tools. `test_tools_chemistry.py` (respx): `chem_compound("aspirin")` returns `record["cid"] == 2244` and `source == "pubchem"`; unknown CID 404 → `{"error": ..., "source": "pubchem"}`, no exception; `chem_similar_compounds` returns `count == 2`; invalid `id_type="foo"` returns error dict mentioning allowed values.
- [ ] **Step 2: Run, confirm failure** — `pytest tests/test_server.py tests/test_tools_chemistry.py -q`.
- [ ] **Step 3: Implement** — tool functions are closures inside `register(mcp, service)` calling `mcp.tool(name=...)`; each wraps provider calls in `try/except ProviderError as e: return tool_error(f"{e.kind}: {e}", source=...)`; validate `id_type` against `{"name","cid","smiles","inchikey"}` and `cid >= 1`; `__main__.main()` parses `--http --host --port`, defaults to stdio, and calls `mcp.run(transport="streamable-http")` when `--http`; set `mcp.settings.host/port` before running.
- [ ] **Step 4: Run, confirm pass**; also `python -c "from scientific_data_mcp.__main__ import main"` and `scientific-data-mcp --help` (after `uv pip install -e .`).
- [ ] **Step 5: Commit** — `git commit -am "feat: chemistry tools, server assembly, CLI"`.

### Task 4: ChEMBL provider and tools

**Files:**
- Create: `src/scientific_data_mcp/providers/chembl.py`
- Modify: `src/scientific_data_mcp/runtime.py`, `src/scientific_data_mcp/tools/chemistry.py`
- Test: `tests/test_chembl.py`, extend `tests/test_tools_chemistry.py`

**Interfaces:**
- Produces: `ChemBLProvider(http, settings)` with `base_url = "https://www.ebi.ac.uk/chembl/api/data"`, `async search(resource: str, query: str, limit: int, offset: int) -> tuple[list[dict], int]` (items, total), `async molecule(chembl_id: str) -> dict`, `async target(chembl_id: str) -> dict`, `async activities(chembl_id: str | None, target_chembl_id: str | None, limit: int, offset: int) -> tuple[list[dict], int]`, `async mechanisms(chembl_id: str) -> list[dict]`.
- Produces tools: `chembl_search(resource: str, query: str, limit: int = 10, offset: int = 0)`, `chembl_bioactivity(chembl_id: str | None = None, target_chembl_id: str | None = None, limit: int = 20, offset: int = 0)`, `chembl_mechanisms(chembl_id: str)`.
- List envelope gains `next_offset: int | None`; ChEMBL pagination reads `page_meta.next` (None → no next page).

- [ ] **Step 1: Write failing tests** — molecule GET `/molecule/CHEMBL25.json` → normalized `pref_name == "ASPIRIN"`, `canonical_smiles` present; search `GET /molecule.json?search_parameters__q=imatinib&limit=2` → `("items" len 1, total 1)`; activities with `page_meta.next=null` → `next_offset None`; both/neither ids → tool error mentioning `chembl_id` and `target_chembl_id`; 404 → error dict.
- [ ] **Step 2: Run, confirm failure.**
- [ ] **Step 3: Implement** — quote ChEMBL ids; activities request passes exactly one filter; normalize molecule (`molecule_chembl_id`, `pref_name`, `molecule_type`, `max_phase`, `first_approval`, `black_box_warning`, `canonical_smiles`, `isomeric_smiles`, `standard_inchi_key`, `molecule_properties` subset `mw_freebase`,`full_mwt`,`alogp`,`psa`,`hba`,`hbd`,`rtb`,`num_ro5_violations`); activities (`activity_id`,`molecule_chembl_id`,`target_chembl_id`,`standard_type`,`standard_value`,`standard_units`,`pchembl_value`,`assay_chembl_id`); mechanisms (`molecule_chembl_id`,`target_chembl_id`,`mechanism_of_action`,`action_type`,`direct_interaction`).
- [ ] **Step 4: Run `pytest tests/test_chembl.py tests/test_tools_chemistry.py -q`** — pass.
- [ ] **Step 5: Commit** — `git commit -am "feat: chembl provider and chemistry tools"`.

### Task 5: UniProt provider and protein tools

**Files:**
- Create: `src/scientific_data_mcp/providers/uniprot.py`, `src/scientific_data_mcp/tools/protein.py`
- Modify: `src/scientific_data_mcp/runtime.py`, `src/scientific_data_mcp/tools/__init__.py`
- Test: `tests/test_uniprot.py`, `tests/test_tools_protein.py`

**Interfaces:**
- Produces: `UniProtProvider(http, settings)` with `base_url = "https://rest.uniprot.org"`, `async entry(accession: str, include_sequence: bool = False) -> dict`, `async search(query: str, size: int = 10, cursor: str | None = None) -> dict` returning `{"items": [...], "next_cursor": str | None, "total"?: int}`, `async map_ids(from_db: str, to_db: str, ids: str, timeout: float = 30.0) -> dict` returning `{"job_id": str, "mappings": dict[str, list[str]]}`.
- Produces tools: `protein_entry(accession: str, include_sequence: bool = False)`, `protein_search(query: str, size: int = 10, cursor: str | None = None)`, `protein_map_ids(from_db: str, to_db: str, ids: str)`.
- Entry keys: `accession`, `entry_name`, `protein_name`, `genes` (list), `organism`, `taxid`, `reviewed`, `function`, `keywords`, `sequence_length`, `sequence_mass`, `pdb_ids`, optional `sequence`.

- [ ] **Step 1: Write failing tests** — entry JSON fixture (P05067-like) → normalized keys and `pdb_ids` extracted from `uniProtKBCrossReferences`; `sequence` absent unless requested; search fixture with `Link: <...cursor=abc&size=2>; rel="next"` → `next_cursor == "abc"`, and no Link → `None`; idmapping: POST run → `{"jobId":"j1"}`, status → `{"jobStatus":"FINISHED"}`, results → `{"results":[{"from":"P04637","to":"1A1U"}]}` → `mappings == {"P04637":["1A1U"]}`; 404 → error dict.
- [ ] **Step 2: Run, confirm failure.**
- [ ] **Step 3: Implement** — parse cursor from the `Link` header via `urlparse`/`parse_qs`; poll status every 0.5s until `jobStatus == "FINISHED"` or deadline, raising `UpstreamError("idmapping timed out")`; protein name prefers `recommendedName.fullName.value` then first `submissionNames`; function joins `comments` of type `FUNCTION`.
- [ ] **Step 4: Run `pytest tests/test_uniprot.py tests/test_tools_protein.py -q`** — pass.
- [ ] **Step 5: Commit** — `git commit -am "feat: uniprot provider and protein tools"`.

### Task 6: RCSB PDB provider and structure tools

**Files:**
- Create: `src/scientific_data_mcp/providers/rcsb.py`
- Modify: `src/scientific_data_mcp/runtime.py`, `src/scientific_data_mcp/tools/protein.py`
- Test: `tests/test_rcsb.py`, extend `tests/test_tools_protein.py`

**Interfaces:**
- Produces: `RcsbProvider(http, settings)` with `data_base = "https://data.rcsb.org/rest/v1/core"`, `search_base = "https://search.rcsb.org/rcsbsearch/v2/query"`, `async entry(pdb_id: str) -> dict`, `async entity(pdb_id: str, entity_id: str) -> dict`, `async search(query: str, rows: int = 10, start: int = 0) -> dict` returning `{"total": int, "identifiers": list[str], "next_start": int | None}`.
- Produces tools: `protein_structure(pdb_id: str)`, `protein_structure_search(query: str, rows: int = 10, start: int = 0)`.
- Entry keys: `pdb_id`, `title`, `method`, `resolution`, `deposited`, `polymer_entity_ids`, `entities` (list of `{"entity_id","description","type","chains","length"}` capped at 5).

- [ ] **Step 1: Write failing tests** — entry fixture 4HHB with `rcsb_entry_container_identifiers.polymer_entity_ids ["1","2"]` and two entity fixtures → `len(record["entities"]) == 2`, `title` starts "THE CRYSTAL STRUCTURE"; search POST body asserts `query.type == "terminal"`, `service == "full_text"`, `parameters.value == "hemoglobin"`; response `{"total_count":569,"result_set":[{"identifier":"1A3N"}]}` → `total == 569`, `next_start == 10`; unknown PDB 404 → error dict.
- [ ] **Step 2: Run, confirm failure.**
- [ ] **Step 3: Implement** — uppercase PDB ids; entity description from `rcsb_polymer_entity.pdbx_description`, type from `entity_poly.type`, chains from `rcsb_polymer_entity_container_identifiers.auth_asym_ids`, length from `entity_poly.rcsb_sample_sequence_length`.
- [ ] **Step 4: Run tests** — pass.
- [ ] **Step 5: Commit** — `git commit -am "feat: rcsb pdb provider and structure tools"`.

### Task 7: PubMed E-utilities provider and record tool

**Files:**
- Create: `src/scientific_data_mcp/providers/pubmed.py`, `src/scientific_data_mcp/tools/literature.py`
- Modify: `src/scientific_data_mcp/runtime.py`, `src/scientific_data_mcp/tools/__init__.py`
- Test: `tests/test_pubmed.py`, `tests/test_tools_literature.py`

**Interfaces:**
- Produces: `PubMedProvider(http, settings)` with `efetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"`, `idconv_url = "https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/"`, `async by_pmid(pmid: str) -> dict`, `async by_doi(doi: str) -> dict` (resolves then fetches).
- Produces tool: `pubmed_record(pmid: str | None = None, doi: str | None = None)`.
- Record keys: `pmid`, `doi`, `pmcid`, `title`, `authors` (list of `"Family Given"` or collective), `journal`, `year`, `volume`, `issue`, `pages`, `abstract`.

- [ ] **Step 1: Write failing tests** — efetch XML fixture with two `AbstractText` sections (one labelled) → `abstract` contains both texts, `authors[0] == "Doe Jane"`, `doi`/`pmcid` extracted from `ArticleIdList`; DOI path: idconv JSON `{"records":[{"pmid":"123"}]}` then efetch; idconv `{"records":[{}]}` → `NotFound`; both/neither params → tool error; efetch 500 → `{"error": ...}`.
- [ ] **Step 2: Run, confirm failure.**
- [ ] **Step 3: Implement** — `xml.etree.ElementTree.fromstring`; `AbstractText` join using `itertext()` and prefix `Label + ": "` when present; `api_key` param only when `settings.ncbi_api_key`; include `tool=scientific-data-mcp` and `email` omitted.
- [ ] **Step 4: Run `pytest tests/test_pubmed.py tests/test_tools_literature.py -q`** — pass.
- [ ] **Step 5: Commit** — `git commit -am "feat: pubmed record provider and tool"`.

### Task 8: Tool surface lock, DSH docs, memory migration, packaging

**Files:**
- Create: `AGENTS.md`, `README.md` (rewrite), `LICENSE`, `.dockerignore`, `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `scripts/live_smoke.py`, `docs/memory/MEMORY.md` + 6 notes, `docs/research/kimi-sources/README.md`
- Modify: `docs/计划.md` (status header only), `tests/test_server.py` (12-tool assertion)
- Test: `tests/test_server.py`

**Interfaces:**
- Produces: exactly 12 tools: `chem_compound`, `chem_compound_properties`, `chem_similar_compounds`, `chembl_search`, `chembl_bioactivity`, `chembl_mechanisms`, `protein_entry`, `protein_search`, `protein_map_ids`, `protein_structure`, `protein_structure_search`, `pubmed_record`.

- [ ] **Step 1: Write failing test** — `assert {t.name for t in await build_server().list_tools()} == EXPECTED_12`.
- [ ] **Step 2: Run, confirm failure** if any tool missing; fix registration until pass.
- [ ] **Step 3: Write docs** — AGENTS.md: 定位/边界、命令、纪律、记忆索引指针、codegraph/firecrawl 工具纪律。`docs/memory/` notes: kimi 五源裁决（含“kimi 侧无需改动，science 源仅这五个且全是免费 1:1 镜像”）、hatch-vcs 发布、secrets/配额、境外 API 退避、tool description 纪律、sibling 边界。README：定位表、5 源、12 工具表、安装/运行/mcpo 配置、免 key 声明、边界。
- [ ] **Step 4: Packaging + CI** — Dockerfile python:3.12-slim, non-root, `pip install .`, `ENTRYPOINT ["scientific-data-mcp"]`; compose stdio 不适用，提供 `--http` 服务示例；CI matrix 3.10/3.12: ruff + pytest; live smoke script calls all 12 tools once and prints PASS/FAIL table (excluded from CI).
- [ ] **Step 5: Commit** — `git commit -am "docs: DSH maintenance, memory migration, packaging"`.

### Task 9: Full verification, GitHub, codegraph, tag

**Files:** none new.

- [ ] **Step 1:** `uv venv --python 3.12 && uv pip install -e '.[dev]' && pytest -q && ruff check .` — all green, 0 skips except live.
- [ ] **Step 2:** `python scripts/live_smoke.py` — 12/12 PASS against real APIs.
- [ ] **Step 3:** `docker build -t scientific-data-mcp:dev .` — success; `docker run --rm scientific-data-mcp:dev --help`.
- [ ] **Step 4:** `gh repo create xyonium/scientific-data-mcp --public --source=. --remote=origin --push`; set description/topics.
- [ ] **Step 5:** `codegraph init` at repo root; `codegraph status` shows the 12 tools; `codegraph explore "chem_compound"` returns source.
- [ ] **Step 6:** `git tag v0.1.0 && git push origin main --tags`; confirm CI green via `gh run list`.
