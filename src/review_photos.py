# SECTION 1: IMPORTS AND PATHS
import json
import re
import uuid
import html
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from flask import Flask, jsonify, render_template_string, request, send_from_directory
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent.parent
DESTINATIONS_FILE = ROOT / 'data' / 'destinations.json'
MAPPING_FILE = ROOT / 'static' / 'js' / 'destination_images.js'
IMAGE_DIR = ROOT / 'static' / 'images'
CREDITS_FILE = ROOT / 'data' / 'review_image_credits.json'
MAX_PHOTOS = 10
COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
USER_AGENT = 'MalaysiaTravelStudentProject/1.0 (educational photo review)'

ALLOWED = {'.jpg', '.jpeg', '.png', '.webp'}
IMAGE_DIR.mkdir(parents=True, exist_ok=True)
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 12 * 1024 * 1024

# SECTION 2: READ AND WRITE DATA
def destinations():
    data = json.loads(DESTINATIONS_FILE.read_text(encoding='utf-8'))
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ('destinations', 'data'):
            if isinstance(data.get(key), list):
                return data[key]
    raise ValueError('Unexpected destinations.json structure')

def mapping():
    if not MAPPING_FILE.exists():
        return {}
    source = MAPPING_FILE.read_text(encoding='utf-8')
    match = re.search(r'window\.DESTINATION_IMAGES\s*=\s*(\{.*?\})\s*;', source, re.S)
    if not match:
        raise ValueError('Cannot read destination_images.js. Expected window.DESTINATION_IMAGES = {...};')
    return json.loads(match.group(1))

