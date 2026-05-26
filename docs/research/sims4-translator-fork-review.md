# Sims 4 Translator Fork Review

Reviewed on 2026-05-26 as inspiration only. The current repo remains the
source of truth; do not copy fork code without a separate license and design
review.

| Repository | Signal | Useful idea | Decision |
| --- | --- | --- | --- |
| [ZDrokaiz/sims4-translator](https://github.com/ZDrokaiz/sims4-translator) | Small July 2025 fork of `voky1/sims4-translator`; README says it added MyMemory. | MyMemory fallback provider. | Already covered in this repo, along with DeepL, Gemini, OpenAI-compatible, and Ollama. No import. |
| [EliD-Dev/sims4-translator](https://github.com/EliD-Dev/sims4-translator) | Active fork with Cohere, Google Cloud Translation, and extra placeholder prompts. | Batch separator prompting and gender-token awareness. | Concept only. Do not add `cohere` dependency or copy prompt/code; current token preservation, cache, provider adapters, and line-count rejection are safer. |
| [Hardingfele2212/sims4-translator](https://github.com/Hardingfele2212/sims4-translator) | Norwegian interface translation fork. | Possible future Norwegian UI catalog. | Skip for now; catalog is for an older UI and is far below current interface coverage. |
| [KielD-01/sims4-translator](https://github.com/KielD-01/sims4-translator) | Ukrainian interface translation fork. | Ukrainian UI language. | Already covered by the current bundled Ukrainian catalog. |
| [mariannetops/sims4-translator](https://github.com/mariannetops/sims4-translator) | Danish interface translation fork. | Danish UI language. | Already covered by the current bundled Danish catalog. |
| [wahyudiZulhaidar/sims4-translator](https://github.com/wahyudiZulhaidar/sims4-translator) | Indonesian support fork with PyInstaller path fixes and font license notes. | Resolve bundled `prefs` from the app/bundle path instead of current working directory. | Adopted as a resource-path hardening idea for `prefs/interface`, `prefs/languages.xml`, `prefs/dlc.ini`, and legacy `prefs/config.xml`. |

## Conclusions

- Do not merge old provider implementations from forks; the current provider
  architecture is broader and better tested.
- Keep old localization forks as attribution and review signals, not as direct
  runtime assets.
- The one concrete fix worth carrying forward is CWD-independent bundled
  resource lookup for `prefs`, matching the existing font-path hardening.
