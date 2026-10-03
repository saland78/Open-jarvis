"""One fixed production historical case. No vault, retries or extra generation."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

EXPECTED = {'check_structured.py': 'd2c54eafbb953fb57535354461054008741d978942b3e483d3defa63cd92a651', 'collaudo.py': 'ebbd828888b1aaccf8a3846d4d242606f5327feccc136af91de757a425142fa4', 'structured_cases.json': 'c1113ace4a06d99a241920f8196f75de5795fccc6c3b0da8cfb86ca947cbaa41'}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    args = parser.parse_args()
    directory = args.project.expanduser().resolve(strict=True)/'scripts/andrea'
    for name, expected in EXPECTED.items():
        if hashlib.sha256((directory/name).read_bytes()).hexdigest() != expected:
            raise SystemExit('Client o casi diversi dalla versione verificata. Nessuna richiesta inviata.')
    cases = json.loads((directory/'structured_cases.json').read_text())
    selected = [case for case in cases if case['id'] == 'historical']
    if len(selected) != 1:
        raise SystemExit('Caso storico non univoco. Nessuna richiesta inviata.')
    client = load('verified_client',directory/'collaudo.py')
    collector = load('verified_structured_collector',directory/'check_structured.py')
    print('Una richiesta: stesso caso storico del collaudo, senza note personali o retry.',flush=True)
    print(json.dumps(collector.collect(client.run_request,selected),ensure_ascii=False,indent=2))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit('Controllo interrotto; caso non concluso.')
