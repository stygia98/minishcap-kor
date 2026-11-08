# script.json 을 내장한 자기완결 HTML 검수 앱(work/review.html) 생성
# 더블클릭 실행 -> 좌(일)/우(한) 편집 -> "JSON 내보내기"로 script.json 저장 -> 삽입기에 투입
import os, json, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "work", "script.json")
OUT  = os.path.join(ROOT, "work", "review.html")
SPK  = os.path.join(ROOT, "work", "speakers.json")   # 없으면 화자 표시 생략
DESC = os.path.join(ROOT, "work", "대사블록_목록.txt")  # 블록 설명(좌측 목록에서 펼쳐 보기), 없으면 생략

HTML = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>미니쉬 캡 번역 검수</title>
<style>
:root{--bg:#1e1f22;--panel:#2b2d31;--line:#3a3d42;--fg:#e6e6e6;--mut:#9aa0a6;--acc:#5b9dff;--done:#3ba55d;--warn:#e0a53b}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,"Malgun Gothic",sans-serif;background:var(--bg);color:var(--fg);height:100vh;display:flex;flex-direction:column}
header{display:flex;gap:10px;align-items:center;padding:8px 12px;background:var(--panel);border-bottom:1px solid var(--line);flex-wrap:wrap}
header b{font-size:15px}button{background:#3a3d42;color:var(--fg);border:1px solid #4a4d52;border-radius:6px;padding:6px 10px;cursor:pointer}
button:hover{border-color:var(--acc)}input[type=search]{background:#1a1b1e;border:1px solid #4a4d52;color:var(--fg);border-radius:6px;padding:6px 8px;min-width:160px}
.bar{height:6px;background:#1a1b1e;border-radius:4px;flex:none;width:120px;overflow:hidden}.bar>i{display:block;height:100%;background:var(--done)}
main{flex:1;display:flex;min-height:0}
/* 블록 목록: 자리(#navwrap)는 190px 고정, 설명을 펼치면 목록(#blocks)만 오른쪽으로 넓어져 번역창 위를 덮음 */
/* 자리 폭(#navwrap)은 접힌 목록 폭에 맞춰 JS가 지정(스크롤바가 진행 숫자 바로 옆) */
#navwrap{flex:none;position:relative}
#blocks{position:absolute;top:0;bottom:0;left:0;width:max-content;overflow-y:auto;overflow-x:hidden;background:#242528;border-right:1px solid var(--line);z-index:5}
#blocks.wide{max-width:calc(100vw - 20px);box-shadow:6px 0 16px #0008}
#blocks a{display:flex;align-items:center;gap:12px;padding:6px 10px;cursor:pointer;border-bottom:1px solid #2f3134;font-size:13px;white-space:nowrap}
#blocks a .top{flex:none;display:flex;align-items:center;gap:6px}
#blocks a.sel{background:var(--acc);color:#001}#blocks a .c{color:var(--mut);font-size:11px;min-width:48px;text-align:right}#blocks a.sel .c{color:#013}
#blocks .desc{font-size:12px;color:#b8bec6;padding-right:6px}#blocks a.sel .desc{color:#012}
#descBtn{background:var(--done);color:#fff;font-weight:bold;border-color:var(--done)}#descBtn:hover{filter:brightness(1.15)}#list{flex:1;overflow:auto;padding:12px}
.msg{background:var(--panel);border:1px solid var(--line);border-radius:8px;margin-bottom:10px;padding:10px}
.msg.done{border-left:3px solid var(--done)}.msg .idx{color:var(--mut);font-size:12px;margin-bottom:4px}
.jp{white-space:pre-wrap;word-break:break-word;color:#cdd3da;background:#1a1b1e;border-radius:6px;padding:8px;margin-bottom:6px}
.kr{white-space:pre-wrap;word-break:break-word;color:#9fd3a8;background:#15201a;border-radius:6px;padding:8px;margin-bottom:6px}
.kr b{color:#6fae7a;font-weight:normal}.special{color:var(--warn);font-size:12px;margin-bottom:6px}
.tags{font-size:11px;color:var(--warn);margin-bottom:6px;min-height:14px}.tags span{cursor:pointer;margin-right:6px;padding:1px 4px;background:#2a2410;border-radius:4px}
textarea{width:100%;background:#15171a;color:#eaf2ff;border:1px solid #4a4d52;border-radius:6px;padding:8px;font:inherit;resize:vertical;min-height:46px}
/* 일·한·번역 3열 가로 배치(같은 글꼴·크기), 좁은 화면에선 세로로 */
.row{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;align-items:stretch}
.row .ko,.row .col{display:flex;flex-direction:column}.row .ko textarea,.row .col>.jp,.row .col>.kr{flex:1 0 auto}.row .jp,.row .kr{margin-bottom:0}
.cbtns{font-size:11px;min-height:18px;margin-bottom:4px}.cbtns span{cursor:pointer;padding:1px 4px;border-radius:4px}  /* 칸 위 버튼(한글 복사·대사만 보기) */
.jp,.kr,textarea{font-size:14px;line-height:1.5}
@media (max-width:900px){.row{grid-template-columns:1fr}}
.meta{font-size:11px;color:var(--mut);margin-top:3px;text-align:right}
#pv{background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:10px;padding:14px;width:1100px;max-width:none;box-sizing:border-box}
#pv .row{grid-template-columns:repeat(3,minmax(0,1fr))}  /* 고정 폭이라 좁은 창에서도 3열 유지 */
#pv::backdrop{background:#0008}#pv h3{margin:0 0 10px;font-size:14px;display:flex;justify-content:space-between}
#pv .row>div{white-space:pre-wrap;word-break:break-word;border-radius:6px;padding:10px;min-height:40px}
#pv .pk{background:#15171a;color:#eaf2ff}#pv small{display:block;color:var(--mut);font-size:11px;margin-bottom:4px}
mark{background:#5b4a00;color:#ffd}.spk{color:#c9a0ff}
</style></head><body>
<header>
 <b>미니쉬 캡 번역 검수</b>
 <button id="descBtn">블록설명 펼치기</button>
 <button id="exp">JSON 내보내기</button>
 <label style="cursor:pointer;border:1px solid #4a4d52;border-radius:6px;padding:6px 10px">JSON 불러오기<input id="imp" type="file" accept=".json" hidden></label>
 <input id="q" type="search" placeholder="전체 블록 검색(일/한)">
 <div class="bar"><i id="pbar"></i></div><span id="pct" class="meta"></span>
</header>
<dialog id="pv"><h3><span id="pvT"></span><button onclick="pv.close()">닫기 (Esc)</button></h3>
 <div class="row"><div class="jp"><small>일본어</small><span id="pv_jp"></span></div><div class="kr"><small>현재 한글</small><span id="pv_kr"></span></div><div class="pk"><small>번역</small><span id="pv_ko"></span></div></div></dialog>
<main>
 <div id="navwrap"><nav id="blocks"></nav></div>
 <section id="list"></section>
</main>
<script>
const DATA = __DATA__;
const SPK = __SPK__;  // 화자 매핑(speaker_map.py) "블록#메시지" -> [화자]
const DESC = __DESC__;  // 블록 설명(work/대사블록_목록.txt) 블록번호 -> "TEXT_xxx (수)\n내용"
let showDesc = false;  // 블록 설명 모두 펼치기 상태
let cur = 0;
const $ = s => document.querySelector(s);
const tagRe = /<[^<>]+>|\{[0-9A-Fa-f]{2,4}\}/g;
const isDone = m => m.ko.trim() !== "";
// 번역 대상(글자 있는) 메시지만 진행률 집계: 태그/공백만 있는 건 제외
// 개발용 라벨(KOBITO＿HONDANA＿007·MINKA＿019 등): 번역 대상 아님 → 비워 두면 원문 유지
const devLabel = m => { const t=m.jp.split("<END>")[0].replace(tagRe,"").trim(); return /[_＿]/.test(t) && /^[A-ZＡ-Ｚ0-9０-９_＿\s]+$/.test(t); };
// 첫 <END> 뒤는 블록 정렬 패딩(FF=ホ)이라 제외 — 삽입기 비교 기준과 동일
const translatable = m => m.jp.split("<END>")[0].replace(tagRe,"").trim() !== "" && !devLabel(m);

function stats(){
  let tot=0,done=0;
  DATA.blocks.forEach(b=>b.msgs.forEach(m=>{if(translatable(m)){tot++;if(isDone(m))done++;}}));
  return {tot,done};
}
function renderBlocks(){
  const nav=$("#blocks"),sc=nav.scrollTop;nav.innerHTML="";
  nav.classList.toggle("wide",showDesc);
  $("#descBtn").textContent=showDesc?"블록설명 접기":"블록설명 펼치기";
  DATA.blocks.forEach((b,i)=>{
    let t=0,d=0;b.msgs.forEach(m=>{if(translatable(m)){t++;if(isDone(m))d++;}});
    const a=document.createElement("a");a.className=i===cur?"sel":"";
    const ds=showDesc&&DESC[b.n];
    a.innerHTML=`<div class="top"><span>블록 ${String(b.n).padStart(2,"0")}</span><span class="c">${d}/${t}</span></div>${ds?`<span class="desc">${esc(ds.replace("\n"," · "))}</span>`:""}`;
    a.onclick=()=>{cur=i;renderBlocks();renderList();};nav.appendChild(a);
  });
  nav.scrollTop=sc;  // 다시 그려도 스크롤 위치 유지
  if(!showDesc)$("#navwrap").style.width=nav.offsetWidth+"px";  // 접힌 목록 폭 = 번역창 시작 위치
}
function hl(txt,q){ if(!q)return esc(txt); return esc(txt).replace(new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g,"\\$&"),"gi"),m=>`<mark>${m}</mark>`); }
// 표시 전용: <BR> 뒤에서 줄바꿈(pre-wrap) — 데이터 값은 그대로
const brView=h=>h.replace(/&lt;BR&gt;/g,"&lt;BR&gt;\n");
function esc(s){return s.replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));}
function renderList(){
  const q=query, L=$("#list");
  L.innerHTML="";
  // 검색어가 있으면 블록 구분 없이 80블록 전체의 jp·kr·ko 를 검색, 없으면 선택한 블록만
  const hits=[];
  (q?DATA.blocks.map((_,i)=>i):[cur]).forEach(bi=>DATA.blocks[bi].msgs.forEach((m,idx)=>{
    if(q && !(m.jp.includes(q)||(m.kr||"").includes(q)||m.ko.includes(q))) return;
    hits.push([bi,idx]);}));
  const MAX=500;  // 한두 글자 검색으로 수천 건이 걸려도 화면이 멈추지 않게
  if(q)L.insertAdjacentHTML("beforeend",`<div class="meta" style="margin:0 0 8px">전체 블록 검색: ${hits.length}건${hits.length>MAX?` (앞 ${MAX}건만 표시 — 검색어를 더 구체적으로)`:""}</div>`);
  hits.slice(0,MAX).forEach(([bi,idx])=>{
    const b=DATA.blocks[bi],m=b.msgs[idx];
    const tags=[...new Set((m.jp.match(tagRe)||[]))];
    const d=document.createElement("div");d.className="msg"+(isDone(m)?" done":"");
    const special=b.special;
    d.innerHTML=`${special?'<div class="special">⚠ special 블록(비표준 구조) — 삽입 시 원본 보존</div>':''}
      <div class="row">
        <div class="col"><div class="cbtns idx">${q?`블록 ${b.n} `:""}#${idx}${translatable(m)?"":devLabel(m)?" · (개발용 라벨)":" · (제어/빈 메시지)"}${(SPK[b.n+"#"+idx]||[]).length?` · <span class="spk">화자: ${esc(SPK[b.n+"#"+idx].join(", "))}</span>`:""}</div><div class="jp">${brView(hl(m.jp,q))}</div></div>
        <div class="col"><div class="cbtns">${m.kr?'<span class="kr2ko" style="color:#9fd3a8;background:#15201a">⇨ 한글 복사</span>':''}</div><div class="kr">${m.kr?brView(hl(m.kr,q)):''}</div></div>
        <div class="ko"><div class="cbtns"><span class="plain" style="color:#cfe0ff;background:#1d2a3d">대사만 보기</span></div><textarea data-b="${bi}" data-i="${idx}" placeholder="${translatable(m)?'번역 입력':'비워두면 원문 유지'}">${brView(esc(m.ko))}</textarea></div>
      </div>
      <div class="tags" style="margin:6px 0 0">${tags.map(t=>`<span data-t="${esc(t)}">${esc(t)}</span>`).join("")}</div>`;
    L.appendChild(d);
  });
  // 입력창 높이를 내용에 맞춤(스크롤바 없이 전체 표시)
  const fit=t=>{t.style.height="auto";t.style.height=(t.scrollHeight+2)+"px";};
  const msgOf=ta=>DATA.blocks[ta.dataset.b].msgs[ta.dataset.i];  // 입력창 → 해당 블록의 메시지
  L.querySelectorAll("textarea").forEach(t=>{fit(t);t.addEventListener("input",()=>fit(t));});
  L.querySelectorAll("textarea").forEach(t=>{
    // 입력창은 <BR> 뒤 줄바꿈으로 표시, 저장값은 줄바꿈 제거. Enter = <BR> 입력
    t.oninput=()=>{const v=t.value.replace(/\r?\n/g,"");msgOf(t).ko=v;
      t.closest(".msg").classList.toggle("done",v.trim()!=="");
      updProg();renderBlocks();};
    t.onkeydown=e=>{if(e.key!=="Enter"||e.isComposing)return;e.preventDefault();insertAt(t,"<BR>\n");};
  });
  // kr(현재 한글) 전체를 ko 입력창에 복사(기존 입력이 있으면 확인 후 덮어씀)
  L.querySelectorAll(".kr2ko").forEach(s=>{s.onclick=()=>{
    const ta=s.closest(".msg").querySelector("textarea");
    if(ta.value.trim()&&!confirm("입력한 번역을 현재 한글로 덮어쓸까요?"))return;
    ta.value=msgOf(ta).kr.replace(/<BR>/g,"<BR>\n");ta.dispatchEvent(new Event("input"));ta.focus();};});
  // 대사만 보기: 제어문 뺀 jp/kr/ko 를 팝업으로(데이터는 건드리지 않음)
  L.querySelectorAll(".plain").forEach(s=>{s.onclick=()=>{
    const ta=s.closest(".msg").querySelector("textarea"),m=msgOf(ta);
    $("#pvT").textContent=`블록 ${DATA.blocks[ta.dataset.b].n} #${ta.dataset.i}`;
    ["jp","kr","ko"].forEach(k=>{$("#pv_"+k).textContent=plainText(m[k]||"");});
    $("#pv").showModal();};});
  L.querySelectorAll(".tags span[data-t]").forEach(s=>{s.onclick=()=>{
    const ta=s.closest(".msg").querySelector("textarea");
    insertAt(ta,s.dataset.t==="<BR>"?"<BR>\n":s.dataset.t);};});
}
// 커서 위치에 문자열 삽입 후 input 이벤트로 저장
function insertAt(ta,s){const p=ta.selectionStart;ta.value=ta.value.slice(0,p)+s+ta.value.slice(ta.selectionEnd);
  ta.dispatchEvent(new Event("input"));ta.focus();ta.selectionStart=ta.selectionEnd=p+s.length;
}
// 표시용 대사 텍스트: 첫 <END> 뒤(패딩) 버림, <BR>=줄바꿈, <name>=〈이름〉, 선택지=▸, 나머지 제어문 제거
function plainText(s){if(s.includes("<END>"))s=s.slice(0,s.indexOf("<END>"));
  return s.replace(/<BR>/g,"\n").replace(/<name>/g,"〈이름〉").replace(/<select:[0-9A-F]+>/g," ▸").replace(tagRe,"");}
$("#pv").onclick=e=>{if(e.target.id==="pv")$("#pv").close();};  // 바깥 클릭 닫기(Esc는 기본 동작)
function updProg(){const{tot,done}=stats();const p=tot?Math.round(done/tot*100):0;
  $("#pbar").style.width=p+"%";$("#pct").textContent=`${done}/${tot} (${p}%)`;}
// 불러오기/내보내기로 고른 파일 핸들을 IndexedDB에 보관 → 앱을 다시 열어도 같은 파일·폴더 사용
// (file:// 에서는 picker의 id 폴더 기억이 동작하지 않음)
let saveHandle=null,baseStamp=__GEN__;  // baseStamp = 화면 데이터의 기준 시각(내장 시 script.json 수정 시각)
const idb=(mode,fn)=>new Promise((res,rej)=>{const o=indexedDB.open("mc_review",1);
  o.onupgradeneeded=()=>o.result.createObjectStore("kv");o.onerror=()=>rej(o.error);
  o.onsuccess=()=>{const tx=o.result.transaction("kv",mode),r=fn(tx.objectStore("kv"));tx.oncomplete=()=>res(r.result);tx.onerror=()=>rej(tx.error);};});
const keepHandle=h=>{saveHandle=h;idb("readwrite",s=>s.put(h,"h")).catch(()=>{});};
const pickOpt=()=>({id:"mc_script",...(saveHandle?{startIn:saveHandle}:{}),types:[{description:"JSON",accept:{"application/json":[".json"]}}]});
$("#exp").onclick=async()=>{const blob=new Blob([JSON.stringify({base:DATA.base,blocks:DATA.blocks})],{type:"application/json"});
  if(window.showSaveFilePicker){try{
    if(saveHandle&&await saveHandle.requestPermission({mode:"readwrite"})!=="granted")saveHandle=null;
    if(!saveHandle)keepHandle(await showSaveFilePicker({...pickOpt(),suggestedName:"script.json"}));
    // 앱이 데이터를 읽은 뒤 파일이 바뀌었으면(다른 탭 저장·dump 수정 등) 옛 데이터로 덮어쓰기 전에 경고
    const cur=(await saveHandle.getFile()).lastModified;
    if(cur>baseStamp+2000&&!confirm("파일이 이 화면의 데이터보다 최신입니다(다른 탭·스크립트에서 수정됨).\n덮어쓰면 그 변경이 사라집니다. 먼저 'JSON 불러오기'를 권장합니다.\n\n그래도 덮어쓸까요?"))return;
    const w=await saveHandle.createWritable();await w.write(blob);await w.close();
    baseStamp=(await saveHandle.getFile()).lastModified;alert("저장 완료: "+saveHandle.name);return;
  }catch(x){if(x.name==="AbortError")return;alert("저장 실패: "+x);return;}}
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="script.json";a.click();};
const loadJson=t=>{try{const j=JSON.parse(t);if(j.base)DATA.base=j.base;DATA.blocks=j.blocks;renderBlocks();renderList();updProg();}catch(x){alert("JSON 오류: "+x);}};
$("#imp").onchange=e=>{const f=e.target.files[0];if(!f)return;f.text().then(loadJson);};
// 지원 브라우저: 불러온 파일 핸들을 저장 대상으로도 기억(불러온 파일에 바로 내보내기)
if(window.showOpenFilePicker)$("#imp").onclick=async e=>{e.preventDefault();try{
  const[h]=await showOpenFilePicker(pickOpt());
  keepHandle(h);const f=await h.getFile();baseStamp=f.lastModified;loadJson(await f.text());}catch(x){if(x.name!=="AbortError")alert("불러오기 실패: "+x);}};
// 검색: 타이핑 중엔 그대로, Enter(또는 × 로 지우기) 때만 검색어 확정 후 필터링
let query="";
$("#q").addEventListener("search",()=>{query=$("#q").value.trim();renderList();});
// 블록설명 펼치기/접기(펼치면 각 블록 오른쪽에 한 줄로 표시, 번역창 위를 덮음)
$("#descBtn").onclick=()=>{showDesc=!showDesc;renderBlocks();};
// 열 때마다 script.json 자동 다시 읽기(HTML에 내장된 데이터는 생성 시점이라 옛것일 수 있음)
//  ① http로 열었으면 같은 폴더의 script.json 을 fetch
//  ② 더블클릭(file://)이면 fetch 불가 → 불러오기/내보내기로 기억해 둔 파일 핸들로 읽음.
//     브라우저가 파일 접근을 허용한 상태일 때만(예: '방문할 때마다 허용') 읽고, 아니면 내장 데이터 그대로 사용
const readHandle=async h=>{const f=await h.getFile();baseStamp=f.lastModified;loadJson(await f.text());};
async function autoLoad(){
  if(location.protocol.startsWith("http"))try{const r=await fetch("script.json",{cache:"no-store"});
    if(r.ok){baseStamp=Date.parse(r.headers.get("Last-Modified"))||Date.now();loadJson(await r.text());return;}}catch(x){}
  if(!window.indexedDB)return;
  const h=await idb("readonly",s=>s.get("h")).catch(()=>null);if(!h)return;
  saveHandle=h;
  try{if(await h.queryPermission({mode:"readwrite"})==="granted")await readHandle(h);}catch(x){}
}
renderBlocks();renderList();updProg();autoLoad();
</script></body></html>"""

def load_desc():
    """대사블록_목록.txt 의 ' 1  TEXT_SAVE (22)   설명' 줄 -> {1: "TEXT_SAVE (22)\n설명"}"""
    out = {}
    if os.path.exists(DESC):
        for line in open(DESC, encoding="utf-8").read().splitlines():
            m = re.match(r"\s*(\d+)\s+(TEXT_\S+\s*\(\d+\))\s+(.*\S)", line)
            if m:
                out[int(m.group(1))] = m.group(2) + "\n" + m.group(3)
    return out

def main():
    data = open(DATA, "r", encoding="utf-8").read()
    spk = open(SPK, encoding="utf-8").read() if os.path.exists(SPK) else "{}"
    desc = json.dumps(load_desc(), ensure_ascii=False)
    gen = str(int(os.path.getmtime(DATA) * 1000))
    html = HTML.replace("__GEN__", gen).replace("__DESC__", desc).replace("__DATA__", data).replace("__SPK__", spk)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("검수 앱 생성: %s (%.1f KB)" % (OUT, len(html)/1024))

if __name__ == "__main__":
    main()
