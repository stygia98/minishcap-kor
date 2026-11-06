// 이름 입력 한글 조합형 개조 (K롬, 0x08E51800에 링크)
// 세이브 이름 8바이트 = 항목 나열: 1바이트 글자(0x10~0xFF, 가나/영숫자) 또는
//   2바이트 한글 항목 [1+(v>>8), v&0xFF] — v<2350: 완성형 KS 순번, v>=2350: 자모(v-2350, 0~39)
// 종료 0. 둘째 바이트가 0일 수 있으므로 반드시 항목 단위로 읽는다.
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef signed int s32;

#include "tables.h"   // ks2uni[2350], hangul_tm[640], key_tiles[40*64], NSYL, NJAMO, KEYBASE

#define NAME        ((u8*)0x02002AC0)          // gSave.name
#define SAVES_NAME  ((u8*)0x02019F6C)          // gMapDataBottomSpecial.saves[0].name
#define SAVE_SIZE   0x4B4
#define MENU        ((volatile u8*)0x02000080) // [1]=column_idx, [0x10..0x13]=unk10.a[0..3]
#define NEWKEYS     (*(volatile u16*)0x03000FF2)
#define BG3         ((u16*)0x02001A40)
#define BG1_ROWS    ((void*)0x02022030)          // gBG1Buffer+0x100 (원본 0x8051348 리터럴)
#define SCREEN      ((volatile u8*)0x03000F50)
#define TEXTGFX     ((void*)0x02000D00)
#define NAMEBUF     ((u8*)0x0203B800)          // 변환된 이름 텍스트(최대 13바이트)
#define KBD_DIRTY   (*(volatile u8*)0x0203B810)
#define VRAM        ((u8*)0x06000000)
#define OBJ_NAME    ((u8*)0x06014000)

#define NAME_MAX    8
#define WIDTH_MAX   48

typedef struct {
    u8 flags, unk1, charColor, bgColor;
    u16 unk4, unk6;
    void* unk8;
} WStruct;

#define F(addr, type) ((type)((addr) | 1))
#define SoundReq      F(0x080A3020, void (*)(u32))
#define SaveRedraw    F(0x08051440, void (*)(u32))      // sub_08051574: 효과음 + 슬롯 반영 + 이름 다시 그리기
#define SetMenuType   F(0x080A6ECC, void (*)(u32))
#define LoadGfx       F(0x08050274, void (*)(u32))      // sub_080503A8
#define MemCopy       F(0x0801D650, void (*)(const void*, void*, u32))
#define MemClear      F(0x0801D614, void (*)(void*, u32))
#define KeyGlyphs     F(0x0805065C, void (*)(void))     // 코드 0~255를 자판 VRAM에 렌더
#define GetWS         F(0x0805F108, WStruct* (*)(void))
#define FreeWS        F(0x0805F140, void (*)(WStruct*))
#define DrawChar      F(0x0805F61C, u32 (*)(u32, WStruct*))
#define Dakuten       F(0x08051388, u32 (*)(u32))       // sub_080514BC (a[3] 기준으로 직전 글자 참조)
#define DrawStr       F(0x080A4298, u32 (*)(WStruct*, const void*, u32))
#define NumToStr      F(0x08002632, u32 (*)(u32))

// ---------------- 항목 처리 ----------------
typedef struct { u8 pos, len; s32 v; } Item;   // v: -1=1바이트 글자, 그 외 한글 번호

static int parse(const u8* n, Item* it) {
    int k = 0, p = 0;
    while (p < NAME_MAX && n[p]) {
        if (n[p] < 0x10) {
            if (p + 1 >= NAME_MAX) break;
            it[k].pos = p; it[k].len = 2; it[k].v = ((n[p] - 1) << 8) | n[p + 1];
            p += 2;
        } else {
            it[k].pos = p; it[k].len = 1; it[k].v = -1;
            p += 1;
        }
        k++;
    }
    return k;
}

static int bytelen(const Item* it, int k) { return k ? it[k - 1].pos + it[k - 1].len : 0; }

static int width(const Item* it, int k) {
    int w = 0;
    for (int i = 0; i < k; i++) w += it[i].v < 0 ? 8 : 9;
    return w;
}

static void put(u8* p, s32 v) { p[0] = 1 + (v >> 8); p[1] = v & 0xFF; }

