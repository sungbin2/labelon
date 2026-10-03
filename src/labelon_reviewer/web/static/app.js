// labelon-reviewer 검토 화면 (순수 JS, 빌드 없음). frontend-components.md 참조.

// ------------------------------------------------------------ store
const store = {
  item: null,          // ReviewItem 스냅샷
  config: null,
  serverOffsetMs: 0,   // server_now - client now
  tab: "review",
  focusField: null,    // 편집 중인 필드 (SSE 갱신 시 초안 패널을 다시 그리지 않음)
  pendingItem: null,   // 편집 중 보류된 최신 스냅샷 (blur 후 반영)
  loadedVersion: null, // 처음 받은 server_version
  needReload: false,   // 서버 버전이 바뀌어 새로고침 필요
  composing: false,    // 한글 IME 조합 중
  warned10: null,
  listeners: [],
  set(item) { this.item = item; this.listeners.forEach((f) => f(item)); },
  on(f) { this.listeners.push(f); },
};

// ------------------------------------------------------------ api
const api = {
  async get(path) { const r = await fetch(path); if (!r.ok) throw await err(r); return r.json(); },
  async post(path, body) {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
    if (!r.ok) throw await err(r); return r.json();
  },
  async put(path, body) {
    const r = await fetch(path, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!r.ok) throw await err(r); return r.json();
  },
};
async function err(r) { let d = {}; try { d = await r.json(); } catch {} const e = new Error(d.detail || `HTTP ${r.status}`); e.status = r.status; e.data = d; return e; }

// ------------------------------------------------------------ sse
function connectSSE() {
  const es = new EventSource("/events");
  es.addEventListener("state", (ev) => {
    const data = JSON.parse(ev.data);
    if (data.server_now) store.serverOffsetMs = new Date(data.server_now).getTime() - Date.now();
    // 서버가 새 버전으로 재시작되면 옛 화면 코드를 계속 쓰지 않도록 새로고침 (편집 중이면 칸을 벗어난 뒤)
    if (data.server_version) {
      if (!store.loadedVersion) store.loadedVersion = data.server_version;
      else if (data.server_version !== store.loadedVersion) { store.needReload = true; if (!store.focusField) { location.reload(); return; } }
    }
    store.set(data);
  });
  es.onerror = () => { es.close(); setTimeout(connectSSE, 3000); };
}

// ------------------------------------------------------------ helpers
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const STATE_LABEL = { READY: "준비됨", FETCHING: "가져오는 중", JUDGING: "1단계 판정 중", REVISING: "2단계 수정 중", REVIEW: "검토 대기", SUBMITTING: "제출 중", DONE: "제출 완료", ERROR: "오류", EXPIRED: "제한시간 만료" };
const BUSY = new Set(["FETCHING", "JUDGING", "REVISING", "SUBMITTING"]);
const SELECTABLE = new Set(["READY", "DONE", "ERROR", "EXPIRED"]);
function toast(msg, isError = false) { const t = $("toast"); t.textContent = msg; t.className = "toast" + (isError ? " error" : ""); clearTimeout(t._h); t._h = setTimeout(() => t.classList.add("hidden"), isError ? 6000 : 3500); }
function fieldValue(draft, name) {
  if (!draft) return "";
  if (name === "archetype" || name === "persona" || name === "task") return draft.instruction ? draft.instruction[name] : "";
  if (name === "scene") return draft.scene;
  if (name.startsWith("fact_")) return draft.facts[+name.slice(5) - 1] ?? "";
  if (/^cot[123]$/.test(name)) return draft[name];
  const m = name.match(/^turn_(\d+)_(assistant|user)$/);
  if (m) { const t = (draft.dialogue.turns || []).find((x) => x.turn === +m[1]); return t ? t[m[2]] : ""; }
  return "";
}
function fieldLabel(name) {
  if (name === "archetype" || name === "persona" || name === "task") return `Instruction ${name}`;
  if (name === "scene") return "Scene";
  if (name.startsWith("fact_")) return `Fact ${name.slice(5)}`;
  if (/^cot[123]$/.test(name)) return { cot1: "CoT 1 공간 파악", cot2: "CoT 2 상태·위험", cot3: "CoT 3 행동 계획" }[name];
  let m = name.match(/^turn_(\d+)_assistant$/); if (m) return `대화 ${m[1]}턴 assistant`;
  m = name.match(/^turn_(\d+)_user$/); return m ? `대화 ${m[1]}턴 user (질문)` : name;
}
function subjectParticle(w) { w = (w || "").trim(); if (!w) return "가"; const c = w.charCodeAt(w.length - 1); return c >= 0xAC00 && c <= 0xD7A3 ? ((c - 0xAC00) % 28 ? "이" : "가") : "가"; }
function debounce(fn, ms) { let h; return (...a) => { clearTimeout(h); h = setTimeout(() => fn(...a), ms); }; }

