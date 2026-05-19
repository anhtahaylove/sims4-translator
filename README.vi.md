# The Sims 4 Translator Plus

**The Sims 4 Translator Plus** là bản fork cộng đồng của
[voky1/sims4-translator](https://github.com/voky1/sims4-translator), một ứng
dụng desktop dùng để dịch chuỗi text trong package mod của The Sims 4.

Bản fork này giữ nguyên định dạng package/export và workflow dịch của app gốc,
đồng thời bổ sung ổn định hiệu năng, xử lý job bất đồng bộ, dedupe an toàn,
synthetic smoke test, và chuẩn bị lại tài liệu để public open-source bài bản hơn.

> Dự án này không liên kết với Electronic Arts, Maxis, The Sims, hoặc maintainer
> upstream. The Sims 4 là trademark của chủ sở hữu tương ứng.

[English README](README.md)

## Trạng Thái

Fork này đang được chuẩn bị để public open-source. Trọng tâm hiện tại là ổn định,
rebrand rõ ràng, và kiểm tra release trước khi phân phối rộng rãi.

## Công Cụ Này Làm Gì

- Mở nguồn dịch `.package`, `.stbl`, `.xml`, `.json`, và `.binary`.
- Hiển thị source và bản dịch trong workspace desktop.
- Dịch từ dictionary hoặc các engine dịch online được app hỗ trợ.
- Lưu dictionary để tái sử dụng khi mod cập nhật phiên bản mới.
- Export bản dịch sang STBL, XML, XML-DP, JSON, Binary, hoặc Translation Hub CSV.
- Lưu bản dịch thành package riêng hoặc finalize vào bản copy của package.

## Cải Tiến Trong Fork Này

- Async hóa package loading, dictionary loading, export, save, và finalize.
- UI vẫn phản hồi trong lúc job nền đang chạy.
- Chuỗi duplicate exact trong package được bỏ qua, không import vào workspace.
- Export/save/finalize giữ nguyên format hiện tại nhưng tránh ghi duplicate rows.
- Job Drawer log non-modal cho các summary load/import/export/save.
- Hỗ trợ destination cộng đồng `VI_VN` cho workflow Việt hóa fan localization.
- Giao diện TS4 Plus Balanced thống nhất, không còn cảm giác tách rời giữa light/dark theme.
- Synthetic package generator và verifier để smoke test GUI khi không có package thật.
- Regression tests cho dedupe, import, cancel translate, export, save, finalize, và smoke artifacts.

## Cài Đặt Và Chạy Từ Source

Yêu cầu:

- Python 3.12+
- Windows là môi trường desktop chính đang được test.

Cài dependency:

```powershell
python -m pip install -r requirements.txt
```

Chạy app:

```powershell
python main.py
```

## Workflow Cơ Bản

1. Chọn ngôn ngữ nguồn và ngôn ngữ đích trong Options. Nếu Việt hóa, chọn destination `VI_VN`.
2. Mở package mod hoặc file dịch được hỗ trợ.
3. Chỉnh sửa hoặc tạo bản dịch.
4. Validate các dòng đã dịch.
5. Export định dạng cần dùng, lưu dictionary, save thành package mới, hoặc finalize vào bản copy package.

## Synthetic GUI Smoke Test

Nếu bạn không có package mod thật, hãy tạo package test cố định:

```powershell
python scripts\create_synthetic_package.py
```

Package sẽ được ghi vào:

```text
build/synthetic/synthetic_smoke.package
```

Mở app, load package đó, và xác nhận bảng chỉ có hai dòng unique: `Hello` và
`World`. Sau đó export các định dạng STBL/XML/XML-DP/JSON/Binary/CSV, rồi thử
Save As hoặc Finalize As.

Sau khi click-through thủ công, chạy verifier:

```powershell
python scripts\verify_synthetic_smoke.py --directory build\synthetic --require-gui-outputs
```

Verifier kiểm tra export chỉ có hai chuỗi unique, duplicate không quay lại, không
còn file tạm `.tmp`, và package vẫn load qua storage layer bình thường với dedupe bật.

## Kiểm Tra Khi Phát Triển

Chạy toàn bộ regression tests:

```powershell
python -m unittest discover -s tests -v
```

Chạy compile checks:

```powershell
python -m compileall -q models packer singletons storages themes utils widgets windows tests scripts
```

## Đóng Góp

Xem [CONTRIBUTING.md](CONTRIBUTING.md) để biết workflow phát triển, kỳ vọng test,
và checklist release.

## License Và Credits

Fork này được phân phối theo MIT License. Xem [LICENSE](LICENSE) và
[NOTICE.md](NOTICE.md).

Dự án gốc: [voky1/sims4-translator](https://github.com/voky1/sims4-translator)

Ý tưởng ban đầu được credit cho
[xTranslator](https://www.nexusmods.com/skyrimspecialedition/mods/134).

Fonts:

- [Roboto](https://fonts.google.com/specimen/Roboto), Apache License 2.0.
- [JetBrains Mono](https://www.jetbrains.com/lp/mono/), SIL Open Font License 1.1.
