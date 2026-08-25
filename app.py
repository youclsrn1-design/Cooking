"""
오늘 뭐 해먹지 — 냉장고 재료 레시피
Streamlit Cloud 배포용 (React 아티팩트 디자인 이식 버전)

실행: streamlit run app.py
필요: Streamlit Cloud → Settings → Secrets 에
      ANTHROPIC_API_KEY = "sk-ant-..."
"""

import base64
import html as html_lib
import json
import random
import re

import streamlit as st
import streamlit.components.v1 as components
from anthropic import Anthropic

MODEL = "claude-sonnet-5"

st.set_page_config(page_title="오늘 뭐 해먹지", page_icon="🍳", layout="centered")

INK, TILE, LINE, PAPER = "#16241F", "#DCE7E2", "#B4C7BF", "#FBF7EF"
TOMATO, BUTTER, HERB = "#D4402C", "#F0BA3F", "#4E7A5E"


# ────────────────────────────── 스타일 ──────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=IBM+Plex+Sans+KR:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

.stApp {{ background:{TILE}; }}
.block-container {{ max-width:640px; padding-top:1.6rem; padding-bottom:4rem; }}
html, body, [class*="css"] {{ font-family:'IBM Plex Sans KR',system-ui,sans-serif; color:{INK}; }}
#MainMenu, footer {{ visibility:hidden; }}

.fr-eyebrow {{ font-family:'IBM Plex Mono',monospace; font-size:11px; letter-spacing:.22em;
  text-transform:uppercase; color:{HERB}; margin:0 0 10px; }}
.fr-title {{ font-family:'Black Han Sans',sans-serif; font-weight:400; line-height:.98;
  font-size:clamp(40px,12vw,62px); margin:0; letter-spacing:-.01em; color:{INK}; }}