// ------------------------------------------------------------ dialog
function dialog({ title, message, input = false, placeholder = "", defaultValue = "", okLabel = "확인" }) {
  return new Promise((resolve) => {
    $("dialog-title").textContent = title; $("dialog-message").textContent = message;
    const inp = $("dialog-input"); inp.classList.toggle("hidden", !input); inp.value = defaultValue; inp.placeholder = placeholder;
    $("dialog-ok").textContent = okLabel; $("dialog").classList.remove("hidden");
    if (input) setTimeout(() => inp.focus(), 0);
    const done = (v) => { $("dialog").classList.add("hidden"); $("dialog-ok").onclick = $("dialog-cancel").onclick = null; resolve(v); };
    $("dialog-ok").onclick = () => done(input ? inp.value : true);
    $("dialog-cancel").onclick = () => done(null);
  });
}

// ------------------------------------------------------------ renderers
function renderHeader(item) {
  const st = item.state;
  const badge = $("state-badge");
  badge.textContent = item.login_required && st === "READY" ? "로그인을 완료해 주세요" : (STATE_LABEL[st] || st);
  badge.className = "badge " + (st === "REVIEW" ? "review" : BUSY.has(st) ? "busy" : (st === "ERROR" || st === "EXPIRED") ? "error" : "");
  $("file-name").textContent = item.source ? `${item.source.org_file_name}` : "";
  renderDatasets(item);
  $("reopen-browser").classList.toggle("hidden", item.browser_alive !== false);
  const s = item.summary;
  if (s) $("usage").textContent = `오늘 ${s.today_items}건 · 누적 ${s.total_items}건 (승인 제출 기준) · 토큰 입력 ${fmtK(s.tokens.input + s.tokens.cache_read)} / 출력 ${fmtK(s.tokens.output)}`;
  renderBanner(item);
}
function renderDatasets(item) {
  const sel = $("dataset-select"); const list = item.datasets || []; const cur = item.selected_dataset_id;
  const opts = list.map((d) => `<option value="${d.dataset_id}" ${d.dataset_id === cur ? "selected" : ""}>${esc(d.dataset_name)}${d.credit ? ` · ${d.credit}` : ""}</option>`);
  if (!list.some((d) => d.dataset_id === cur) && cur) opts.unshift(`<option value="${cur}" selected>${esc(item.selected_dataset_name || cur)}</option>`);
  if (sel.innerHTML !== opts.join("")) sel.innerHTML = opts.join("");
  sel.disabled = !SELECTABLE.has(item.state) || !!item.login_required; $("dataset-refresh").disabled = BUSY.has(item.state);
  sel.title = item.datasets_error ? item.datasets_error : `진행중 데이터셋 ${list.length}개`;
}
async function selectDataset(id) {
  try { await api.put("/datasets/selected", { dataset_id: +id }); toast("데이터셋을 바꿨습니다"); }
  catch (e) { toast(e.message, true); if (store.item) renderDatasets(store.item); }
}
async function refreshDatasets() { try { const r = await api.post("/datasets/refresh"); toast(r.datasets_error ? r.datasets_error : `진행중 데이터셋 ${r.datasets.length}개`, !!r.datasets_error); } catch (e) { toast(e.message, true); } }
$("dataset-select").addEventListener("change", (e) => selectDataset(e.target.value));
$("dataset-refresh").addEventListener("click", refreshDatasets);

function fmtK(n) { return n >= 1e6 ? (n / 1e6).toFixed(1) + "M" : n >= 1e3 ? (n / 1e3).toFixed(1) + "K" : String(n); }
function renderBanner(item) {
  const b = $("banner"); const msgs = [];
  if (item.login_required) msgs.push("Chrome 창에서 LabelOn 에 직접 로그인해 주세요. 로그인이 확인되면(약 5초 간격) 자동으로 복구됩니다.");
  if (item.datasets_error && !item.login_required) msgs.push("데이터셋 목록: " + item.datasets_error);
  if (item.browser_alive === false) msgs.push("브라우저 창이 닫혔습니다. 오른쪽 위 '브라우저 다시 열기'를 누르세요.");
  if (item.state === "ERROR" && item.error) msgs.push(item.error);
  if (item.state === "EXPIRED") msgs.push("제한시간이 만료되어 이 건은 LabelOn 에 반환되었습니다. 다음 건을 가져오세요.");
  if (item.state === "DONE" && item.submission) msgs.push(`제출 완료: ${item.submission.response_message || ""}`);
  b.classList.toggle("hidden", msgs.length === 0); b.className = "banner" + (item.state === "ERROR" ? " error" : ""); b.textContent = msgs.join(" ");
}

