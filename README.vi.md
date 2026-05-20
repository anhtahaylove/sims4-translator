# The Sims 4 Translator Plus

**The Sims 4 Translator Plus** là ứng dụng desktop Windows hỗ trợ dịch chuỗi
text trong mod/package của The Sims 4. Dự án này là bản fork cộng đồng từ
[voky1/sims4-translator](https://github.com/voky1/sims4-translator), giữ nguyên
workflow package/export quen thuộc và bổ sung giao diện Life Studio Green, hỗ trợ
`VI_VN`, kiểm tra trước khi phát hành, job chạy nền an toàn hơn, và build Windows
lặp lại được.

[English README](README.md)

> Dự án này không liên kết với Electronic Arts, Maxis, The Sims, hoặc maintainer
> upstream. The Sims 4 là trademark của chủ sở hữu tương ứng. Fork này dùng asset
> cộng đồng tự tạo, không ship artwork, logo, font, hoặc UI asset chính thức của
> EA, Maxis, hoặc The Sims.

## Điểm nổi bật

- Workspace dạng bảng, ưu tiên làm việc với package lớn.
- Locale cộng đồng cho Việt hóa: `VI_VN`.
- Workflow mặc định: `ENG_US -> VI_VN`.
- Search hybrid theo ID, Original, hoặc Translation.
- Selection Preview để đọc chuỗi dài ngay trên màn hình chính.
- Editor Focus Studio có highlight token và cảnh báo token mềm.
- Batch Translate có DeepL cost guard và kiểm tra usage/API key.
- Pre-release Validation Report với chế độ Soft release và Strict release.
- Save as package, Finalize, và Export giữ nguyên format hiện có.
- Giao diện Life Studio Green và bộ resource rebrand thống nhất.
- Script build Windows bằng PyInstaller dạng build-only dependency.

## Định dạng hỗ trợ

App có thể mở:

- `.package`
- `.stbl`
- `.xml`
- `.json`
- `.binary`

App có thể export hoặc lưu bản dịch thành:

- STBL
- XML
- XML-DP cho Deaderpool's STBL editor
- JSON
- Binary
- Translation Hub CSV
- `.package` đã chứa bản dịch

## Tải và chạy

Người dùng thông thường nên tải bản Windows ZIP tại trang
[Releases](https://github.com/anhtahaylove/sims4-translator/releases), giải nén,
rồi chạy:

```text
The Sims 4 Translator Plus.exe
```

App lưu thiết lập cá nhân trong `prefs/config.xml` cạnh ứng dụng khi chạy từ
source hoặc từ bản build đã giải nén. File config local này không được commit vào
git.

## Workflow Việt hóa khuyến nghị

Thiết lập nên dùng:

- Source: `ENG_US`
- Destination: `VI_VN`
- Interface Language: `Vietnamese` hoặc `English`
- Create backup before Finalize: bật
- Use conflict-free save mode: tắt, trừ khi bạn đang test trên package copy

Quy trình phát hành an toàn:

1. Open hoặc Add một hay nhiều file `.package`.
2. Search, filter, edit, translate, và approve các string.
3. Chạy `Validate Release...`.
4. Dùng `Save as package` để tạo package đưa vào thư mục Mods.
5. Test package trong `Documents\Electronic Arts\The Sims 4\Mods`.
6. Chỉ dùng `Finalize` khi bạn thật sự muốn ghi lại vào một package copy.

`VI_VN` là locale cộng đồng/fan dành cho workflow Việt hóa. Nó không được trình
bày như locale chính thức của EA.

## Thiết lập DeepL

DeepL là tùy chọn. Cách dùng:

1. Mở `Options`.
2. Dán DeepL API key.
3. Bấm `Test key` để kiểm tra key mà không tốn ký tự dịch.
4. Bấm `Check usage` trước khi batch translate lớn.
5. Chọn DeepL trong Editor hoặc Batch Translate.

Optional glossary ID chỉ cần khi bạn đã tự tạo glossary trong DeepL và muốn các
thuật ngữ như `Trait`, `Lot`, hoặc `Moodlet` được dịch nhất quán. Batch Translate
sẽ ước tính số ký tự nguồn trước khi gửi job DeepL để tránh tốn quota ngoài ý muốn.

## Validate Release là gì?

`Validate Release...` là báo cáo kiểm tra trước khi bạn public hoặc ghi file phát
hành. Nó giúp phát hiện rủi ro blank text, thiếu Sims token, lệch `\n`, lệch tag,
duplicate output, hoặc lỗi chuyển sang destination locale.

- **Soft release**: phù hợp trong lúc làm việc. Untranslated, Draft, và Needs
  review là warning.
- **Strict release**: phù hợp trước khi public. Untranslated, Draft, và Needs
  review là critical.

Report này là safety gate mềm. Bạn có thể quay lại sửa hoặc tiếp tục nếu thật sự
muốn, nhưng nên sửa các lỗi critical trước khi phát hành rộng rãi.

## Chạy từ source

Yêu cầu:

- Windows
- Python 3.12+

Cài dependency:

```powershell
python -m pip install -r requirements.txt
```

Chạy app:

```powershell
python main.py
```

## Kiểm tra khi phát triển

Chạy các lệnh kiểm tra:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts main.py
python scripts\create_synthetic_package.py
python scripts\verify_synthetic_smoke.py --directory build\synthetic --require-gui-outputs
git diff --check
```

## Build Windows

Script build tạo venv tạm trong `%TEMP%`, cài PyInstaller ở đó, chạy kiểm tra,
rồi build app Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

PyInstaller chỉ là dependency phục vụ build, không phải runtime dependency và
không nằm trong `requirements.txt`.

Không commit các output local:

- `build/`
- `dist/`
- file `.spec` sinh ra
- file `.package` sinh ra
- dictionary local
- `prefs/config.xml`

## Checklist phát hành

Xem [docs/release-checklist.md](docs/release-checklist.md) để biết workflow
Việt hóa, checklist QA package lớn, ghi chú DeepL, và quy tắc release hygiene.

## License và credit

Fork này phát hành theo MIT License. Xem [LICENSE](LICENSE) và [NOTICE.md](NOTICE.md).

Dự án gốc:
[voky1/sims4-translator](https://github.com/voky1/sims4-translator)

Ý tưởng ban đầu được credit cho
[xTranslator](https://www.nexusmods.com/skyrimspecialedition/mods/134).

Font đi kèm:

- [Roboto](https://fonts.google.com/specimen/Roboto), Apache License 2.0.
- [JetBrains Mono](https://www.jetbrains.com/lp/mono/), SIL Open Font License 1.1.