// ---------------- 한글 조합 ----------------
// 컴파일러가 나눗셈 루프를 __aeabi_uidiv 호출로 바꾸므로 직접 제공(시프트-뺄셈)
u32 __aeabi_uidiv(u32 n, u32 d) {
    u32 q = 0;
    for (int b = 31; b >= 0; b--)
        if ((n >> b) >= d) { n -= d << b; q |= 1u << b; }
    return q;
}
static u32 udiv(u32 n, u32 d, u32* r) { u32 q = __aeabi_uidiv(n, d); *r = n - q * d; return q; }

static void decomp(s32 v, int* cho, int* jung, int* jong) {
    u32 u = ks2uni[v], r;
    *cho = udiv(u, 588, &r);
    *jung = udiv(r, 28, &r);
    *jong = r;
}

static s32 make(int cho, int jung, int jong) {   // 완성형에 없으면 -1
    u32 u = cho * 588 + jung * 28 + jong;
    int lo = 0, hi = NSYL - 1;
    while (lo <= hi) {
        int m = (lo + hi) >> 1;
        if (ks2uni[m] == u) return m;
        if (ks2uni[m] < u) lo = m + 1; else hi = m - 1;
    }
    return -1;
}

static const u8 CHO2JONG[19] = { 1, 2, 4, 7, 0, 8, 16, 17, 0, 19, 20, 21, 22, 0, 23, 24, 25, 26, 27 };
// 받침 → (남는 받침 << 5) | 다음 글자로 넘어갈 초성
static const u16 SPLIT[28] = {
    0, 0, 1, (1 << 5) | 9, 2, (4 << 5) | 12, (4 << 5) | 18, 3, 5, (8 << 5) | 0, (8 << 5) | 6, (8 << 5) | 7,
    (8 << 5) | 9, (8 << 5) | 16, (8 << 5) | 17, (8 << 5) | 18, 6, 7, (17 << 5) | 9, 9, 10, 11, 12, 14, 15, 16, 17, 18 };

static int jong_add(int jong, int cho) {
    static const u8 T[][3] = { {1, 9, 3}, {4, 12, 5}, {4, 18, 6}, {8, 0, 9}, {8, 6, 10}, {8, 7, 11},
                               {8, 9, 12}, {8, 16, 13}, {8, 17, 14}, {8, 18, 15}, {17, 9, 18} };
    for (u32 i = 0; i < sizeof T / 3; i++) if (T[i][0] == jong && T[i][1] == cho) return T[i][2];
    return 0;
}

static int jung_add(int a, int b) {
    static const u8 T[][3] = { {8, 0, 9}, {8, 1, 10}, {8, 20, 11}, {13, 4, 14}, {13, 5, 15}, {13, 20, 16}, {18, 20, 19} };
    for (u32 i = 0; i < sizeof T / 3; i++) if (T[i][0] == a && T[i][1] == b) return T[i][2];
    return -1;
}

static int jung_strip(int j) {
    if (j >= 9 && j <= 11) return 8;
    if (j >= 14 && j <= 16) return 13;
    if (j == 19) return 18;
    return -1;
}

static void sync_cursor(void) {
    Item it[8];
    int k = parse(NAME, it);
    int w = width(it, k);
    MENU[0x13] = (w + 4) >> 3;
}

static int room(const Item* it, int k, int bytes, int w) {
    return bytelen(it, k) + bytes <= NAME_MAX && width(it, k) + w <= WIDTH_MAX;
}

static int append_v(Item* it, int k, s32 v) {
    if (!room(it, k, 2, 9)) return 0;
    int p = bytelen(it, k);
    put(NAME + p, v);
    if (p + 2 < NAME_MAX) NAME[p + 2] = 0;
    return 1;
}

// j: 0~18 초성 자음, 19~39 중성 모음
static int hangul_input(int j) {
    Item it[8];
    int k = parse(NAME, it);
    Item* last = k ? &it[k - 1] : 0;
    int cho, jung, jong;
    s32 s;

    if (j < 19) {
        if (last && last->v >= 0 && last->v < NSYL) {
            decomp(last->v, &cho, &jung, &jong);
            int jg = jong ? jong_add(jong, j) : CHO2JONG[j];
            if (jg && (s = make(cho, jung, jg)) >= 0) { put(NAME + last->pos, s); return 1; }
        }
        return append_v(it, k, NSYL + j);
    }

    int v = j - 19;
    if (last && last->v >= 0) {
        if (last->v < NSYL) {
            decomp(last->v, &cho, &jung, &jong);
            if (!jong) {
                int v2 = jung_add(jung, v);
                if (v2 >= 0 && (s = make(cho, v2, 0)) >= 0) { put(NAME + last->pos, s); return 1; }
            } else {
                s32 s1 = make(cho, jung, SPLIT[jong] >> 5);
                s32 s2 = make(SPLIT[jong] & 31, v, 0);
                if (s1 >= 0 && s2 >= 0 && room(it, k, 2, 9)) {
                    put(NAME + last->pos, s1);
                    return append_v(it, k, s2);
                }
            }
        } else {
            int x = last->v - NSYL;
            if (x < 19) {
                if ((s = make(x, v, 0)) >= 0) { put(NAME + last->pos, s); return 1; }
            } else {
                int v2 = jung_add(x - 19, v);
                if (v2 >= 0) { put(NAME + last->pos, NSYL + 19 + v2); return 1; }
            }
        }
    }
    return append_v(it, k, NSYL + j);
}

