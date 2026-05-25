# Translation Tool Reference Review

Reviewed on 2026-05-25 as inspiration only. Do not copy source code from
third-party projects into this repo without a separate license review.

| Repository | Signal | License | Useful ideas | Notes for this repo |
| --- | --- | --- | --- | --- |
| `veloxcity/xml-ai-translator` | Small, early WPF app | MIT | Gemini batch translation, model-aware batching, translation cache, progress preservation | Good concept fit, but Sims 4 Translator Plus already has stronger package workflow, validation, and release engineering. |
| `UmaruMG/Sims-XML-Auto-Translator` | Small, inactive Sims XML tool | No license found | Simple DeepL XML workflow | Do not copy code. Current app already covers this workflow more safely. |
| `hydropix/TranslateBooksWithLLMs` | Large active Python project | AGPL-3.0 | Provider abstraction, local/cloud provider choice, checkpoint/resume, long-document preservation | Treat as concept-only because AGPL is not compatible with copying implementation into this MIT app. |
| `nidhaloff/deep-translator` | Mature Python library | Apache-2.0 | Provider abstraction, language/provider surface, docs organization | Avoid adding it as a dependency now because this app needs Sims token handling, package context, and provider-specific safety controls. |
| `GardenAtDesk/gemini-game-translator` | Small game-localization tool | MIT | Visual text QA, cost caps, glossary workflow, regex variable protection, progress autosave | Best inspiration for layout-risk warnings and AI cost guard wording. |

## Conclusions

- Keep the app package-first and Sims-specific; generic translator libraries do not understand STBL/package safety.
- Add persistent translation cache and resume behavior before adding more AI providers.
- Add heuristic length/layout warnings in Validate Release, but do not claim to simulate the real game UI.
- Add Gemini and OpenAI-compatible providers through internal adapters, using `requests` and mocked tests only.
- Keep API keys local, redact them from logs, and never store them in translation cache rows.
