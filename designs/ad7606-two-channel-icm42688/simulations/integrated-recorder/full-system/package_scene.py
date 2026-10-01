"""Package the visible Wokwi scene and its tested simulation-only image."""
from pathlib import Path
import hashlib
import json
import zipfile

from verify_scene import verify

P = Path(__file__).resolve().parent


def package():
    checks = verify()
    target = P.parents[2]
    image_manifest = json.loads((P.parent / 'firmware/manifest.json').read_text())
    for name, digest in image_manifest['sha256'].items():
        assert hashlib.sha256((target/name).read_bytes()).hexdigest() == digest, name
    names = ['README.md', 'NOTICE.md', 'esp32-bin-file.ino', 'diagram.json',
             'manifest.json', 'scene-checks.json', 'browser-checks.json', 'browser-proof.png', 'assembly-proof.png']
    files = {f'integrated-recorder/full-system/{name}': P/name for name in names}
    for path in sorted(P.glob('*.chip.*')):
        files[f'integrated-recorder/full-system/{path.name}'] = path
    files['integrated-recorder/full-system/results/normal/result.json'] = P/'results/normal/result.json'
    files['integrated-recorder/full-system/results/saved-project-normal/result.json'] = P/'results/saved-project-normal/result.json'
    for name in ['merged.bin', 'manifest.json']:
        files[f'integrated-recorder/firmware/{name}'] = P.parent/'firmware'/name
    for path in sorted((target/'licenses/esp-idf').rglob('*')):
        if path.is_file():
            files[path.relative_to(target).as_posix()] = path
    assert len([name for name in files if '.chip.' in name]) == 24
    out = P/'full-system-wokwi.zip'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, path in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(out) as archive:
        assert archive.testzip() is None
        for name, path in files.items():
            assert archive.read(name) == path.read_bytes(), name
    manifest = {
        'file': out.name,
        'bytes': out.stat().st_size,
        'sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
        'wokwi_project_url': 'https://wokwi.com/projects/476662256690643969',
        'simulation_only': True,
        'hardware_measured': False,
        'scene_checks': checks,
        'firmware_sha256': image_manifest['sha256']['simulations/integrated-recorder/firmware/merged.bin'],
        'sha256_contents': {name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in sorted(files.items())},
    }
    (P/'download.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (P/'full-system-wokwi.zip.sha256').write_text(f"{manifest['sha256']}  {out.name}\n")
    print(json.dumps({key:manifest[key] for key in ['file','bytes','sha256','simulation_only']}))


if __name__ == '__main__':
    package()