def save_mapping(data):
    # Backup before overwriting the existing mapping.
    if MAPPING_FILE.exists():
        backup = MAPPING_FILE.with_suffix('.js.bak')
        backup.write_text(MAPPING_FILE.read_text(encoding='utf-8'), encoding='utf-8')
    MAPPING_FILE.write_text('window.DESTINATION_IMAGES = ' + json.dumps(data, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')

def valid_id(destination_id):
    return isinstance(destination_id, str) and any(d.get('id') == destination_id for d in destinations())

def safe_image(filename):
    return (isinstance(filename, str) and filename == Path(filename).name
            and Path(filename).suffix.lower() in ALLOWED
            and (IMAGE_DIR / filename).is_file())

def credits():
    if CREDITS_FILE.exists():
        return json.loads(CREDITS_FILE.read_text(encoding='utf-8'))
    return {}

# SECTION 3: PHOTO REVIEW INTERFACE
PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Travel Photo Review</title>
<style>
*{box-sizing:border-box}body{font-family:Arial,sans-serif;margin:0;background:#f3f7f4;color:#203629}
main{max-width:1180px;margin:30px auto;padding:0 18px}h1{color:#17653c}p{line-height:1.5}
.toolbar,.upload{background:white;border-radius:14px;padding:18px;margin:18px 0;box-shadow:0 2px 10px #0001}
select,input,button{font:inherit;padding:10px;border-radius:8px;border:1px solid #c9d7cc}
button{cursor:pointer;background:#17653c;color:white;border:0}button:disabled{opacity:.45;cursor:not-allowed}
button.secondary{background:#e8f0e9;color:#184d30}button.danger{background:#9b3434}
.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(245px,1fr));gap:16px;margin-top:18px}
.card{background:white;border-radius:13px;overflow:hidden;box-shadow:0 2px 10px #0001;border:2px solid transparent}
.card.cover{border-color:#238b50}.card img{width:100%;height:185px;object-fit:cover;display:block}
.card .inner{padding:12px}.filename{font-size:12px;overflow-wrap:anywhere;color:#647269}
.note{color:#5d6c61;font-size:13px}.tag{font-size:12px;font-weight:bold;color:#17653c}
#status{font-weight:bold;min-height:20px}label{display:block;margin:8px 0 4px}
.upload-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px}
input[type=file],input[type=text],input[type=url],select{width:100%}
</style></head><body><main>
<h1>Malaysia Travel — Photo Review</h1>
<p>Choose beautiful photos of <b>famous tourist attractions</b>. Add photos you have permission to use, reorder them, and select the best cover photo. Maximum: 10 per destination.</p>
<section class="toolbar"><label for="destination">Destination</label><select id="destination"></select>
<div class="controls"><button id="save">Save Gallery</button><span id="count"></span></div>
<p id="status" role="status"></p></section>
<section class="upload"><h2>Add attraction photos</h2>
<p class="note">Download a suitable, licensed photograph to your computer first (for example, from Wikimedia Commons), then upload it here. Record its source and licence.</p>
<div class="upload-grid"><div><label for="photo">Photo file</label><input id="photo" type="file" accept="image/jpeg,image/png,image/webp"></div>
<div><label for="attraction">Attraction name</label><input id="attraction" type="text" placeholder="e.g. Dutch Square"></div>
<div><label for="source">Photo source URL</label><input id="source" type="url" placeholder="https://commons.wikimedia.org/..."></div>
<div><label for="author">Photographer / author</label><input id="author" type="text" placeholder="Name shown on source page"></div>
<div><label for="licence">Licence</label><input id="licence" type="text" placeholder="e.g. CC BY-SA 4.0"></div></div>
<div class="controls"><button id="upload">Add Photo</button><span class="note">Uploads are saved locally. Only use photos you have the rights to use.</span></div></section>
<section class="upload"><h2>Find famous attraction photos automatically</h2>
<p class="note">Search Wikimedia Commons for photos of a famous attraction. Preview candidates, then click <b>Add to gallery</b>. Review relevance and licence before approving. No photos are automatically published.</p>
<div class="upload-grid"><div><label for="searchTerm">Famous attraction or landmark</label><input id="searchTerm" type="text" placeholder="e.g. Dutch Square Melaka"></div><div><label>&nbsp;</label><button id="searchPhotos">Search Attraction Photos</button></div></div>
<p id="searchStatus" class="note"></p><div id="candidates" class="grid"></div></section>
<h2>Selected gallery photos</h2><p class="note">The first image is the cover. Use ← and → to change the order, or remove an unwanted photo from the gallery. Removed photos remain on your computer.</p>
<div id="gallery" class="grid"></div>
</main><script>
let mapping = {}, selected = [], activeId = '';
const el = id => document.getElementById(id);
function message(text, error=false){el('status').textContent=text;el('status').style.color=error?'#a22':'#17653c'}
function filesFor(id){const files=mapping[id]||[];return Array.isArray(files)?[...files]:[files]}
function button(label,handler,cls='secondary'){const b=document.createElement('button');b.textContent=label;b.className=cls;b.onclick=handler;return b}
function render(){const area=el('gallery');area.replaceChildren();el('count').textContent=`${selected.length} / 10 photos`;
if(!selected.length){const p=document.createElement('p');p.textContent='No photos selected. Add a famous attraction photo above.';area.append(p)}
selected.forEach((filename,index)=>{const card=document.createElement('article');card.className='card'+(index===0?' cover':'');
const img=document.createElement('img');img.src='/review/images/'+encodeURIComponent(filename);img.alt=filename;
const inner=document.createElement('div');inner.className='inner';
const title=document.createElement('div');title.className='tag';title.textContent=index===0?'★ Main cover photo':`Photo ${index+1}`;
const name=document.createElement('p');name.className='filename';name.textContent=filename;
const controls=document.createElement('div');controls.className='controls';
const left=button('←',()=>move(index,-1));left.disabled=index===0;
const right=button('→',()=>move(index,1));right.disabled=index===selected.length-1;
const cover=button('Set as cover',()=>{selected.splice(index,1);selected.unshift(filename);render()});cover.disabled=index===0;
const remove=button('Remove',()=>{selected.splice(index,1);render()},'danger');
controls.append(left,right,cover,remove);inner.append(title,name,controls);card.append(img,inner);area.append(card)});
}
function move(i,dir){const j=i+dir;if(j<0||j>=selected.length)return;[selected[i],selected[j]]=[selected[j],selected[i]];render()}
function changeDestination(){activeId=el('destination').value;selected=filesFor(activeId);message('');render()}
async function init(){try{const response=await fetch('/api/review/data');if(!response.ok)throw Error('Cannot load destinations');const data=await response.json();mapping=data.mapping;
for(const d of data.destinations){const option=document.createElement('option');option.value=d.id;option.textContent=`${d.id} — ${d.name}`;el('destination').append(option)}
el('destination').onchange=changeDestination;changeDestination()}catch(e){message(e.message,true)}}
async function save(){try{const response=await fetch('/api/review/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({destination_id:activeId,images:selected})});const data=await response.json();if(!response.ok)throw Error(data.error||'Save failed');mapping[activeId]=[...selected];message('Gallery saved! Refresh your main travel website to see the changes.')}catch(e){message(e.message,true)}}
async function searchPhotos(){const query=el('searchTerm').value.trim();if(!query){el('searchStatus').textContent='Enter a famous attraction name.';return}
el('searchStatus').textContent='Searching Wikimedia Commons...';el('candidates').replaceChildren();
try{const response=await fetch('/api/review/search?destination_id='+encodeURIComponent(activeId)+'&q='+encodeURIComponent(query));const data=await response.json();if(!response.ok)throw Error(data.error||'Search failed');
el('searchStatus').textContent=data.results.length?`${data.results.length} candidate photos found. Check each picture carefully.`:'No suitable results. Try a more specific landmark name.';
for(const photo of data.results){const card=document.createElement('article');card.className='card';const img=document.createElement('img');img.src=photo.thumb;img.alt=photo.title;img.loading='lazy';const inner=document.createElement('div');inner.className='inner';
const title=document.createElement('p');title.className='filename';title.textContent=photo.title;
const info=document.createElement('p');info.className='note';info.textContent=`Licence: ${photo.licence || 'Check source'} | Author: ${photo.author || 'See source'}`;
const source=document.createElement('a');source.href=photo.page;source.target='_blank';source.rel='noopener noreferrer';source.textContent='View source and licence';
const add=button('Add to gallery',()=>addCandidate(photo),'');inner.append(title,info,source,document.createElement('br'),add);card.append(img,inner);el('candidates').append(card)}}catch(e){el('searchStatus').textContent=e.message}}
async function addCandidate(photo){if(selected.length>=10){message('Maximum 10 photos per destination.',true);return}
try{const response=await fetch('/api/review/import',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({destination_id:activeId,title:photo.title,attraction:el('searchTerm').value.trim()})});const data=await response.json();if(!response.ok)throw Error(data.error||'Download failed');if(!selected.includes(data.filename))selected.push(data.filename);render();message('Photo downloaded into your review list. Click Save Gallery to publish.')}catch(e){message(e.message,true)}}
async function upload(){const photo=el('photo').files[0];if(!photo){message('Choose a photo file first.',true);return}if(selected.length>=10){message('Maximum 10 photos. Remove one first.',true);return}
const fd=new FormData();fd.append('destination_id',activeId);fd.append('photo',photo);
for(const field of ['attraction','source','author','licence'])fd.append(field,el(field).value.trim());
try{const response=await fetch('/api/review/upload',{method:'POST',body:fd});const data=await response.json();if(!response.ok)throw Error(data.error||'Upload failed');selected.push(data.filename);render();el('photo').value='';message('Photo added to the review list. Click Save Gallery to publish it.')}catch(e){message(e.message,true)}}
el('save').onclick=save;el('upload').onclick=upload;el('searchPhotos').onclick=searchPhotos;init();
</script></body></html>'''

# SECTION 4: FLASK ROUTES
@app.get('/')
def home():
    return render_template_string(PAGE)

@app.get('/review/images/<path:filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_DIR, filename)

@app.get('/api/review/data')
def review_data():
    return jsonify({'destinations': destinations(), 'mapping': mapping()})

@app.post('/api/review/save')
def review_save():
    data = request.get_json(silent=True) or {}
    destination_id = data.get('destination_id')
    images = data.get('images')
    if not valid_id(destination_id):
        return jsonify(error='Invalid destination'), 400
    if not isinstance(images, list) or len(images) > MAX_PHOTOS or len(images) != len(set(map(str, images))):
        return jsonify(error='Select up to 10 different photos'), 400
    if not all(safe_image(name) for name in images):
        return jsonify(error='One or more photo files are missing or invalid'), 400
    data_map = mapping()
    data_map[destination_id] = images
    save_mapping(data_map)
    return jsonify(success=True)

@app.post('/api/review/upload')
def review_upload():
    destination_id = request.form.get('destination_id', '')
    if not valid_id(destination_id):
        return jsonify(error='Invalid destination'), 400
    uploaded = request.files.get('photo')
    if not uploaded or not uploaded.filename:
        return jsonify(error='Please select a photo'), 400
    ext = Path(secure_filename(uploaded.filename)).suffix.lower()
    if ext not in ALLOWED:
        return jsonify(error='Use JPG, PNG or WEBP'), 400
    # Validate actual file signature rather than trusting the filename alone.
    signature = uploaded.stream.read(16)
    uploaded.stream.seek(0)
    is_jpeg = signature.startswith(b'\xff\xd8\xff')
    is_png = signature.startswith(b'\x89PNG\r\n\x1a\n')
    is_webp = signature[:4] == b'RIFF' and signature[8:12] == b'WEBP'
    if not ((ext in ('.jpg', '.jpeg') and is_jpeg) or (ext == '.png' and is_png) or (ext == '.webp' and is_webp)):
        return jsonify(error='The file is not a valid image of the selected type'), 400
    filename = f'{destination_id}_curated_{uuid.uuid4().hex[:12]}{ext}'
    uploaded.save(IMAGE_DIR / filename)
    info = credits()
    info[filename] = {
        'destination_id': destination_id,
        'attraction': request.form.get('attraction', '').strip(),
        'source': request.form.get('source', '').strip(),
        'author': request.form.get('author', '').strip(),
        'licence': request.form.get('licence', '').strip()
    }
    CREDITS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDITS_FILE.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
    return jsonify(success=True, filename=filename)

@app.errorhandler(413)
def too_large(_error):
    return jsonify(error='Photo too large. Maximum upload size is 12 MB.'), 413


# SECTION 5: SEARCH WIKIMEDIA COMMONS (REVIEW BEFORE APPROVAL)
def commons_api(params):
    query = urllib.parse.urlencode({'format': 'json', 'formatversion': 2, **params})
    req = urllib.request.Request(COMMONS_API + '?' + query, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(req, timeout=18) as response:
        return json.load(response)

def clean_meta(value):
    return re.sub(r'<[^>]*>', '', html.unescape(value or '')).strip()[:350]

def commons_photo(title):
    result = commons_api({'action': 'query', 'titles': title, 'prop': 'imageinfo',
                          'iiprop': 'url|size|extmetadata|mime', 'iiurlwidth': 480})
    pages = result.get('query', {}).get('pages', [])
    if not pages or 'missing' in pages[0] or not pages[0].get('imageinfo'):
        return None
    page = pages[0]
    info = page['imageinfo'][0]
    metadata = info.get('extmetadata', {})
    licence = clean_meta(metadata.get('LicenseShortName', {}).get('value', ''))
    # Only accept photos with clearly identifiable Creative Commons or public-domain licences.
    allowed = ('CC BY', 'CC-BY', 'CC0', 'PUBLIC DOMAIN', 'PD-', 'PDM')
    if not any(licence.upper().startswith(x) for x in allowed):
        return None
    if info.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
        return None
    return {'title': page['title'], 'thumb': info.get('thumburl', info.get('url', '')),
            'url': info.get('url', ''), 'page': info.get('descriptionurl', ''),
            'licence': licence, 'author': clean_meta(metadata.get('Artist', {}).get('value', '')),
            'size': info.get('size', 0), 'mime': info.get('mime', '')}

@app.get('/api/review/search')
def review_search():
    destination_id = request.args.get('destination_id', '')
    q = request.args.get('q', '').strip()
    if not valid_id(destination_id) or not 3 <= len(q) <= 100:
        return jsonify(error='Choose a destination and enter a valid attraction name'), 400
    try:
        result = commons_api({'action': 'query', 'generator': 'search',
                              'gsrsearch': 'filetype:bitmap ' + q,
                              'gsrnamespace': 6, 'gsrlimit': 25,
                              'prop': 'imageinfo', 'iiprop': 'url|size|extmetadata|mime',
                              'iiurlwidth': 480})
        photos = []
        for page in result.get('query', {}).get('pages', []):
            info = (page.get('imageinfo') or [{}])[0]
            metadata = info.get('extmetadata', {})
            licence = clean_meta(metadata.get('LicenseShortName', {}).get('value', ''))
            if not any(licence.upper().startswith(x) for x in ('CC BY', 'CC-BY', 'CC0', 'PUBLIC DOMAIN', 'PD-', 'PDM')):
                continue
            if info.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
                continue
            photos.append({'title': page['title'], 'thumb': info.get('thumburl', info.get('url', '')),
                           'page': info.get('descriptionurl', ''), 'licence': licence,
                           'author': clean_meta(metadata.get('Artist', {}).get('value', ''))})
            if len(photos) >= 15:
                break
        return jsonify(results=photos)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return jsonify(error='Cannot reach Wikimedia Commons. Check internet connection and retry.'), 502

@app.post('/api/review/import')
def review_import():
    data = request.get_json(silent=True) or {}
    destination_id = data.get('destination_id', '')
    title = data.get('title', '')
    if not valid_id(destination_id) or not isinstance(title, str) or not title.startswith('File:') or len(title) > 240:
        return jsonify(error='Invalid destination or photo'), 400
    try:
        photo = commons_photo(title)
        if not photo:
            return jsonify(error='This photo has no supported open licence or image format'), 400
        if photo['size'] > 12 * 1024 * 1024:
            return jsonify(error='Image exceeds 12 MB; choose a smaller photo'), 400
        ext = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp'}[photo['mime']]
        url = photo['url']
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or not parsed.hostname or not (parsed.hostname == 'upload.wikimedia.org' or parsed.hostname.endswith('.wikimedia.org')):
            return jsonify(error='Unexpected image host'), 400
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(req, timeout=25) as response:
            blob = response.read(12 * 1024 * 1024 + 1)
        if len(blob) > 12 * 1024 * 1024:
            return jsonify(error='Photo is too large'), 400
        if not ((ext == '.jpg' and blob.startswith(b'\xff\xd8\xff')) or
                (ext == '.png' and blob.startswith(b'\x89PNG\r\n\x1a\n')) or
                (ext == '.webp' and blob.startswith(b'RIFF') and blob[8:12] == b'WEBP')):
            return jsonify(error='Invalid image data'), 400
        filename = f'{destination_id}_commons_{uuid.uuid4().hex[:12]}{ext}'
        (IMAGE_DIR / filename).write_bytes(blob)
        info = credits()
        info[filename] = {'destination_id': destination_id,
                          'attraction': str(data.get('attraction', ''))[:150],
                          'source': photo['page'], 'author': photo['author'],
                          'licence': photo['licence'], 'commons_title': photo['title']}
        CREDITS_FILE.parent.mkdir(parents=True, exist_ok=True)
        CREDITS_FILE.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding='utf-8')
        return jsonify(success=True, filename=filename)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return jsonify(error='Could not download this photo. Try another.'), 502

# SECTION 6: START LOCAL REVIEW SERVER
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5002, debug=False)
