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

# 검색어 입력 (새로운 테스트 ORCID iD를 기본값으로 설정)
orcid_id = st.text_input("수집할 ORCID iD 입력", "0000-0001-8783-5884")

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
# 2. 공통 함수: JSON 데이터 파싱 모듈화
# ==========================================
def format_date(timestamp_ms):
    """ORCID의 ms 단위 타임스탬프를 YYYY-MM-DD 형식으로 변환"""
    if not timestamp_ms: return ""
    try:
        return datetime.datetime.fromtimestamp(int(timestamp_ms) / 1000.0).strftime('%Y-%m-%d')
    except:
        return ""

def extract_affiliations(data, activity_type, summary_key):
    """Employment, Education, Qualification 등 동일한 구조의 소속 데이터를 안전하게 추출"""
    results = []
    try:
        # JSON 값이 null(None)일 경우를 완벽하게 대비하기 위해 or {} 연산자 사용
        acts = data.get("activities-summary") or {}
        section = acts.get(activity_type) or {}
        groups = section.get("affiliation-group") or []
        
        for group in groups:
            summaries = group.get("summaries") or []
            for summary in summaries:
                item = summary.get(summary_key) or {}
                
                org = item.get("organization") or {}
                org_name = org.get("name") or "Unknown Organization"
                
                addr = org.get("address") or {}
                city = addr.get("city") or ""
                country = addr.get("country") or ""
                location = f"{city}, {country}".strip(", ")
                if not location: location = "Location Not Available"
                
                role = item.get("role-title") or ""
                dept = item.get("department-name") or ""
                
                # 학력의 경우 부서(전공)명을 괄호로 묶어서 역할 뒤에 표기
                if role and dept:
                    role_display = f"{role} ({dept})"
                elif dept:
                    role_display = dept
                else:
                    role_display = role
                
                start = item.get("start-date") or {}
                start_y = (start.get("year") or {}).get("value") or ""
                start_m = (start.get("month") or {}).get("value") or ""
                start_str = f"{start_y}-{start_m}" if start_m else start_y
                
                end = item.get("end-date") or {}
                end_str = "present"
                if end:
                    end_y = (end.get("year") or {}).get("value") or ""
                    end_m = (end.get("month") or {}).get("value") or ""
                    end_str = f"{end_y}-{end_m}" if end_m else end_y
                
                date_str = f"{start_str} to {end_str}".strip(" to ")
                
                source = (item.get("source") or {}).get("source-name", {}).get("value") or ""
                
                disambig_org = org.get("disambiguated-organization") or {}
                org_id_source = disambig_org.get("disambiguation-source") or ""
                org_id_value = disambig_org.get("disambiguated-organization-identifier") or ""
                
                added_date = format_date((item.get("created-date") or {}).get("value"))
                modified_date = format_date((item.get("last-modified-date") or {}).get("value"))
                
                type_label = summary_key.split('-')[0].capitalize() # Employment, Education 등
                
                results.append({
                    "org": org_name, "location": location, "role": role_display, "date": date_str, 
                    "source": source, "org_id_source": org_id_source, "org_id_value": org_id_value,
                    "added": added_date, "modified": modified_date, "type": type_label
                })
    except Exception as e:
        print(f"Error parsing {activity_type}: {e}")
    return results

def extract_works(data):
    """연구 성과(Works) 데이터를 안전하게 추출"""
    works = []
    try:
        acts = data.get("activities-summary") or {}
        section = acts.get("works") or {}
        groups = section.get("group") or []
        
        for group in groups:
            summaries = group.get("work-summary") or []
            for summary in summaries:
                title_obj = summary.get("title") or {}
                title = (title_obj.get("title") or {}).get("value") or "Untitled"
                
                journal_obj = summary.get("journal-title") or {}
                journal = journal_obj.get("value") or ""
                
                work_type = (summary.get("type") or "").replace("-", " ").capitalize()
                
                pub_date = summary.get("publication-date") or {}
                pub_y = (pub_date.get("year") or {}).get("value") or ""
                
                doi = ""
                ext_ids = (summary.get("external-ids") or {}).get("external-id") or []
                for ext_id in ext_ids:
                    if ext_id.get("external-id-type") == "doi":
                        doi = ext_id.get("external-id-value") or ""
                        break
                        
                source = (summary.get("source") or {}).get("source-name", {}).get("value") or ""
                
                added_date = format_date((summary.get("created-date") or {}).get("value"))
                modified_date = format_date((summary.get("last-modified-date") or {}).get("value"))
                
                works.append({
                    "title": title, "journal": journal, "type": work_type, 
                    "year": pub_y, "doi": doi, "source": source,
                    "added": added_date, "modified": modified_date
                })
    except Exception as e:
        print(f"Error parsing works: {e}")
    return works

