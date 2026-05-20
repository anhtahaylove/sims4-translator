# -*- coding: utf-8 -*-

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packer.dbpf import DbpfPackage
from packer.resource import ResourceID
from scripts.synthetic_package import build_stbl

DEFAULT_OUTPUT = ROOT / 'build' / 'visual-qa' / 'large_visual_qa.package'
STBL_TYPE = 0x220557DA


SOURCE_SNIPPETS = (
    'Long tooltip for {0.SimFirstName} with {1.Money} and <b>bold reward</b>\\nSecond line for UI wrapping.',
    'Career notification: {0.SimFirstName} finished a task, gained {2.Number}, and unlocked <i>new advice</i>.',
    'Package-heavy string with tokens {0.SimPronounSubjective} {1.SimFirstName} and repeated Vietnamese QA text.',
    'Dialog line with XML-like <font color="#1E81E6">{0.Number}</font> and escaped line break\\n\\nNext paragraph.',
)

VI_SNIPPETS = (
    'Dòng dài để kiểm tra {0.SimFirstName}, {1.Money}, <b>phần thưởng in đậm</b>\\nDòng thứ hai cho preview.',
    'Thông báo nghề nghiệp: {0.SimFirstName} hoàn thành việc, nhận {2.Number}, và mở <i>gợi ý mới</i>.',
    'Chuỗi gói lớn có token {0.SimPronounSubjective} {1.SimFirstName} và đoạn tiếng Việt dài để QA.',
    'Dòng hội thoại có <font color="#1E81E6">{0.Number}</font> và ký tự xuống dòng\\n\\nĐoạn tiếp theo.',
)


def make_visual_qa_strings(start_id: int, count: int, translated: bool = False) -> dict:
    snippets = VI_SNIPPETS if translated else SOURCE_SNIPPETS
    strings = {}
    for offset in range(count):
        sid = start_id + offset
        snippet = snippets[offset % len(snippets)]
        strings[sid] = f'{snippet} QA row {sid:,}. ' + (
            'Nội dung đủ dài để kiểm tra table, Selection Preview, Editor, token highlight, và validation report.'
            if translated else
            'Content is intentionally long enough to check table, Selection Preview, Editor, token highlight, and validation report.'
        )
    return strings


def create_visual_qa_package(
        path: str = str(DEFAULT_OUTPUT),
        total_records: int = 100_000,
        resource_count: int = 4,
        destination_locale: str = 'VI_VN') -> dict:
    if total_records < 1:
        raise ValueError('total_records must be at least 1')
    if resource_count < 1:
        raise ValueError('resource_count must be at least 1')

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)

    base_count, remainder = divmod(total_records, resource_count)
    written = 0
    resources = []

    with DbpfPackage.write(str(output)) as package:
        for index in range(resource_count):
            count = base_count + (1 if index < remainder else 0)
            if count <= 0:
                continue

            instance = index + 1
            start_id = index * 1_000_000 + 1
            source = ResourceID(group=0, instance=instance, type=STBL_TYPE)
            destination = source.convert_instance(destination_locale)

            package.put(source, build_stbl(source, make_visual_qa_strings(start_id, count)).binary)
            package.put(
                destination,
                build_stbl(destination, make_visual_qa_strings(start_id, count, translated=True)).binary,
            )
            resources.append((source, destination, count))
            written += count

    return {
        'path': str(output),
        'records': written,
        'resources': len(resources),
        'destination_locale': destination_locale,
    }


def main():
    parser = argparse.ArgumentParser(description='Create a large package for manual UI visual QA.')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT), help='Output .package path.')
    parser.add_argument('--records', type=int, default=100_000, help='Total source strings to generate.')
    parser.add_argument('--resources', type=int, default=4, help='Number of STBL resources to split across.')
    parser.add_argument('--destination-locale', default='VI_VN', help='Destination locale for translated STBL resources.')
    args = parser.parse_args()

    info = create_visual_qa_package(
        path=args.output,
        total_records=args.records,
        resource_count=args.resources,
        destination_locale=args.destination_locale,
    )
    print('Created visual QA package:')
    print(f"  Path: {info['path']}")
    print(f"  Records: {info['records']:,}")
    print(f"  STBL resource pairs: {info['resources']}")
    print(f"  Destination: {info['destination_locale']}")


if __name__ == '__main__':
    main()
