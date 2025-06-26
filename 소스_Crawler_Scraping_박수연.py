# 라이브러리 임포트

import requests  # HTTP 요청을 보내고 응답을 받을 수 있도록 하는 라이브러리
from bs4 import BeautifulSoup  # HTML/XML 문서 파싱을 위한 BeautifulSoup 라이브러리
import pandas as pd  # 데이터 조작 및 분석을 위한 pandas 라이브러리
import time  # 시간 관련 함수(예: sleep) 사용을 위한 모듈
import re  # 정규 표현식(Regex) 작업을 위한 모듈
from datetime import datetime, timedelta  # 날짜 및 시간 조작을 위한 datetime 모듈과 시간 차를 나타내는 timedelta 클래스

from selenium import webdriver  # 웹 브라우저를 자동으로 제어하기 위한 Selenium 웹 드라이버 가져오기
from selenium.webdriver.chrome.options import Options  # Chrome 브라우저의 여러 가지 옵션(설정)을 지정하기 위한 클래스
from selenium.webdriver.common.by import By  # 웹 페이지에서 요소를 찾는 방법을 지정할 수 있도록 하는 모듈
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as Ec
from selenium.common.exceptions import TimeoutException
from xarray.tutorial import base_url


def setup_driver():
    # Chrome 옵션 설정
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0")
    driver = webdriver.Chrome(options=options)
    return driver

def get_book_links(driver, max_pages=10, books_per_keyword=30, total_books=60):
  total_links = set()
  # 자기계발/재테크 검색
  search_keywords = ["재테크","자기계발"]

  for keyword in search_keywords:
    keyword_links = set()
    encoded_keyword = requests.utils.quote(keyword)
    base_url = f"https://www.yes24.com/product/search?query={encoded_keyword}"
    page = 1

    while len(keyword_links) < books_per_keyword and page <= max_pages and len(total_links) < total_books:
      try:
        #page url생성
        page_url = f"https://www.yes24.com/Product/Search?query={encoded_keyword}&Page={page}"
        #page 접속
        driver.get(page_url)
        print(f"[Info]검색어'{keyword}'| {page} 페이지 접속 중")
        # JavaScript 실행 완료 대기
        time.sleep(3)


          #페이지 소스 가져오기
        soup = BeautifulSoup(driver.page_source,'html.parser')
        #도서 링크 추출
        items = soup.select('a.gd_name')

        if not items:
          print(f"[Warning] '{keyword}' | {page}페이지 도서 없음 → 다음 페이지로")
          page += 1
          continue
          
        for item in items:
          # 총 60권 도달시  for문 루프 탈출
          if len(total_links) >= total_books:
            break

          href = item.get('href')
          if href and href.startswith('/product/goods'):
            full_url = "http://www.yes24.com" + href
            if full_url not in keyword_links:
              keyword_links.add(full_url)
              total_links.add(full_url)
              print(f"[Info]'{keyword}'수집된 도서 수: {len(keyword_links)}")
        if len(keyword_links) >= books_per_keyword:
          print(f"[Info]'{keyword}'도서 링크 {len(keyword_links)}권 수집 완료")
        page += 1
          #과도한 요청 방지를 위한 대기
        time.sleep(3)
      except TimeoutException:
        print(f"[Warning]{page}페이지 로딩 시간 초과")
        page += 1
      except Exception as e:
        print(f"[Error]도서 목록 페이지 수집 중 오류 발생:{e}")
        page += 1
      # 키워드 몇권 수집
    print(f"[Info] '{keyword}' 총 수집 완료: {len(keyword_links)}권")
    print(f"[Info] 총 수집 완료: {len(total_links)}권")
  return list(total_links)