function renderImage(item) {
  const img = $("source-image"), ph = $("image-placeholder");
  if (item.item_id && item.image_paths) { img.src = `/images/${item.item_id}?t=${item.item_id}`; img.classList.remove("hidden"); ph.classList.add("hidden"); }
  else { img.classList.add("hidden"); ph.classList.remove("hidden"); ph.textContent = BUSY.has(item.state) ? "이미지 준비 중..." : "건을 가져오면 이미지가 표시됩니다"; }
}
function renderMeta(item) {
  const s = item.source;
  $("meta-panel").innerHTML = s ? `<h4>메타</h4><div class="kv"><span>데이터셋</span><span><span class="tag ds">${esc(s.dataset_name || s.dataset_id)}</span></span><span>파일</span><span>${esc(s.org_file_name)}</span><span>category</span><span>${esc(s.category)}</span><span>weather</span><span>${esc(s.weather)}</span><span>detected</span><span>${esc(s.detected_object)}</span><span>job id</span><span>${s.job_id}</span></div>` : "<h4>메타</h4><span class='muted'>-</span>";
  $("qa-panel").innerHTML = "<h4>연관 QA</h4>" + (s && s.related_qa.length ? s.related_qa.map((q) => `<div class="qa-item"><div>Q. ${esc(q.question)}</div><div class="muted">A. ${esc(q.answer)}</div></div>`).join("") : "<span class='muted'>-</span>");
}
function renderInstruction(item) {
  // 사이클 7: archetype(select) · persona(input) · task(textarea) 를 사람이 편집. 모델 정정안 위에 다시 고칠 수 있다
  const d = item.draft, ic = item.judge && item.judge.instruction_check;
  const panel = $("instruction-panel");
  if (!d) { panel.innerHTML = "<h4>Instruction</h4><span class='muted'>-</span>"; return; }
  const warn = ic && !(ic.archetype_known && ic.task_matches_template && ic.persona_matches_config);
  const f = (item.final && item.final.instruction) || d.instruction;
  const editable = item.state === "REVIEW";
  const dis = editable ? "" : "disabled";
  const changedKeys = ["archetype", "persona", "task"].filter((k) => f[k] !== d.instruction[k]);
  const archetypes = (store.config && store.config.archetypes) || [];
  const opts = [...new Set([...archetypes, f.archetype])].filter(Boolean).map((a) => `<option value="${esc(a)}" ${a === f.archetype ? "selected" : ""}>${esc(a)}</option>`).join("");
  const row = (k, ctrl) => `<span>${k}${changedKeys.includes(k) ? ' <span class="tag changed">변경됨</span>' + revertBtn(k, editable) : ""}</span>
    <span>${changedKeys.includes(k) ? `<div class="diff"><span class="del">${esc(d.instruction[k])}</span></div>` : ""}${ctrl}</span>`;
  panel.innerHTML = `<h4>Instruction ${changedKeys.length ? '<span class="tag changed">수정됨</span>' : ""} ${warn ? '<span class="tag false">템플릿 불일치</span>' : ic ? '<span class="tag true">템플릿 일치</span>' : ""}</h4>
    <div class="kv ins-edit" data-testid="instruction-edit">
      ${row("archetype", `<select data-field="archetype" class="ins-ctl" data-testid="instruction-archetype" ${dis}>${opts}</select>`)}
      ${row("persona", `<input type="text" data-field="persona" class="ins-ctl" data-testid="instruction-persona" value="${esc(f.persona)}" ${dis}>`)}
      ${row("task", `<textarea data-field="task" class="ins-ctl" data-testid="instruction-task" ${dis}>${esc(f.task)}</textarea>
        <button id="btn-fill-task" class="btn small" data-testid="instruction-fill-task" ${dis} title="선택한 아키타입 템플릿에 페르소나와 조사를 넣어 Task 를 채웁니다">템플릿으로 Task 채우기</button>`)}
    </div>
    ${warn ? `<div class="alert warn">${ic.mismatch_details.map(esc).join("<br>")}</div>` : ""}`;
  panel.querySelectorAll("[data-field]").forEach(bindEditable);
  panel.querySelectorAll("[data-revert]").forEach(bindRevert);
  const sel = panel.querySelector('select[data-field="archetype"]');
  if (sel) sel.addEventListener("change", () => saveEdit("archetype", sel.value));
  const fill = $("btn-fill-task");
  if (fill) fill.onclick = () => {
    const tpl = (store.config && store.config.archetype_templates && store.config.archetype_templates[sel ? sel.value : f.archetype]) || "";
    if (!tpl) { toast("이 아키타입의 템플릿이 없습니다", true); return; }
    const persona = (panel.querySelector('input[data-field="persona"]') || {}).value || f.persona;
    const task = tpl.replace("(Persona)", persona.trim() + subjectParticle(persona));
    const ta = panel.querySelector('textarea[data-field="task"]'); if (ta) ta.value = task;
    saveEdit("task", task);
  };
}
function bindEditable(el) {
  // textarea/input 공통: 지연 저장, IME 조합 보호, blur 즉시 저장 (사이클 6·7)
  const delay = (store.config && store.config.edit_delay_ms) || 1500;
  const scheduled = debounce(() => { if (!store.composing) saveEdit(el.dataset.field, el.value); }, delay);
  el.addEventListener("focus", () => (store.focusField = el.dataset.field));
  el.addEventListener("compositionstart", () => (store.composing = true));
  el.addEventListener("compositionend", () => { store.composing = false; scheduled(); });
  if (el.tagName !== "SELECT") el.addEventListener("input", scheduled);
  el.addEventListener("blur", async () => {
    if (store.focusField !== el.dataset.field) return;
    store.focusField = null; store.composing = false;
    const base = store.item ? fieldValue(store.item.final, el.dataset.field) : null;
    if (base !== null && base !== el.value) await saveEdit(el.dataset.field, el.value); // 즉시 저장
    if (store.needReload) { location.reload(); return; }
    if (store.pendingItem && !store.focusField) { const it = store.pendingItem; store.pendingItem = null; renderEditable(it); }
  });
}
function renderEditable(item) { renderInstruction(item); renderDraft(item); }

