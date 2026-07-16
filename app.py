import streamlit as st
import requests

# 페이지 기본 설정
st.set_page_config(page_title="ORCID 데이터 수집기", page_icon="🔍", layout="wide")

st.title("🔍 ORCID Public API 기반 데이터 수집")
st.markdown("Streamlit Cloud의 `Secrets` 기능을 활용하여 안전하게 데이터를 조회합니다.")

# 1. API 키 설정 (보안 적용)
# 로컬: .streamlit/secrets.toml 에서 로드
# 클라우드: Streamlit Cloud Settings -> Secrets 에서 로드
try:
    CLIENT_ID = st.secrets["ORCID_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["ORCID_CLIENT_SECRET"]
except KeyError:
    st.error("API 키가 설정되지 않았습니다. `.streamlit/secrets.toml` 또는 클라우드 Secrets 설정을 확인해 주세요.")
    st.stop() # 키가 없으면 앱 실행 중지

# 2. UI 구성
orcid_id = st.text_input("수집할 ORCID iD 입력 (형식: xxxx-xxxx-xxxx-xxxx)", "0009-0009-9177-9083")

if st.button("데이터 수집 시작"):
    if not orcid_id.strip():
        st.warning("ORCID iD를 정확히 입력해 주세요.")
    else:
        with st.spinner("ORCID 서버와 통신 중입니다..."):
            try:
                # 3. Access Token 발급 (Client Credentials 방식)
                auth_response = requests.post(
                    'https://orcid.org/oauth/token',
                    headers={'Accept': 'application/json'},
                    data={
                        'client_id': CLIENT_ID,
                        'client_secret': CLIENT_SECRET,
                        'grant_type': 'client_credentials',
                        'scope': '/read-public'
                    }
                )
                auth_response.raise_for_status() # HTTP 4xx, 5xx 에러 발생 시 예외 처리
                access_token = auth_response.json().get('access_token')

                if access_token:
                    # 4. 특정 ORCID iD의 전체 레코드 조회
                    headers = {
                        'Accept': 'application/json',
                        'Authorization': f'Bearer {access_token}'
                    }
                    
                    # API v3.0 Endpoint 호출
                    api_url = f'https://pub.orcid.org/v3.0/{orcid_id}'
                    response = requests.get(api_url, headers=headers)
                    response.raise_for_status()
                    
                    data = response.json()

                    st.success("데이터 수집이 완료되었습니다!")
                    
                    # 5. 수집된 JSON 데이터 출력
                    st.subheader("수집된 원본 메타데이터")
                    st.json(data)
                else:
                    st.error("Access Token 발급에 실패했습니다.")
                    
            except requests.exceptions.HTTPError as http_err:
                st.error(f"서버 통신 오류가 발생했습니다: {http_err}")
            except Exception as err:
                st.error(f"예기치 못한 오류가 발생했습니다: {err}")