# 도서 상세 정보 수집 함수
def get_book_info(driver,book_url):
  print(f"[Debug] 크롤링할 도서 URL: {book_url}")
  book_info = {
    '도서명': '',
    '저자': '',
    '출판사': '',
    '출판일': '',
    '정가': 0,
    '판매가': 0,
    '도서 소개': '',
    '판매지수': 0,
    '평점': 0.0,
    '책 이미지 URL': ''
  }
  # 상세페이지 크롤링
  try:
    driver.get(book_url)
    print(f"[Info]도서 상세 페이지 접속:{book_url}")
    # 상세 페이지 주요 영역 로딩 대기
    WebDriverWait(driver,10).until(
      Ec.presence_of_element_located((By.ID,"yDetailTopWrap"))
    )
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    # 도서명
    title_tag = soup.select_one('div.gd_titArea > h2.gd_name')
    if title_tag:
      book_info['도서명'] = title_tag.text.strip()
   #저자(여러명일 수 있음 )
    authors = soup.select('span.gd_auth > a')
    if authors:
      book_info['저자'] =','.join([a.text.strip() for a in authors])
    #출판사
    publisher_tag = soup.select_one('span.gd_pub')
    if publisher_tag:
      book_info['출판사'] = publisher_tag.text.strip()
    #출판일
    pub_date_tag = soup.select_one('span.gd_date')
    if pub_date_tag:
      date_text = pub_date_tag.text.strip()
      m = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', date_text)
      if m:
        year, month, day = m.groups()
        try:
          book_info['출판일'] = datetime(int(year), int(month), int(day))
        except:
          book_info['출판일'] = None
      else:
        book_info['출판일'] = None

    #정가
    rows = soup.select('table tr')
    for row in rows:
      th =row.select_one('th')
      if th and '정가' in th.text:
        em = row.select_one('td span em.yes_m')
        if em:
          price_str = em.text.strip()
          book_info['정가'] = int(re.sub(r'[^\d]','',price_str))
    #판매가(없으면 정가와 동일)
      if th and '판매가' in th.text:
        em = row.select_one('td span em.yes_m')
        if em:
          price_str = em.text.strip()
          book_info['판매가'] = int(re.sub(r'[^\d]','',price_str))
        else:
          book_info['판매가'] = book_info['정가']
      # 도서 소개 (간략 설명, 첫 100자 이내)
    intro_tag = soup.select_one('div.infoWrap_txtInner')
    if intro_tag:
      text = intro_tag.text.strip().replace('\n', ' ')
      book_info['도서 소개'] = text[:100]
    hidden_intro = soup.select_one('textarea.txtContentText')
    if hidden_intro:
      hidden_text = hidden_intro.text.strip().replace('\n', ' ')
      if len(hidden_text) > len(book_info['도서 소개']):
        book_info['도서 소개'] = hidden_text[:300]

    #판매지수
    sales_score_tag = soup.select_one('span.gd_sellNum')
    if sales_score_tag:
      sales_text = sales_score_tag.text.strip()
      sales_num = re.sub(r'[^\d]','',sales_text)
      book_info['판매지수'] = int(sales_num) if sales_num.isdigit() else 0

    # 평점 (별점, 예: '평점 4.5')
    try:
      rating_tag = soup.select_one('span.gd_rating em.yes_b')
      if rating_tag:
        rating_text = rating_tag.text.strip()
        book_info['평점'] = float(rating_text)
      else:
        print(f'[Debug]평점 태그 없음')
        book_info['평점'] = 0.0
    except Exception as e:
      print(f"[Error] 평점 수집 오류: {e}")
      book_info['평점'] = 0.0

    # 책 이미지 URL
    img_tag = soup.select_one('img.glmg')
    if img_tag and img_tag.has_attr('src'):
      book_info['책 이미지 URL'] = img_tag['src']
    else:
      print(f"[Debug] - 책 이미지 url: {book_url}")
  except Exception:
      pass
  except TimeoutException:
    print("[Warning] 도서 상세 페이지 로딩 시간 초과")
  except Exception as e:
    print(f"[Error] 도서 상세 정보 수집 중 오류: {e}")
  return book_info

# 결과 출력 함수
def show_results(df):
  # 출판일 문자열을 datetime으로 변환 (추가)
  # 1년간의 2만원 이상 도서
  df['출판일'] = pd.to_datetime(df['출판일'], format="%Y년 %m월 %d일", errors='coerce')
  recent_books = df[
    (df['출판일'] >= datetime.now() - timedelta(days=365)) &
    (df['판매가'] >= 20000)
    ]
  print("\n[출력] 최근 1년, 2만원 이상 도서:")
  print(recent_books[['도서명', '저자', '판매가', '출판일']])
    #평균 판매가 계산
  try:
    avg_price = df['판매가'].mean()
    print(f"\n[출력] 전체 도서 평균 판매가: {avg_price:.0f}원")
    # 판매 지수 탑3
    top_sales = df.sort_values('판매지수', ascending=False).head(3)
    print("\n[출력] 판매지수 상위 3권 도서:")
    print(top_sales[['도서명', '판매지수']])
     # 평점 상위 3권 도서 출력
    df['평점'] = pd.to_numeric(df['평점'], errors='coerce')
    top_rated = df[df['평점'] > 0].sort_values('평점', ascending=False).head(3)
    print("\n[출력] 평점 상위 3권 도서:")
    print(top_rated[['도서명', '평점']])
  except Exception as e:
    print(f"[Error] 통계 출력 오류: {e}")

def main():
  driver = setup_driver()
  links = get_book_links(driver)
  all_books = []
  for idx, link in enumerate(links,1):
    info = get_book_info(driver,link)
    all_books.append(info)
    print(f"[Info]{idx}번째 도서 정보 수집 완료")
    time.sleep(1)
  df = pd.DataFrame(all_books)
  df.to_csv("yes24_books.csv", index=False, encoding='utf-8-sig')
  print("[Info] CSV 저장 완료")
  show_results(df)

if __name__ == "__main__":
  main()



