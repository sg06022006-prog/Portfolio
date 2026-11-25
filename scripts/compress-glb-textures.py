"""Resize embedded GLB textures for the browser; keep mesh buffers unchanged."""
import io, json, struct, sys
from pathlib import Path
from PIL import Image
path = Path(sys.argv[1])
data = path.read_bytes()
assert data[:4] == b'glTF'
json_length = struct.unpack_from('<I', data, 12)[0]
document = json.loads(data[20:20 + json_length])
bin_offset = 20 + json_length
bin_length = struct.unpack_from('<I', data, bin_offset)[0]
binary = data[bin_offset + 8:bin_offset + 8 + bin_length]
colors = set()
for material in document.get('materials', []):
    for texture in [material.get('pbrMetallicRoughness', {}).get('baseColorTexture'), material.get('emissiveTexture')]:
        if texture:
            colors.add(document['textures'][texture['index']]['source'])
images_by_view = {image['bufferView']: (index, image) for index, image in enumerate(document['images'])}
new_binary = bytearray()
for index, view in enumerate(document['bufferViews']):
    assert view.get('buffer', 0) == 0
    old_offset = view.get('byteOffset', 0)
    payload = binary[old_offset:old_offset + view['byteLength']]
    if index in images_by_view:
        image_index, image_info = images_by_view[index]
        image = Image.open(io.BytesIO(payload))
        image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        encoded = io.BytesIO()
        has_alpha = 'A' in image.getbands() and image.getchannel('A').getextrema()[0] < 255
        if image_index in colors and (not has_alpha):
            image.convert('RGB').save(encoded, format='JPEG', quality=90, optimize=True)
            image_info['mimeType'] = 'image/jpeg'
        else:
            image.save(encoded, format='PNG', optimize=True)
            image_info['mimeType'] = 'image/png'
        payload = encoded.getvalue()
    while len(new_binary) % 4:
        new_binary.append(0)
    view['byteOffset'] = len(new_binary)
    view['byteLength'] = len(payload)
    new_binary.extend(payload)
document['buffers'][0]['byteLength'] = len(new_binary)
while len(new_binary) % 4:
    new_binary.append(0)
new_json = json.dumps(document, separators=(',', ':')).encode()
while len(new_json) % 4:
    new_json += b' '
length = 12 + 8 + len(new_json) + 8 + len(new_binary)
output = struct.pack('<4sII', b'glTF', 2, length) + struct.pack('<I4s', len(new_json), b'JSON') + new_json + struct.pack('<I4s', len(new_binary), b'BIN\x00') + new_binary
path.write_bytes(output)
print(f'GLB texture compression: {len(data)} -> {len(output)} bytes. Geometry unchanged.')
