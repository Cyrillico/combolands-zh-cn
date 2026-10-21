"""对象级校验：确认补丁只改了该改的文本，其余内容逐字节一致。

用法：
    python tools/verify.py --game-dir "F:\\...\\Combolands" --out ./out
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from tools.gameassets import LOCALIZED_FULLNAME, iter_localized, load_serialized, script_map
from tools.unitytree import Trees


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-dir", default=config.DEFAULT_GAME_DIR)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "out"))
    ap.add_argument("--translations", default=None)
    args = ap.parse_args()

    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tr_path = args.translations or os.path.join(here, "translations", "translations.json")
    with open(tr_path, encoding="utf-8") as f:
        translations = json.load(f)

    trees = Trees(os.path.join(args.game_dir, config.MANAGED_SUBDIR), config.UNITY_VERSION)
    nodes = trees.nodes(LOCALIZED_FULLNAME)
    data_dir = os.path.join(args.game_dir, config.DATA_DIR)
    scripts = script_map(None, data_dir)

    problems = 0
    for rel in config.ASSET_FILES:
        a = load_serialized(os.path.join(args.game_dir, rel))
        b = load_serialized(os.path.join(args.out, rel))
        objs_a = {o.path_id: o for o in a.objects.values()}
        objs_b = {o.path_id: o for o in b.objects.values()}
        print(f"\n== {os.path.basename(rel)}  objects {len(objs_a)} -> {len(objs_b)}")
        if len(objs_a) != len(objs_b):
            print("   ✗ 对象数量不一致")
            problems += 1
            continue

        expected = {}
        for obj, tree in iter_localized(a, scripts, nodes):
            zh = translations.get(tree.get("Key", ""))
            if zh and zh != tree.get("_originalString"):
                expected[obj.path_id] = (tree.get("Key"), zh)

        # 字体多图集是预期内的改动，单独计入
        font_nodes = trees.nodes("TMPro.TMP_FontAsset", "Unity.TextMeshPro.dll")
        fonts = set()
        for obj in a.objects.values():
            if obj.type.name != "MonoBehaviour":
                continue
            try:
                ftt = obj.read_typetree(font_nodes)
            except Exception:
                continue
            if ftt.get("m_Name") in config.MULTI_ATLAS_FONTS \
                    and not ftt.get("m_IsMultiAtlasTexturesEnabled"):
                fonts.add(obj.path_id)
        expected.update({pid: ("@font", None) for pid in fonts})

        changed = [pid for pid in objs_a
                   if objs_a[pid].get_raw_data() != objs_b[pid].get_raw_data()]
        unexpected = [pid for pid in changed if pid not in expected]
        missed = [pid for pid in expected if pid not in changed]
        print(f"   变化 {len(changed)} 个（预期 {len(expected)}），意外 {len(unexpected)}，漏改 {len(missed)}")
        problems += len(unexpected) + len(missed)

        bad_text = 0
        for pid, (key, zh) in expected.items():
            if zh is None:            # 字体资源只校验是否被改动
                continue
            tree = objs_b[pid].read_typetree(nodes)
            if tree.get("_originalString") != zh:
                bad_text += 1
                if bad_text <= 3:
                    print(f"   ✗ {key}: 写回内容不符")
        problems += bad_text

        # 本地化对象总数（确认没有把别的脚本错认成文本资源）
        print(f"   本地化对象 {sum(1 for _ in iter_localized(b, scripts, nodes))} 个可正常解析")

    dll_rel = config.DLL_FILE
    src, dst = os.path.join(args.game_dir, dll_rel), os.path.join(args.out, dll_rel)
    if os.path.exists(dst):
        with open(src, "rb") as f:
            a = f.read()
        with open(dst, "rb") as f:
            b = f.read()
        print(f"\n== Assembly-CSharp.dll  {len(a):,} -> {len(b):,} bytes")
        if len(a) != len(b):
            print("   ✗ 文件大小变化")
            problems += 1
        else:
            diffs = sum(1 for x, y in zip(a, b) if x != y)
            print(f"   差异字节 {diffs}（应只落在字符串槽位内）")

    print("\n" + ("全部校验通过" if problems == 0 else f"发现 {problems} 处异常"))
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
