"""Assess an actual whole-scene transcript with the existing strict assessor."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
import tempfile

from verify_scene import verify

P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parent))
import run as integrated


def assess(out=None):
    checked = verify()
    out = Path(out) if out is not None else P / 'results/normal'
    image = json.loads((out/'tested-build.json').read_text())
    root = P.parents[2]
    for name, digest in image['sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest() == digest, name
    assert json.loads((out/'diagram.json').read_text()) == json.loads((P/'diagram.json').read_text()), 'Saved scene differs'
    text = (out/'serial.txt').read_text()
    prefix = image['sha256']['simulations/integrated-recorder/firmware/integrated_recorder.elf'][:9]
    assert f'ELF file SHA256:  {prefix}' in text, 'Wrong uploaded image'
    with tempfile.TemporaryDirectory(prefix='afo-scene-check-') as directory:
        fresh = Path(directory)
        result = integrated.assess('normal', text, fresh)
        for name in ['recorder-output.raw', 'udp-output.raw']:
            if (out/name).exists():
                assert (out/name).read_bytes() == (fresh/name).read_bytes(), 'Original evidence changed'
        for path in fresh.iterdir():
            target = out/path.name
            if target.exists():
                continue
            if path.is_dir():
                shutil.copytree(path, target)
            else:
                shutil.copyfile(path, target)
    result.update(scene='complete-system-context', case='normal', engine='Wokwi web editor',
                  hardware_measured=False, scene_checks=checked,
                  scene_sha256=hashlib.sha256((out/'diagram.json').read_bytes()).hexdigest(),
                  serial_sha256=hashlib.sha256((out/'serial.txt').read_bytes()).hexdigest(),
                  merged_image_sha256=image['sha256']['simulations/integrated-recorder/firmware/merged.bin'])
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', type=Path, default=P/'results/normal')
    args = parser.parse_args()
    result = assess(args.results)
    print(json.dumps({key:result[key] for key in ['pass','production','saved_record_count','udp_packets','scene_checks']}))
    raise SystemExit(0 if result['pass'] else 1)
