"""
오늘 뭐 해먹지 — 냉장고 재료 레시피 (오프라인 버전)

API 키가 필요 없습니다. recipes.json 안의 요리 데이터에서
가진 재료와 가장 잘 맞는 요리를 골라 보여 줍니다.

실행: streamlit run app.py
"""

import html as html_lib
import json
import random
import re
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="오늘 뭐 해먹지", page_icon="🍳", layout="centered")

INK, TILE, LINE, PAPER = "#16241F", "#DCE7E2", "#B4C7BF", "#FBF7EF"
TOMATO, BUTTER, HERB = "#D4402C", "#F0BA3F", "#4E7A5E"

# 집에 늘 있다고 보는 기본 조미료
PANTRY = {"소금", "후추", "설탕", "간장", "식용유", "올리브유", "참기름",
          "마늘", "고춧가루", "식초", "물"}

# 다르게 부르는 재료 이름을 하나로 모아 준다
SYNONYM = {
    "달걀": "계란", "계란후라이": "계란",
    "파": "대파", "쪽파": "대파", "실파": "대파",
    "돼지": "돼지고기", "삼겹살": "돼지고기", "목살": "돼지고기", "앞다리살": "돼지고기",
    "쇠고기": "소고기", "우삼겹": "소고기", "차돌박이": "소고기",
    "닭": "닭고기", "닭가슴살": "닭고기", "닭다리살": "닭고기", "닭안심": "닭고기",
    "다진 고기": "다진고기", "간고기": "다진고기",
    "파스타": "스파게티", "파스타면": "스파게티", "스파게티면": "스파게티",
    "라면": "면", "중화면": "면", "라멘": "면",
    "국수": "소면", "소면국수": "소면",
    "모짜렐라": "치즈", "모차렐라": "치즈", "슬라이스치즈": "치즈",
    "체다치즈": "치즈", "파마산": "치즈", "파르메산": "치즈",
    "방울토마토": "토마토", "토마토소스": "토마토", "홀토마토": "토마토",
    "느타리버섯": "버섯", "새송이버섯": "버섯", "표고버섯": "버섯",
    "팽이버섯": "버섯", "양송이": "버섯", "느타리": "버섯", "새송이": "버섯",
    "쌀밥": "밥", "찬밥": "밥", "즉석밥": "밥",
    "김가루": "김", "조미김": "김",
    "냉동새우": "새우", "칵테일새우": "새우",
    "무우": "무", "적양파": "양파",
    "호박": "애호박", "단호박": "애호박",
    "카레": "카레가루", "카레분말": "카레가루",
    "생크림": "생크림", "휘핑크림": "생크림",
    "떡볶이떡": "떡", "가래떡": "떡",
    "부침가루": "밀가루", "튀김가루": "밀가루",
    "로메인": "상추", "양상추": "상추",
    "토르티야": "또띠아", "뚜르띠아": "또띠아",
    "우동": "우동면",
}

CATEGORIES = {
    "채소": ["양파", "감자", "당근", "애호박", "양배추", "대파", "토마토", "오이",
           "가지", "버섯", "상추", "콩나물", "숙주", "피망", "시금치", "무"],
    "단백질": ["계란", "두부", "돼지고기", "소고기", "닭고기", "다진고기", "새우",
            "참치캔", "베이컨", "햄", "어묵", "렌틸콩"],
    "밥·면·빵": ["밥", "쌀", "소면", "스파게티", "쌀국수", "우동면", "면", "떡",
              "식빵", "또띠아", "바게트", "밀가루"],
    "양념·기타": ["김치", "치즈", "우유", "버터", "마요네즈", "김", "된장", "고추장",
              "카레가루", "미역", "레몬", "바질", "고수", "생강", "청양고추"],
}


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
  border-radius:20px; font-weight:400; font-size:13px; padding:6px 8px; box-shadow:none; }}
[class*="st-key-qk"] .stButton > button:hover {{ border-color:{HERB}; color:{HERB}; background:transparent; }}

[class*="st-key-go"] .stButton > button {{
  background:{TOMATO}; color:#FFF6EC; border:1.5px solid {INK}; border-radius:4px;
  font-family:'Black Han Sans',sans-serif; font-size:19px; letter-spacing:.02em;
  padding:16px; box-shadow:0 4px 0 {INK}; }}
[class*="st-key-go"] .stButton > button:hover {{ background:#B93522; color:#FFF6EC;
  transform:translateY(2px); box-shadow:0 2px 0 {INK}; }}
[class*="st-key-go"] .stButton > button:disabled {{ opacity:.42; box-shadow:0 4px 0 {LINE}; }}

