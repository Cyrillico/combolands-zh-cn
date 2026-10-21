"""把中文译文注入游戏资源，生成补丁文件。

用法：
    python tools/apply.py                       # 生成到 ./out
    python tools/apply.py --install             # 生成后直接装进游戏（会自动备份）

只读写自己的正版游戏文件，仓库里不附带任何游戏本体内容。
"""

import argparse
import hashlib
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from tools import dll_patch
from tools.gameassets import (LOCALIZED_FULLNAME, iter_localized, load_serialized,
                              script_map)
from tools.unitytree import Trees

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_FONT_FULLNAME = "TMPro.TMP_FontAsset"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_version(game_dir, force):
    """版本守卫：原版文件哈希不一致说明游戏可能已更新。"""
    bad = []
    for rel, expected in config.EXPECTED_SHA256.items():
        path = os.path.join(game_dir, rel)
        if not os.path.exists(path):
            bad.append((rel, "文件不存在"))
            continue
        actual = sha256(path)
        if actual != expected:
            bad.append((rel, f"{actual[:16]}…"))
    if not bad:
        return True
    print(f"⚠ 原版文件与目标构建 {config.TARGET_BUILD} 不一致：")
    for rel, info in bad:
        print(f"   {rel}: {info}")
    if force:
        print("   已指定 --force，继续执行（可能损坏游戏文件）。")
        return True
    print("   这个译文表是为特定构建准备的，强行套用可能破坏资源。")
    print("   如果确认要试，加 --force；否则先用 Steam 更新/回滚到对应版本。")
    return False


def patch_assets(game_dir, out_dir, translations, trees, nodes, multi_atlas):
    scripts = script_map(None, os.path.join(game_dir, config.DATA_DIR))
    total = {"written": 0, "skipped": 0, "missed": 0}

    for rel in config.ASSET_FILES:
        src = os.path.join(game_dir, rel)
        sf = load_serialized(src)
        written = 0
        missed = []
        for obj, tree in iter_localized(sf, scripts, nodes):
            key = tree.get("Key", "")
            zh = translations.get(key)
            if not zh:
                total["missed"] += 1
                continue
            if tree.get("_originalString") != zh:
                tree["_originalString"] = zh
                obj.save_typetree(tree, nodes)
                written += 1

        if multi_atlas and os.path.basename(rel) == "sharedassets0.assets":
            font_nodes = trees.nodes(TMP_FONT_FULLNAME, "Unity.TextMeshPro.dll")
            for obj in sf.objects.values():
                if obj.type.name != "MonoBehaviour":
                    continue
                try:
                    ftt = obj.read_typetree(font_nodes)
                except Exception:
                    continue
                if ftt.get("m_Name") in config.MULTI_ATLAS_FONTS \
                        and not ftt.get("m_IsMultiAtlasTexturesEnabled"):
                    ftt["m_IsMultiAtlasTexturesEnabled"] = True
                    obj.save_typetree(ftt, font_nodes)
                    print(f"   字体多图集：{ftt['m_Name']}")

        dst = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(sf.save())
        total["written"] += written
        print(f"{os.path.basename(rel)}: 写入 {written} 条 -> {dst}")
    return total


def patch_dll(game_dir, out_dir, entries):
    src = os.path.join(game_dir, config.DLL_FILE)
    if not os.path.exists(src):
        print("未找到 Assembly-CSharp.dll，跳过")
        return
    with open(src, "rb") as f:
        data = f.read()
    new_data, report = dll_patch.patch_bytes(data, entries)
    dst = os.path.join(out_dir, config.DLL_FILE)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "wb") as f:
        f.write(new_data)
    ok = sum(1 for r in report if r["status"] == "ok")
    print(f"Assembly-CSharp.dll: 替换 {ok}/{len(report)} 条（大小 {len(new_data):,} 不变）")
    for r in report:
        if r["status"] != "ok":
            print(f"   跳过 {r['source']}: {r['reason']}")


def install(game_dir, out_dir):
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(os.path.dirname(game_dir.rstrip("\\/")),
                          f"Combolands_backup_{stamp}")
    files = config.ASSET_FILES + [config.DLL_FILE]
    for rel in files:
        src = os.path.join(game_dir, rel)
        if not os.path.exists(src):
            continue
        bak = os.path.join(backup, rel)
        os.makedirs(os.path.dirname(bak), exist_ok=True)
        shutil.copy2(src, bak)
    for rel in files:
        src = os.path.join(out_dir, rel)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(game_dir, rel))
    print(f"已安装。原文件备份在：{backup}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game-dir", default=config.DEFAULT_GAME_DIR)
    ap.add_argument("--translations", default=os.path.join(HERE, "translations", "translations.json"))
    ap.add_argument("--dll-strings", default=os.path.join(HERE, "translations", "dll_strings.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--install", action="store_true", help="生成后直接替换游戏文件（自动备份）")
    ap.add_argument("--force", action="store_true", help="忽略版本校验")
    ap.add_argument("--skip-dll", action="store_true")
    ap.add_argument("--no-font", action="store_true", help="不修改字体多图集设置")
    args = ap.parse_args()

    if not os.path.isdir(args.game_dir):
        sys.exit(f"找不到游戏目录：{args.game_dir}\n用 --game-dir 指定 Combolands.exe 所在目录")
    if not check_version(args.game_dir, args.force):
        sys.exit(1)

    with open(args.translations, encoding="utf-8") as f:
        translations = json.load(f)
    print(f"载入译文 {len(translations)} 条")

    trees = Trees(os.path.join(args.game_dir, config.MANAGED_SUBDIR), config.UNITY_VERSION)
    nodes = trees.nodes(LOCALIZED_FULLNAME)

    stats = patch_assets(args.game_dir, args.out, translations, trees, nodes,
                         multi_atlas=not args.no_font)

    if not args.skip_dll and os.path.exists(args.dll_strings):
        with open(args.dll_strings, encoding="utf-8") as f:
            patch_dll(args.game_dir, args.out, json.load(f))

    print(f"\n完成：写入 {stats['written']} 条，未匹配 {stats['missed']} 条")
    print(f"输出目录：{args.out}")
    if args.install:
        install(args.game_dir, args.out)
    else:
        print("确认无误后可加 --install 安装，或手动把 out 下的文件覆盖到游戏目录。")


if __name__ == "__main__":
    main()
