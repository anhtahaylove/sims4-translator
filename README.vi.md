# The Sims 4 Translator Plus

[![Release](https://img.shields.io/github/v/release/anhtahaylove/sims4-translator?sort=semver)](https://github.com/anhtahaylove/sims4-translator/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-10%2B-32c36c)](https://github.com/anhtahaylove/sims4-translator/releases)

**Translation Studio ưu tiên workflow Việt hóa cho package và STBL của The Sims 4.**

[English README](README.md) · [Checklist phát hành](docs/release-checklist.md) · [Tải bản Windows mới nhất](https://github.com/anhtahaylove/sims4-translator/releases/latest)

> Lưu ý cộng đồng: dự án này không liên kết chính thức với Electronic Arts, Maxis, The Sims hoặc maintainer upstream ban đầu. Repo không chứa artwork, logo, font hoặc asset chính thức của game.

## Ứng Dụng Này Dùng Để Làm Gì?

The Sims 4 Translator Plus giúp bạn mở, rà soát, dịch, kiểm tra và xuất string của The Sims 4 mà không cần tự sửa package bằng tay.

- **Mặc định cho Việt hóa**: lần chạy đầu dùng `ENG_US -> VI_VN`.
- **Workspace dạng bảng**: phù hợp cả package nhỏ lẫn package rất lớn.
- **Tìm kiếm hybrid**: một ô tìm kiếm theo ID, văn bản gốc hoặc bản dịch.
- **Selection Preview**: đọc đầy đủ string đang chọn mà không cần mở Editor.
- **Translation Studio**: sửa từng string, highlight token, kiểm tra token safety và chèn token nhanh.
- **DeepL**: kiểm tra API key, xem usage, glossary ID, context và cảnh báo quota trước batch translate.
- **Validate Release**: rà nguy cơ text trống, thiếu token, duplicate output và trạng thái chưa sẵn sàng trước khi ghi file.
- **Build Windows**: có script build PyInstaller để đóng gói bản exe cục bộ.

## Tải Và Chạy Bản Windows

1. Mở [trang release mới nhất](https://github.com/anhtahaylove/sims4-translator/releases/latest).
2. Tải `The-Sims-4-Translator-Plus-v2.0.0-windows.zip`.
3. Giải nén ZIP vào một thư mục bình thường, ví dụ `D:\Tools\The Sims 4 Translator Plus`.
4. Chạy `The Sims 4 Translator Plus.exe`.

Không chạy trực tiếp file exe bên trong ZIP. Hãy giải nén trước để app đọc được thư mục `prefs` và `fonts` đi kèm.

## Workflow Việt Hóa Khuyến Nghị

Với workflow Việt hóa game/DLC, nên đi theo hướng an toàn:

1. Mở **Tùy chọn**.
2. Kiểm tra **Source** là `ENG_US`.
3. Kiểm tra **Destination** là `VI_VN`.
4. Mở một hoặc nhiều file `.package` hoặc `.stbl`.
5. Dịch và rà soát string trong bảng hoặc Translation Studio.
6. Chạy **Validate Release** trước khi xuất bản.
7. Ưu tiên **Save as package** để tạo package đưa vào thư mục Mods.
8. Test package đã xuất trong:

```text
Documents\Electronic Arts\The Sims 4\Mods
```

Chỉ dùng **Finalize** khi bạn thật sự muốn ghi lại package bằng destination STBL resource. Nếu dùng Finalize, hãy bật **Create backup before Finalize**.

## Định Dạng Hỗ Trợ

| Hướng xử lý | Định dạng |
| --- | --- |
| Mở / nhập | `.package`, `.stbl`, XML, JSON, Binary, dữ liệu dịch dạng CSV |
| Xuất | STBL package, XML, XML cho Deaderpool's STBL editor, JSON, Binary, Hub CSV |
| QA phát hành | Báo cáo `.txt` hoặc `.csv` |
| Từ điển | Build từ string resource trong các pack đã cài |

## Cấu Hình DeepL

DeepL là tùy chọn. Bạn vẫn có thể dùng Google hoặc MyMemory, nhưng DeepL thường hữu ích hơn khi dịch batch lớn.

1. Mở **Tùy chọn**.
2. Dán **DeepL API key**.
3. Bấm **Test key**. Nút này kiểm tra quota/usage và không tốn ký tự dịch.
4. Bấm **Check usage** trước khi dịch batch lớn.
5. Nếu đã tạo glossary trên DeepL, bạn có thể dán **Glossary ID** để ép thuật ngữ như `Trait`, `Lot`, `Moodlet` dịch nhất quán hơn.

Trước khi Batch Translate bằng DeepL, app sẽ ước tính số ký tự nguồn sắp gửi để bạn tránh tốn quota ngoài ý muốn.

## Token Safety

String của The Sims 4 thường có token và format như:

```text
{0.SimFirstName}
{1.Money}
\n
<b>...</b>
<i>...</i>
```

Editor sẽ highlight các token này và cảnh báo khi bản dịch thiếu token, thừa token, đổi thứ tự token hoặc khác số lần xuống dòng. **Approve** và **Needs Review** đều hiện cảnh báo mềm nếu token khác nhau; bạn vẫn có thể tiếp tục nếu biết chắc sự khác biệt đó là có chủ ý.

## Validate Release

Hãy chạy **Validate Release** trước khi public package Việt hóa.

- **Soft release**: phù hợp khi đang làm việc hằng ngày. Untranslated, Draft và Needs Review là cảnh báo.
- **Strict release**: phù hợp trước khi public. Untranslated, Draft và Needs Review được nâng lên mức nghiêm trọng.

Báo cáo này là safety gate mềm. Bạn có thể quay lại sửa hoặc tiếp tục nếu đã kiểm tra và chấp nhận rủi ro.

Xem thêm [docs/release-checklist.md](docs/release-checklist.md) để có checklist phát hành chi tiết.

## Chạy Từ Source

Yêu cầu:

- Windows 10 trở lên
- Python 3.11 trở lên
- Git

Cài đặt:

```powershell
git clone https://github.com/anhtahaylove/sims4-translator.git
cd sims4-translator
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

Kiểm tra:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts main.py
python scripts\create_synthetic_package.py
python scripts\verify_synthetic_smoke.py --directory build\synthetic --require-gui-outputs
git diff --check
```

## Build Bản Windows

Chạy script build:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\build_windows.ps1
```

Script dùng PyInstaller như dependency build-only trong virtual environment tạm. PyInstaller không phải runtime dependency và không cần nếu bạn chỉ chạy app từ source.

## Lỗi Thường Gặp

| Vấn đề | Cách xử lý |
| --- | --- |
| Destination không phải `VI_VN` | Mở **Tùy chọn** và chọn lại `VI_VN`. ZIP public không đóng kèm `prefs/config.xml` cục bộ, nên lần chạy đầu sẽ mặc định `ENG_US -> VI_VN`. |
| Đã nhập DeepL key nhưng không dịch được | Kiểm tra loại key Free/Pro rồi bấm **Test key** trong Tùy chọn. Key Free thường kết thúc bằng `:fx`. |
| Text trong game bị trống | Chạy **Validate Release**, kiểm tra thiếu token, bản dịch trống, duplicate output và destination locale. |
| App không thấy pack của game | Trong **Tùy chọn**, chọn thư mục cài game có các thư mục `Data`, `EP`, `GP`, `SP`, `FP`. |
| Windows cảnh báo file exe | Bản release chưa ký số. Chỉ chạy nếu bạn tin nguồn tải từ GitHub release của repo này. |

## Credits

Fork này dựa trên dự án gốc [voky1/sims4-translator](https://github.com/voky1/sims4-translator) và tiếp tục dùng giấy phép MIT.

Cảm ơn cộng đồng modding/localization The Sims đã góp workflow thực tế, package test và các edge case dịch thuật.

## License

MIT. Xem [LICENSE](LICENSE).
