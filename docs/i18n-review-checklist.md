# Interface Language Review Checklist

Use this checklist when reviewing bundled interface languages after machine-assisted translation.

## What To Open

1. Main window with a synthetic or real package loaded.
2. Options > General.
3. Options > Providers.
4. Batch Translate.
5. Translation Studio.
6. Validate Release / Release QA report.

## What To Check

- Text is natural for the selected language and does not sound like raw machine translation.
- Buttons, tabs, labels, status badges, combo boxes, and table headers are readable.
- Long labels do not overlap nearby controls or disappear behind the window edge.
- Provider names and technical terms stay recognizable: DeepL, Gemini, OpenAI-compatible, Ollama, token, package, Validate Release, Save as package.
- Placeholders and shortcuts stay intact: `{0.SimFirstName}`, `{}`, `Ctrl+Enter`, URLs, XML-like tags, and `\n`.
- Warning and confirmation text does not overclaim safety or translation quality.

## Feedback Template

```text
Language:
Screen:
Current text:
Suggested text:
Reason:
Layout issue? yes/no
Screenshot path or note:
```

## Recommended Order

Review Vietnamese first, then French, German, Spanish, and Chinese Traditional. Other bundled languages can follow based on user reports.

The bundled catalogs are machine-assisted and QA-checked for coverage, placeholders, XML validity, and obvious layout risk. They are not claimed to be native-speaker perfect.