.fr-title em {{ font-style:normal; color:{TOMATO}; }}
.fr-sub {{ font-size:14.5px; line-height:1.65; color:#3D544B; margin:14px 0 0; max-width:34ch; }}

.fr-label {{ font-family:'IBM Plex Mono',monospace; font-size:11px; letter-spacing:.2em;
  text-transform:uppercase; color:{HERB}; margin:26px 0 8px; }}
.fr-note {{ font-size:12.5px; color:#7A8E86; text-align:center; margin-top:10px; line-height:1.6; }}
.fr-empty {{ font-size:13.5px; color:#7A8E86; padding:6px 2px; }}

[data-testid="stTextInput"] input {{
  background:#fff; border:1.5px solid {LINE}; border-radius:4px; padding:11px 13px;
  font-size:15px; font-family:'IBM Plex Sans KR'; color:{INK}; }}
[data-testid="stTextInput"] input:focus {{ border-color:{HERB}; box-shadow:0 0 0 2px rgba(78,122,94,.25); }}

.stButton > button {{
  border:1.5px solid {INK}; background:#fff; color:{INK}; border-radius:4px;
  font-family:'IBM Plex Sans KR'; font-size:14px; font-weight:600; padding:9px 14px; width:100%; }}
.stButton > button:hover {{ background:{INK}; color:{PAPER}; border-color:{INK}; }}

[class*="st-key-mag"] .stButton > button {{
  background:{BUTTER}; border:1.5px solid {INK}; border-radius:3px;
  box-shadow:2px 2px 0 rgba(22,36,31,.85); font-weight:500; padding:7px 10px; }}
[class*="st-key-mag"] .stButton > button:hover {{ background:{TOMATO}; color:#FFF6EC; }}

[class*="st-key-qk"] .stButton > button {{
  border:1px solid {LINE}; background:transparent; color:#3D544B;
  border-radius:20px; font-weight:400; font-size:13px; padding:6px 10px; box-shadow:none; }}
[class*="st-key-qk"] .stButton > button:hover {{ border-color:{HERB}; color:{HERB}; background:transparent; }}

[class*="st-key-go"] .stButton > button {{
  background:{TOMATO}; color:#FFF6EC; border:1.5px solid {INK}; border-radius:4px;
  font-family:'Black Han Sans',sans-serif; font-size:19px; letter-spacing:.02em;
  padding:16px; box-shadow:0 4px 0 {INK}; }}
[class*="st-key-go"] .stButton > button:hover {{ background:#B93522; color:#FFF6EC;
  transform:translateY(2px); box-shadow:0 2px 0 {INK}; }}
[class*="st-key-go"] .stButton > button:disabled {{ opacity:.42; box-shadow:0 4px 0 {LINE}; }}

[data-testid="stRadio"] label {{ font-size:14px; color:#3D544B; }}
[data-testid="stFileUploader"] section {{ background:{PAPER}; border:1.5px dashed {LINE}; border-radius:4px; }}
</style>
""", unsafe_allow_html=True)


# ────────────────────────────── Claude 호출 ──────────────────────────────
@st.cache_resource
def get_client():
    key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if not key:
        st.error('API 키가 없습니다. Streamlit Cloud → Settings → Secrets 에 '
                 'ANTHROPIC_API_KEY = "sk-ant-..." 를 넣어 주세요.')
        st.stop()
    return Anthropic(api_key=key)


def ask(content, max_tokens=4000):
    msg = get_client().messages.create(
        model=MODEL, max_tokens=max_tokens,
        messages=[{"role": "user", "content": content}],
    )
    return "".join(b.text for b in msg.content if b.type == "text")


def parse_json(text):
    t = re.sub(r"```(?:json)?", "", text).strip()
    for a, b in (("[", "]"), ("{", "}")):
        s, e = t.find(a), t.rfind(b)
        if s != -1 and e != -1:
            try:
                return json.loads(t[s:e + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("JSON 파싱 실패")


# ────────────────────────────── 요리 그림(SVG) ──────────────────────────────
def shade(hex_color, amt):
    h = str(hex_color or "#cccccc").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        r = g = b = 200
    f = lambda v: max(0, min(255, round(v + 255 * amt)))
    return "#%02x%02x%02x" % (f(r), f(g), f(b))


def dish_svg(name, form, palette):
    """요리 이름을 시드로 써서 매번 같은 그림이 나오는 SVG 일러스트"""
    ok = (isinstance(palette, list) and len(palette) >= 3
          and str(palette[0]).startswith("#"))
    main, sauce, garnish = palette[:3] if ok else ("#C8552F", "#E9B44C", "#5B7F5B")
    rnd = random.Random(name)
    bowl = form in ("soup", "stew", "noodle")
    hot = form in ("soup", "stew", "noodle", "stirfry", "grill", "dumpling")
    cy = 74 if bowl else 86
    p = []

    if form in ("soup", "stew"):
        p.append(f'<ellipse cx="100" cy="{cy}" rx="66" ry="17" fill="{sauce}"/>')
        for i in range(7):
            x, y = 100 + rnd.uniform(-46, 46), cy + rnd.uniform(-9, 9)
            c = garnish if i % 3 == 0 else main
            p.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rnd.uniform(5,11):.1f}" '
                     f'ry="{rnd.uniform(3,6):.1f}" fill="{c}"/>')
    elif form == "noodle":
        p.append(f'<ellipse cx="100" cy="{cy}" rx="66" ry="17" fill="{sauce}"/>')
        for i in range(5):
            y = cy - 6 + i * 3.4
            p.append(f'<path d="M46,{y} q18,-7 36,0 q18,7 36,0 q12,-5 24,1" '
                     f'stroke="{shade(main,0.12)}" stroke-width="3.4" fill="none" stroke-linecap="round"/>')
        p.append(f'<ellipse cx="130" cy="{cy-2}" rx="11" ry="7" fill="{garnish}"/>')
    elif form == "rice":
        p.append(f'<path d="M54,{cy} q46,-40 92,0 z" fill="{shade(main,0.18)}"/>')
        for i in range(26):
            x = 60 + rnd.uniform(0, 80)
            y = cy - rnd.uniform(0, max(4, 34 - abs(x - 100) * 0.6))
            c = garnish if i % 4 == 0 else sauce
            p.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.uniform(1.6,3.2):.1f}" fill="{c}"/>')
    elif form == "grill":
        for i in range(3):
            x, y = 54 + i * 32, cy - 20 - rnd.uniform(0, 6)
            rot = rnd.uniform(-8, 8)
            p.append(f'<rect x="{x}" y="{y:.1f}" width="38" height="24" rx="7" fill="{main}" '
                     f'transform="rotate({rot:.1f} {x+19} {y+12:.1f})"/>')
            for j in range(3):
                p.append(f'<line x1="{x+5}" y1="{y+6+j*6:.1f}" x2="{x+33}" y2="{y+6+j*6:.1f}" '
                         f'stroke="{shade(main,-0.25)}" stroke-width="2" stroke-linecap="round" '
                         f'transform="rotate({rot:.1f} {x+19} {y+12:.1f})"/>')
        p.append(f'<ellipse cx="144" cy="{cy-4}" rx="12" ry="7" fill="{garnish}"/>')
    elif form == "salad":
        for i in range(11):
            x, y = 100 + rnd.uniform(-46, 46), cy - 8 + rnd.uniform(-11, 11)
            c = (main, garnish, shade(garnish, 0.15))[i % 3]
            p.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rnd.uniform(8,15):.1f}" '
                     f'ry="{rnd.uniform(5,9):.1f}" fill="{c}" '
                     f'transform="rotate({rnd.uniform(0,180):.0f} {x:.1f} {y:.1f})"/>')
    elif form == "pancake":
        p.append(f'<ellipse cx="100" cy="{cy-4}" rx="48" ry="16" fill="{shade(main,-0.08)}"/>')
        p.append(f'<ellipse cx="103" cy="{cy-15}" rx="46" ry="15" fill="{main}"/>')
        for i in range(6):
            c = garnish if i % 2 else sauce
            p.append(f'<ellipse cx="{70+rnd.uniform(0,62):.1f}" cy="{cy-20+rnd.uniform(0,8):.1f}" '
                     f'rx="{rnd.uniform(4,7):.1f}" ry="2.5" fill="{c}"/>')
    elif form == "bread":
        p.append(f'<rect x="56" y="{cy-34}" width="88" height="34" rx="12" fill="{main}"/>')
        p.append(f'<rect x="66" y="{cy-27}" width="68" height="18" rx="8" fill="{shade(main,0.22)}"/>')
        p.append(f'<ellipse cx="130" cy="{cy-2}" rx="11" ry="6" fill="{garnish}"/>')
    elif form == "dumpling":
        for i in range(4):
            x, y = 58 + i * 28, cy - 12 - rnd.uniform(0, 8)
            p.append(f'<path d="M{x-14},{y:.1f} q14,-20 28,0 q-14,9 -28,0 z" fill="{main}" '
                     f'transform="rotate({rnd.uniform(-12,12):.1f} {x} {y:.1f})"/>')
        p.append(f'<ellipse cx="140" cy="{cy-3}" rx="10" ry="6" fill="{garnish}"/>')
    else:  # stirfry / 기본
        for i in range(12):
            x, y = 100 + rnd.uniform(-46, 46), cy - 10 + rnd.uniform(-10, 10)
            c = (garnish, sauce, main, main)[i % 4]
            p.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{rnd.uniform(7,23):.1f}" height="5.5" '
                     f'rx="2.7" fill="{c}" transform="rotate({rnd.uniform(0,180):.0f} {x:.1f} {y:.1f})"/>')

    inner = "".join(p)
    uid = abs(hash(str(name))) % 100000
    if bowl:
        vessel = (f'<path d="M30,70 Q34,122 100,124 Q166,122 170,70 Z" fill="#ffffff"/>'
                  f'<path d="M30,70 Q34,122 100,124 Q166,122 170,70 Z" fill="#0d1f19" opacity=".05"/>'
                  f'<ellipse cx="100" cy="70" rx="70" ry="19" fill="#f6f2ea"/>'
                  f'<clipPath id="c{uid}"><ellipse cx="100" cy="70" rx="70" ry="19"/></clipPath>'
                  f'<g clip-path="url(#c{uid})">{inner}</g>'
                  f'<ellipse cx="100" cy="70" rx="70" ry="19" fill="none" stroke="#fff" stroke-width="5"/>')
    else:
        vessel = ('<ellipse cx="100" cy="98" rx="80" ry="30" fill="#ffffff"/>'
                  '<ellipse cx="100" cy="97" rx="63" ry="22" fill="#f6f2ea"/>' + inner)

    steam = ('<g class="fr-steam" stroke="#fff" stroke-width="4" fill="none" stroke-linecap="round" opacity=".7">'
             '<path d="M82,40 q9,-11 0,-21 q-8,-9 0,-18"/>'
             '<path d="M102,34 q9,-11 0,-21 q-8,-9 0,-17"/>'
             '<path d="M122,42 q9,-11 0,-21 q-8,-9 0,-16"/></g>') if hot else ""

    return (f'<svg class="fr-art" viewBox="0 0 200 140">'
            f'<ellipse cx="100" cy="126" rx="74" ry="8" fill="#0d1f19" opacity=".09"/>'
            f'{vessel}{steam}</svg>')


# ────────────────────────────── 결과 카드 ──────────────────────────────
CARD_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=IBM+Plex+Sans+KR:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
* {{ box-sizing:border-box; }}
body {{ margin:0; background:{TILE}; font-family:'IBM Plex Sans KR',system-ui,sans-serif; color:{INK}; }}
.fr-card {{ background:{PAPER}; border:1.5px solid {LINE}; border-radius:6px; overflow:hidden;
  margin-bottom:16px; box-shadow:0 3px 0 {LINE}; }}
.fr-artbox {{ background:linear-gradient(170deg,#EAF0EC,#D7E3DD); padding:12px 0 0; position:relative; }}
.fr-art {{ display:block; width:100%; height:auto; max-height:190px; }}
.fr-flag {{ position:absolute; top:11px; left:12px; background:{INK}; color:{PAPER};
  font-family:'IBM Plex Mono',monospace; font-size:10.5px; letter-spacing:.12em;
  padding:4px 8px; border-radius:3px; }}
.fr-steam {{ animation:frSteam 3.4s ease-in-out infinite; }}
@keyframes frSteam {{ 0%,100%{{opacity:0;transform:translateY(6px)}} 50%{{opacity:.7;transform:translateY(-4px)}} }}
.fr-body {{ padding:16px 16px 18px; }}
.fr-name {{ font-family:'Black Han Sans',sans-serif; font-weight:400; font-size:26px; line-height:1.15; margin:0; }}
.fr-summary {{ font-size:14px; line-height:1.6; color:#3D544B; margin:8px 0 0; }}
.fr-meta {{ display:flex; gap:14px; margin-top:13px; padding-top:12px; border-top:1px solid {LINE};
  font-family:'IBM Plex Mono',monospace; font-size:12px; color:{HERB}; }}
.fr-tags {{ margin-top:14px; font-size:13.5px; line-height:1.9; }}
.fr-tags b {{ font-weight:600; font-size:12px; color:#7A8E86; margin-right:6px; }}
.fr-have {{ border-bottom:2px solid {HERB}; padding-bottom:1px; margin-right:8px; }}
.fr-need {{ border-bottom:2px solid {TOMATO}; padding-bottom:1px; margin-right:8px; color:{TOMATO}; }}
.fr-steps {{ list-style:none; padding:0; margin:16px 0 0; counter-reset:st; }}
.fr-steps li {{ display:flex; gap:13px; padding:11px 0; border-top:1px dashed {LINE};
  font-size:14.5px; line-height:1.65; }}
.fr-steps li::before {{ counter-increment:st; content:counter(st,decimal-leading-zero);
  font-family:'IBM Plex Mono',monospace; font-size:12px; color:{TOMATO}; padding-top:3px; flex:none; }}
.fr-tip {{ margin-top:14px; background:#F3EADA; border-radius:4px; padding:12px 14px;
  font-size:13.5px; line-height:1.65; }}
.fr-tip b {{ font-family:'IBM Plex Mono',monospace; font-size:11px; letter-spacing:.14em;
  display:block; margin-bottom:4px; color:{HERB}; }}
@media (prefers-reduced-motion:reduce) {{ .fr-steam {{ animation:none; opacity:.55; }} }}
</style>
"""


def esc(s):
    return html_lib.escape(str(s if s is not None else ""))


def card_html(r):
    steps = "".join(f"<li>{esc(s)}</li>" for s in r.get("steps", []))
    have = "".join(f'<span class="fr-have">{esc(h)}</span>' for h in r.get("have", []))
    need_list = r.get("need") or []
    need = "".join(f'<span class="fr-need">{esc(n)}</span>' for n in need_list)
    need_row = f'<div><b>사야 할 것</b>{need}</div>' if need_list else ""
    tip = f'<div class="fr-tip"><b>맛내기</b>{esc(r.get("tip"))}</div>' if r.get("tip") else ""
    return f"""
<article class="fr-card">
  <div class="fr-artbox">
    <span class="fr-flag">{esc(r.get('cuisine', '요리'))}</span>
    {dish_svg(r.get('name', '요리'), r.get('form'), r.get('palette'))}
  </div>
  <div class="fr-body">
    <h3 class="fr-name">{esc(r.get('name', '요리'))}</h3>
    <p class="fr-summary">{esc(r.get('summary'))}</p>
    <div class="fr-meta">
      <span>{esc(r.get('minutes', '—'))}분</span>
      <span>{esc(r.get('difficulty', '보통'))}</span>
      <span>{esc(r.get('servings', ''))}인분</span>
    </div>
    <div class="fr-tags">
      <div><b>있는 재료</b>{have}</div>
      {need_row}
    </div>
    <ol class="fr-steps">{steps}</ol>
    {tip}
  </div>
</article>"""


def card_height(r):
    h = 200 + 46 + 46 + 56 + 46 + 54 * len(r.get("steps", [])) + 36
    if r.get("need"):
        h += 32
    if r.get("tip"):
        h += 100
    return h


# ────────────────────────────── 프롬프트 ──────────────────────────────
RECIPE_PROMPT = """너는 요리 레시피 큐레이터다.
사용자가 지금 가진 재료: {ings}
요청한 요리 방향: {style}

이 재료로 실제로 만들 수 있는 요리 3가지를 추천해라.

규칙:
- 기본 조미료(소금, 후추, 설탕, 간장, 식용유, 참기름, 다진마늘, 고춧가루, 식초, 물)는 집에 있다고 가정한다. need에 넣지 마라.
- 3개 중 최소 2개는 가진 재료만으로 완성 가능해야 한다. 나머지 1개는 재료를 1~2개만 더 사면 되는 요리로 한다.
- "{style}"가 '세계요리'면 서로 다른 나라 요리로, '한식'이면 모두 한국 요리로, '아무거나'면 한식 1개 + 다른 나라 요리 2개로 구성한다.
- steps는 5~7단계. 한 단계는 한 문장. 불 세기와 시간을 반드시 넣어라.
- palette는 완성된 요리를 사진으로 찍었을 때의 실제 색 3개를 hex로: [주재료색, 국물이나 소스색, 고명색].
- form은 반드시 이 중 하나: soup, stew, noodle, stirfry, rice, grill, salad, pancake, bread, dumpling

JSON 배열만 출력한다. 코드펜스와 설명은 금지.
[{{"name":"김치볶음밥","cuisine":"한국","summary":"한 줄 설명","minutes":15,"difficulty":"쉬움","servings":2,"form":"rice","palette":["#C8402C","#E8B44C","#4E7A5E"],"have":["김치","밥"],"need":[],"steps":["..."],"tip":"..."}}]"""

SUGGESTED = ["계란", "양파", "김치", "두부", "감자", "대파", "밥", "참치캔", "애호박", "당근", "우유", "닭가슴살"]


# ────────────────────────────── 화면 ──────────────────────────────
st.session_state.setdefault("items", [])
st.session_state.setdefault("recipes", [])


def add_items(raw):
    for part in re.split(r"[,、·\n]", str(raw)):
        part = part.strip()
        if part and part not in st.session_state["items"] and len(st.session_state["items"]) < 24:
            st.session_state["items"].append(part)


st.markdown(
    '<p class="fr-eyebrow">냉장고 파먹기</p>'
    '<h1 class="fr-title">오늘<br>뭐 <em>해먹지</em></h1>'
    '<p class="fr-sub">지금 집에 있는 재료만 적어 주세요. 그 재료로 만들 수 있는 '
    '한식과 세계 요리 세 가지를 그림과 조리 순서로 보여 드립니다.</p>',
    unsafe_allow_html=True)

st.markdown(f'<p class="fr-label">내가 가진 재료 · {len(st.session_state["items"])}개</p>',
            unsafe_allow_html=True)

if st.session_state["items"]:
    cols = st.columns(3)
    for i, it in enumerate(list(st.session_state["items"])):
        with cols[i % 3]:
            if st.button(f"{it}  ✕", key=f"mag{i}"):
                st.session_state["items"].remove(it)
                st.rerun()
else:
    st.markdown('<p class="fr-empty">아직 비어 있어요. 아래에 적거나 사진을 올려 주세요.</p>',
                unsafe_allow_html=True)

c1, c2 = st.columns([3, 1])
typed = c1.text_input("재료", placeholder="예: 두부, 대파, 계란", label_visibility="collapsed")
if c2.button("담기", key="addbtn") and typed:
    add_items(typed)
    st.rerun()

photo = st.file_uploader("냉장고 사진에서 재료 읽기", type=["jpg", "jpeg", "png", "webp"])
if photo is not None and st.button("사진에서 재료 찾기", key="photobtn"):
    with st.spinner("사진 읽는 중…"):
        try:
            b64 = base64.b64encode(photo.getvalue()).decode()
            media = "image/png" if photo.type == "image/png" else "image/jpeg"
            out = ask([
                {"type": "image",
                 "source": {"type": "base64", "media_type": media, "data": b64}},
                {"type": "text",
                 "text": "이 사진에 보이는 식재료 이름만 한국어로 뽑아라. 조미료·그릇·포장지 제외. "
                         'JSON 배열만 출력. 예: ["양파","계란"]'},
            ], max_tokens=500)
            add_items(",".join(parse_json(out)))
            st.rerun()
        except Exception:
            st.warning("사진에서 재료를 못 읽었어요. 직접 적어 주세요.")

rest = [s for s in SUGGESTED if s not in st.session_state["items"]]
if rest:
    st.markdown('<p class="fr-label">자주 쓰는 재료</p>', unsafe_allow_html=True)
    cols = st.columns(4)
    for i, s in enumerate(rest):
        if cols[i % 4].button(f"+ {s}", key=f"qk{i}"):
            st.session_state["items"].append(s)
            st.rerun()

st.markdown('<p class="fr-label">요리 방향</p>', unsafe_allow_html=True)
style = st.radio("요리 방향", ["아무거나", "한식", "세계요리"], horizontal=True,
                 label_visibility="collapsed")

with st.container(key="go"):
    run = st.button("이 재료로 요리 찾기", use_container_width=True,
                    disabled=not st.session_state["items"])

st.markdown('<p class="fr-note">소금·간장·설탕·기름·마늘 같은 기본 조미료는 있다고 보고 찾습니다.</p>',
            unsafe_allow_html=True)

if run:
    with st.spinner("냉장고 뒤지는 중…"):
        try:
            out = ask(RECIPE_PROMPT.format(
                ings=", ".join(st.session_state["items"]), style=style))
            st.session_state["recipes"] = parse_json(out)[:3]
        except Exception:
            st.session_state["recipes"] = []
            st.error("레시피를 불러오지 못했어요. 다시 시도해 주세요.")

if st.session_state["recipes"]:
    rs = st.session_state["recipes"]
    st.markdown(f'<p class="fr-label">만들 수 있는 요리 {len(rs)}</p>', unsafe_allow_html=True)
    components.html(CARD_CSS + "".join(card_html(r) for r in rs),
                    height=sum(card_height(r) for r in rs) + 30, scrolling=False)

