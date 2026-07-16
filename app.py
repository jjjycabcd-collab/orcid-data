import streamlit as st
import requests

# 페이지 기본 설정
st.set_page_config(page_title="ORCID 정보 조회", page_icon="🔍")

st.title("🔍 ORCID 정보 조회 웹 서비스")
st.write("ORCID iD를 입력하여 연구자의 공개(Public) 데이터를 조회합니다.")

# TODO: 실제 배포 시에는 st.secrets를 사용하여 보안을 강화해야 합니다.
# 예: CLIENT_ID = st.secrets["ORCID_CLIENT_ID"]
CLIENT_ID = 'APP-AYX8Q4H9SQSH9EGG'
CLIENT_SECRET = '05af1a5d-0c23-459c-9ddb-12802ba0634b' # 반드시 재발급 받은 키로 변경하세요!

# 사용자로부터 ORCID iD 입력받기
orcid_id = st.text_input("ORCID iD 입력 (예: 0009-0009-9177-9083)", "0009-0009-9177-9083")

# 조회 버튼 생성
if st.button("데이터 조회하기"):
    if not orcid_id.strip():
        st.warning("ORCID iD를 입력해 주세요.")
    else:
        with st.spinner('ORCID 서버에서 데이터를 불러오는 중입니다...'):
            try:
                # 1. Access Token 발급 (Client Credentials)
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
                auth_response.raise_for_status() # HTTP 오류 발생 시 예외 처리
                access_token = auth_response.json().get('access_token')

                if access_token:
                    # 2. 특정 ORCID iD 데이터 조회
                    headers = {
                        'Accept': 'application/json',
                        'Authorization': f'Bearer {access_token}'
                    }
                    response = requests.get(f'https://pub.orcid.org/v3.0/{orcid_id}', headers=headers)
                    response.raise_for_status()
                    data = response.json()

                    st.success("데이터 조회가 완료되었습니다!")
                    
                    # 3. 수집된 데이터를 예쁘게 출력
                    st.subheader("전체 데이터 (JSON)")
                    st.json(data)
                else:
                    st.error("Access Token 발급에 실패했습니다. API 키를 확인해 주세요.")
                    
            except requests.exceptions.RequestException as e:
                st.error(f"API 요청 중 오류가 발생했습니다: {e}")
