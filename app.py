import streamlit as st
import streamlit.components.v1 as components
import requests
import datetime

# 페이지 기본 설정
st.set_page_config(page_title="ORCID 데이터 수집 및 미리보기", page_icon="🔍", layout="wide")

# API 키 설정 (보안 적용)
try:
    CLIENT_ID = st.secrets["ORCID_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["ORCID_CLIENT_SECRET"]
except KeyError:
    st.error("API 키가 설정되지 않았습니다. `.streamlit/secrets.toml`을 확인해 주세요.")
    st.stop()

st.title("🔍 ORCID 데이터 수집 및 웹 미리보기")
st.markdown("버튼을 선택하여 원본 JSON 데이터를 수집하거나, 공식 홈페이지 형태의 웹 미리보기를 확인할 수 있습니다.")

# 검색어 입력
orcid_id = st.text_input("수집할 ORCID iD 입력", "0009-0009-9177-9083")

# ==========================================
# 1. 공통 함수: ORCID API 호출
# ==========================================
def fetch_orcid_data(orcid_id):
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

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    resp = requests.get(f'https://pub.orcid.org/v3.0/{orcid_id}', headers=headers)
    resp.raise_for_status()
    return resp.json()

# ==========================================
# 2. 공통 함수: JSON 데이터 파싱
# ==========================================
def format_date(timestamp_ms):
    """ORCID의 ms 단위 타임스탬프를 YYYY-MM-DD 형식으로 변환"""
    if not timestamp_ms: return ""
    try:
        return datetime.datetime.fromtimestamp(int(timestamp_ms) / 1000.0).strftime('%Y-%m-%d')
    except:
        return ""

def parse_orcid_metadata(data):
    # 이름 추출
    name = "Name Not Available"
    try:
        person = data.get("person", {}).get("name", {})
        if person:
            given = person.get("given-names", {}).get("value", "")
            family = person.get("family-name", {}).get("value", "")
            name = f"{given} {family}".strip()
    except Exception: pass

    # 소속/경력 추출 (세부 정보 추가)
    employments = []
    try:
        emp_groups = data.get("activities-summary", {}).get("employments", {}).get("affiliation-group", [])
        for group in emp_groups:
            for summary in group.get("summaries", []):
                emp = summary.get("employment-summary", {})
                org = emp.get("organization", {}).get("name", "Unknown Organization")
                
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

                # 식별자(Identifiers) 추출
                disambig_org = emp.get("organization", {}).get("disambiguated-organization", {})
                org_id_source = disambig_org.get("disambiguation-source", "")
                org_id_value = disambig_org.get("disambiguated-organization-identifier", "")

                # 등록일/수정일 추출
                created_ms = emp.get("created-date", {}).get("value")
                added_date = format_date(created_ms)
                modified_ms = emp.get("last-modified-date", {}).get("value")
                modified_date = format_date(modified_ms)
                
                employments.append({
                    "org": org, "location": location, "role": role, "date": date_str, "source": source,
                    "org_id_source": org_id_source, "org_id_value": org_id_value,
                    "added": added_date, "modified": modified_date
                })
    except Exception: pass

    # 연구 성과 추출 (세부 정보 추가)
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

                # 등록일/수정일 추출
                created_ms = summary.get("created-date", {}).get("value")
                added_date = format_date(created_ms)
                modified_ms = summary.get("last-modified-date", {}).get("value")
                modified_date = format_date(modified_ms)
                
                works.append({
                    "title": title, "journal": journal, "type": work_type, 
                    "year": pub_y, "doi": doi, "source": source,
                    "added": added_date, "modified": modified_date
                })
    except Exception: pass

    return {"name": name, "employments": employments, "works": works}

# ==========================================
# 3. 공통 함수: HTML 렌더링 (자바스크립트 추가)
# ==========================================
def render_orcid_html(parsed, orcid_id):
    # JavaScript 로직 (토글 기능)
    js_script = '''
    <script>
        function toggleSection(contentId, iconId) {
            var content = document.getElementById(contentId);
            var icon = document.getElementById(iconId);
            if (content.style.display === "none") {
                content.style.display = "block";
                icon.innerHTML = "&#709;"; // 아래 화살표
            } else {
                content.style.display = "none";
                icon.innerHTML = "&#707;"; // 오른쪽 화살표
            }
        }

        function toggleAll() {
            var btn = document.getElementById('expand-all-btn');
            var state = btn.innerText === "Collapse all" ? "none" : "block";
            var iconStr = btn.innerText === "Collapse all" ? "&#707;" : "&#709;";
            
            var empContent = document.getElementById('employment-content');
            var empIcon = document.getElementById('employment-icon');
            if(empContent) { empContent.style.display = state; empIcon.innerHTML = iconStr; }
            
            var workContent = document.getElementById('works-content');
            var workIcon = document.getElementById('works-icon');
            if(workContent) { workContent.style.display = state; workIcon.innerHTML = iconStr; }
            
            btn.innerText = state === "none" ? "Expand all" : "Collapse all";
        }
    </script>
    '''

    html_content = f'''
    {js_script}
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
                    <a href="#" id="expand-all-btn" onclick="toggleAll(); return false;" style="color: #0077cc; text-decoration: none; font-size: 14px;">Collapse all</a>
                </div>
                
                <!-- Employment Section -->
                <div style="margin-bottom: 25px;">
                    <div onclick="toggleSection('employment-content', 'employment-icon')" style="cursor: pointer; background-color: #4a7729; color: white; padding: 12px 15px; font-weight: bold; font-size: 16px; display: flex; justify-content: space-between; align-items: center; border-radius: 3px 3px 0 0;">
                        <span><span id="employment-icon">&#709;</span> Employment ({len(parsed['employments'])})</span>
                        <span style="font-size: 14px; font-weight: normal;">&#8645; Sort</span>
                    </div>
                    <div id="employment-content" style="display: block;">
    '''
    for emp in parsed['employments']:
        # 기관 식별자 HTML 생성
        id_html = ""
        if emp.get('org_id_source') and emp.get('org_id_value'):
            val = emp['org_id_value']
            val_html = f'<a href="{val}" style="color: #0077cc; text-decoration: none;" target="_blank">{val}</a>' if val.startswith('http') else val
            id_html = f'''
                <div style="margin-bottom: 15px;">
                    <strong>Organization identifiers</strong><br>
                    {emp['org_id_source']}: {val_html}<br>
                    {emp['org']}
                </div>
            '''
        
        # 날짜 정보 HTML 생성
        dates_html = ""
        if emp.get('added'):
            dates_html += f'<div style="margin-bottom: 15px;"><strong>Added</strong><br>{emp["added"]}</div>'
        if emp.get('modified'):
            dates_html += f'<div style="margin-bottom: 15px;"><strong>Last modified</strong><br>{emp["modified"]}</div>'

        # 세부 정보 합치기
        details_html = ""
        if id_html or dates_html:
            details_html = f'''
                <div style="margin-top: 15px; border-top: 1px solid #ccc; padding-top: 15px; font-size: 14px; color: #222;">
                    {id_html}
                    {dates_html}
                </div>
            '''

        html_content += f'''
                        <div style="border: 1px solid #ccc; border-top: none; padding: 20px; background: #fafafa;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <div>
                                    <div style="font-weight: bold; font-size: 16px; color: #000;">{emp['org']}: {emp['location']}</div>
                                    <div style="font-size: 14px; color: #222; margin-top: 8px;">
                                        {emp['date']} | {emp['role']}<br>
                                        Employment
                                    </div>
                                </div>
                                <a href="#" style="color: #0077cc; text-decoration: none; font-size: 14px;">Show less detail</a>
                            </div>
                            {details_html}
                            <div style="margin-top: 15px; font-size: 13px; color: #555; border-top: 1px solid #ccc; padding-top: 12px; display: flex; align-items: center;">
                                <strong>Source:</strong> &nbsp; <span style="display: inline-flex; align-items: center; gap: 5px;"><div style="width: 16px; height: 16px; background-color: #a6ce39; border-radius: 50%; color: white; text-align: center; line-height: 16px; font-size: 10px;">iD</div> {emp['source']}</span>
                            </div>
                        </div>
        '''
        
    html_content += f'''
                    </div>
                </div>
                
                <!-- Works Section -->
                <div style="margin-bottom: 25px;">
                    <div onclick="toggleSection('works-content', 'works-icon')" style="cursor: pointer; background-color: #4a7729; color: white; padding: 12px 15px; font-weight: bold; font-size: 16px; display: flex; justify-content: space-between; align-items: center; border-radius: 3px 3px 0 0;">
                        <span><span id="works-icon">&#709;</span> Works ({len(parsed['works'])})</span>
                        <span style="font-size: 14px; font-weight: normal;">&#8645; Sort</span>
                    </div>
                    <div id="works-content" style="display: block;">
    '''
    for work in parsed['works']:
        # 연구 성과 날짜 정보 HTML 생성
        work_dates_html = ""
        if work.get('added'):
            work_dates_html += f'<div style="margin-bottom: 15px;"><strong>Added</strong><br>{work["added"]}</div>'
        if work.get('modified'):
            work_dates_html += f'<div style="margin-bottom: 15px;"><strong>Last modified</strong><br>{work["modified"]}</div>'

        work_details_html = ""
        if work_dates_html:
            work_details_html = f'''
                <div style="margin-top: 15px; border-top: 1px solid #ccc; padding-top: 15px; font-size: 14px; color: #222;">
                    {work_dates_html}
                </div>
            '''

        html_content += f'''
                        <div style="border: 1px solid #ccc; border-top: none; padding: 20px; background: #fafafa;">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                                <div>
                                    <div style="font-weight: bold; font-size: 16px; color: #000;">{work['title']}</div>
                                    <div style="font-size: 14px; color: #222; margin-top: 8px; line-height: 1.5;">
                                        {work['journal']}<br>
                                        {work['year']} | {work['type']}<br>
                                        {'<div style="margin-top: 5px;"><strong>DOI:</strong> <a href="https://doi.org/' + work['doi'] + '" style="color: #0077cc; text-decoration: none;" target="_blank">' + work['doi'] + '</a></div>' if work['doi'] else ''}
                                    </div>
                                </div>
                                <a href="#" style="color: #0077cc; text-decoration: none; font-size: 14px;">Show less detail</a>
                            </div>
                            {work_details_html}
                            <div style="margin-top: 15px; font-size: 13px; color: #555; border-top: 1px solid #ccc; padding-top: 12px; display: flex; align-items: center;">
                                <strong>Source:</strong> &nbsp; <span style="display: inline-flex; align-items: center; gap: 5px;"><div style="width: 16px; height: 16px; background-color: #a6ce39; border-radius: 50%; color: white; text-align: center; line-height: 16px; font-size: 10px;">iD</div> {work['source']}</span>
                            </div>
                        </div>
        '''
        
    html_content += '''
                    </div>
                </div>
            </div>
        </div>
    </div>
    '''
    return html_content


# ==========================================
# 4. 화면 UI (버튼 2개 분리)
# ==========================================
col1, col2 = st.columns(2)

with col1:
    btn_json = st.button("수집 JSON", use_container_width=True)

with col2:
    btn_preview = st.button("웹 미리보기", use_container_width=True)

st.divider()

# JSON 버튼 클릭 시 동작
if btn_json:
    if not orcid_id.strip():
        st.warning("ORCID iD를 정확히 입력해 주세요.")
    else:
        with st.spinner("JSON 데이터 수집 중..."):
            try:
                data = fetch_orcid_data(orcid_id)
                st.success("데이터 수집 완료!")
                st.subheader("원본 JSON 데이터")
                st.json(data)
            except Exception as e:
                st.error(f"데이터 수집 중 오류가 발생했습니다: {e}")

# 웹 미리보기 버튼 클릭 시 동작
if btn_preview:
    if not orcid_id.strip():
        st.warning("ORCID iD를 정확히 입력해 주세요.")
    else:
        with st.spinner("웹 미리보기 렌더링 중..."):
            try:
                data = fetch_orcid_data(orcid_id)
                parsed_data = parse_orcid_metadata(data)
                preview_html = render_orcid_html(parsed_data, orcid_id)
                st.success("렌더링 완료!")
                st.subheader("🌐 ORCID 웹 미리보기")
                components.html(preview_html, height=1000, scrolling=True)
            except Exception as e:
                st.error(f"미리보기 생성 중 오류가 발생했습니다: {e}")
