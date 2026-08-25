# 오늘 뭐 해먹지

냉장고에 있는 재료를 적거나 사진으로 올리면, 그 재료로 만들 수 있는
한식·세계 요리 3가지를 요리 그림과 조리 순서로 보여 주는 앱.

## 배포 (Streamlit Cloud)

1. 이 폴더를 깃허브 저장소에 올린다.
2. share.streamlit.io → New app → 저장소 / 브랜치 / `app.py` 선택
3. Advanced settings → Secrets 에 아래 한 줄 입력

   ANTHROPIC_API_KEY = "sk-ant-..."

4. Deploy

## 로컬 실행

    pip install -r requirements.txt
    streamlit run app.py

로컬에서는 `.streamlit/secrets.toml` 파일을 만들고 위 키를 넣는다.
이 파일은 절대 깃허브에 올리지 말 것.

## 파일

- `app.py` — 앱 본체
- `requirements.txt` — 패키지 목록
- `.streamlit/config.toml` — 색 테마
- `.gitignore` — secrets.toml 제외

