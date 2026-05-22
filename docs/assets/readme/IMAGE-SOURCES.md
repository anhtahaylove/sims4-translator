# README Image Sources

This file documents the provenance and intended use of images under `docs/assets/readme`.

The project is a community localization tool. These images must not use official EA, Maxis, or The Sims artwork, logos, fonts, game screenshots, characters, copied UI assets, or copyrighted game visuals.

## Real App Screenshots

These images are screenshots of The Sims 4 Translator Plus using synthetic or demo package data. They should not contain API keys, personal paths, private package names, real mod data, or game screenshots.

| Image | README use | Notes |
| --- | --- | --- |
| `workspace.png` | English README workspace section | English UI screenshot showing table-first workflow, Selection Preview, filters, token highlighting, and activity dock. |
| `editor.png` | English README editor section | English UI screenshot showing Translation Studio and token safety. |
| `validate-release.png` | English README validation section | English UI screenshot showing the pre-release validation report. |
| `vi/workspace.png` | Vietnamese README workspace section | Vietnamese UI screenshot using demo translation data. |
| `vi/editor.png` | Vietnamese README editor section | Vietnamese UI screenshot. Original source text remains English; translation text is Vietnamese. |
| `vi/validate-release.png` | Vietnamese README validation section | Vietnamese UI screenshot showing localized validation labels and synthetic/demo issue data. |
| `demo-workflow.webp` | English and Vietnamese README quick demo section | Short animated WebP assembled from README screenshots and diagrams using synthetic/demo data. It is documentation media, not a game screenshot. |

## Generated Diagrams

These images are explanatory diagrams created for README documentation. They are not app screenshots and should not be presented as real UI.

| Image | Purpose | Notes |
| --- | --- | --- |
| `workflow.png` | Explains the recommended package-to-Mods workflow. | Shared by English and Vietnamese READMEs to reduce duplicate maintenance. Step 3 uses `...` because Sims runtime token patterns are not limited to the examples shown. |
| `token-safety.png` | Explains why source tokens must be preserved in Vietnamese translations. | Original text is English source text. Translation text is Vietnamese output. Token examples are illustrative, not exhaustive. |

## Decorative Banner

| Image | Purpose | Notes |
| --- | --- | --- |
| `hero.png` | Shared README banner. | Decorative, non-official visual for the translation studio theme. If replaced, keep it abstract and avoid official Sims branding or exact plumbob/logo composition. |

## Future Hero Redesign Prompt

If the banner is redesigned with an image generation tool, use a safe abstract prompt like:

```text
A polished banner for an open-source desktop translation utility. Dark green modern desk scene, abstract translation workspace on a monitor, clean table rows, document and speech bubble motifs, small validation/check icons, soft mint and lime accents, original faceted green translation crystal that is not a plumbob, professional software landing page style, no text, no logos, no game characters, no official game UI, high readability, balanced composition, subtle depth, friendly and trustworthy.
```

Avoid:

```text
The Sims logo, EA logo, Maxis logo, official plumbob, exact plumbob silhouette, game screenshots, game characters, copyrighted UI, official fonts, fake app screenshot with readable UI text, brand marks, watermark, overly cartoonish, noisy background, unreadable tiny details.
```

Recommended output: `docs/assets/readme/hero.png`, `1600x720`, optimized PNG or WebP-compatible replacement if the README is updated accordingly.