static int hangul_delete(void) {
    Item it[8];
    int k = parse(NAME, it);
    if (!k) return 0;
    Item* last = &it[k - 1];
    int cho, jung, jong, j2;
    if (last->v >= 0 && last->v < NSYL) {
        decomp(last->v, &cho, &jung, &jong);
        s32 s;
        if (jong) s = make(cho, jung, SPLIT[jong] >= 32 ? SPLIT[jong] >> 5 : 0);   // 겹받침→앞 받침, 홑받침→없음
        else if ((j2 = jung_strip(jung)) >= 0) s = make(cho, j2, 0);              // 복모음→단모음
        else s = NSYL + cho;                                                       // 모음 제거→초성 자모
        if (s >= 0) { put(NAME + last->pos, s); return 1; }
    } else if (last->v >= NSYL + 19 && (j2 = jung_strip(last->v - NSYL - 19)) >= 0) {
        put(NAME + last->pos, NSYL + 19 + j2);
        return 1;
    }
    for (int p = last->pos; p < NAME_MAX; p++) NAME[p] = 0;
    return 1;
}

static int kana_input(u32 c) {
    Item it[8];
    int k = parse(NAME, it);
    if (c == 0 || c == 0xE || c == 0xF) {           // 탁음/반탁음 키: 직전이 1바이트 글자일 때만
        if (!k || it[k - 1].v >= 0) return 0;
        u8 save = MENU[0x13];
        MENU[0x13] = bytelen(it, k);
        u32 r = Dakuten(c);
        MENU[0x13] = save;
        if (r == 0) return 0;
        if (r != 1) { NAME[it[k - 1].pos] = r; return 1; }
    }
    if (!room(it, k, 1, 8)) return 0;
    int p = bytelen(it, k);
    NAME[p] = c;
    if (p + 1 < NAME_MAX) NAME[p + 1] = 0;
    return 1;
}

// ---------------- 텍스트 변환 ----------------
static u8* to_text(const u8* n, u8* d) {
    Item it[8];
    int k = parse(n, it);
    for (int i = 0; i < k; i++) {
        s32 v = it[i].v;
        if (v < 0) { *d++ = n[it[i].pos]; continue; }
        if (v >= NSYL) { *d++ = 0x0F; *d++ = 0x46; *d++ = v - NSYL; }
        else if (v < 1024) { *d++ = 0x0B + (v >> 8); *d++ = v & 0xFF; }
        else { v -= 1024; *d++ = 0x0F; *d++ = 0x40 + (v >> 8); *d++ = v & 0xFF; }
    }
    *d = 0;
    return d;
}

static u32 glyph_code(s32 v) {
    if (v >= NSYL) return 0xF00 | (v - NSYL);
    if (v < 1024) return ((4 + (v >> 8)) << 8) | (v & 0xFF);
    v -= 1024;
    return ((9 + (v >> 8)) << 8) | (v & 0xFF);
}

// ---------------- 훅 ----------------
// 동작5: B=지우기, A(하단 4번째 버튼)=한글 페이지
u32 hk_act5(u32 tmp3) {
    if (NEWKEYS & 2) {
        if (hangul_delete()) { sync_cursor(); SaveRedraw(0x6C); }
        return tmp3;
    }
    return 3;
}

// 동작6: 글자 칸에서 A
u32 hk_act6(u32 tmp3) {
    u32 c = BG3[MENU[0x10] * 2 + 0xC3 + MENU[0x11] * 0x40] >> 1 & 0xFF;
    int ok;
    if (MENU[1] == 3 && c >= KEYBASE && c < KEYBASE + NJAMO) ok = hangul_input(c - KEYBASE);
    else ok = kana_input(c);
    if (ok) { sync_cursor(); SaveRedraw(0x6B); }
    return tmp3;
}

