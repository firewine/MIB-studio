# MIB Studio FE v5 Critic Review

## User correction absorbed
- Removed marketing/explainer copy that described the product philosophy inside the UI.
- Replaced route key-in UX with a block-based Define workspace inspired by MIT App Inventor / block programming.
- v5 is a full-page mockup, not a partial Define-only screen. Sidebar navigation works across Workbench, Hardware, Define, Data, Train, AgentBench, Package, Export, and Settings.

## Critic pass 1 — Problems in v4
1. Define screen still relied on route-card text and explanatory prose instead of true block composition.
2. UI copy looked like product positioning, not an app interface.
3. v4 was a partial slice and did not preserve the full workflow; this caused non-Define screens to feel broken.
4. Recipe Blocks were visually card-based, not block-based; they did not evoke MIT App Inventor enough.
5. The interface still looked AI-generated because it used too much explanation and too many abstract claims.

## Corrections in v5
1. Introduced a real block workspace with toolbox categories, colored puzzle-style blocks, sockets, and nested blocks.
2. Kept copy short and functional: labels, states, values, status, thresholds.
3. Restored the whole app shell and all workflow pages.
4. Moved route definition into block composition:
   - when input arrives
   - normalize text
   - route among labels
   - unsafe guard
   - confidence branch
   - emit JSON
   - log trace
5. Kept advanced contract editing as secondary, not default.
6. Preserved MIB’s core flow: Hardware → Define → Data → Train → Bench → Package → Export.

## Evaluation
| Criteria | Score | Notes |
|---|---:|---|
| Ease of use | 4.4 / 5 | Blocks make Define more understandable; still needs real drag/drop later. |
| Non-AI-generated feel | 4.5 / 5 | Less slogan copy, more tool-like density. |
| Simple aesthetics | 4.2 / 5 | Neutral workbench style; blocks add visual identity. |
| Benchmark app strengths | 4.4 / 5 | Keeps Kiln-like workbench, App Inventor-like blocks, Ollama-like local capability, promptfoo-like benchmark. |
| Extensibility | 4.6 / 5 | Blocks can map directly to preset/macro DSL. |

## Remaining implementation work
- Add actual drag/drop block editor later; static v5 only establishes IA and visual language.
- Map each block to a preset/macro YAML node.
- Add route lane/table view as a secondary tab for users who prefer structured tables.
- Add conflict detection between route blocks and guard blocks.
- Add keyboard-first editing for expert users.
