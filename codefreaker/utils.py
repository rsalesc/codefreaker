import pathlib
import itertools

def create_and_write(path: pathlib.Path, *args, **kwargs):
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(*args, **kwargs)

def normalize_with_underscores(s: str) -> str:
  res = s.replace(' ', '_').replace('.', '_').strip('_')
  final = []

  last = ''
  for c in res:
    if c == '_' and last == c:
      continue
    last = c
    final.append(c)
  return ''.join(final)