"""从游戏资源中导出全部本地化条目，用于翻译或核对。

用法：
    python tools/extract.py --game-dir "F:\\SteamLibrary\\steamapps\\common\\Combolands" \
        --out current_strings.json
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
    ap.add_argument("--out", default="current_strings.json")
    args = ap.parse_args()

    data_dir = os.path.join(args.game_dir, config.DATA_DIR)
    trees = Trees(os.path.join(args.game_dir, config.MANAGED_SUBDIR), config.UNITY_VERSION)
    nodes = trees.nodes(LOCALIZED_FULLNAME)
    scripts = script_map(None, data_dir)

    rows = []
    for rel in config.ASSET_FILES:
        sf = load_serialized(os.path.join(args.game_dir, rel))
        count = 0
        for obj, tree in iter_localized(sf, scripts, nodes):
            rows.append({
                "file": os.path.basename(rel),
                "path_id": obj.path_id,
                "key": tree.get("Key", ""),
                "english": tree.get("_originalString", ""),
            })
            count += 1
        print(f"{os.path.basename(rel)}: {count} 条")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    print(f"共 {len(rows)} 条 -> {args.out}")


if __name__ == "__main__":
    main()
