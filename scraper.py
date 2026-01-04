async def get_rank(page, region):
    # '베스트셀러' 카테고리에서 페이지를 넘기며 탐색 (최대 3페이지)
    for page_num in range(1, 4): 
        url = f"https://store.playstation.com/{region}/category/05a79ebd-771a-40ad-87d0-14fb847b019a/{page_num}"
        try:
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_timeout(3000) 
            
            # 모든 상품 이름과 링크 가져오기
            items = await page.locator('[data-qa="product-name"]').all_text_contents()
            
            for i, name in enumerate(items):
                # 붉은사막 키워드 매칭
                if any(kw in name.lower() for kw in ["crimson desert", "붉은사막", "紅の砂漠"]):
                    # 페이지 번호를 계산하여 정확한 순위 도출 (한 페이지당 24개)
                    actual_rank = ((page_num - 1) * 24) + (i + 1)
                    return actual_rank
        except:
            continue
    return 100 # 3페이지 안에도 없으면 100위로 처리