[data-testid="stRadio"] label {{ font-size:14px; color:#3D544B; }}
[data-testid="stExpander"] {{ border:1.5px solid {LINE}; border-radius:4px; background:{PAPER}; }}
[data-testid="stExpander"] summary {{ font-size:14px; font-weight:600; }}
</style>
""", unsafe_allow_html=True)


# ────────────────────────────── 데이터 ──────────────────────────────
@st.cache_data
def load_recipes():
    path = Path(__file__).parent / "recipes.json"
    return json.loads(path.read_text(encoding="utf-8"))


RECIPES = load_recipes()


def canon(word):
    w = re.sub(r"\s+", "", str(word)).strip()
    return SYNONYM.get(w, w)


def match_recipes(user_items, style):
    """가진 재료와 요리를 맞춰 점수순으로 돌려준다"""
    have = {canon(i) for i in user_items} | PANTRY
    scored = []
    for r in RECIPES:
        if style == "한식" and r["cuisine"] != "한국":
            continue
        if style == "세계요리" and r["cuisine"] == "한국":
            continue

        core = [canon(c) for c in r["core"]]
        opt = [canon(o) for o in r.get("optional", [])]
        core_hit = [c for c in core if c in have]
        missing = [c for c in core if c not in have]
        opt_hit = [o for o in opt if o in have]

        if not core_hit:
            continue

        score = (len(core_hit) / len(core)) * 100 + len(opt_hit) * 9 - len(missing) * 34
        shown_have = [c for c in core_hit if c not in PANTRY] + opt_hit
        scored.append((score, r, shown_have, missing))

    scored.sort(key=lambda x: -x[0])
    return scored


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
    else:
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


def card_html(r, have, missing):
    steps = "".join(f"<li>{esc(s)}</li>" for s in r["steps"])
    have_html = "".join(f'<span class="fr-have">{esc(h)}</span>' for h in have)
    need_html = "".join(f'<span class="fr-need">{esc(n)}</span>' for n in missing)
    need_row = f'<div><b>사야 할 것</b>{need_html}</div>' if missing else ""
    tip = f'<div class="fr-tip"><b>맛내기</b>{esc(r.get("tip"))}</div>' if r.get("tip") else ""
    return f"""
<article class="fr-card">
  <div class="fr-artbox">
    <span class="fr-flag">{esc(r['cuisine'])}</span>
    {dish_svg(r['name'], r['form'], r['palette'])}
  </div>
  <div class="fr-body">
    <h3 class="fr-name">{esc(r['name'])}</h3>
    <p class="fr-summary">{esc(r.get('summary'))}</p>
    <div class="fr-meta">
      <span>{esc(r['minutes'])}분</span>
      <span>{esc(r['difficulty'])}</span>
      <span>{esc(r['servings'])}인분</span>
    </div>
    <div class="fr-tags">
      <div><b>있는 재료</b>{have_html}</div>
      {need_row}
    </div>
    <ol class="fr-steps">{steps}</ol>
    {tip}
  </div>
</article>"""


def card_height(r, missing):
    h = 200 + 46 + 46 + 56 + 46 + 54 * len(r["steps"]) + 36
    if missing:
        h += 32
    if r.get("tip"):
        h += 100
    return h


# ────────────────────────────── 화면 ──────────────────────────────
st.session_state.setdefault("items", [])
st.session_state.setdefault("results", None)
st.session_state.setdefault("page", 0)


def add_items(raw):
    for part in re.split(r"[,、·\n]", str(raw)):
        part = part.strip()
        if part and part not in st.session_state["items"] and len(st.session_state["items"]) < 24:
            st.session_state["items"].append(part)


st.markdown(
    '<p class="fr-eyebrow">냉장고 파먹기</p>'
    '<h1 class="fr-title">오늘<br>뭐 <em>해먹지</em></h1>'
    f'<p class="fr-sub">지금 집에 있는 재료만 골라 주세요. 한국·일본·중국·이탈리아 등 '
    f'{len(RECIPES)}가지 요리 중에서 지금 만들 수 있는 것을 찾아 드립니다.</p>',
    unsafe_allow_html=True)

st.markdown(f'<p class="fr-label">내가 가진 재료 · {len(st.session_state["items"])}개</p>',
            unsafe_allow_html=True)

if st.session_state["items"]:
    cols = st.columns(3)
    for i, it in enumerate(list(st.session_state["items"])):
        with cols[i % 3]:
            if st.button(f"{it}  ✕", key=f"mag{i}"):
                st.session_state["items"].remove(it)
                st.session_state["results"] = None
                st.rerun()
else:
    st.markdown('<p class="fr-empty">아직 비어 있어요. 아래에서 골라 주세요.</p>',
                unsafe_allow_html=True)

c1, c2 = st.columns([3, 1])
typed = c1.text_input("재료", placeholder="예: 두부, 대파, 계란", label_visibility="collapsed")
if c2.button("담기", key="addbtn") and typed:
    add_items(typed)
    st.session_state["results"] = None
    st.rerun()

st.markdown('<p class="fr-label">재료 고르기</p>', unsafe_allow_html=True)
n = 0
for cat, names in CATEGORIES.items():
    rest = [x for x in names if x not in st.session_state["items"]]
    if not rest:
        continue
    with st.expander(cat, expanded=(cat == "채소")):
        cols = st.columns(3)
        for x in rest:
            n += 1
            if cols[n % 3].button(f"+ {x}", key=f"qk{n}"):
                st.session_state["items"].append(x)
                st.session_state["results"] = None
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
    st.session_state["results"] = match_recipes(st.session_state["items"], style)
    st.session_state["page"] = 0

results = st.session_state["results"]
if results is not None:
    if not results:
        st.warning("이 재료로 만들 수 있는 요리를 못 찾았어요. 재료를 몇 개 더 담아 보세요.")
    else:
        page = st.session_state["page"]
        batch = results[page * 3:page * 3 + 3]
        if not batch:
            st.session_state["page"] = 0
            batch = results[:3]

        st.markdown(f'<p class="fr-label">만들 수 있는 요리 {len(batch)}</p>',
                    unsafe_allow_html=True)
        body = "".join(card_html(r, have, miss) for _, r, have, miss in batch)
        total = sum(card_height(r, miss) for _, r, _, miss in batch) + 30
        components.html(CARD_CSS + body, height=total, scrolling=False)

        if len(results) > (page + 1) * 3:
            if st.button("다른 요리 더 보기", key="more"):
                st.session_state["page"] += 1
                st.rerun()