def parse_orcid_metadata(data):
    # 1. 이름 추출
    name = "Name Not Available"
    try:
        person = data.get("person") or {}
        name_obj = person.get("name") or {}
        if name_obj:
            given = (name_obj.get("given-names") or {}).get("value") or ""
            family = (name_obj.get("family-name") or {}).get("value") or ""
            name = f"{given} {family}".strip()
    except Exception: pass

    # 2. Employment 추출
    employments = extract_affiliations(data, 'employments', 'employment-summary')
    
    # 3. Education & Qualifications 추출 후 통합
    educations = extract_affiliations(data, 'educations', 'education-summary')
    qualifications = extract_affiliations(data, 'qualifications', 'qualification-summary')
    edu_quals = educations + qualifications
    
    # 4. Works 추출
    works = extract_works(data)

    return {
        "name": name, 
        "employments": employments, 
        "edu_quals": edu_quals, 
        "works": works
    }

# ==========================================
# 3. 공통 함수: HTML 동적 렌더링
# ==========================================
def render_section_html(title, items, content_id, icon_id):
    """각 항목(Employment, Education, Works)의 HTML 섹션을 동적으로 생성"""
    if not items: return ""
    
    html = f'''
        <div style="margin-bottom: 25px;">
            <div onclick="toggleSection('{content_id}', '{icon_id}')" style="cursor: pointer; background-color: #4a7729; color: white; padding: 12px 15px; font-weight: bold; font-size: 16px; display: flex; justify-content: space-between; align-items: center; border-radius: 3px 3px 0 0;">
                <span><span id="{icon_id}">&#709;</span> {title} ({len(items)})</span>
                <span style="font-size: 14px; font-weight: normal;">&#8645; Sort</span>
            </div>
            <div id="{content_id}" style="display: block;">
    '''
    
    for item in items:
        # Affiliation (소속/학력 등)인 경우
        if 'org' in item: 
            id_html = ""
            if item.get('org_id_source') and item.get('org_id_value'):
                val = item['org_id_value']
                val_html = f'<a href="{val}" style="color: #0077cc; text-decoration: none;" target="_blank">{val}</a>' if val.startswith('http') else val
                id_html = f'''
                    <div style="margin-bottom: 15px;">
                        <strong>Organization identifiers</strong><br>
                        {item['org_id_source']}: {val_html}<br>
                        {item['org']}
                    </div>
                '''
            
            dates_html = ""
            if item.get('added'):
                dates_html += f'<div style="margin-bottom: 15px;"><strong>Added</strong><br>{item["added"]}</div>'
            if item.get('modified'):
                dates_html += f'<div style="margin-bottom: 15px;"><strong>Last modified</strong><br>{item["modified"]}</div>'

            details_html = ""
            if id_html or dates_html:
                details_html = f'''
                    <div style="margin-top: 15px; border-top: 1px solid #ccc; padding-top: 15px; font-size: 14px; color: #222;">
                        {id_html}
                        {dates_html}
                    </div>
                '''

            html += f'''
                <div style="border: 1px solid #ccc; border-top: none; padding: 20px; background: #fafafa;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div style="font-weight: bold; font-size: 16px; color: #000;">{item['org']}: {item['location']}</div>
                            <div style="font-size: 14px; color: #222; margin-top: 8px;">
                                {item['date']} | {item['role']}<br>
                                {item['type']}
                            </div>
                        </div>
                        <a href="#" style="color: #0077cc; text-decoration: none; font-size: 14px;">Show less detail</a>
                    </div>
                    {details_html}
                    <div style="margin-top: 15px; font-size: 13px; color: #555; border-top: 1px solid #ccc; padding-top: 12px; display: flex; align-items: center;">
                        <strong>Source:</strong> &nbsp; <span style="display: inline-flex; align-items: center; gap: 5px;"><div style="width: 16px; height: 16px; background-color: #a6ce39; border-radius: 50%; color: white; text-align: center; line-height: 16px; font-size: 10px;">iD</div> {item['source']}</span>
                    </div>
                </div>
            '''
        # Works (논문/성과)인 경우
        else: 
            work_dates_html = ""
            if item.get('added'):
                work_dates_html += f'<div style="margin-bottom: 15px;"><strong>Added</strong><br>{item["added"]}</div>'
            if item.get('modified'):
                work_dates_html += f'<div style="margin-bottom: 15px;"><strong>Last modified</strong><br>{item["modified"]}</div>'

            work_details_html = ""
            if work_dates_html:
                work_details_html = f'''
                    <div style="margin-top: 15px; border-top: 1px solid #ccc; padding-top: 15px; font-size: 14px; color: #222;">
                        {work_dates_html}
                    </div>
                '''
            
            doi_html = f'<div style="margin-top: 5px;"><strong>DOI:</strong> <a href="https://doi.org/{item["doi"]}" style="color: #0077cc; text-decoration: none;" target="_blank">{item["doi"]}</a></div>' if item.get('doi') else ''

            html += f'''
                <div style="border: 1px solid #ccc; border-top: none; padding: 20px; background: #fafafa;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <div>
                            <div style="font-weight: bold; font-size: 16px; color: #000;">{item['title']}</div>
                            <div style="font-size: 14px; color: #222; margin-top: 8px; line-height: 1.5;">
                                {item['journal']}<br>
                                {item['year']} | {item['type']}<br>
                                {doi_html}
                            </div>
                        </div>
                        <a href="#" style="color: #0077cc; text-decoration: none; font-size: 14px;">Show less detail</a>
                    </div>
                    {work_details_html}
                    <div style="margin-top: 15px; font-size: 13px; color: #555; border-top: 1px solid #ccc; padding-top: 12px; display: flex; align-items: center;">
                        <strong>Source:</strong> &nbsp; <span style="display: inline-flex; align-items: center; gap: 5px;"><div style="width: 16px; height: 16px; background-color: #a6ce39; border-radius: 50%; color: white; text-align: center; line-height: 16px; font-size: 10px;">iD</div> {item['source']}</span>
                    </div>
                </div>
            '''
            
    html += '''
            </div>
        </div>
    '''
    return html