function renderDraft(item) {
  const panel = $("draft-panel");
  if (!item.draft || !item.final) { panel.innerHTML = "<div class='card'><span class='muted'>검토할 건이 없습니다. '다음 건 가져오기'를 누르세요.</span></div>"; return; }
  const editable = item.state === "REVIEW";
  const diffs = Object.fromEntries((item.diffs || []).map((d) => [d.field, d]));
  const verdictByFact = Object.fromEntries((item.judge ? item.judge.fact_verdicts : []).map((v) => [`fact_${v.index + 1}`, v]));
  const fieldVerdict = Object.fromEntries((item.judge ? item.judge.field_verdicts : []).map((v) => [v.field, v]));
  const names = ["scene", ...item.draft.facts.map((_, i) => `fact_${i + 1}`), "cot1", "cot2", "cot3"];
  const turns = item.draft.dialogue.turns || [];
  const finalTurns = (item.final.dialogue.turns || []).filter((t) => t.user || t.assistant);
  const html = [];
  for (const name of names) html.push(fieldHTML(name, item, diffs[name], verdictByFact[name], fieldVerdict[name], editable));
  html.push(`<div class="card"><h4>대화 (context 는 읽기 전용)</h4><div class="kv"><span>user_type</span><span>${esc(item.draft.dialogue.context.user_type)}</span><span>situation</span><span>${esc(item.draft.dialogue.context.situation)}</span><span>priority</span><span class="muted">${esc(item.draft.dialogue.context.priority)}</span></div></div>`);
  const activeDraft = turns.filter((t) => t.user || t.assistant);
  if (finalTurns.length < activeDraft.length) {
    // 삭제·병합된 턴이 있음: 최종안 턴을 먼저, 그다음 삭제 표시
    for (const t of finalTurns) html.push(turnHTML(t.turn, item, diffs, fieldVerdict, editable));
    for (const t of activeDraft.slice(finalTurns.length)) html.push(`<div class="field" data-testid="draft-field-dropped-turn-${t.turn}"><div class="field-head"><span class="label">대화 ${t.turn}턴</span><span class="tag false">삭제됨</span></div><div class="diff"><span class="del">user: ${esc(t.user)}</span><br><span class="del">assistant: ${esc(t.assistant)}</span></div></div>`);
  } else {
    for (const t of turns) {
      const empty = !(t.user || t.assistant);
      const name = `turn_${t.turn}_assistant`;
      if (empty) { html.push(`<div class="field"><div class="field-head"><span class="label">대화 ${t.turn}턴</span><span class="tag">비어 있음 (유지)</span></div></div>`); continue; }
      html.push(turnHTML(t.turn, item, diffs, fieldVerdict, editable));
    }
  }
  for (let n = Math.max(turns.length, finalTurns.length) + 1; n <= 6; n++) html.push(`<div class="field"><div class="field-head"><span class="label">대화 ${n}턴</span><span class="tag">비어 있음 (유지)</span></div></div>`);
  panel.innerHTML = html.join("");
  panel.querySelectorAll("textarea[data-field]").forEach(bindEditable);
  panel.querySelectorAll("[data-revert]").forEach(bindRevert);
}
function revertBtn(field, editable) {
  return editable ? ` <button type="button" class="btn tiny" data-revert="${esc(field)}" data-testid="revert-${esc(field)}" title="이 항목만 서버 초안 값으로 되돌립니다">초안으로</button>` : "";
}
function bindRevert(btn) {
  btn.addEventListener("mousedown", (e) => e.preventDefault()); // 편집 중 blur 로 저장이 먼저 일어나지 않게
  btn.addEventListener("click", async () => {
    try { await api.post("/actions/revert-field", { field: btn.dataset.revert }); toast(`${fieldLabel(btn.dataset.revert)} 를 초안으로 되돌렸습니다`); } catch (e) { toast(e.message, true); }
  });
}
function turnHTML(n, item, diffs, fieldVerdict, editable) {
  // 사이클 6: user(질문)·assistant 모두 편집 가능. 한 카드 안에 두 textarea
  const u = `turn_${n}_user`, a = `turn_${n}_assistant`;
  const uBase = fieldValue(item.draft, u), uCur = fieldValue(item.final, u);
  const uChanged = diffs[u] ? diffs[u].changed : uBase !== uCur;
  const uDiff = uChanged && diffs[u] ? `<div class="diff">${diffs[u].segments.map(segHTML).join("")}</div>` : "";
  const userBlock = `<div class="turn-user-edit" id="field-${u}" data-testid="draft-field-${u}"><div class="field-head"><span class="label">${fieldLabel(u)}</span><span>${uChanged ? '<span class="tag changed">변경됨</span>' + revertBtn(u, editable) : ""}</span></div>${uDiff}
    <textarea class="user" data-field="${u}" ${editable ? "" : "disabled"} data-testid="draft-textarea-${u}">${esc(uCur)}</textarea></div>`;
  return fieldHTML(a, item, diffs[a], null, fieldVerdict[`turn_${n}`], editable, undefined, userBlock);
}
function fieldHTML(name, item, diff, factVerdict, fieldVerdict, editable, userText, prefixHtml = "") {
  const base = fieldValue(item.draft, name), cur = fieldValue(item.final, name);
  const changed = diff ? diff.changed : base !== cur;
  let tags = "";
  if (changed) tags += '<span class="tag changed">변경됨</span>' + revertBtn(name, editable);
  if (factVerdict) tags += `<span class="tag ${factVerdict.verdict.toLowerCase()}">${factVerdict.verdict}</span>`;
  if (fieldVerdict) tags += `<span class="tag ${fieldVerdict.consistent ? "true" : "false"}">${fieldVerdict.consistent ? "정합" : "불일치"}</span>`;
  const diffHtml = changed && diff ? `<div class="diff">${diff.segments.map(segHTML).join("")}</div>` : "";
  const evidence = factVerdict && factVerdict.evidence ? `<div class="evidence">근거: ${esc(factVerdict.evidence)}</div>` : fieldVerdict && !fieldVerdict.consistent && fieldVerdict.note ? `<div class="evidence">메모: ${esc(fieldVerdict.note)}</div>` : "";
  return `<div class="field" id="field-${name}" data-testid="draft-field-${name}"><div class="field-head"><span class="label">${fieldLabel(name)}</span><span>${tags}</span></div>
    ${prefixHtml}${userText !== undefined ? `<div class="turn-user">user: ${esc(userText)}</div>` : ""}${diffHtml}
    <textarea data-field="${name}" ${editable ? "" : "disabled"} data-testid="draft-textarea-${name}">${esc(cur)}</textarea>${evidence}</div>`;
}
function segHTML(s) {
  if (s.op === "EQUAL") return esc(s.base_text) + " ";
  if (s.op === "DELETE") return `<span class="del">${esc(s.base_text)}</span>`;
  if (s.op === "INSERT") return `<span class="ins">${esc(s.other_text)}</span>`;
  return `<span class="del">${esc(s.base_text)}</span><span class="ins">${esc(s.other_text)}</span>`;
}
async function saveEdit(field, value) {
  try { await api.put("/draft", { field, value }); } catch (e) { toast(e.message, true); }
}

