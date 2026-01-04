async def get_exact_rank(page, region):
    # PS 스토어의 '출시 예정/예약 주문' 전체 보기 카테고리 (가장 공신력 있는 순위 포인트)
    # 이 ID는 PS Store의 정식 예약판매 리스트를 불러옵니다.
    category_id = "601955f3-5290-449e-9907-f3160a2b918b"
    
    # 최대 3페이지(약 72개 항목)까지 뒤져서 붉은사막을 찾습니다.
    for page_num in range(1, 4):
        url = f"https://store.playstation.com/{region}/category/{category_id}/{page_num}"
        try:
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(4000) # 로딩 대기시간 증가
            
            # 상품 이름 추출
            names = await page.locator('[data-qa="product-name"]').all_text_contents()
            
            if not names: continue

            for i, name in enumerate(names):
                # 에디션 명칭(Deluxe 등)에 상관없이 'Crimson Desert' 단어 포함 여부 확인
                if any(kw in name.lower() for kw in ["crimson desert", "붉은사막", "紅の砂漠"]):
                    # 정확한 순위 계산: (이전 페이지 수 * 24) + 현재 페이지 순서
                    return ((page_num - 1) * 24) + (i + 1)
        except:
            continue
    return 100 # 끝까지 없으면 100위
