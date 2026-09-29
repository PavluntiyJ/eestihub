"""Convert the official EHAK ZIP to our small, attributed Tallinn GeoJSON.

Maintenance only: pip install pyshp pyproj. Runtime has no new dependencies.
Usage: python -m scripts.build_district_boundaries path/to/asustusyksus_shp.zip
"""
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import shapefile
from pyproj import Transformer

IDS = {'0596': 'pirita', '0524': 'nomme', '0387': 'lasnamae',
       '0339': 'kristiine', '0482': 'mustamae', '0614': 'pohja-tallinn',
       '0298': 'kesklinn', '0176': 'haabersti'}


def main():
    source = Path(sys.argv[1]).read_bytes()
    transform = Transformer.from_crs(3301, 4326, always_xy=True)

    def coordinates(value):
        if isinstance(value[0], (int, float)):
            return [round(n, 6) for n in transform.transform(*value[:2])]
        return [coordinates(v) for v in value]

    with zipfile.ZipFile(io.BytesIO(source)) as archive:
        reader = shapefile.Reader(**{ext: io.BytesIO(archive.read('asustusyksus.' + ext))
                                     for ext in ('shp', 'shx', 'dbf')}, encoding='cp1257')
        features = []
        for row in reader.iterShapeRecords():
            data = row.record.as_dict()
            if data['OKOOD'] != '0784' or data['TYYP'] != '6':
                continue
            geometry = row.shape.__geo_interface__
            geometry['coordinates'] = coordinates(geometry['coordinates'])
            features.append({'type': 'Feature', 'id': IDS[data['AKOOD']],
                             'properties': {'id': IDS[data['AKOOD']], 'name': data['ANIMI'],
                                            'ehak': data['AKOOD'], 'observed_on': str(data['EKSPORT'])},
                             'geometry': geometry})
    assert {f['id'] for f in features} == set(IDS.values())
    output = {'type': 'FeatureCollection', 'features': features,
              'attribution': 'Maa- ja Ruumiamet, EHAK 2026-09-02',
              'source_url': 'https://geoportaal.maaruum.ee/est/ruumiandmed/haldus-ja-asustusjaotus-p119.html',
              'download_url': 'https://s3.pilw.io/rp-kemit-kataster/EHAK/asustusyksus_shp.zip',
              'license_url': 'https://kataster.ee/sites/default/files/documents/2024-03/MTP_andmeteenuste_kasutustingimused.pdf',
              'retrieved_at': '2026-09-29', 'source_sha256': hashlib.sha256(source).hexdigest()}
    path = Path(__file__).resolve().parents[1] / 'app/data/districts.geojson'
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    print(f'{len(features)} districts; {path.stat().st_size} bytes')


if __name__ == '__main__':
    main()
