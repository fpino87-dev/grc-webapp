import json
from pathlib import Path


BASE = Path("frontend/src/i18n")
LANG_REFERENCE = "en"
TARGET_LANGS = ["fr", "pl", "tr"]


def load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def ensure_path(target, path, value):
    cur = target
    for key in path[:-1]:
        if key not in cur or not isinstance(cur.get(key), dict):
            cur[key] = {}
        cur = cur[key]
    if path[-1] not in cur:
        cur[path[-1]] = value


def walk_leaves(obj, prefix=None):
    if prefix is None:
        prefix = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk_leaves(v, prefix + [k])
    else:
        yield prefix, obj


def main():
    ref_path = BASE / LANG_REFERENCE / "common.json"
    ref = load(ref_path)

    ref_leaves = list(walk_leaves(ref))

    for lang in TARGET_LANGS:
        path = BASE / lang / "common.json"
        data = load(path)
        missing = 0

        for p, value in ref_leaves:
            cur = data
            exists = True
            for key in p[:-1]:
                if not isinstance(cur, dict) or key not in cur:
                    exists = False
                    break
                cur = cur[key]
            if not exists or not isinstance(cur, dict) or p[-1] not in cur:
                ensure_path(data, p, value)
                missing += 1

        save(path, data)
        print(f"{lang}: added {missing} missing keys")


if __name__ == "__main__":
    main()