const TEXT_KIND = { typo: "오탈자", speculation: "추측", number: "숫자 표기", direction: "방향" };

function renderJudge(item) {
  const j = item.judge, p = $("judge-panel");
  if (!j) { p.innerHTML = `<h4>판정</h4><span class="muted">${BUSY.has(item.state) ? "판정 중..." : item.state === "REVIEW" ? "판정 결과 없음 (모델 오류 → 초안 그대로 검토)" : "-"}</span>`; return; }
  const th = store.config ? store.config.threshold : 40;
  const low = j.consistency_score <= th;
  p.innerHTML = `<h4>정합성 점수</h4><div class="score">${j.consistency_score} <span class="muted" style="font-size:14px">/ 100 (임계값 ${th})</span></div>
    <div class="score-bar ${low ? "low" : ""}"><div style="width:${j.consistency_score}%"></div></div>
    ${j.impossible_candidate ? `<div class="alert">불가 후보입니다.<br>${(j.impossible_reasons || []).map((r) => `• ${esc(r)}`).join("<br>")}<br>사진에 없는 것: ${esc(j.missing_in_image.join(", ") || "-")}<br>제안 사유: ${esc(j.impossible_reason_suggestion || "-")}</div>` : ""}
    ${j.archetype_suggestion && !j.archetype_suggestion.fits && j.archetype_suggestion.suggested ? `<div class="alert warn">아키타입 정정 제안: ${esc(item.draft.instruction.archetype)} → <b>${esc(j.archetype_suggestion.suggested)}</b> — ${esc(j.archetype_suggestion.reason)}</div>` : ""}
    ${j.qa_matches_cot3 === false ? '<div class="alert warn">대화가 CoT 3단계와 맞지 않습니다</div>' : ""}
    ${(j.phone_numbers || []).length ? `<div class="alert warn">전화번호 발견(삭제 대상): ${esc(j.phone_numbers.join(", "))}</div>` : ""}
    ${j.archetype_fits_environment === false ? `<div class="alert"><span class="tag false">환경 부적합</span> 아키타입이 사진 환경과 맞지 않습니다${j.environment_note ? " — " + esc(j.environment_note) : ""}</div>` : ""}
    ${(j.text_issues || []).length ? `<div class="alert warn">텍스트 오류 ${j.text_issues.length}건<br>${j.text_issues.map((t) => `• <span data-jump="${esc(t.field)}" class="link">${esc(t.field)}</span> <span class="tag ${esc(t.kind)}">${TEXT_KIND[t.kind] || esc(t.kind)}</span> '${esc(t.wrong)}' → '${esc(t.correct)}'`).join("<br>")}</div>` : ""}
    ${j.needs_revision ? '<div class="alert warn">수정안이 생성되었습니다. diff 를 확인하세요.</div>' : '<div class="muted">모델 수정 없음</div>'}
    <h4 style="margin-top:12px">Facts 판정</h4>${j.fact_verdicts.map((v) => `<div class="verdict-row" data-jump="fact_${v.index + 1}"><span class="idx">${v.index + 1}</span><span class="tag ${v.verdict.toLowerCase()}">${v.verdict}</span><span>${esc(v.evidence)}</span></div>`).join("")}
    <h4 style="margin-top:12px">필드 정합</h4><div class="field-grid">${j.field_verdicts.map((v) => `<span data-jump="${v.field.replace(/^turn_(\d+)$/, "turn_$1_assistant")}" class="verdict-row"><span>${esc(v.field)}${v.role_fits === false ? ' <span class="tag false">역할</span>' : ""}${v.beyond_cot3 ? ' <span class="tag false">CoT3 밖</span>' : ""}</span><span class="${v.consistent ? "ok" : "ng"}">${v.consistent ? "O" : "X"}</span></span>`).join("")}</div>
    ${!(j.persona_task_fit.cot_fits && j.persona_task_fit.dialogue_fits) ? `<div class="alert warn">페르소나·태스크 적합성: CoT ${j.persona_task_fit.cot_fits ? "O" : "X"}, 대화 ${j.persona_task_fit.dialogue_fits ? "O" : "X"} — ${esc(j.persona_task_fit.note)}</div>` : ""}
    ${j.model_usage ? `<div class="muted" style="margin-top:8px">judge: ${j.model_usage.model}, ${(j.model_usage.latency_ms / 1000).toFixed(1)}s, 출력 ${j.model_usage.output_tokens} 토큰</div>` : ""}`;
  p.querySelectorAll("[data-jump]").forEach((el) => el.addEventListener("click", () => { const f = $("field-" + el.dataset.jump); if (f) { f.scrollIntoView({ behavior: "smooth", block: "center" }); f.querySelector("textarea")?.focus(); } }));
}
function renderWarnings(item) {
  const w = $("warnings-panel"); const list = item.warnings || [];
  w.classList.toggle("hidden", list.length === 0);
  w.innerHTML = "<h4>경고</h4>" + list.map((x) => `<div class="alert warn">${esc(x)}</div>`).join("");
}
function renderProgress(item) {
  const p = $("progress-panel"); const busy = BUSY.has(item.state);
  p.classList.toggle("hidden", !busy);
  if (busy) { const started = new Date(item.stage_started_at).getTime(); p.innerHTML = `<h4>진행</h4><div>${STATE_LABEL[item.state]}... <span id="elapsed" class="muted"></span></div>`; p._started = started; }
}
function renderActions(item) {
  const st = item.state, review = st === "REVIEW";
  // 사이클 7: 로그인 필요 상태여도 눌러 볼 수 있다(서버가 로그인 페이지를 만나면 안내하고, 재로그인은 자동 감지)
  const canFetch = ["READY", "DONE", "ERROR", "EXPIRED"].includes(st) && item.browser_alive !== false;
  $("btn-fetch").disabled = !canFetch;
  $("btn-revert").disabled = !review || !(item.final && item.final.edited_by_user || (item.diffs || []).some((d) => d.changed));
  $("btn-reanalyze").disabled = !review; $("btn-skip").disabled = !review; $("btn-impossible").disabled = !review;
  const problems = review ? validate(item.final) : ["-"];
  $("btn-approve").disabled = !review || problems.length > 0; $("btn-approve").title = problems.length ? problems.join("\n") : "Alt+A";
}
function validate(final) {
  if (!final) return ["초안 없음"]; const p = [];
  ["archetype", "persona", "task"].forEach((k) => { if (!(final.instruction && final.instruction[k] || "").trim()) p.push(`Instruction ${k} 이 비어 있습니다`); });
  if (!final.scene.trim()) p.push("Scene 이 비어 있습니다");
  final.facts.forEach((f, i) => { if (!f.trim()) p.push(`Fact ${i + 1} 이 비어 있습니다`); });
  ["cot1", "cot2", "cot3"].forEach((n) => { if (!final[n].trim()) p.push(`${n} 이 비어 있습니다`); });
  (final.dialogue.turns || []).forEach((t) => {
    if (t.user.trim() && !t.assistant.trim()) p.push(`대화 ${t.turn}턴 assistant 가 비어 있습니다`);
    if (t.assistant.trim() && !t.user.trim()) p.push(`대화 ${t.turn}턴 user 가 비어 있습니다`);
  });
  const draft = store.item && store.item.draft;
  if (draft) (draft.dialogue.turns || []).filter((t) => t.user || t.assistant).forEach((ot) => {
    const ft = (final.dialogue.turns || []).find((x) => x.turn === ot.turn);
    if (!ft || !(ft.user.trim() || ft.assistant.trim())) p.push(`대화 ${ot.turn}턴을 삭제할 수 없습니다 (내용을 수정하세요)`);
  });
  return p;
}

