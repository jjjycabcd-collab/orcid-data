import streamlit as st
import streamlit.components.v1 as components
import requests

st.set_page_config(page_title="ORCID 데이터 수집 및 미리보기", page_icon="🔍", layout="wide")

try:
    CLIENT_ID = st.secrets["ORCID_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["ORCID_CLIENT_SECRET"]
except KeyError:
    st.error("API 키가 설정되지 않았습니다. `.streamlit/secrets.toml`을 확인해 주세요.")
    st.stop()

st.title("🔍 ORCID 데이터 수집 및 웹 미리보기")
st.markdown("수집된 원본 메타데이터를 ORCID 공식 홈페이지와 유사한 UI로 렌더링합니다.")

orcid_id = st.text_input("수집할 ORCID iD 입력", "0009-0009-9177-9083")

def parse_orcid_metadata(data):
    # 1. 이름 추출
    name = "Name Not Available"
    try:
        person = data.get("person", {}).get("name", {})
        if person:
            given = person.get("given-names", {}).get("value", "")
            family = person.get("family-name", {}).get("value", "")
            name = f"{given} {family}".strip()
    except Exception: pass

    # 2. Employment (소속/경력) 추출
    employments = []
    try:
        emp_groups = data.get("activities-summary", {}).get("employments", {}).get("affiliation-group", [])
        for group in emp_groups:
            for summary in group.get("summaries", []):
                emp = summary.get("employment-summary", {})
                org = emp.get("organization", {}).get("name", "Unknown Organization")
                
                # 주소 조합
                addr = emp.get("organization", {}).get("address", {})
                city = addr.get("city", "")
                country = addr.get("country", "")
                location = f"{city}, {country}".strip(", ")
                if not location: location = "Location Not Available"
                
                role = emp.get("role-title", "")
                
                # 기간 조합
                start = emp.get("start-date", {}) or {}
                start_y = start.get("year", {}).get("value", "") if start.get("year") else ""
                start_m = start.get("month", {}).get("value", "") if start.get("month") else ""
                start_str = f"{start_y}-{start_m}" if start_m else start_y
                
                end = emp.get("end-date", {})
                end_str = "present"
                if end:
                    end_y = end.get("year", {}).get("value", "") if end.get("year") else ""
                    end_m = end.get("month", {}).get("value", "") if end.get("month") else ""
                    end_str = f"{end_y}-{end_m}" if end_m else end_y
                
                date_str = f"{start_str} to {end_str}".strip(" to ")
                source = emp.get("source", {}).get("source-name", {}).get("value", "")
                
                employments.append({
                    "org": org, "location": location, "role": role, "date": date_str, "source": source
                })
    except Exception: pass

    # 3. Works (연구 성과) 추출
    works = []
    try:
        work_groups = data.get("activities-summary", {}).get("works", {}).get("group", [])
        for group in work_groups:
            for summary in group.get("work-summary", []):
                title = summary.get("title", {}).get("title", {}).get("value", "Untitled")
                journal = summary.get("journal-title", {}).get("value", "") if summary.get("journal-title") else ""
                work_type = summary.get("type", "").replace("-", " ").capitalize()
                
                pub_date = summary.get("publication-date", {}) or {}
                pub_y = pub_date.get("year", {}).get("value", "") if pub_date.get("year") else ""
                
                doi = ""
                for ext_id in summary.get("external-ids", {}).get("external-id", []):
                    if ext_id.get("external-id-type") == "doi":
                        doi = ext_id.get("external-id-value")
                        break
                        
                source = summary.get("source", {}).get("source-name", {}).get("value", "")
                
                works.append({
                    "title": title, "journal": journal, "type": work_type, 
                    "year": pub_y, "doi": doi, "source": source
                })
    except Exception: pass

    return {"name": name, "employments": employments, "works": works}

def render_orcid_html(parsed, orcid_id):
    html_content = f'''
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 1000px; margin: auto; background: #fff; border: 1px solid #ddd; border-radius: 4px;">
        <!-- 상단 헤더 -->
        <div style="background-color: #002b36; color: white; padding: 30px;">
            <h1 style="margin: 0; font-size: 32px; font-weight: 600;">{parsed['name']}</h1>
            <div style="margin-top: 15px; font-size: 16px; display: flex; align-items: center;">
                <div style="background-color: #a6ce39; color: white; border-radius: 50%; width: 24px; height: 24px; display: inline-flex; justify-content: center; align-items: center; font-weight: bold; margin-right: 10px; font-size: 14px;">iD</div>
                <a href="https://orcid.org/{orcid_id}" style="color: white; text-decoration: none;" target="_blank">https://orcid.org/{orcid_id}</a>
            </div>
        </div>
        
        <div style="padding: 30px; display: flex; gap: 40px;">
            <!-- 좌측 사이드바 -->
            <div style="width: 25%;">
                <h3 style="font-size: 16px; border-bottom: 1px solid #ddd; padding-bottom: 10px; margin-top: 0; color: #000;">Personal information</h3>
                <p style="font-size: 14px; color: #333;">No personal information available</p>
            </div>
            
            <!-- 우측 메인 콘텐츠 -->
            <div style="width: 75%;">
                <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 15px;">
                    <h2 style="font-size: 20px; margin: 0; color: #000;">Activities</h2>
                    <a href="#" style="color: #0077cc; text-decoration: none; font-size: 14px;">Expand all</a>
                </div>
                
                <!-- Employment Section -->
                <div style="margin-bottom: 25px;">
                    <div style="background-color: #4a7729; color: white; padding: 12px 15px; font-weight: bold; font-size: 16px; display: flex; justify-content: space-between; align-items: center; border-radius: 3px 3px 0 0;">
                        <span>&#709; Employment ({len(parsed['employments'])})</span>
                        <span style="font-size: 14px; cursor: pointer; font-weight: normal;">&#8645; Sort</span>
                    </div>
    '''
    for emp in parsed['employments']:
        html_content += f'''
                    <div style="border: 1px solid #ccc; border-top: none; padding: 20px; background: #fafafa;">
                        <div style="font-weight: bold; font-size: 16px; color: #000;">{emp['org']}: {emp['location']}</div>
                        <div style="font-size: 14px; color: #222; margin-top: 12px;">
                            {emp['date']} | {emp['role']}<br>
                            Employment
                        </div>
                        <div style="margin-top: 20px; font-size: 13px; color: #555; border-top: 1px solid #eaeaea; padding-top: 12px; display: flex; align-items: center;">
                            <strong>Source:</strong> &nbsp; <span style="display: inline-flex; align-items: center; gap: 5px;"><div style="width: 16px; height: 16px; background-color: #a6ce39; border-radius: 50%; color: white; text-align: center; line-height: 16px; font-size: 10px;">iD</div> {emp['source']}</span>
                        </div>
                    </div>
        '''
        
    html_content += f'''
                </div>
                
                <!-- Works Section -->
                <div style="margin-bottom: 25px;">
                    <div style="background-color: #4a7729; color: white; padding: 12px 15px; font-weight: bold; font-size: 16px; display: flex; justify-content: space-between; align-items: center; border-radius: 3px 3px 0 0;">
                        <span>&#709; Works ({len(parsed['works'])})</span>
                        <span style="font-size: 14px; cursor: pointer; font-weight: normal;">&#8645; Sort</span>
                    </div>
    '''
    for work in parsed['works']:
        html_content += f'''
                    <div style="border: 1px solid #ccc; border-top: none; padding: 20px; background: #fafafa;">
                        <div style="font-weight: bold; font-size: 16px; color: #000;">{work['title']}</div>
                        <div style="font-size: 14px; color: #222; margin-top: 12px; line-height: 1.5;">
                            {work['journal']}<br>
                            {work['year']} | {work['type']}<br>
                            {'<div style="margin-top: 5px;"><strong>DOI:</strong> <a href="https://doi.org/' + work['doi'] + '" style="color: #0077cc; text-decoration: none;" target="_blank">' + work['doi'] + '</a></div>' if work['doi'] else ''}
                        </div>
                        <div style="margin-top: 20px; font-size: 13px; color: #555; border-top: 1px solid #eaeaea; padding-top: 12px; display: flex; align-items: center;">
                            <strong>Source:</strong> &nbsp; <span style="display: inline-flex; align-items: center; gap: 5px;"><div style="width: 16px; height: 16px; background-color: #a6ce39; border-radius: 50%; color: white; text-align: center; line-height: 16px; font-size: 10px;">iD</div> {work['source']}</span>
                        </div>
                    </div>
        '''
        
    html_content += '''
                </div>
            </div>
        </div>
    </div>
    '''
    return html_content

if st.button("데이터 수집 및 미리보기 렌더링"):
    if not orcid_id.strip():
        st.warning("ORCID iD를 정확히 입력해 주세요.")
    else:
        with st.spinner("ORCID API 호출 및 복합 메타데이터 구조 파싱 중..."):
            try:
                auth_resp = requests.post(
                    'https://orcid.org/oauth/token',
                    headers={'Accept': 'application/json'},
                    data={
                        'client_id': CLIENT_ID,
                        'client_secret': CLIENT_SECRET,
                        'grant_type': 'client_credentials',
                        'scope': '/read-public'
                    }
                )
                auth_resp.raise_for_status()
                access_token = auth_resp.json().get('access_token')

                if access_token:
                    headers = {
                        'Accept': 'application/json',
                        'Authorization': f'Bearer {access_token}'
                    }
                    resp = requests.get(f'https://pub.orcid.org/v3.0/{orcid_id}', headers=headers)
                    resp.raise_for_status()
                    data = resp.json()
                    
                    # 깊은 뎁스의 JSON 파싱
                    parsed_data = parse_orcid_metadata(data)
                    preview_html = render_orcid_html(parsed_data, orcid_id)
                    
                    st.success("데이터 수집 및 파싱 완료!")
                    
                    # 1. 렌더링된 미리보기 출력
                    st.subheader("🌐 ORCID 웹 미리보기")
                    components.html(preview_html, height=800, scrolling=True)
                    
                    # 2. 원본 JSON
                    with st.expander("원본 JSON 전체 구조 확인"):
                        st.json(data)
                else:
                    st.error("Access Token 발급 실패")
            except Exception as e:
                st.error(f"오류 발생: {e}")
