# script.json 을 내장한 자기완결 HTML 검수 앱(work/review.html) 생성
# 더블클릭 실행 -> 좌(일)/우(한) 편집 -> "JSON 내보내기"로 script.json 저장 -> 삽입기에 투입
import os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "work", "script.json")
OUT  = os.path.join(ROOT, "work", "review.html")
SPK  = os.path.join(ROOT, "work", "speakers.json")   # 없으면 화자 표시 생략

HTML = r"""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>미니쉬 캡 번역 검수</title>
<style>
:root{--bg:#1e1f22;--panel:#2b2d31;--line:#3a3d42;--fg:#e6e6e6;--mut:#9aa0a6;--acc:#5b9dff;--done:#3ba55d;--warn:#e0a53b}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 system-ui,"Malgun Gothic",sans-serif;background:var(--bg);color:var(--fg);height:100vh;display:flex;flex-direction:column}
header{display:flex;gap:10px;align-items:center;padding:8px 12px;background:var(--panel);border-bottom:1px solid var(--line);flex-wrap:wrap}
header b{font-size:15px}button{background:#3a3d42;color:var(--fg);border:1px solid #4a4d52;border-radius:6px;padding:6px 10px;cursor:pointer}
button:hover{border-color:var(--acc)}input[type=search]{background:#1a1b1e;border:1px solid #4a4d52;color:var(--fg);border-radius:6px;padding:6px 8px;min-width:160px}
.bar{height:6px;background:#1a1b1e;border-radius:4px;flex:1;min-width:120px;overflow:hidden}.bar>i{display:block;height:100%;background:var(--done)}
main{flex:1;display:flex;min-height:0}
#blocks{width:150px;overflow:auto;background:#242528;border-right:1px solid var(--line)}
#blocks a{display:flex;justify-content:space-between;padding:6px 10px;cursor:pointer;border-bottom:1px solid #2f3134;font-size:13px}
#blocks a.sel{background:var(--acc);color:#001}#blocks a .c{color:var(--mut);font-size:11px}#blocks a.sel .c{color:#013}
#list{flex:1;overflow:auto;padding:12px}
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
#pv{background:var(--panel);color:var(--fg);border:1px solid var(--line);border-radius:10px;padding:14px;width:1000px;max-width:none;box-sizing:border-box}
#pv .row{grid-template-columns:repeat(3,minmax(0,1fr))}  /* 고정 폭이라 좁은 창에서도 3열 유지 */
#pv::backdrop{background:#0008}#pv h3{margin:0 0 10px;font-size:14px;display:flex;justify-content:space-between}
#pv .row>div{white-space:pre-wrap;word-break:break-word;border-radius:6px;padding:10px;min-height:40px}
#pv .pk{background:#15171a;color:#eaf2ff}#pv small{display:block;color:var(--mut);font-size:11px;margin-bottom:4px}
mark{background:#5b4a00;color:#ffd}.spk{color:#c9a0ff}
</style></head><body>
<header>
 <b>미니쉬 캡 번역 검수</b>
 <button id="exp">JSON 내보내기</button>
 <label style="cursor:pointer;border:1px solid #4a4d52;border-radius:6px;padding:6px 10px">JSON 불러오기<input id="imp" type="file" accept=".json" hidden></label>
 <input id="q" type="search" placeholder="검색(일/한)">
 <label><input type="checkbox" id="onlyTodo"> 미번역만</label>
 <div class="bar"><i id="pbar"></i></div><span id="pct" class="meta"></span>
</header>
<dialog id="pv"><h3><span id="pvT"></span><button onclick="pv.close()">닫기 (Esc)</button></h3>
 <div class="row"><div class="jp"><small>일본어</small><span id="pv_jp"></span></div><div class="kr"><small>현재 한글</small><span id="pv_kr"></span></div><div class="pk"><small>번역</small><span id="pv_ko"></span></div></div></dialog>
<main>
 <nav id="blocks"></nav>
 <section id="list"></section>
</main>
<script>
const DATA = __DATA__;
const SPK = __SPK__;  // 화자 매핑(speaker_map.py) "블록#메시지" -> [화자]
let cur = 0;
const $ = s => document.querySelector(s);
const tagRe = /<[^<>]+>|\{[0-9A-Fa-f]{2,4}\}/g;
const isDone = m => m.ko.trim() !== "";
// 번역 대상(글자 있는) 메시지만 진행률 집계: 태그/공백만 있는 건 제외
// 개발용 라벨(KOBITO＿HONDANA＿007·MINKA＿019 등): 번역 대상 아님 → 비워 두면 원문 유지
const devLabel = m => { const t=m.jp.split("<start>")[0].replace(tagRe,"").trim(); return /[_＿]/.test(t) && /^[A-ZＡ-Ｚ0-9０-９_＿\s]+$/.test(t); };
// 첫 <start> 뒤는 블록 정렬 패딩(FF=ホ)이라 제외 — 삽입기 비교 기준과 동일
const translatable = m => m.jp.split("<start>")[0].replace(tagRe,"").trim() !== "" && !devLabel(m);

function stats(){
  let tot=0,done=0;
  DATA.blocks.forEach(b=>b.msgs.forEach(m=>{if(translatable(m)){tot++;if(isDone(m))done++;}}));
  return {tot,done};
}
function renderBlocks(){
  const nav=$("#blocks");nav.innerHTML="";
  DATA.blocks.forEach((b,i)=>{
    let t=0,d=0;b.msgs.forEach(m=>{if(translatable(m)){t++;if(isDone(m))d++;}});
    const a=document.createElement("a");a.className=i===cur?"sel":"";
    // 블록 검수완료 체크 → b.reviewed 로 script.json 에 함께 저장
    a.innerHTML=`<span><input type="checkbox" title="검수완료"${b.reviewed?" checked":""}> 블록 ${String(b.n).padStart(2,"0")}</span><span class="c">${d}/${t}</span>`;
    const cb=a.querySelector("input");cb.onclick=e=>{e.stopPropagation();b.reviewed=cb.checked;updProg();};
    a.onclick=()=>{cur=i;renderBlocks();renderList();};nav.appendChild(a);
  });
}
function hl(txt,q){ if(!q)return esc(txt); return esc(txt).replace(new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g,"\\$&"),"gi"),m=>`<mark>${m}</mark>`); }
// 표시 전용: <BR> 뒤에서 줄바꿈(pre-wrap) — 데이터 값은 그대로
const brView=h=>h.replace(/&lt;BR&gt;/g,"&lt;BR&gt;\n");
function esc(s){return s.replace(/[&<>]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));}
function renderList(){
  const q=$("#q").value.trim(), todo=$("#onlyTodo").checked, b=DATA.blocks[cur], L=$("#list");
  L.innerHTML="";
  b.msgs.forEach((m,idx)=>{
    if(todo && (!translatable(m)||isDone(m))) return;
    if(q && !(m.jp.includes(q)||m.ko.includes(q))) return;
    const tags=[...new Set((m.jp.match(tagRe)||[]))];
    const d=document.createElement("div");d.className="msg"+(isDone(m)?" done":"");
    const special=DATA.blocks[cur].special;
    d.innerHTML=`${special?'<div class="special">⚠ special 블록(비표준 구조) — 삽입 시 원본 보존</div>':''}
      <div class="row">
        <div class="col"><div class="cbtns idx">#${idx}${translatable(m)?"":devLabel(m)?" · (개발용 라벨)":" · (제어/빈 메시지)"}${(SPK[b.n+"#"+idx]||[]).length?` · <span class="spk">화자: ${esc(SPK[b.n+"#"+idx].join(", "))}</span>`:""}</div><div class="jp">${brView(hl(m.jp,q))}</div></div>
        <div class="col"><div class="cbtns">${m.kr?'<span class="kr2ko" style="color:#9fd3a8;background:#15201a">⇨ 한글 복사</span>':''}</div><div class="kr">${m.kr?brView(hl(m.kr,q)):''}</div></div>
        <div class="ko"><div class="cbtns"><span class="plain" style="color:#cfe0ff;background:#1d2a3d">대사만 보기</span></div><textarea data-i="${idx}" placeholder="${translatable(m)?'번역 입력':'비워두면 원문 유지'}">${brView(esc(m.ko))}</textarea></div>
      </div>
      <div class="tags" style="margin:6px 0 0">${tags.map(t=>`<span data-t="${esc(t)}">${esc(t)}</span>`).join("")}</div>`;
    L.appendChild(d);
  });
  // 입력창 높이를 내용에 맞춤(스크롤바 없이 전체 표시)
  const fit=t=>{t.style.height="auto";t.style.height=(t.scrollHeight+2)+"px";};
  L.querySelectorAll("textarea").forEach(t=>{fit(t);t.addEventListener("input",()=>fit(t));});
  L.querySelectorAll("textarea").forEach(t=>{
    // 입력창은 <BR> 뒤 줄바꿈으로 표시, 저장값은 줄바꿈 제거. Enter = <BR> 입력
    t.oninput=()=>{const v=t.value.replace(/\r?\n/g,"");b.msgs[t.dataset.i].ko=v;
      t.closest(".msg").classList.toggle("done",v.trim()!=="");
      updProg();renderBlocks();};
    t.onkeydown=e=>{if(e.key!=="Enter"||e.isComposing)return;e.preventDefault();insertAt(t,"<BR>\n");};
  });
  // kr(현재 한글) 전체를 ko 입력창에 복사(기존 입력이 있으면 확인 후 덮어씀)
  L.querySelectorAll(".kr2ko").forEach(s=>{s.onclick=()=>{
    const ta=s.closest(".msg").querySelector("textarea");
    if(ta.value.trim()&&!confirm("입력한 번역을 현재 한글로 덮어쓸까요?"))return;
    ta.value=b.msgs[ta.dataset.i].kr.replace(/<BR>/g,"<BR>\n");ta.dispatchEvent(new Event("input"));ta.focus();};});
  // 대사만 보기: 제어문 뺀 jp/kr/ko 를 팝업으로(데이터는 건드리지 않음)
  L.querySelectorAll(".plain").forEach(s=>{s.onclick=()=>{
    const i=s.closest(".msg").querySelector("textarea").dataset.i,m=b.msgs[i];
    $("#pvT").textContent=`블록 ${b.n} #${i}`;
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
// 표시용 대사 텍스트: 첫 <start> 뒤(패딩) 버림, <BR>=줄바꿈, <name>=〈이름〉, 선택지=▸, 나머지 제어문 제거
function plainText(s){if(s.includes("<start>"))s=s.slice(0,s.indexOf("<start>"));
  return s.replace(/<BR>/g,"\n").replace(/<name>/g,"〈이름〉").replace(/<select:[0-9A-F]+>/g," ▸").replace(tagRe,"");}
$("#pv").onclick=e=>{if(e.target.id==="pv")$("#pv").close();};  // 바깥 클릭 닫기(Esc는 기본 동작)
function updProg(){const{tot,done}=stats();const p=tot?Math.round(done/tot*100):0;
  $("#pbar").style.width=p+"%";$("#pct").textContent=`${done}/${tot} (${p}%) · 검수 ${DATA.blocks.filter(b=>b.reviewed).length}/${DATA.blocks.length}블록`;}
// 불러오기/내보내기로 고른 파일 핸들을 IndexedDB에 보관 → 앱을 다시 열어도 같은 파일·폴더 사용
// (file:// 에서는 picker의 id 폴더 기억이 동작하지 않음)
let saveHandle=null,baseStamp=__GEN__;  // baseStamp = 화면 데이터의 기준 시각(내장 시 script.json 수정 시각)
const idb=(mode,fn)=>new Promise((res,rej)=>{const o=indexedDB.open("mc_review",1);
  o.onupgradeneeded=()=>o.result.createObjectStore("kv");o.onerror=()=>rej(o.error);
  o.onsuccess=()=>{const tx=o.result.transaction("kv",mode),r=fn(tx.objectStore("kv"));tx.oncomplete=()=>res(r.result);tx.onerror=()=>rej(tx.error);};});
const keepHandle=h=>{saveHandle=h;idb("readwrite",s=>s.put(h,"h")).catch(()=>{});};
if(window.indexedDB)idb("readonly",s=>s.get("h")).then(h=>{if(h)saveHandle=h;}).catch(()=>{});
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
$("#q").oninput=renderList;$("#onlyTodo").onchange=renderList;
renderBlocks();renderList();updProg();
</script></body></html>"""

def main():
    data = open(DATA, "r", encoding="utf-8").read()
    spk = open(SPK, encoding="utf-8").read() if os.path.exists(SPK) else "{}"
    gen = str(int(os.path.getmtime(DATA) * 1000))
    html = HTML.replace("__GEN__", gen).replace("__DATA__", data).replace("__SPK__", spk)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("검수 앱 생성: %s (%.1f KB)" % (OUT, len(html)/1024))

if __name__ == "__main__":
    main()