// 동작7: R(탁음)
u32 hk_act7(u32 tmp3) {
    if (kana_input(0)) { sync_cursor(); SaveRedraw(0x6B); }
    return tmp3;
}

// 동작8: END — 뒤쪽 공백 제거 후 종료
u32 hk_act8(u32 tmp3) {
    Item it[8];
    int k = parse(NAME, it);
    while (k && it[k - 1].v < 0 && NAME[it[k - 1].pos] == 0x20) k--;
    for (int p = bytelen(it, k); p < NAME_MAX; p++) NAME[p] = 0;
    sync_cursor();
    SaveRedraw(0x6A);
    SetMenuType(NAME[0] ? 2 : 3);
    return tmp3;
}

// sub_08051458 대체: 페이지 타일맵 로드
void hk_page_load(void) {
    u32 col = MENU[1];
    if (col == 3) {
        MemCopy(hangul_tm, BG3, 0x500);
        *(volatile u16*)(SCREEN + 0x1A) = 1;
        *(volatile u16*)(SCREEN + 0x26) = 1;
        MemCopy(key_tiles, VRAM + KEYBASE * 64, NJAMO * 64);
        KBD_DIRTY = 1;
    } else {
        if (KBD_DIRTY) { KeyGlyphs(); KBD_DIRTY = 0; }
        LoadGfx(col + 9);
    }
    MemCopy(BG3 + 0x80, BG1_ROWS, 0x400);
}

// sub_0805070C 대체: 3개 슬롯 이름 스프라이트
void hk_name_draw(void) {
    WStruct* ws = GetWS();
    if (!ws) return;
    ws->charColor = 0;
    ws->bgColor = 5;
    ws->unk1 = 1;
    ws->unk4 = 0x30;
    ws->unk8 = TEXTGFX;
    for (int i = 0; i < 3; i++) {
        const u8* n = SAVES_NAME + i * SAVE_SIZE;
        Item it[8];
        int k = parse(n, it);
        ws->unk6 = 0;
        MemClear(ws->unk8, 0x200);
        for (int j = 0; j < k; j++) {
            if (it[j].v < 0) DrawChar(n[it[j].pos], ws);
            else { ws->unk1 = 0; DrawChar(glyph_code(it[j].v), ws); ws->unk1 = 1; }
        }
        MemCopy(ws->unk8, OBJ_NAME + i * 0x200, 0x200);
    }
    FreeWS(ws);
}

// 0x80A424C 대체(메뉴의 이름 + 키스톤 이름 표시)
u32 hk_menu_name(void) {
    WStruct* ws = GetWS();
    if (!ws) return 0;
    ws->unk8 = TEXTGFX;
    ws->charColor = 0;
    ws->bgColor = 5;
    ws->unk1 = 0;
    to_text(NAME, NAMEBUF);
    DrawStr(ws, NAMEBUF, 0x80);
    u32 r = DrawStr(ws, (const void*)NumToStr(*(u32*)(0x02022740 + 0xC)), 0xA0);
    FreeWS(ws);
    return r;
}

// 대사 `06 XX`: XX==0(이름)이면 변환 버퍼, 그 외는 원래 표
const void* hk_str(u32 xx, u8* token) {
    if (xx == 0) { to_text(NAME, NAMEBUF); return NAMEBUF; }
    const void* const* tbl = *(const void* const**)(token + 0xC);
    if (!tbl) tbl = (const void* const*)0x08108EF4;
    return tbl[xx];
}

// ---------------- 어셈블리 스텁 ----------------
__asm__(
    ".text\n.thumb\n.align 2\n"
    ".global st_act5\n.thumb_func\nst_act5:\n adds r0, r4, #0\n bl hk_act5\n b st_back\n"
    ".global st_act6\n.thumb_func\nst_act6:\n adds r0, r4, #0\n bl hk_act6\n b st_back\n"
    ".global st_act7\n.thumb_func\nst_act7:\n adds r0, r4, #0\n bl hk_act7\n b st_back\n"
    ".global st_act8\n.thumb_func\nst_act8:\n adds r0, r4, #0\n bl hk_act8\n b st_back\n"
    "st_back:\n adds r4, r0, #0\n ldr r0, =0x080511EF\n bx r0\n"
    ".global st_str\n.thumb_func\nst_str:\n adds r0, r4, #0\n adds r1, r6, #0\n bl hk_str\n adds r1, r0, #0\n adds r0, r6, #0\n"
    " ldr r2, =0x0805ED81\n bl st_call_r2\n ldr r0, =0x0805EE2D\n bx r0\n"
    "st_call_r2:\n bx r2\n"
    ".ltorg\n");