function renderAll(item) {
  renderHeader(item); renderImage(item); renderMeta(item);
  if (store.focusField && document.querySelector(`[data-field="${store.focusField}"]`)) {
    store.pendingItem = item; // 편집 중: Instruction·초안 패널은 다시 그리지 않는다 (DOM 교체가 한글 조합을 끊음). blur 후 반영
  } else { store.pendingItem = null; renderEditable(item); }
  renderJudge(item); renderWarnings(item); renderProgress(item); renderActions(item);
}

// ------------------------------------------------------------ countdown
setInterval(() => {
  const item = store.item; const el = $("countdown");
  if (!item || !item.deadline || !["JUDGING", "REVISING", "REVIEW"].includes(item.state)) { el.textContent = ""; el.className = "countdown"; return; }
  const rem = Math.floor((new Date(item.deadline).getTime() - (Date.now() + store.serverOffsetMs)) / 1000);
  const m = Math.max(0, Math.floor(rem / 60)), s = Math.max(0, rem % 60);
  el.textContent = `남은 시간 ${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  el.className = "countdown" + (rem < 600 ? " warn" : "");
  if (rem < 600 && store.warned10 !== item.item_id) { store.warned10 = item.item_id; toast("남은 제한시간이 10분 미만입니다", true); }
  const p = $("progress-panel"); if (!p.classList.contains("hidden") && p._started) { const e = $("elapsed"); if (e) e.textContent = `${Math.floor((Date.now() - p._started) / 1000)}초 경과`; }
}, 1000);

// ------------------------------------------------------------ actions
async function doFetch() { if ($("btn-fetch").disabled) return; try { await api.post("/actions/fetch"); } catch (e) { toast(e.message, true); } }
async function doApprove() {
  if ($("btn-approve").disabled) return;
  const it = store.item; const notes = [];
  if (it && it.final && it.draft) { const ks = ["archetype", "persona", "task"].filter((k) => it.final.instruction[k] !== it.draft.instruction[k]); if (ks.length) notes.push(`Instruction(${ks.join(", ")})이 수정된 값으로 제출됩니다.`); }
  if (it && it.final && it.draft) { const a = (it.draft.dialogue.turns || []).filter((t) => t.user || t.assistant).length, b = (it.final.dialogue.turns || []).filter((t) => t.user || t.assistant).length; if (b < a) notes.push(`대화 턴이 ${a}개 → ${b}개로 줄어듭니다(삭제된 턴은 빈 값으로 제출).`); }
  const ok = await dialog({ title: "승인·제출", message: "현재 화면의 내용으로 LabelOn 에 제출합니다. 계속할까요?" + (notes.length ? "\n\n" + notes.join("\n") : ""), okLabel: "제출" });
  if (!ok) return;
  try { const r = await api.post("/actions/approve"); toast(r.submission && r.submission.success ? "제출 완료" : "제출 실패: " + (r.submission?.error || ""), !(r.submission && r.submission.success)); } catch (e) { toast(e.message, true); }
}
async function doImpossible() {
  if ($("btn-impossible").disabled) return;
  const j = store.item?.judge; const def = j && j.impossible_candidate ? j.impossible_reason_suggestion : "";
  const reason = await dialog({ title: "불가 제출", message: "이 건을 작업 불가로 제출합니다. 사유는 비워 둘 수 있습니다.", input: true, defaultValue: def, placeholder: "선택: 예) 이미지와 초안의 장면이 전혀 다름", okLabel: "불가 제출" });
  if (reason === null) return;
  try { await api.post("/actions/impossible", { reason }); toast("불가 제출 완료"); } catch (e) { toast(e.message, true); }
}
async function doReanalyze() {
  if ($("btn-reanalyze").disabled) return;
  const ok = await dialog({ title: "다시 판독", message: "현재 건의 사진과 서버 초안으로 판정·수정을 다시 실행합니다. 지금까지 직접 고친 내용은 사라집니다. 계속할까요?", okLabel: "다시 판독" });
  if (!ok) return;
  try { await api.post("/actions/reanalyze"); } catch (e) { toast(e.message, true); }
}
async function doSkip() {
  if ($("btn-skip").disabled) return;
  const ok = await dialog({ title: "반환", message: "이 건을 제출하지 않고 LabelOn 에 반환합니다. 계속할까요?", okLabel: "반환" });
  if (!ok) return;
  try { await api.post("/actions/skip"); toast("반환했습니다"); } catch (e) { toast(e.message, true); }
}
async function doRevert() {
  if ($("btn-revert").disabled) return;
  const ok = await dialog({ title: "초안으로 되돌리기", message: "모든 필드를 서버 초안 값으로 되돌립니다.", okLabel: "되돌리기" });
  if (!ok) return;
  try { await api.post("/actions/revert"); } catch (e) { toast(e.message, true); }
}
async function doReopen() { try { await api.post("/actions/reopen-browser"); toast("브라우저를 다시 열었습니다"); } catch (e) { toast(e.message, true); } }
async function doShutdown() { const ok = await dialog({ title: "종료", message: "서버와 Chrome 창을 종료합니다. 검토 중인 건은 제출되지 않습니다.", okLabel: "종료" }); if (!ok) return; try { await api.post("/actions/shutdown"); toast("종료 중..."); } catch (e) { toast(e.message, true); } }

$("btn-fetch").onclick = doFetch; $("btn-approve").onclick = doApprove; $("btn-impossible").onclick = doImpossible;
$("btn-skip").onclick = doSkip; $("btn-reanalyze").onclick = doReanalyze; $("btn-revert").onclick = doRevert; $("reopen-browser").onclick = doReopen; $("shutdown").onclick = doShutdown;
document.addEventListener("keydown", (e) => {
  if (!e.altKey) return; const k = e.key.toLowerCase();
  if (k === "n") { e.preventDefault(); doFetch(); } else if (k === "a") { e.preventDefault(); doApprove(); } else if (k === "x") { e.preventDefault(); doImpossible(); }
  else if (k === "s") { e.preventDefault(); doReanalyze(); } else if (k === "r") { e.preventDefault(); doRevert(); }
});

// ------------------------------------------------------------ lightbox (확대·휠 줌)
let zoom = 1;
$("source-image").onclick = () => { $("lightbox-img").src = $("source-image").src; zoom = 1; $("lightbox-img").style.transform = ""; $("lightbox").classList.remove("hidden"); };
$("lightbox").onclick = () => $("lightbox").classList.add("hidden");
$("lightbox").addEventListener("wheel", (e) => { e.preventDefault(); zoom = Math.min(6, Math.max(1, zoom * (e.deltaY < 0 ? 1.15 : 0.87))); $("lightbox-img").style.transform = `scale(${zoom})`; }, { passive: false });

// ------------------------------------------------------------ tabs & history
document.querySelectorAll(".tab").forEach((b) => b.addEventListener("click", () => switchTab(b.dataset.tab)));
function switchTab(tab) {
  store.tab = tab; document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === tab));
  $("review-view").classList.toggle("hidden", tab !== "review"); $("action-bar").classList.toggle("hidden", tab !== "review");
  $("history-view").classList.toggle("hidden", tab !== "history");
  if (tab === "history") loadHistory();
}
async function loadHistory() {
  try {
    const [s, h] = await Promise.all([api.get("/history/summary"), api.get("/history")]);
    const bk = s.by_kind_today || {}, bt = s.by_kind || {};
    $("history-summary").innerHTML = `<div class="summary-cards">
      <div class="stat">오늘<b>${s.today_items}건</b><span class="muted">승인 제출 기준 · 불가 ${bk.IMPOSSIBLE || 0} · 반환 ${bk.SKIP || 0}</span></div>
      <div class="stat">누적<b>${s.total_items}건</b><span class="muted">승인 제출 기준 · 불가 ${bt.IMPOSSIBLE || 0} · 반환 ${bt.SKIP || 0} · 만료 ${s.expired} · 미완료 ${s.unfinished ?? 0} · 가져옴 ${s.fetched_items ?? 0}</span></div>
      <div class="stat">모델 호출<b>${s.model_calls}</b><span class="muted">입력 ${fmtK(s.tokens.input + s.tokens.cache_read)} · 출력 ${fmtK(s.tokens.output)} · 추정 $${s.cost_usd_estimate}</span></div></div>`;
    const unf = h.unfinished || [];
    const bd = s.by_dataset || {};
    const dsCards = Object.values(bd).map((d) => `<div class="stat">${esc(d.name)}<b>${d.total}건</b><span class="muted">제출 ${d.APPROVE || 0} · 불가 ${d.IMPOSSIBLE || 0} · 건너뜀 ${d.SKIP || 0} · 가져옴 ${d.fetched ?? 0}</span></div>`).join("");
    if (dsCards) $("history-summary").innerHTML += `<div class="summary-cards" style="margin-top:10px">${dsCards}</div>`;
    const rows = h.items.map((r) => `<tr class="row" data-id="${r.id}"><td>${esc((r.fetched_at || "").slice(11, 16))}</td><td>${esc((r.dataset_name || r.dataset_id || "").toString().replace(/^\[[^\]]*\]\s*/, ""))}</td><td>${esc(r.org_file_name)}</td><td>${esc(r.last_kind || r.state)}${unf.some((u) => u.id === r.id) ? ' <span class="tag false">미완료</span>' : ""}</td><td>${r.score ?? "-"}</td></tr>`).join("");
    $("history-list").innerHTML = `<table class="hist"><thead><tr><th>시각</th><th>데이터셋</th><th>파일명</th><th>결과</th><th>점수</th></tr></thead><tbody>${rows}</tbody></table>`;
    $("history-list").querySelectorAll("tr.row").forEach((tr) => tr.addEventListener("click", () => { $("history-list").querySelectorAll("tr").forEach((x) => x.classList.remove("selected")); tr.classList.add("selected"); loadDetail(+tr.dataset.id); }));
  } catch (e) { toast(e.message, true); }
}
async function loadDetail(id) {
  try {
    const d = await api.get(`/history/${id}`);
    const tabs = { judge: d.judge, revised: d.revised, final: { final: d.final, submissions: d.submissions, usage: d.usage }, source: { draft: d.draft, related_qa: d.related_qa, state: d.state, state_note: d.state_note } };
    const render = (k) => { $("history-detail").innerHTML = `<div class="detail-tabs">${Object.keys(tabs).map((t) => `<button data-t="${t}" class="${t === k ? "active" : ""}">${{ judge: "판정", revised: "수정안", final: "최종·제출", source: "원본" }[t]}</button>`).join("")}</div>
      ${d.file_name ? `<img src="/images/${id}" style="max-width:100%;border-radius:6px;margin-bottom:8px" onerror="this.remove()">` : ""}<pre class="json">${esc(JSON.stringify(tabs[k], null, 2))}</pre>`;
      $("history-detail").querySelectorAll("button[data-t]").forEach((b) => b.addEventListener("click", () => render(b.dataset.t))); };
    render("judge");
  } catch (e) { toast(e.message, true); }
}

// ------------------------------------------------------------ boot
store.on(renderAll);
(async () => {
  try { store.config = await api.get("/config"); } catch {}
  try { const s = await api.get("/state"); if (s.server_now) store.serverOffsetMs = new Date(s.server_now).getTime() - Date.now(); store.set(s); } catch (e) { toast(e.message, true); }
  connectSSE();
})();