def render_orcid_html(parsed, orcid_id):
    # JavaScript 로직 (다중 섹션 토글 처리 지원)
    js_script = '''
    <script>
        function toggleSection(contentId, iconId) {
            var content = document.getElementById(contentId);
            var icon = document.getElementById(iconId);
            if (content.style.display === "none") {
                content.style.display = "block";
                icon.innerHTML = "&#709;";
            } else {
                content.style.display = "none";
                icon.innerHTML = "&#707;";
            }
        }

        function toggleAll() {
            var btn = document.getElementById('expand-all-btn');
            var state = btn.innerText === "Collapse all" ? "none" : "block";
            var iconStr = btn.innerText === "Collapse all" ? "&#707;" : "&#709;";
            
            var sections = ['employment', 'edu-qual', 'works'];
            sections.forEach(function(sec) {
                var content = document.getElementById(sec + '-content');
                var icon = document.getElementById(sec + '-icon');
                if(content) { content.style.display = state; }
                if(icon) { icon.innerHTML = iconStr; }
            });
            
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
    '''
    
    # 각 섹션을 동적으로 합산
    html_content += render_section_html("Employment", parsed['employments'], 'employment-content', 'employment-icon')
    html_content += render_section_html("Education and qualifications", parsed['edu_quals'], 'edu-qual-content', 'edu-qual-icon')
    html_content += render_section_html("Works", parsed['works'], 'works-content', 'works-icon')

    html_content += '''
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
                components.html(preview_html, height=1200, scrolling=True)
            except Exception as e:
                st.error(f"미리보기 생성 중 오류가 발생했습니다: {e}")
