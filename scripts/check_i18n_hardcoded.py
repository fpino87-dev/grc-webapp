import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


TSX_PATTERN = re.compile(r"\"[A-Za-zÀ-ÖØ-öø-ÿ].+\"")
PY_PATTERN = re.compile(r"\"[A-Za-zÀ-ÖØ-öø-ÿ].+\"")


def check_tsx() -> list[str]:
  problems: list[str] = []
  for path in ROOT.joinpath("frontend", "src").rglob("*.tsx"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
      if " t(" in line or "useTranslation" in line or "i18n." in line:
        continue
      if "// i18n-ignore" in line:
        continue
      if TSX_PATTERN.search(line):
        problems.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
  return problems


def check_py() -> list[str]:
  problems: list[str] = []
  for path in ROOT.joinpath("backend").rglob("*.py"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    for lineno, line in enumerate(text.splitlines(), start=1):
      if "gettext" in line or "_(" in line:
        continue
      if "# i18n-ignore" in line:
        continue
      if PY_PATTERN.search(line):
        problems.append(f"{path.relative_to(ROOT)}:{lineno}: {line.strip()}")
  return problems


def main() -> None:
  tsx_problems = check_tsx()
  py_problems = check_py()

  if not tsx_problems and not py_problems:
    print("i18n check: OK (no obvious hardcoded strings)")
    return

  print("i18n check: potential hardcoded strings found.\n")
  if tsx_problems:
    print("Frontend (.tsx):")
    for p in tsx_problems:
      print("  ", p)
    print()
  if py_problems:
    print("Backend (.py):")
    for p in py_problems:
      print("  ", p)

  raise SystemExit(1)


if __name__ == "__main__":
  main()

